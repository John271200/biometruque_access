"""État de l'API."""

from fastapi import APIRouter, Request

from app import __version__

router = APIRouter(tags=["santé"])


@router.get("/sante")
def sante(request: Request) -> dict:
    """Indique si l'API répond et si les modèles biométriques sont chargés."""
    return {
        "statut": "ok",
        "modeles_charges": getattr(request.app.state, "moteur", None) is not None,
        "version": __version__,
    }
