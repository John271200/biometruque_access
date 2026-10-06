"""Texte, octroi, refus et retrait du consentement."""

from .outils import connecter, consentir, entete, inscrire


def test_texte(client):
    r = client.get("/api/consentement/texte")
    assert r.status_code == 200
    corps = r.json()
    assert corps["version"] and corps["titre"] and corps["responsable"]
    assert isinstance(corps["paragraphes"], list) and len(corps["paragraphes"]) >= 3


def test_accorder_puis_retirer(client):
    inscrire(client)
    jeton = connecter(client)
    u = consentir(client, jeton)
    assert u["consentement"]["etat"] == "ACCORDE"
    assert u["consentement"]["version"] == client.get("/api/consentement/texte").json()["version"]
    assert u["consentement"]["date"].endswith("+00:00")

    r = client.delete("/api/consentement", headers=entete(jeton))
    assert r.status_code == 200 and r.json()["consentement"]["etat"] == "RETIRE"


def test_version_obsolete(client):
    inscrire(client)
    jeton = connecter(client)
    r = client.post("/api/consentement", json={"accepte": True, "version": "0.1"}, headers=entete(jeton))
    assert r.status_code == 422
    assert "version" in r.json()["detail"]["champs"]


def test_refus_sans_consentement_prealable(client):
    inscrire(client)
    jeton = connecter(client)
    version = client.get("/api/consentement/texte").json()["version"]
    r = client.post("/api/consentement", json={"accepte": False, "version": version}, headers=entete(jeton))
    assert r.status_code == 200 and r.json()["consentement"]["etat"] == "ABSENT"


def test_consentement_exige_jeton_compte(client):
    r = client.post("/api/consentement", json={"accepte": True, "version": "1.0"})
    assert r.status_code == 401
