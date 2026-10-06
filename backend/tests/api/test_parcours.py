"""Parcours complet de bout en bout, tel que le vivra un utilisateur."""

from .outils import (
    MOT_DE_PASSE, authentifier, connecter, consentir, enroler, entete, imposteur, inscrire, legitime,
)


def test_parcours_complet(client, moteur):
    # Inscription → connexion → consentement → enrôlement
    utilisateur = inscrire(client)
    jeton = connecter(client)
    assert consentir(client, jeton)["consentement"]["etat"] == "ACCORDE"
    assert enroler(client, jeton)["utilisateur"]["enrolement"]["etat"] == "ENROLE"

    # Authentification légitime (vecteurs proches) acceptée → base protégée accessible
    legitime(moteur)
    reponse = authentifier(client).json()
    assert reponse["decision"]["accepte"] is True
    acces = reponse["jeton_acces"]
    assert client.get("/api/dossiers", headers=entete(acces)).status_code == 200
    r = client.get("/api/dossiers", headers=entete(jeton))
    assert r.status_code == 403 and r.json()["detail"]["code"] == "JETON_ACCES_REQUIS"

    # Imposteur (vecteurs différents) refusé, cinq fois → verrouillage
    imposteur(moteur)
    for _ in range(5):
        assert authentifier(client).json()["decision"]["accepte"] is False
    r = client.post("/api/authentification/sessions", json={"email": utilisateur["email"]})
    assert r.status_code == 423 and r.json()["detail"]["code"] == "COMPTE_VERROUILLE"
    assert client.get("/api/moi", headers=entete(jeton)).json()["echecs_consecutifs"] == 5
    assert len(client.get("/api/moi/tentatives", headers=entete(jeton)).json()["tentatives"]) == 6

    # Révocation → nouvelle authentification impossible
    r = client.post("/api/moi/revocation", json={"mot_de_passe": MOT_DE_PASSE}, headers=entete(jeton))
    assert r.json()["enrolement"]["etat"] == "REVOQUE" and r.json()["echecs_consecutifs"] == 5
    assert client.get("/api/dossiers", headers=entete(acces)).status_code == 401
    r = client.post("/api/authentification/sessions", json={"email": utilisateur["email"]})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "COMPTE_NON_ENROLE"

    # Suppression du compte
    r = client.request("DELETE", "/api/moi", json={"mot_de_passe": MOT_DE_PASSE, "confirmation": "SUPPRIMER"},
                       headers=entete(jeton))
    assert r.status_code == 204
    assert client.get("/api/moi", headers=entete(jeton)).status_code == 401
