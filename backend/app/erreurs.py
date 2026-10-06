"""Format d'erreur unique de l'API : {"detail": {"code", "message", "champs"?}}."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

journal = logging.getLogger("bioaccess.api")

# Codes des erreurs dont le message est déjà rédigé en français par nos validateurs.
TYPES_PERSONNALISES = {"nom_invalide", "email_invalide", "mot_de_passe_faible", "confirmation_invalide"}

MESSAGES_PYDANTIC = {
    "missing": "Ce champ est obligatoire.",
    "string_type": "Ce champ doit être une chaîne de caractères.",
    "bool_type": "Ce champ doit valoir true ou false.",
    "bool_parsing": "Ce champ doit valoir true ou false.",
    "int_type": "Ce champ doit être un nombre entier.",
    "int_parsing": "Ce champ doit être un nombre entier.",
    "json_invalid": "Le corps de la requête n'est pas un JSON valide.",
    "model_attributes_type": "Le corps de la requête doit être un objet JSON.",
    "dict_type": "Le corps de la requête doit être un objet JSON.",
}

MESSAGES_HTTP = {
    404: ("RESSOURCE_INTROUVABLE", "Cette ressource n'existe pas."),
    405: ("METHODE_NON_AUTORISEE", "Cette méthode HTTP n'est pas autorisée sur cette ressource."),
}


class ErreurAPI(Exception):
    """Erreur métier renvoyée au client avec un code machine et un message français."""

    def __init__(
        self,
        statut: int,
        code: str,
        message: str,
        champs: dict[str, str] | None = None,
        **supplements: Any,
    ) -> None:
        super().__init__(message)
        self.statut = statut
        self.code = code
        self.message = message
        self.champs = champs
        self.supplements = supplements

    def corps(self) -> dict:
        detail: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.champs:
            detail["champs"] = self.champs
        detail.update(self.supplements)
        return {"detail": detail}


def erreur_validation(champs: dict[str, str]) -> ErreurAPI:
    """Erreur 422 au même format que les erreurs de validation automatiques."""
    if len(champs) == 1:
        message = next(iter(champs.values()))
    else:
        message = "Certaines données sont invalides : " + " ".join(champs.values())
    return ErreurAPI(422, "DONNEES_INVALIDES", message, champs)


def _nom_champ(loc: tuple) -> str:
    morceaux = [str(p) for p in loc[1:]] if len(loc) > 1 else []
    return ".".join(morceaux) or "corps"


def _message_pydantic(erreur: dict) -> str:
    if erreur["type"] in TYPES_PERSONNALISES:
        return erreur["msg"]
    return MESSAGES_PYDANTIC.get(erreur["type"], "Valeur invalide.")


def installer_gestionnaires(app: FastAPI) -> None:
    """Enregistre les gestionnaires d'erreurs qui produisent le format commun."""

    @app.exception_handler(ErreurAPI)
    async def _erreur_api(_: Request, exc: ErreurAPI) -> JSONResponse:
        return JSONResponse(exc.corps(), status_code=exc.statut)

    @app.exception_handler(RequestValidationError)
    async def _erreur_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        champs: dict[str, str] = {}
        for erreur in exc.errors():
            champs.setdefault(_nom_champ(tuple(erreur["loc"])), _message_pydantic(erreur))
        return JSONResponse(erreur_validation(champs).corps(), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _erreur_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = MESSAGES_HTTP.get(exc.status_code, ("ERREUR_HTTP", str(exc.detail)))
        return JSONResponse(
            {"detail": {"code": code, "message": message}},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _erreur_interne(_: Request, exc: Exception) -> JSONResponse:
        journal.exception("Erreur interne non prévue")
        return JSONResponse(
            {"detail": {"code": "ERREUR_INTERNE",
                        "message": "Une erreur interne est survenue. Réessayez plus tard."}},
            status_code=500,
        )
