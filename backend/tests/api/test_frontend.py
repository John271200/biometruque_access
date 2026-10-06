"""Service du frontend compilé (frontend/dist) avec repli SPA."""

from fastapi.testclient import TestClient

from app.main import creer_app

from .conftest import settings_test


def test_frontend_compile_et_repli_spa(tmp_path, moteur):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>BioAccess</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("ne pas servir", encoding="utf-8")

    app = creer_app(settings_test(tmp_path), moteur=moteur, dossier_frontend=dist)
    with TestClient(app) as client:
        assert "BioAccess" in client.get("/").text
        assert client.get("/assets/app.js").text == "console.log('ok')"
        assert "BioAccess" in client.get("/dossiers/3").text  # route du routeur Vue
        assert "ne pas servir" not in client.get("/..%2Fsecret.txt").text
        r = client.get("/api/inexistante")
        assert r.status_code == 404 and r.json()["detail"]["code"] == "RESSOURCE_INTROUVABLE"
        assert client.get("/api/sante").json()["statut"] == "ok"
