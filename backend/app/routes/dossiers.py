"""Base protégée de dossiers patients FICTIFS : accessible uniquement avec un jeton `acces`."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependances import Authentifie, adresse_ip, authentifie_acces, obtenir_bdd
from app.erreurs import ErreurAPI
from app.modeles import AccesBase, DossierPatient
from app.schemas import dossier_complet, dossier_resume
from app.securite import secondes_restantes

router = APIRouter(tags=["dossiers"])


def _journaliser_acces(bdd: Session, auth: Authentifie, request: Request, ressource: str) -> None:
    bdd.add(AccesBase(
        utilisateur_id=auth.utilisateur.id,
        tentative_id=auth.jeton.get("tentative"),
        ressource=ressource,
        ip=adresse_ip(request),
    ))
    bdd.commit()


@router.get("/dossiers")
def lister_dossiers(request: Request, auth: Authentifie = Depends(authentifie_acces),
                    bdd: Session = Depends(obtenir_bdd)) -> dict:
    """Liste des dossiers (résumé) et temps restant du jeton d'accès."""
    dossiers = bdd.scalars(select(DossierPatient).order_by(DossierPatient.id)).all()
    _journaliser_acces(bdd, auth, request, "/dossiers")
    return {
        "dossiers": [dossier_resume(d) for d in dossiers],
        "expire_dans": secondes_restantes(auth.jeton),
    }


@router.get("/dossiers/{dossier_id}")
def lire_dossier(dossier_id: int, request: Request, auth: Authentifie = Depends(authentifie_acces),
                 bdd: Session = Depends(obtenir_bdd)) -> dict:
    """Détail d'un dossier fictif."""
    dossier = bdd.get(DossierPatient, dossier_id)
    if dossier is None:
        raise ErreurAPI(404, "DOSSIER_INTROUVABLE", "Ce dossier n'existe pas.")
    _journaliser_acces(bdd, auth, request, f"/dossiers/{dossier_id}")
    return dossier_complet(dossier)
