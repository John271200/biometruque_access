"""Santé de l'API, moteur absent (503) et chargement de la configuration."""

import base64

import pytest

from app.config import ErreurConfiguration, charger_settings

from .outils import entete, connecter, consentir, inscrire


def test_sante_modeles_charges(client):
    r = client.get("/api/sante")
    assert r.status_code == 200
    corps = r.json()
    assert corps["statut"] == "ok" and corps["modeles_charges"] is True
    assert corps["version"]


def test_modeles_absents_503(fabrique_client):
    client = fabrique_client(moteur_injecte=None)
    assert client.get("/api/sante").json()["modeles_charges"] is False

    r = client.post("/api/authentification/sessions", json={"email": "awa@exemple.bj"})
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["code"] == "MODELES_ABSENTS"
    assert "telecharger_modeles.py" in detail["message"]

    inscrire(client)
    jeton = connecter(client)
    consentir(client, jeton)
    r = client.post("/api/enrolement/sessions", headers=entete(jeton))
    assert r.status_code == 503 and r.json()["detail"]["code"] == "MODELES_ABSENTS"
    # Le reste de l'API fonctionne.
    assert client.get("/api/moi", headers=entete(jeton)).status_code == 200


def test_route_inconnue_format_erreur(client):
    r = client.get("/api/inexistante")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "RESSOURCE_INTROUVABLE"


def test_dossiers_fictifs_deterministes(client):
    from app.donnees_fictives import generer_dossiers

    a, b = generer_dossiers(), generer_dossiers()
    assert len(a) == 50
    assert [(d.nom, d.age, d.medecin) for d in a] == [(d.nom, d.age, d.medecin) for d in b]
    assert all(d.fictif for d in a)


@pytest.fixture
def env_vierge(monkeypatch):
    for nom in ("ENV", "CLE_MAITRESSE", "SECRET_JWT", "DATABASE_URL"):
        monkeypatch.delenv(f"BIOACCESS_{nom}", raising=False)


def test_config_dev_genere_les_secrets(tmp_path, env_vierge, caplog):
    fichier = tmp_path / ".env"
    fichier.write_text("BIOACCESS_ENV=dev", encoding="utf-8")
    settings = charger_settings(fichier)
    assert len(base64.b64decode(settings.cle_maitresse)) == 32
    assert settings.secret_jwt
    contenu = fichier.read_text(encoding="utf-8")
    assert f"BIOACCESS_CLE_MAITRESSE={settings.cle_maitresse}" in contenu
    assert f"BIOACCESS_SECRET_JWT={settings.secret_jwt}" in contenu
    assert settings.afficher_scores is True and settings.apercu_oreille is True
    assert settings.database_url.startswith("sqlite:///") and settings.database_url.endswith("bioaccess.db")
    # Au second chargement, les mêmes secrets sont relus (pas de nouvelle génération).
    relu = charger_settings(fichier)
    assert relu.cle_maitresse == settings.cle_maitresse
    assert fichier.read_text(encoding="utf-8") == contenu


def test_config_production_refuse_sans_secret(tmp_path, env_vierge):
    fichier = tmp_path / ".env"
    fichier.write_text("BIOACCESS_ENV=production\n", encoding="utf-8")
    with pytest.raises(ErreurConfiguration, match="BIOACCESS_CLE_MAITRESSE"):
        charger_settings(fichier)
    assert fichier.read_text(encoding="utf-8") == "BIOACCESS_ENV=production\n"  # rien n'est généré


def test_config_production_valeurs_par_defaut(tmp_path, env_vierge):
    fichier = tmp_path / ".env"
    cle = base64.b64encode(b"k" * 32).decode()
    fichier.write_text(f"BIOACCESS_ENV=production\nBIOACCESS_CLE_MAITRESSE={cle}\n"
                       f"BIOACCESS_SECRET_JWT={'s' * 48}\n", encoding="utf-8")
    settings = charger_settings(fichier)
    assert settings.afficher_scores is False and settings.apercu_oreille is False


def test_config_cle_mal_formee(tmp_path, env_vierge):
    fichier = tmp_path / ".env"
    fichier.write_text("BIOACCESS_CLE_MAITRESSE=trop-courte\nBIOACCESS_SECRET_JWT=abc\n", encoding="utf-8")
    with pytest.raises(ErreurConfiguration, match="32 octets"):
        charger_settings(fichier)
