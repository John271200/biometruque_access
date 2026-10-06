"""Script de téléchargement : cas « modèles déjà présents » (aucun accès réseau)."""

import importlib.util
from pathlib import Path

import pytest

CHEMIN_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "telecharger_modeles.py"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("telecharger_modeles", CHEMIN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_modeles_deja_presents_rien_a_telecharger(script, tmp_path, monkeypatch, capsys):
    for nom in script.MODELES_UTILES:
        (tmp_path / nom).write_bytes(b"factice")

    def interdit(*args, **kwargs):
        raise AssertionError("aucun téléchargement ne doit avoir lieu")

    monkeypatch.setattr(script.urllib.request, "urlopen", interdit)
    assert script.main(["--dossier", str(tmp_path)]) == 0
    sortie = capsys.readouterr().out
    assert "déjà présents" in sortie
    assert "non commercial" in sortie


def test_detection_modeles_manquants(script, tmp_path):
    assert not script.modeles_presents(tmp_path)
    (tmp_path / "det_10g.onnx").write_bytes(b"x")
    assert not script.modeles_presents(tmp_path)
