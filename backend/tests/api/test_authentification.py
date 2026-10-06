"""Authentification biométrique : décision, verrouillage, jetons d'accès, masquage des scores."""

from sqlalchemy import select

from app.modeles import Evenement, Gabarit, Tentative

from .outils import (
    compte_enrole, connecter, entete, envoyer, imposteur, inscrire, legitime, authentifier,
)


def test_compte_inconnu_ou_non_enrole(client):
    r = client.post("/api/authentification/sessions", json={"email": "inconnu@exemple.bj"})
    assert r.status_code == 404
    assert r.json()["detail"] == {"code": "COMPTE_NON_ENROLE",
                                  "message": "Aucun compte enrôlé ne correspond à cette adresse."}
    inscrire(client, email="kofi@exemple.bj")
    r = client.post("/api/authentification/sessions", json={"email": "kofi@exemple.bj"})
    assert r.status_code == 404


def test_session_info(client, moteur):
    compte_enrole(client)
    r = client.post("/api/authentification/sessions", json={"email": "AWA@exemple.bj"})
    assert r.status_code == 201
    info = r.json()
    assert info["etape"] == "visage" and info["cote_attendu"] == "droite"
    assert info["captures_visage_requises"] == 3 and info["captures_oreille_requises"] == 3
    assert info["expire_dans"] == 120
    session = moteur.sessions[-1]
    assert session.mode == "authentification" and session.cote_attendu == "droite"


def test_legitime_accepte(client, moteur):
    compte_enrole(client)
    legitime(moteur)
    r = authentifier(client)
    assert r.status_code == 200
    corps = r.json()
    assert corps["etape"] == "terminee"
    decision = corps["decision"]
    assert decision["accepte"] is True and decision["raison"] is None
    assert [regle["code"] for regle in decision["regles"]] == ["R1", "R2", "R3", "R4"]
    assert decision["score_visage"] > 0.9 and isinstance(decision["score_fusion"], float)
    assert corps["jeton_acces"] and corps["expire_dans"] == 600
    assert moteur.sessions[-1].effacee

    with client.app.state.bdd.session() as bdd:
        tentative = bdd.scalars(select(Tentative)).one()
        assert tentative.accepte and tentative.contexte == "production"
        assert tentative.duree_ms is not None and tentative.version_parametres == 1
        assert tentative.email_revendique == "awa@exemple.bj"


def test_imposteur_refuse(client, moteur):
    compte_enrole(client)
    imposteur(moteur)
    corps = authentifier(client).json()
    assert corps["decision"]["accepte"] is False
    assert corps["decision"]["raison"]
    assert "jeton_acces" not in corps


def test_vivacite_refusee(client, moteur):
    compte_enrole(client)
    legitime(moteur)
    moteur.programme.vivacite_ok = False
    corps = authentifier(client).json()
    assert corps["decision"]["accepte"] is False
    assert corps["decision"]["regles"][0] == {"code": "R1", "libelle": "Vivacité", "ok": False,
                                              "valeur": None, "seuil": None}


def test_verrouillage_apres_cinq_echecs(client, moteur):
    jeton = compte_enrole(client)
    imposteur(moteur)
    for i in range(4):
        assert authentifier(client).json()["decision"]["accepte"] is False
    assert client.get("/api/moi", headers=entete(jeton)).json()["echecs_consecutifs"] == 4
    # Le 5e échec est un échec de capture (vivacité) : il compte aussi.
    moteur.programmer(echec_a=2)
    r = authentifier(client)
    assert r.json()["etape"] == "echec"

    r = client.post("/api/authentification/sessions", json={"email": "awa@exemple.bj"})
    assert r.status_code == 423
    detail = r.json()["detail"]
    assert detail["code"] == "COMPTE_VERROUILLE" and detail["verrouille_jusqua"]
    moi = client.get("/api/moi", headers=entete(jeton)).json()
    assert moi["verrouille_jusqua"] == detail["verrouille_jusqua"]
    with client.app.state.bdd.session() as bdd:
        assert len(bdd.scalars(select(Tentative)).all()) == 5
        assert "COMPTE_VERROUILLE" in bdd.scalars(select(Evenement.type)).all()


