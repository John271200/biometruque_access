"""Authentification biométrique : 3 captures du visage + 3 de l'oreille, fusion et décision."""

import time
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.audit import journaliser
from app.biometrie import ErreurIntegrite, ParametresDecision, biohash, decider, similarite_hamming
from app.captures import EntreeSession, GestionnaireSessions, info_session, lire_image_jpeg
from app.config import Settings
from app.db import maintenant
from app.dependances import (
    adresse_ip, obtenir_bdd, obtenir_chiffreur, obtenir_moteur, obtenir_sessions, obtenir_settings,
)
from app.erreurs import ErreurAPI
from app.gabarits import charger_references
from app.modeles import Tentative, Utilisateur
from app.schemas import DemandeAuthentification, iso, masquer_nombres, verrou_actif
from app.securite import creer_jeton

router = APIRouter(tags=["authentification"])

NB_CAPTURES = 3
SEUIL_VERROUILLAGE = 5
DUREE_VERROUILLAGE = timedelta(minutes=15)


def _non_enrole() -> ErreurAPI:
    return ErreurAPI(404, "COMPTE_NON_ENROLE", "Aucun compte enrôlé ne correspond à cette adresse.")


def _verrouille(utilisateur: Utilisateur) -> ErreurAPI:
    fin = utilisateur.verrouille_jusqua
    return ErreurAPI(
        423, "COMPTE_VERROUILLE",
        f"Compte verrouillé après {SEUIL_VERROUILLAGE} échecs consécutifs. Réessayez après "
        f"{fin.strftime('%H:%M')} (UTC).",
        verrouille_jusqua=iso(fin),
    )


def _lever_verrou_echu(utilisateur: Utilisateur) -> None:
    """Un verrouillage arrivé à échéance remet le compteur d'échecs à zéro."""
    if utilisateur.verrouille_jusqua and utilisateur.verrouille_jusqua <= maintenant():
        utilisateur.verrouille_jusqua = None
        utilisateur.echecs_consecutifs = 0


def _comptabiliser(bdd: Session, utilisateur: Utilisateur, accepte: bool) -> None:
    """Met à jour le compteur d'échecs : 5 échecs consécutifs verrouillent 15 minutes."""
    if accepte:
        utilisateur.echecs_consecutifs = 0
        utilisateur.verrouille_jusqua = None
        return
    _lever_verrou_echu(utilisateur)
    utilisateur.echecs_consecutifs += 1
    if utilisateur.echecs_consecutifs >= SEUIL_VERROUILLAGE and not verrou_actif(utilisateur):
        utilisateur.verrouille_jusqua = maintenant() + DUREE_VERROUILLAGE
        journaliser(bdd, "COMPTE_VERROUILLE", utilisateur.id,
                    jusqua=iso(utilisateur.verrouille_jusqua))


@router.post("/authentification/sessions", status_code=201)
def creer_session(
    corps: DemandeAuthentification,
    moteur=Depends(obtenir_moteur),
    bdd: Session = Depends(obtenir_bdd),
    sessions: GestionnaireSessions = Depends(obtenir_sessions),
) -> dict:
    """Ouvre une session d'authentification pour le compte revendiqué (email)."""
    utilisateur = bdd.scalar(select(Utilisateur).where(Utilisateur.email == corps.email))
    if utilisateur is None or utilisateur.enrolement_etat != "ENROLE":
        raise _non_enrole()
    _lever_verrou_echu(utilisateur)
    bdd.commit()
    if verrou_actif(utilisateur):
        raise _verrouille(utilisateur)
    session = moteur.nouvelle_session("authentification", NB_CAPTURES, NB_CAPTURES,
                                      cote_attendu=utilisateur.cote_oreille)
    sessions.ajouter(session, "authentification", utilisateur.id, utilisateur.email)
    return info_session(session.id, NB_CAPTURES, NB_CAPTURES, utilisateur.cote_oreille,
                        sessions.duree_inactivite)


def _echec_capture(bdd: Session, entree: EntreeSession, raison: str | None, ip: str | None) -> None:
    """Session passée en échec (vivacité, identité incohérente…) : compte comme un échec."""
    utilisateur = bdd.get(Utilisateur, entree.utilisateur_id)
    raison = raison or "Capture biométrique interrompue."
    bdd.add(Tentative(
        utilisateur_id=utilisateur.id if utilisateur else None,
        email_revendique=entree.email,
        accepte=False,
        raison=raison,
        ip=ip,
    ))
    if utilisateur is not None:
        _comptabiliser(bdd, utilisateur, accepte=False)
    journaliser(bdd, "AUTHENTIFICATION_ECHEC_CAPTURE", entree.utilisateur_id, raison=raison)
    bdd.commit()


