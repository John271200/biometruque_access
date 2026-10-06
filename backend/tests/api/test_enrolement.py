"""Enrôlement : préconditions, capture, protection des gabarits, erreurs de session."""

import threading

from sqlalchemy import select

from app.biometrie import Chiffreur
from app.captures import TAILLE_MAX_IMAGE
from app.modeles import Evenement, Gabarit, JetonBiohash

from .outils import (
    JPEG, compte_enrole, connecter, consentir, entete, envoyer, inscrire,
)


def _pret(client, email="awa@exemple.bj"):
    inscrire(client, email=email)
    jeton = connecter(client, email=email)
    consentir(client, jeton)
    return jeton


def test_consentement_requis(client):
    inscrire(client)
    jeton = connecter(client)
    r = client.post("/api/enrolement/sessions", headers=entete(jeton))
    assert r.status_code == 403 and r.json()["detail"]["code"] == "CONSENTEMENT_REQUIS"


def test_enrolement_complet(client, moteur):
    jeton = _pret(client)
    r = client.post("/api/enrolement/sessions", headers=entete(jeton))
    assert r.status_code == 201
    info = r.json()
    assert info["etape"] == "visage" and info["captures_visage_requises"] == 5
    assert info["captures_oreille_requises"] == 5 and info["cote_attendu"] is None
    assert info["expire_dans"] == 120
    session = moteur.sessions[-1]
    assert session.mode == "enrolement" and session.apercu is False

    for i in range(9):
        r = envoyer(client, f"/api/enrolement/sessions/{info['session_id']}/images", jeton)
        assert r.status_code == 200 and r.json()["etape"] in ("visage", "oreille")
        assert "utilisateur" not in r.json()
    r = envoyer(client, f"/api/enrolement/sessions/{info['session_id']}/images", jeton)
    corps = r.json()
    assert corps["etape"] == "terminee"
    u = corps["utilisateur"]
    assert u["enrolement"]["etat"] == "ENROLE" and u["enrolement"]["extracteur_oreille"] == "lbp-v1"
    assert u["enrolement"]["cote_oreille"] == "droite" and u["enrolement"]["date"]
    assert session.effacee  # données de capture effacées

    # La session est supprimée.
    r = envoyer(client, f"/api/enrolement/sessions/{info['session_id']}/images", jeton)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "SESSION_INTROUVABLE"

    # Gabarits stockés chiffrés, déchiffrables uniquement avec la bonne AAD.
    chiffreur = Chiffreur(client.app.state.settings.cle_maitresse_octets)
    with client.app.state.bdd.session() as bdd:
        gabarits = bdd.scalars(select(Gabarit).where(Gabarit.utilisateur_id == u["id"])).all()
        assert {g.modalite for g in gabarits} == {"visage", "oreille"}
        for g in gabarits:
            assert len(chiffreur.dechiffrer(g.donnees_chiffrees, f"{u['id']}|{g.modalite}".encode())) == 32
        jeton_bh = bdd.get(JetonBiohash, u["id"])
        assert len(chiffreur.dechiffrer(jeton_bh.jeton_chiffre, f"{u['id']}|jeton".encode())) == 32
        types = bdd.scalars(select(Evenement.type)).all()
        assert "ENROLEMENT_TERMINE" in types


def test_deja_enrole(client):
    jeton = compte_enrole(client)
    r = client.post("/api/enrolement/sessions", headers=entete(jeton))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "DEJA_ENROLE"


def test_type_et_taille_image(client):
    jeton = _pret(client)
    sid = client.post("/api/enrolement/sessions", headers=entete(jeton)).json()["session_id"]
    url = f"/api/enrolement/sessions/{sid}/images"
    r = envoyer(client, url, jeton, type_contenu="image/png")
    assert r.status_code == 415
    r = envoyer(client, url, jeton, contenu=b"\xff" * (TAILLE_MAX_IMAGE + 1))
    assert r.status_code == 413 and r.json()["detail"]["code"] == "IMAGE_TROP_GRANDE"
    assert envoyer(client, url, jeton, contenu=JPEG).status_code == 200


def test_image_en_cours_409(client, moteur):
    jeton = _pret(client)
    attente, entree = threading.Event(), threading.Event()
    moteur.programmer(attente=attente, entree=entree)
    sid = client.post("/api/enrolement/sessions", headers=entete(jeton)).json()["session_id"]
    url = f"/api/enrolement/sessions/{sid}/images"

    resultats = {}
    fil = threading.Thread(target=lambda: resultats.update(premiere=envoyer(client, url, jeton)))
    fil.start()
    assert entree.wait(timeout=5)
    seconde = envoyer(client, url, jeton)
    attente.set()
    fil.join(timeout=5)
    assert seconde.status_code == 409 and seconde.json()["detail"]["code"] == "IMAGE_EN_COURS"
    assert resultats["premiere"].status_code == 200
    # Une fois la première image traitée, la session accepte la suivante.
    assert envoyer(client, url, jeton).status_code == 200


def test_session_reservee_au_proprietaire(client):
    jeton_a = _pret(client, "awa@exemple.bj")
    jeton_b = _pret(client, "kofi@exemple.bj")
    sid = client.post("/api/enrolement/sessions", headers=entete(jeton_a)).json()["session_id"]
    r = envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton_b)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "SESSION_INTROUVABLE"
    # La suppression par un tiers n'a aucun effet.
    assert client.delete(f"/api/enrolement/sessions/{sid}", headers=entete(jeton_b)).status_code == 204
    assert envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton_a).status_code == 200


def test_abandon_et_expiration(client, moteur):
    jeton = _pret(client)
    sid = client.post("/api/enrolement/sessions", headers=entete(jeton)).json()["session_id"]
    assert client.delete(f"/api/enrolement/sessions/{sid}", headers=entete(jeton)).status_code == 204
    assert moteur.sessions[-1].effacee
    r = envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton)
    assert r.status_code == 404

    sid = client.post("/api/enrolement/sessions", headers=entete(jeton)).json()["session_id"]
    entree = client.app.state.sessions.obtenir(sid)
    entree.derniere_activite -= 121  # 120 s d'inactivité dépassées
    r = envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "SESSION_INTROUVABLE"
    assert moteur.sessions[-1].effacee


def test_echec_de_capture(client, moteur):
    jeton = _pret(client)
    moteur.programmer(echec_a=3, raison_echec="Identité incohérente entre les captures.")
    sid = client.post("/api/enrolement/sessions", headers=entete(jeton)).json()["session_id"]
    for _ in range(2):
        envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton)
    r = envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton)
    assert r.json()["etape"] == "echec" and r.json()["raison_echec"]
    assert client.get("/api/moi", headers=entete(jeton)).json()["enrolement"]["etat"] == "NON_ENROLE"
    assert envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton).status_code == 404


def test_apercu_oreille_transmis(fabrique_client, moteur):
    client = fabrique_client(apercu_oreille=True)
    jeton = _pret(client)
    client.post("/api/enrolement/sessions", headers=entete(jeton))
    assert moteur.sessions[-1].apercu is True