def test_succes_remet_le_compteur_a_zero(client, moteur):
    jeton = compte_enrole(client)
    imposteur(moteur)
    for _ in range(3):
        authentifier(client)
    legitime(moteur)
    assert authentifier(client).json()["decision"]["accepte"] is True
    assert client.get("/api/moi", headers=entete(jeton)).json()["echecs_consecutifs"] == 0


def test_abandon_ne_compte_pas(client, moteur):
    jeton = compte_enrole(client)
    sid = client.post("/api/authentification/sessions", json={"email": "awa@exemple.bj"}).json()["session_id"]
    envoyer(client, f"/api/authentification/sessions/{sid}/images")
    assert client.delete(f"/api/authentification/sessions/{sid}").status_code == 204
    assert moteur.sessions[-1].effacee
    assert envoyer(client, f"/api/authentification/sessions/{sid}/images").status_code == 404
    # Expiration (120 s d'inactivité) : ne compte pas non plus.
    sid = client.post("/api/authentification/sessions", json={"email": "awa@exemple.bj"}).json()["session_id"]
    client.app.state.sessions.obtenir(sid).derniere_activite -= 121
    assert envoyer(client, f"/api/authentification/sessions/{sid}/images").status_code == 404
    assert client.get("/api/moi", headers=entete(jeton)).json()["echecs_consecutifs"] == 0


def test_nouveau_jeton_invalide_l_ancien(client, moteur):
    compte_enrole(client)
    legitime(moteur)
    premier = authentifier(client).json()["jeton_acces"]
    assert client.get("/api/dossiers", headers=entete(premier)).status_code == 200
    second = authentifier(client).json()["jeton_acces"]
    r = client.get("/api/dossiers", headers=entete(premier))
    assert r.status_code == 401 and r.json()["detail"]["code"] == "JETON_INVALIDE"
    assert client.get("/api/dossiers", headers=entete(second)).status_code == 200


def test_scores_masques(fabrique_client, moteur):
    client = fabrique_client(afficher_scores=False)
    jeton = compte_enrole(client)
    legitime(moteur)
    corps = authentifier(client).json()
    decision = corps["decision"]
    assert decision["accepte"] is True and corps["jeton_acces"]
    for cle in ("score_visage", "score_oreille", "z_visage", "z_oreille", "score_fusion"):
        assert decision[cle] is None
    for regle in decision["regles"]:
        assert regle["valeur"] is None and regle["seuil"] is None and isinstance(regle["ok"], bool)
    imposteur(moteur)
    refus = authentifier(client).json()["decision"]
    assert refus["raison"] and refus["accepte"] is False
    tentatives = client.get("/api/moi/tentatives", headers=entete(jeton)).json()["tentatives"]
    assert all(t["score_visage"] is None and t["score_fusion"] is None for t in tentatives)
    assert {t["decision"] for t in tentatives} == {"ACCEPTEE", "REFUSEE"}


def test_gabarit_corrompu(client, moteur):
    compte_enrole(client)
    with client.app.state.bdd.session() as bdd:
        gabarit = bdd.scalars(select(Gabarit).where(Gabarit.modalite == "visage")).one()
        blob = bytearray(gabarit.donnees_chiffrees)
        blob[-1] ^= 0xFF
        gabarit.donnees_chiffrees = bytes(blob)
        bdd.commit()
    legitime(moteur)
    r = authentifier(client)
    assert r.status_code == 500 and r.json()["detail"]["code"] == "GABARIT_CORROMPU"
    assert "jeton_acces" not in r.text
    with client.app.state.bdd.session() as bdd:
        assert "GABARIT_CORROMPU" in bdd.scalars(select(Evenement.type)).all()
        assert bdd.scalars(select(Tentative)).all() == []


def test_images_session_authentification(client, moteur):
    compte_enrole(client)
    sid = client.post("/api/authentification/sessions", json={"email": "awa@exemple.bj"}).json()["session_id"]
    r = envoyer(client, f"/api/authentification/sessions/{sid}/images", type_contenu="text/plain")
    assert r.status_code == 415
    r = envoyer(client, f"/api/authentification/sessions/{sid}/images", contenu=b"\x00" * (2 * 1024 * 1024 + 1))
    assert r.status_code == 413
    # Une session d'authentification n'est pas utilisable sur la route d'enrôlement.
    jeton = connecter(client)
    r = envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton)
    assert r.status_code == 404