def _decider(bdd: Session, settings: Settings, chiffreur, entree: EntreeSession,
             debut: float, ip: str | None) -> dict:
    """Compare les captures aux gabarits, décide, journalise et émet le jeton d'accès."""
    utilisateur = bdd.get(Utilisateur, entree.utilisateur_id)
    if utilisateur is None or utilisateur.enrolement_etat != "ENROLE":
        raise _non_enrole()
    if verrou_actif(utilisateur):
        raise _verrouille(utilisateur)
    try:
        references = charger_references(bdd, chiffreur, utilisateur.id)
    except ErreurIntegrite:
        journaliser(bdd, "GABARIT_CORROMPU", utilisateur.id)
        bdd.commit()
        raise ErreurAPI(
            500, "GABARIT_CORROMPU",
            "Vos gabarits biométriques sont illisibles (contrôle d'intégrité en échec). Accès "
            "refusé : révoquez-les depuis votre espace puis enrôlez-vous à nouveau.",
        ) from None

    resultat = entree.session.resultat()
    score_visage = similarite_hamming(
        biohash(resultat.vecteur_visage, references.jeton, "visage"), references.codes["visage"])
    score_oreille = similarite_hamming(
        biohash(resultat.vecteur_oreille, references.jeton, "oreille"), references.codes["oreille"])
    del references
    params = ParametresDecision()
    decision = decider(score_visage, score_oreille, vivacite_ok=resultat.vivacite.ok, params=params)
    duree_ms = round((time.perf_counter() - debut) * 1000)

    tentative = Tentative(
        utilisateur_id=utilisateur.id,
        email_revendique=entree.email,
        contexte="production",
        score_visage=decision.score_visage,
        score_oreille=decision.score_oreille,
        score_fusion=decision.score_fusion,
        regles=decision.regles,
        accepte=decision.accepte,
        raison=decision.raison,
        duree_ms=duree_ms,
        ip=ip,
        version_parametres=params.version,
    )
    bdd.add(tentative)
    _comptabiliser(bdd, utilisateur, decision.accepte)
    bdd.flush()

    details = decision.to_dict()
    reponse: dict = {"decision": details if settings.afficher_scores else masquer_nombres(details)}
    if decision.accepte:
        jeton = creer_jeton(settings.secret_jwt, "acces", utilisateur.id, tentative_id=tentative.id)
        utilisateur.jeton_acces_jti = jeton.jti  # invalide le jeton d'accès précédent
        reponse |= {"jeton_acces": jeton.jeton, "expire_dans": jeton.expire_dans}
    journaliser(bdd, "AUTHENTIFICATION_ACCEPTEE" if decision.accepte else "AUTHENTIFICATION_REFUSEE",
                utilisateur.id, tentative=tentative.id, duree_ms=duree_ms, raison=decision.raison)
    bdd.commit()
    return reponse


@router.post("/authentification/sessions/{session_id}/images")
async def envoyer_image(
    session_id: str,
    request: Request,
    bdd: Session = Depends(obtenir_bdd),
    settings: Settings = Depends(obtenir_settings),
    chiffreur=Depends(obtenir_chiffreur),
    sessions: GestionnaireSessions = Depends(obtenir_sessions),
) -> dict:
    """Analyse une image ; à la dernière capture, rend la décision (+ jeton si accepté)."""
    octets = await lire_image_jpeg(request)
    entree = sessions.reserver(session_id, "authentification")
    ip = adresse_ip(request)
    debut = time.perf_counter()
    termine = False
    try:
        retour = await run_in_threadpool(entree.session.traiter_image, octets)
        termine = entree.abandonnee or retour.etape in ("terminee", "echec")
        if entree.abandonnee:
            raise ErreurAPI(404, "SESSION_INTROUVABLE", "Cette session de capture a été abandonnée.")
        reponse = retour.to_dict()
        if retour.etape == "echec":
            await run_in_threadpool(_echec_capture, bdd, entree, retour.raison_echec, ip)
        elif retour.etape == "terminee":
            reponse |= await run_in_threadpool(_decider, bdd, settings, chiffreur, entree, debut, ip)
        return reponse
    finally:
        # Session terminée : effacement des données en mémoire (session.effacer()).
        if termine:
            sessions.retirer(entree)
        else:
            sessions.liberer(entree)


@router.delete("/authentification/sessions/{session_id}", status_code=204)
def abandonner_session(session_id: str,
                       sessions: GestionnaireSessions = Depends(obtenir_sessions)) -> Response:
    """Abandon volontaire : ne compte pas comme un échec (idempotent)."""
    sessions.abandonner(session_id, "authentification")
    return Response(status_code=204)
