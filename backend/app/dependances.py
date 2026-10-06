"""Dépendances FastAPI : base de données, configuration, moteur, utilisateur courant."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.captures import GestionnaireSessions
from app.config import Settings
from app.erreurs import ErreurAPI
from app.modeles import JetonRevoque, Utilisateur
from app.securite import decoder_jeton

COMMANDE_MODELES = "python scripts/telecharger_modeles.py"


def obtenir_bdd(request: Request) -> Iterator[Session]:
    """Session SQL ouverte pour la durée de la requête."""
    bdd = request.app.state.bdd.session()
    try:
        yield bdd
    finally:
        bdd.close()


def obtenir_settings(request: Request) -> Settings:
    return request.app.state.settings


def obtenir_sessions(request: Request) -> GestionnaireSessions:
    return request.app.state.sessions


def obtenir_moteur(request: Request) -> Any:
    """Moteur biométrique chargé au démarrage ; 503 MODELES_ABSENTS s'il ne l'est pas."""
    moteur = getattr(request.app.state, "moteur", None)
    if moteur is None:
        raise ErreurAPI(
            503, "MODELES_ABSENTS",
            "Les modèles biométriques ne sont pas chargés. Depuis le dossier backend, lancez "
            f"« {COMMANDE_MODELES} » puis redémarrez l'API.",
            commande=COMMANDE_MODELES,
        )
    return moteur


def adresse_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _jeton_bearer(request: Request) -> str:
    entete = request.headers.get("authorization", "")
    schema, _, jeton = entete.partition(" ")
    if schema.lower() != "bearer" or not jeton.strip():
        raise ErreurAPI(401, "JETON_INVALIDE", "Authentification requise : jeton absent ou mal formé.")
    return jeton.strip()


def _invalide(message: str = "Jeton d'authentification invalide.") -> ErreurAPI:
    return ErreurAPI(401, "JETON_INVALIDE", message)


@dataclass
class Authentifie:
    """Utilisateur courant et contenu de son jeton."""

    utilisateur: Utilisateur
    jeton: dict


def authentifie_compte(
    request: Request,
    bdd: Session = Depends(obtenir_bdd),
    settings: Settings = Depends(obtenir_settings),
) -> Authentifie:
    """Utilisateur courant via un jeton `compte` non révoqué."""
    contenu = decoder_jeton(settings.secret_jwt, _jeton_bearer(request))
    if contenu["type"] != "compte":
        raise _invalide("Ce jeton ne permet pas de gérer le compte : connectez-vous avec votre mot de passe.")
    if bdd.get(JetonRevoque, contenu["jti"]) is not None:
        raise _invalide("Cette session a été fermée. Reconnectez-vous.")
    utilisateur = bdd.get(Utilisateur, contenu["sub"])
    if utilisateur is None:
        raise _invalide("Ce compte n'existe plus.")
    return Authentifie(utilisateur, contenu)


def utilisateur_compte(auth: Authentifie = Depends(authentifie_compte)) -> Utilisateur:
    return auth.utilisateur


def authentifie_acces(
    request: Request,
    bdd: Session = Depends(obtenir_bdd),
    settings: Settings = Depends(obtenir_settings),
) -> Authentifie:
    """Utilisateur courant via un jeton `acces` (le dernier émis pour cet utilisateur)."""
    contenu = decoder_jeton(settings.secret_jwt, _jeton_bearer(request))
    if contenu["type"] != "acces":
        raise ErreurAPI(
            403, "JETON_ACCES_REQUIS",
            "La base protégée exige une authentification biométrique récente "
            "(jeton d'accès). Authentifiez-vous par visage et oreille.",
        )
    utilisateur = bdd.get(Utilisateur, contenu["sub"])
    if utilisateur is None or utilisateur.jeton_acces_jti != contenu["jti"]:
        raise _invalide("Ce jeton d'accès a été remplacé ou révoqué. Authentifiez-vous à nouveau.")
    return Authentifie(utilisateur, contenu)


def obtenir_chiffreur(request: Request):
    """Chiffreur AES-256-GCM construit une fois au démarrage avec la clé maîtresse."""
    return request.app.state.chiffreur
