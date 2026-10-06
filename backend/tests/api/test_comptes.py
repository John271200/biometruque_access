"""Inscription, connexion, déconnexion, jetons."""

from datetime import timedelta

from app.securite import creer_jeton

from .outils import MOT_DE_PASSE, connecter, entete, inscrire


def test_inscription(client):
    r = client.post("/api/comptes", json={"nom": "  Awa   Dossou ", "email": "Awa@Exemple.BJ",
                                          "mot_de_passe": MOT_DE_PASSE})
    assert r.status_code == 201
    u = r.json()
    assert u["nom"] == "Awa Dossou" and u["email"] == "awa@exemple.bj" and u["role"] == "utilisateur"
    assert u["consentement"] == {"etat": "ABSENT", "version": None, "date": None}
    assert u["enrolement"] == {"etat": "NON_ENROLE", "date": None, "extracteur_oreille": None,
                               "cote_oreille": None}
    assert u["verrouille_jusqua"] is None and u["echecs_consecutifs"] == 0
    assert "mot_de_passe" not in r.text and "hash" not in r.text


def test_email_deja_utilise(client):
    inscrire(client, email="awa@exemple.bj")
    r = client.post("/api/comptes", json={"nom": "Autre", "email": "AWA@exemple.bj",
                                          "mot_de_passe": MOT_DE_PASSE})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "EMAIL_DEJA_UTILISE"


def test_mot_de_passe_faible(client):
    r = client.post("/api/comptes", json={"nom": "Awa", "email": "awa@exemple.bj",
                                          "mot_de_passe": "court"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "DONNEES_INVALIDES"
    message = detail["champs"]["mot_de_passe"]
    for manque in ("12 caractères", "une majuscule", "un chiffre"):
        assert manque in message
    assert "minuscule" not in message
    assert "court" not in r.text  # le mot de passe n'est jamais renvoyé


def test_validation_champs(client):
    r = client.post("/api/comptes", json={"nom": "A", "email": "pas-un-email"})
    assert r.status_code == 422
    champs = r.json()["detail"]["champs"]
    assert set(champs) == {"nom", "email", "mot_de_passe"}
    assert champs["mot_de_passe"] == "Ce champ est obligatoire."
    assert champs["email"] == "Adresse email invalide."

    r = client.post("/api/comptes", content=b"{pas du json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "DONNEES_INVALIDES"


def test_connexion_et_moi(client):
    inscrire(client)
    r = client.post("/api/session", json={"email": "AWA@exemple.bj", "mot_de_passe": MOT_DE_PASSE})
    assert r.status_code == 200
    corps = r.json()
    assert corps["expire_dans"] == 3600 and corps["utilisateur"]["email"] == "awa@exemple.bj"
    r = client.get("/api/moi", headers=entete(corps["jeton_compte"]))
    assert r.status_code == 200 and r.json()["id"] == corps["utilisateur"]["id"]


def test_connexion_refusee(client):
    inscrire(client)
    for corps in ({"email": "awa@exemple.bj", "mot_de_passe": "Mauvais2026xx"},
                  {"email": "inconnu@exemple.bj", "mot_de_passe": MOT_DE_PASSE}):
        r = client.post("/api/session", json=corps)
        assert r.status_code == 401
        assert r.json()["detail"]["code"] == "IDENTIFIANTS_INVALIDES"


def test_deconnexion_revoque_le_jeton(client):
    inscrire(client)
    jeton = connecter(client)
    assert client.delete("/api/session", headers=entete(jeton)).status_code == 204
    r = client.get("/api/moi", headers=entete(jeton))
    assert r.status_code == 401 and r.json()["detail"]["code"] == "JETON_INVALIDE"
    # Un nouveau jeton fonctionne.
    assert client.get("/api/moi", headers=entete(connecter(client))).status_code == 200


def test_jetons_absent_invalide_expire(client):
    utilisateur = inscrire(client)
    assert client.get("/api/moi").json()["detail"]["code"] == "JETON_INVALIDE"
    r = client.get("/api/moi", headers=entete("n.importe.quoi"))
    assert r.status_code == 401 and r.json()["detail"]["code"] == "JETON_INVALIDE"

    secret = client.app.state.settings.secret_jwt
    expire = creer_jeton(secret, "compte", utilisateur["id"], duree=timedelta(seconds=-5)).jeton
    r = client.get("/api/moi", headers=entete(expire))
    assert r.status_code == 401 and r.json()["detail"]["code"] == "JETON_EXPIRE"

    falsifie = creer_jeton("un-autre-secret-" + "y" * 40, "compte", utilisateur["id"]).jeton
    assert client.get("/api/moi", headers=entete(falsifie)).json()["detail"]["code"] == "JETON_INVALIDE"


def test_jeton_acces_refuse_sur_routes_compte(client):
    utilisateur = inscrire(client)
    acces = creer_jeton(client.app.state.settings.secret_jwt, "acces", utilisateur["id"], 1).jeton
    r = client.get("/api/moi", headers=entete(acces))
    assert r.status_code == 401 and r.json()["detail"]["code"] == "JETON_INVALIDE"
