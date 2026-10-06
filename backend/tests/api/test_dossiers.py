"""Base protégée : jeton `acces` obligatoire, journalisation des accès."""

from datetime import timedelta

from sqlalchemy import select

from app.modeles import AccesBase, Tentative
from app.securite import creer_jeton

from .outils import authentifier, compte_enrole, connecter, entete, legitime


def _acces(client, moteur) -> str:
    compte_enrole(client)
    legitime(moteur)
    return authentifier(client).json()["jeton_acces"]


def test_liste_et_detail(client, moteur):
    jeton = _acces(client, moteur)
    r = client.get("/api/dossiers", headers=entete(jeton))
    assert r.status_code == 200
    corps = r.json()
    assert len(corps["dossiers"]) == 50 and 590 <= corps["expire_dans"] <= 600
    assert set(corps["dossiers"][0]) >= {"id", "nom", "age", "groupe_sanguin", "medecin"}

    r = client.get("/api/dossiers/7", headers=entete(jeton))
    assert r.status_code == 200
    dossier = r.json()
    assert dossier["id"] == 7 and dossier["fictif"] is True
    assert set(dossier) >= {"antecedents", "traitement", "allergies", "derniere_consultation"}

    r = client.get("/api/dossiers/999", headers=entete(jeton))
    assert r.status_code == 404 and r.json()["detail"]["code"] == "DOSSIER_INTROUVABLE"

    with client.app.state.bdd.session() as bdd:
        tentative = bdd.scalars(select(Tentative)).one()
        acces = bdd.scalars(select(AccesBase).order_by(AccesBase.id)).all()
        assert [a.ressource for a in acces] == ["/dossiers", "/dossiers/7"]
        assert all(a.tentative_id == tentative.id and a.utilisateur_id == tentative.utilisateur_id
                   for a in acces)


def test_jeton_compte_refuse(client, moteur):
    compte_enrole(client)
    r = client.get("/api/dossiers", headers=entete(connecter(client)))
    assert r.status_code == 403 and r.json()["detail"]["code"] == "JETON_ACCES_REQUIS"


def test_jeton_absent_ou_expire(client, moteur):
    _acces(client, moteur)
    assert client.get("/api/dossiers").status_code == 401
    with client.app.state.bdd.session() as bdd:
        tentative = bdd.scalars(select(Tentative)).one()
    expire = creer_jeton(client.app.state.settings.secret_jwt, "acces", tentative.utilisateur_id,
                         tentative.id, duree=timedelta(seconds=-1)).jeton
    r = client.get("/api/dossiers", headers=entete(expire))
    assert r.status_code == 401 and r.json()["detail"]["code"] == "JETON_EXPIRE"
