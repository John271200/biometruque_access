"""Consentement explicite au traitement biométrique."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.audit import journaliser
from app.captures import GestionnaireSessions
from app.db import maintenant
from app.dependances import adresse_ip, obtenir_bdd, obtenir_sessions, utilisateur_compte
from app.erreurs import erreur_validation
from app.gabarits import detruire_gabarits
from app.modeles import Utilisateur
from app.schemas import ReponseConsentement, utilisateur_vers_dict

router = APIRouter(tags=["consentement"])

VERSION_CONSENTEMENT = "1.0"

TEXTE_CONSENTEMENT = {
    "version": VERSION_CONSENTEMENT,
    "titre": "Consentement au traitement de vos données biométriques",
    "paragraphes": [
        "BioAccess vous permet d'accéder à une base de données protégée en vous authentifiant "
        "par la combinaison de votre visage et de votre oreille. Ce traitement repose "
        "uniquement sur votre consentement explicite : sans lui, aucune capture n'est réalisée.",
        "Lors de l'enrôlement puis de chaque authentification, la caméra de votre appareil "
        "capture quelques images de votre visage et de votre oreille. Ces images sont analysées "
        "en mémoire puis effacées : elles ne sont jamais enregistrées.",
        "Seuls des gabarits protégés sont conservés : vos caractéristiques sont transformées "
        "de façon irréversible (BioHashing avec un jeton secret propre à votre compte), puis "
        "chiffrées (AES-256-GCM). Ils ne permettent pas de reconstituer votre image.",
        "Chaque tentative d'authentification est journalisée (date, décision, scores, motif) "
        "afin d'assurer la sécurité et l'auditabilité de la plateforme. Vous pouvez consulter "
        "vos tentatives depuis votre espace.",
        "Vous pouvez à tout moment révoquer vos gabarits, retirer ce consentement ou supprimer "
        "votre compte : vos gabarits sont alors détruits immédiatement et vos traces "
        "d'authentification sont pseudonymisées.",
        "Ce service est un prototype réalisé dans le cadre d'un mémoire de Master. Les dossiers "
        "patients accessibles après authentification sont entièrement fictifs.",
    ],
    "responsable": "Projet BioAccess — mémoire de Master Génie Logiciel, IFRI "
                   "(Université d'Abomey-Calavi, Bénin)",
}


@router.get("/consentement/texte")
def texte_consentement() -> dict:
    """Texte du consentement en vigueur."""
    return TEXTE_CONSENTEMENT


@router.post("/consentement")
def repondre_consentement(
    corps: ReponseConsentement,
    request: Request,
    utilisateur: Utilisateur = Depends(utilisateur_compte),
    bdd: Session = Depends(obtenir_bdd),
    sessions: GestionnaireSessions = Depends(obtenir_sessions),
) -> dict:
    """Accorde (ou refuse) le consentement pour la version en vigueur du texte."""
    if corps.version != VERSION_CONSENTEMENT:
        raise erreur_validation({"version": (
            f"Ce texte n'est plus en vigueur : relisez la version {VERSION_CONSENTEMENT}.")})
    if corps.accepte:
        utilisateur.consentement_etat = "ACCORDE"
        utilisateur.consentement_version = corps.version
        utilisateur.consentement_le = maintenant()
        utilisateur.consentement_ip = adresse_ip(request)
        journaliser(bdd, "CONSENTEMENT_ACCORDE", utilisateur.id, version=corps.version)
    elif utilisateur.consentement_etat == "ACCORDE":
        retirer_consentement(bdd, sessions, utilisateur, request)
    else:
        journaliser(bdd, "CONSENTEMENT_REFUSE", utilisateur.id, version=corps.version)
    bdd.commit()
    return utilisateur_vers_dict(utilisateur)


@router.delete("/consentement")
def supprimer_consentement(
    request: Request,
    utilisateur: Utilisateur = Depends(utilisateur_compte),
    bdd: Session = Depends(obtenir_bdd),
    sessions: GestionnaireSessions = Depends(obtenir_sessions),
) -> dict:
    """Retrait du consentement : les gabarits et le jeton BioHashing sont détruits."""
    retirer_consentement(bdd, sessions, utilisateur, request)
    bdd.commit()
    return utilisateur_vers_dict(utilisateur)


def retirer_consentement(bdd: Session, sessions: GestionnaireSessions,
                         utilisateur: Utilisateur, request: Request) -> None:
    detruire_gabarits(bdd, utilisateur.id)
    sessions.retirer_utilisateur(utilisateur.id)
    if utilisateur.enrolement_etat == "ENROLE":
        utilisateur.enrolement_etat = "REVOQUE"
    utilisateur.jeton_acces_jti = None
    utilisateur.consentement_etat = "RETIRE"
    utilisateur.consentement_le = maintenant()
    utilisateur.consentement_ip = adresse_ip(request)
    journaliser(bdd, "CONSENTEMENT_RETIRE", utilisateur.id)
