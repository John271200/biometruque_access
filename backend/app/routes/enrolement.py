"""Enrôlement guidé par webcam : 5 captures du visage puis 5 de l'oreille."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.audit import journaliser
from app.captures import GestionnaireSessions, info_session, lire_image_jpeg
from app.config import Settings
from app.db import maintenant
from app.dependances import (
    obtenir_bdd, obtenir_chiffreur, obtenir_moteur, obtenir_sessions, obtenir_settings,
    utilisateur_compte,
)
from app.erreurs import ErreurAPI
from app.gabarits import enregistrer_gabarits
from app.modeles import Utilisateur
from app.schemas import utilisateur_vers_dict

router = APIRouter(tags=["enrôlement"])

NB_CAPTURES = 5


def _verifier_preconditions(utilisateur: Utilisateur) -> None:
    if utilisateur.consentement_etat != "ACCORDE":
        raise ErreurAPI(403, "CONSENTEMENT_REQUIS",
                        "Vous devez accorder votre consentement avant l'enrôlement biométrique.")
    if utilisateur.enrolement_etat == "ENROLE":
        raise ErreurAPI(409, "DEJA_ENROLE",
                        "Vous êtes déjà enrôlé. Révoquez vos gabarits pour vous enrôler à nouveau.")


@router.post("/enrolement/sessions", status_code=201)
def creer_session(
    utilisateur: Utilisateur = Depends(utilisateur_compte),
    moteur=Depends(obtenir_moteur),
    settings: Settings = Depends(obtenir_settings),
    sessions: GestionnaireSessions = Depends(obtenir_sessions),
) -> dict:
    """Ouvre une session de capture d'enrôlement pour l'utilisateur connecté."""
    _verifier_preconditions(utilisateur)
    session = moteur.nouvelle_session("enrolement", NB_CAPTURES, NB_CAPTURES, None,
                                      apercu=settings.apercu_oreille)
    sessions.ajouter(session, "enrolement", utilisateur.id, utilisateur.email)
    return info_session(session.id, NB_CAPTURES, NB_CAPTURES, None, sessions.duree_inactivite)


def _finaliser(bdd: Session, chiffreur, utilisateur: Utilisateur, session) -> None:
    """Protège et enregistre les gabarits (transaction unique), puis marque l'utilisateur ENROLE."""
    bdd.refresh(utilisateur)
    _verifier_preconditions(utilisateur)
    resultat = session.resultat()
    enregistrer_gabarits(bdd, chiffreur, utilisateur, resultat)
    utilisateur.enrolement_etat = "ENROLE"
    utilisateur.enrolement_le = maintenant()
    utilisateur.extracteur_oreille = resultat.extracteur_oreille
    utilisateur.cote_oreille = resultat.cote_oreille
    utilisateur.echecs_consecutifs = 0
    utilisateur.verrouille_jusqua = None
    utilisateur.jeton_acces_jti = None
    journaliser(bdd, "ENROLEMENT_TERMINE", utilisateur.id,
                extracteur_visage=resultat.extracteur_visage,
                extracteur_oreille=resultat.extracteur_oreille, cote_oreille=resultat.cote_oreille)
    bdd.commit()


@router.post("/enrolement/sessions/{session_id}/images")
async def envoyer_image(
    session_id: str,
    request: Request,
    utilisateur: Utilisateur = Depends(utilisateur_compte),
    bdd: Session = Depends(obtenir_bdd),
    chiffreur=Depends(obtenir_chiffreur),
    sessions: GestionnaireSessions = Depends(obtenir_sessions),
) -> dict:
    """Analyse une image ; à la dernière capture, enregistre les gabarits protégés."""
    octets = await lire_image_jpeg(request)
    entree = sessions.reserver(session_id, "enrolement", proprietaire=utilisateur.id)
    termine = False
    try:
        retour = await run_in_threadpool(entree.session.traiter_image, octets)
        termine = entree.abandonnee or retour.etape in ("terminee", "echec")
        if entree.abandonnee:
            raise ErreurAPI(404, "SESSION_INTROUVABLE", "Cette session de capture a été abandonnée.")
        reponse = retour.to_dict()
        if retour.etape == "echec":
            journaliser(bdd, "ENROLEMENT_ECHOUE", utilisateur.id, raison=retour.raison_echec)
            bdd.commit()
        elif retour.etape == "terminee":
            await run_in_threadpool(_finaliser, bdd, chiffreur, utilisateur, entree.session)
            reponse["utilisateur"] = utilisateur_vers_dict(utilisateur)
        return reponse
    finally:
        # Session terminée : effacement des données en mémoire (session.effacer()).
        if termine:
            sessions.retirer(entree)
        else:
            sessions.liberer(entree)


@router.delete("/enrolement/sessions/{session_id}", status_code=204)
def abandonner_session(
    session_id: str,
    utilisateur: Utilisateur = Depends(utilisateur_compte),
    sessions: GestionnaireSessions = Depends(obtenir_sessions),
) -> Response:
    """Abandon de l'enrôlement en cours (idempotent)."""
    sessions.abandonner(session_id, "enrolement", proprietaire=utilisateur.id)
    return Response(status_code=204)
