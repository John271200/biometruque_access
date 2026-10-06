"""Fixtures communes aux tests de l'API : configuration isolée et client de test."""

from __future__ import annotations

import base64
import os
import tempfile

import pytest

# --- Isolation : ni le .env local ni la base de développement ne sont touchés ---------
_DOSSIER_IMPORT = tempfile.mkdtemp(prefix="bioaccess-tests-")
CLE_TEST = base64.b64encode(bytes(range(32))).decode()
SECRET_TEST = "secret-jwt-de-test-" + "x" * 48
os.environ.update({
    "BIOACCESS_ENV": "dev",
    "BIOACCESS_CLE_MAITRESSE": CLE_TEST,
    "BIOACCESS_SECRET_JWT": SECRET_TEST,
    "BIOACCESS_DATABASE_URL": f"sqlite:///{_DOSSIER_IMPORT}/import.db",
})

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import creer_app  # noqa: E402

from .outils import FakeMoteur  # noqa: E402


# --- Fixtures ------------------------------------------------------------------------

def settings_test(tmp_path, **surcharges) -> Settings:
    valeurs = dict(
        env="dev",
        database_url=f"sqlite:///{tmp_path.as_posix()}/test.db",
        cle_maitresse=CLE_TEST,
        secret_jwt=SECRET_TEST,
        afficher_scores=True,
        apercu_oreille=False,
    )
    valeurs.update(surcharges)
    return Settings(_env_file=None, **valeurs)


@pytest.fixture
def moteur() -> FakeMoteur:
    return FakeMoteur()


@pytest.fixture
def fabrique_client(tmp_path, moteur):
    """Crée un client de test avec des réglages éventuellement modifiés."""
    clients = []

    def creer(moteur_injecte=moteur, **surcharges) -> TestClient:
        app = creer_app(settings_test(tmp_path, **surcharges), moteur=moteur_injecte,
                        dossier_frontend=tmp_path / "dist-absent")
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        return client

    yield creer
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(fabrique_client) -> TestClient:
    return fabrique_client()


