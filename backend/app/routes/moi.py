"""Espace personnel : profil, tentatives, révocation des gabarits, suppression du compte."""

import hashlib

from fastapi import APIRouter, Depends, Response
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.audit import journaliser
from app.captures import GestionnaireSessions
from app.config import Settings
from app.dependances import obtenir_bdd, obtenir_sessions, obtenir_settings, utilisateur_compte
from app.erreurs import ErreurAPI
from app.gabarits import detruire_gabarits
from app.modeles import AccesBase, Evenement, Tentative, Utilisateur
from app.schemas import MotDePasse, SuppressionCompte, tentative_vers_dict, utilisateur_vers_dict
from app.securite import verifier_mot_de_passe

router = APIRouter(tags=["moi"])

NB_TENTATIVES = 20


def _exiger_mot_de_passe(utilisateur: Utilisateur, mot_de_passe: str) -> None:
    if not verifier_mot_de_passe(utilisateur.mot_de_passe_hash, mot_de_passe):
        raise ErreurAPI(403, "MOT_DE_PASSE_INCORRECT",
                        "Mot de passe incorrect : l'opération n'a pas été effectuée.",
                        {"mot_de_passe": "Mot de passe incorrect."})


@router.get("/moi")
def moi(utilisateur: Utilisateur = Depends(utilisateur_compte)) -> dict:
    return utilisateur_vers_dict(utilisateur)


@router.get("/moi/tentatives")
def mes_tentatives(utilisateur: Utilisateur = Depends(utilisateur_compte),
                   bdd: Session = Depends(obtenir_bdd),
                   settings: Settings = Depends(obtenir_settings)) -> dict:
    """Les 20 dernières tentatives d'authentification biométrique, de la plus récente à la plus ancienne."""
    tentatives = bdd.scalars(
        select(Tentative).where(Tentative.utilisateur_id == utilisateur.id)
        .order_by(Tentative.horodatage.desc(), Tentative.id.desc()).limit(NB_TENTATIVES)
    ).all()
    return {"tentatives": [tentative_vers_dict(t, settings.afficher_scores) for t in tentatives]}


@router.post("/moi/revocation")
def revoquer(corps: MotDePasse,
             utilisateur: Utilisateur = Depends(utilisateur_compte),
             bdd: Session = Depends(obtenir_bdd),
             sessions: GestionnaireSessions = Depends(obtenir_sessions)) -> dict:
    """Révocation : destruction effective des gabarits et du jeton BioHashing."""
    _exiger_mot_de_passe(utilisateur, corps.mot_de_passe)
    detruire_gabarits(bdd, utilisateur.id)
    sessions.retirer_utilisateur(utilisateur.id)
    if utilisateur.enrolement_etat == "ENROLE":
        utilisateur.enrolement_etat = "REVOQUE"
    utilisateur.jeton_acces_jti = None
    journaliser(bdd, "REVOCATION", utilisateur.id)
    bdd.commit()
    return utilisateur_vers_dict(utilisateur)


@router.delete("/moi", status_code=204)
def supprimer_compte(corps: SuppressionCompte,
                     utilisateur: Utilisateur = Depends(utilisateur_compte),
                     bdd: Session = Depends(obtenir_bdd),
                     sessions: GestionnaireSessions = Depends(obtenir_sessions)) -> Response:
    """Suppression du compte ; tentatives et accès sont conservés mais pseudonymisés."""
    _exiger_mot_de_passe(utilisateur, corps.mot_de_passe)
    uid, email = utilisateur.id, utilisateur.email
    pseudonyme = "supprime:" + hashlib.sha256(email.encode()).hexdigest()[:12]
    sessions.retirer_utilisateur(uid)
    bdd.execute(
        update(Tentative)
        .where(or_(Tentative.utilisateur_id == uid, Tentative.email_revendique == email))
        .values(utilisateur_id=None, email_revendique=pseudonyme)
    )
    bdd.execute(update(AccesBase).where(AccesBase.utilisateur_id == uid).values(utilisateur_id=None))
    bdd.execute(update(Evenement).where(Evenement.utilisateur_id == uid).values(utilisateur_id=None))
    detruire_gabarits(bdd, uid)
    bdd.delete(utilisateur)
    journaliser(bdd, "COMPTE_SUPPRIME", None, pseudonyme=pseudonyme)
    bdd.commit()
    return Response(status_code=204)
