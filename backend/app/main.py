"""Point d'entrée de l'API BioAccess.

Lancement (depuis backend/) : .venv/bin/python -m uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import __version__
from app.biometrie import Chiffreur
from app.captures import GestionnaireSessions
from app.config import DOSSIER_FRONTEND_DIST, ErreurConfiguration, Settings, charger_settings
from app.db import BaseDeDonnees
from app.dependances import COMMANDE_MODELES
from app.donnees_fictives import peupler_dossiers
from app.erreurs import ErreurAPI, installer_gestionnaires
from app.routes import (
    authentification, comptes, consentement, dossiers, enrolement, moi, sante,
)

journal = logging.getLogger("bioaccess")

CHARGER = object()  # valeur par défaut de `moteur` : charger le vrai moteur au démarrage


def configurer_journalisation() -> None:
    """Journal lisible « date niveau module : message » pour les loggers bioaccess.*."""
    if journal.handlers:
        return
    gestionnaire = logging.StreamHandler()
    gestionnaire.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s : %(message)s", "%Y-%m-%d %H:%M:%S"))
    journal.addHandler(gestionnaire)
    journal.setLevel(logging.INFO)
    journal.propagate = False


def charger_moteur(settings: Settings) -> Any | None:
    """Charge le moteur biométrique ; renvoie None (API dégradée) si les modèles manquent."""
    try:
        from app.biometrie import MoteurBiometrique

        moteur = MoteurBiometrique(settings.dossier_modeles)
    except Exception as exc:  # modèles absents ou illisibles : l'API démarre quand même
        journal.warning(
            "Moteur biométrique indisponible (%s). Les routes biométriques répondront 503 "
            "MODELES_ABSENTS. Pour corriger : cd backend && %s", exc, COMMANDE_MODELES)
        return None
    journal.info("Moteur biométrique chargé depuis %s", settings.dossier_modeles)
    return moteur


def _installer_frontend(app: FastAPI, dist: Path) -> None:
    """Sert le frontend compilé sur / avec repli SPA vers index.html (hors /api)."""

    @app.get("/{chemin:path}", include_in_schema=False)
    def frontend(chemin: str, request: Request):
        if chemin == "api" or chemin.startswith("api/"):
            raise ErreurAPI(404, "RESSOURCE_INTROUVABLE", "Cette ressource n'existe pas.")
        index = dist / "index.html"
        if not index.is_file():
            raise ErreurAPI(404, "FRONTEND_ABSENT",
                            "Frontend non compilé : lancez « npm run build » dans frontend/ "
                            "(ou utilisez Vite sur le port 5173 en développement).")
        racine = dist.resolve()
        fichier = (racine / chemin).resolve()
        if chemin and fichier.is_file() and fichier.is_relative_to(racine):
            return FileResponse(fichier)
        return FileResponse(index)


def creer_app(settings: Settings | None = None, moteur: Any = CHARGER,
              dossier_frontend: Path = DOSSIER_FRONTEND_DIST) -> FastAPI:
    """Construit l'application. `moteur` permet d'injecter un moteur (tests) ou None."""
    configurer_journalisation()
    settings = settings or charger_settings()

    @asynccontextmanager
    async def cycle_de_vie(app: FastAPI):
        bdd = BaseDeDonnees(settings.database_url)
        bdd.creer_tables()
        with bdd.session() as session:
            nombre = peupler_dossiers(session)
        if nombre:
            journal.info("%d dossiers patients fictifs générés", nombre)
        app.state.bdd = bdd
        app.state.moteur = charger_moteur(settings) if moteur is CHARGER else moteur
        journal.info("API BioAccess %s prête (env=%s, base=%s)", __version__, settings.env,
                     bdd.engine.url.render_as_string(hide_password=True))
        try:
            yield
        finally:
            app.state.sessions.vider()
            bdd.fermer()

    app = FastAPI(
        title="BioAccess API",
        version=__version__,
        description="Accès à une base protégée par fusion biométrique visage + oreille.",
        lifespan=cycle_de_vie,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings
    app.state.sessions = GestionnaireSessions()
    app.state.chiffreur = Chiffreur(settings.cle_maitresse_octets)
    app.state.moteur = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.liste_cors,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    installer_gestionnaires(app)
    for module in (sante, comptes, consentement, enrolement, authentification, dossiers, moi):
        app.include_router(module.router, prefix="/api")
    _installer_frontend(app, dossier_frontend)
    return app


try:
    app = creer_app()
except ErreurConfiguration as exc:
    configurer_journalisation()
    journal.critical("Démarrage impossible : %s", exc)
    raise SystemExit(f"Démarrage impossible : {exc}") from None
