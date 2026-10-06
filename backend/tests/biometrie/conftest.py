"""Fixtures communes aux tests du moteur biométrique.

Aucune photo n'est enregistrée dans le dépôt : l'image de test publique d'InsightFace
(t1.jpg, photo de groupe) est téléchargée à la volée dans un cache hors dépôt
(``~/.cache/bioaccess-tests``). Hors ligne ou sans modèles, les tests concernés sont ignorés.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.biometrie.onnx_insightface import FICHIERS_MODELES

RACINE_BACKEND = Path(__file__).resolve().parents[2]
DOSSIER_MODELES = RACINE_BACKEND / "models" / "buffalo_l"
URL_T1 = ("https://raw.githubusercontent.com/deepinsight/insightface/master/"
          "python-package/insightface/data/images/t1.jpg")


def _dossier_cache(tmp_path_factory) -> Path:
    cache = Path(os.environ.get("BIOACCESS_CACHE_TESTS", Path.home() / ".cache" / "bioaccess-tests"))
    try:
        cache.mkdir(parents=True, exist_ok=True)
        return cache
    except OSError:
        return tmp_path_factory.mktemp("bioaccess-cache")


@pytest.fixture(scope="session")
def moteur():
    """Moteur biométrique réel (ignoré si les modèles buffalo_l sont absents)."""
    if not all((DOSSIER_MODELES / nom).is_file() for nom in FICHIERS_MODELES.values()):
        pytest.skip("Modèles buffalo_l absents : lancez « python scripts/telecharger_modeles.py ».")
    from app.biometrie import MoteurBiometrique

    return MoteurBiometrique(DOSSIER_MODELES)


@pytest.fixture(scope="session")
def image_t1(tmp_path_factory) -> np.ndarray:
    """Photo de groupe publique d'InsightFace (BGR), téléchargée dans un cache temporaire."""
    chemin = _dossier_cache(tmp_path_factory) / "t1.jpg"
    if not chemin.is_file():
        try:
            with urllib.request.urlopen(URL_T1, timeout=20) as reponse:
                donnees = reponse.read()
        except Exception as exc:  # hors ligne, proxy…
            pytest.skip(f"Image de test t1.jpg indisponible (hors ligne ?) : {exc}")
        temporaire = chemin.with_suffix(".tmp")
        temporaire.write_bytes(donnees)
        temporaire.replace(chemin)
    image = cv2.imread(str(chemin), cv2.IMREAD_COLOR)
    if image is None:
        chemin.unlink(missing_ok=True)
        pytest.skip("Image de test t1.jpg illisible.")
    return image


def encoder_jpeg(image: np.ndarray, qualite: int = 92) -> bytes:
    ok, tampon = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, qualite])
    assert ok
    return tampon.tobytes()
