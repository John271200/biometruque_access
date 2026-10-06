"""Espace personnel : tentatives, révocation, retrait du consentement, suppression du compte."""

import hashlib

from sqlalchemy import select

from app.modeles import AccesBase, Gabarit, JetonBiohash, Tentative, Utilisateur

from .outils import (
    MOT_DE_PASSE, authentifier, compte_enrole, entete, imposteur, legitime,
)


def _compter(client, modele, **filtres) -> int:
    with client.app.state.bdd.session() as bdd:
        requete = select(modele)
        for nom, valeur in filtres.items():
            requete = requete.where(getattr(modele, nom) == valeur)
        return len(bdd.scalars(requete).all())


def test_tentatives(client, moteur):
    jeton = compte_enrole(client)
    imposteur(moteur)
    authentifier(client)
    legitime(moteur)
    authentifier(client)
    r = client.get("/api/moi/tentatives", headers=entete(jeton))
    assert r.status_code == 200
    tentatives = r.json()["tentatives"]
    assert [t["decision"] for t in tentatives] == ["ACCEPTEE", "REFUSEE"]  # plus récente d'abord
    t = tentatives[0]
    assert set(t) == {"horodatage", "decision", "raison", "score_visage", "score_oreille",
                      "score_fusion", "regles"}
    assert isinstance(t["score_visage"], float) and len(t["regles"]) == 4
    assert tentatives[1]["raison"]


def test_revocation(client, moteur):
    jeton = compte_enrole(client)
    legitime(moteur)
    acces = authentifier(client).json()["jeton_acces"]
    uid = client.get("/api/moi", headers=entete(jeton)).json()["id"]

    r = client.post("/api/moi/revocation", json={"mot_de_passe": "Mauvais2026xx"}, headers=entete(jeton))
    assert r.status_code == 403 and r.json()["detail"]["code"] == "MOT_DE_PASSE_INCORRECT"
    assert _compter(client, Gabarit, utilisateur_id=uid) == 2

    r = client.post("/api/moi/revocation", json={"mot_de_passe": MOT_DE_PASSE}, headers=entete(jeton))
    assert r.status_code == 200 and r.json()["enrolement"]["etat"] == "REVOQUE"
    assert _compter(client, Gabarit, utilisateur_id=uid) == 0
    assert _compter(client, JetonBiohash, utilisateur_id=uid) == 0
    # Le jeton d'accès ne fonctionne plus et l'authentification est impossible.
    assert client.get("/api/dossiers", headers=entete(acces)).json()["detail"]["code"] == "JETON_INVALIDE"
    r = client.post("/api/authentification/sessions", json={"email": "awa@exemple.bj"})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "COMPTE_NON_ENROLE"
    # Un nouvel enrôlement est possible (consentement toujours accordé).
    assert client.post("/api/enrolement/sessions", headers=entete(jeton)).status_code == 201


def test_retrait_consentement_detruit_les_gabarits(client, moteur):
    jeton = compte_enrole(client)
    uid = client.get("/api/moi", headers=entete(jeton)).json()["id"]
    u = client.delete("/api/consentement", headers=entete(jeton)).json()
    assert u["consentement"]["etat"] == "RETIRE" and u["enrolement"]["etat"] == "REVOQUE"
    assert _compter(client, Gabarit, utilisateur_id=uid) == 0
    assert _compter(client, JetonBiohash, utilisateur_id=uid) == 0
    r = client.post("/api/enrolement/sessions", headers=entete(jeton))
    assert r.status_code == 403 and r.json()["detail"]["code"] == "CONSENTEMENT_REQUIS"


def test_suppression_du_compte(client, moteur):
    jeton = compte_enrole(client)
    legitime(moteur)
    acces = authentifier(client).json()["jeton_acces"]
    client.get("/api/dossiers", headers=entete(acces))
    uid = client.get("/api/moi", headers=entete(jeton)).json()["id"]

    r = client.request("DELETE", "/api/moi", json={"mot_de_passe": MOT_DE_PASSE, "confirmation": "oui"},
                       headers=entete(jeton))
    assert r.status_code == 422 and "confirmation" in r.json()["detail"]["champs"]
    r = client.request("DELETE", "/api/moi", json={"mot_de_passe": "Mauvais2026xx", "confirmation": "SUPPRIMER"},
                       headers=entete(jeton))
    assert r.status_code == 403

    r = client.request("DELETE", "/api/moi", json={"mot_de_passe": MOT_DE_PASSE, "confirmation": "SUPPRIMER"},
                       headers=entete(jeton))
    assert r.status_code == 204
    assert _compter(client, Utilisateur, id=uid) == 0
    assert _compter(client, Gabarit, utilisateur_id=uid) == 0
    assert _compter(client, JetonBiohash, utilisateur_id=uid) == 0
    pseudonyme = "supprime:" + hashlib.sha256(b"awa@exemple.bj").hexdigest()[:12]
    with client.app.state.bdd.session() as bdd:
        tentatives = bdd.scalars(select(Tentative)).all()
        assert tentatives and all(t.utilisateur_id is None and t.email_revendique == pseudonyme
                                  for t in tentatives)
        acces_base = bdd.scalars(select(AccesBase)).all()
        assert acces_base and all(a.utilisateur_id is None for a in acces_base)
    assert client.get("/api/moi", headers=entete(jeton)).status_code == 401
    assert client.get("/api/dossiers", headers=entete(acces)).status_code == 401
    assert client.post("/api/session", json={"email": "awa@exemple.bj",
                                             "mot_de_passe": MOT_DE_PASSE}).status_code == 401
    # L'adresse est de nouveau disponible.
    assert client.post("/api/comptes", json={"nom": "Awa", "email": "awa@exemple.bj",
                                             "mot_de_passe": MOT_DE_PASSE}).status_code == 201
