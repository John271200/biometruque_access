"""Tests sur les vrais modèles buffalo_l avec la photo de groupe publique t1.jpg.

Ignorés si les modèles sont absents ou si l'image ne peut pas être téléchargée.
"""

from __future__ import annotations

import statistics
import time
import warnings

import cv2
import numpy as np
import pytest

from app.biometrie import MoteurBiometrique, SessionCapture
from app.biometrie.onnx_insightface import (FICHIERS_MODELES, GABARIT_ARCFACE,
                                            normalisation_insightface, similitude_umeyama)
from app.biometrie.oreille import cote_oreille_visible, localiser_oreille

from .conftest import DOSSIER_MODELES, encoder_jpeg


class Horloge:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture(scope="module")
def visages_t1(moteur, image_t1):
    """Détections de t1.jpg avec landmarks 3D et lacet."""
    resultat = []
    for v in moteur.modeles.detecter(image_t1):
        lm = moteur.modeles.landmarks3d(image_t1, v)
        resultat.append((v, lm, moteur.modeles.lacet(lm)))
    return resultat


def _recadrage_un_visage(image, visage, facteur_largeur=2.6, ratio=4 / 3):
    """Recadrage 4:3 centré sur un visage, assez serré pour exclure ses voisins."""
    cx, cy = visage.centre
    largeur = visage.largeur * facteur_largeur
    hauteur = largeur / ratio
    x1, y1 = int(max(cx - largeur / 2, 0)), int(max(cy - hauteur / 2, 0))
    x2, y2 = int(min(cx + largeur / 2, image.shape[1])), int(min(cy + hauteur / 2, image.shape[0]))
    return image[y1:y2, x1:x2].copy()


@pytest.fixture(scope="module")
def visage_frontal(visages_t1):
    return min(visages_t1, key=lambda x: abs(x[2]))


@pytest.fixture(scope="module")
def image_webcam(image_t1, visage_frontal):
    """Image 640×480 « type webcam » contenant un seul visage de face."""
    return cv2.resize(_recadrage_un_visage(image_t1, visage_frontal[0]), (640, 480))


# ------------------------------------------------------------------------ chargement
def test_modeles_absents_message_clair(tmp_path):
    with pytest.raises(FileNotFoundError, match="telecharger_modeles.py"):
        MoteurBiometrique(tmp_path)


def test_extracteur_oreille_inconnu(moteur):
    with pytest.raises(ValueError):
        MoteurBiometrique(DOSSIER_MODELES, extracteur_oreille="cnn")


def test_normalisation_determinee_comme_insightface(moteur):
    # 1k3d68 (converti de MXNet) commence par « bn_data » → normalisation intégrée au graphe.
    assert normalisation_insightface(DOSSIER_MODELES / FICHIERS_MODELES["landmarks"], 128.0) == (0.0, 1.0)
    assert normalisation_insightface(DOSSIER_MODELES / FICHIERS_MODELES["reconnaissance"], 127.5) == (127.5, 127.5)


def test_umeyama_identique_a_scikit_image():
    from skimage.transform import SimilarityTransform

    rng = np.random.default_rng(0)
    source = GABARIT_ARCFACE * 1.7 + rng.normal(0, 2, (5, 2)) + 40
    if hasattr(SimilarityTransform, "from_estimate"):
        reference = SimilarityTransform.from_estimate(source, GABARIT_ARCFACE).params[:2]
    else:
        t = SimilarityTransform()
        t.estimate(source, GABARIT_ARCFACE)
        reference = t.params[:2]
    assert np.allclose(similitude_umeyama(source, GABARIT_ARCFACE), reference, atol=1e-6)


# ------------------------------------------------------------------------ détection / qualité
def test_detection_plusieurs_visages_refus(moteur, image_t1, visages_t1):
    assert len(visages_t1) >= 5
    for visage, lm, _ in visages_t1:
        assert visage.score >= 0.5 and visage.kps.shape == (5, 2) and lm.shape == (68, 3)
    session = moteur.nouvelle_session("enrolement", 5, 5)
    retour = session.traiter_image(encoder_jpeg(image_t1))
    assert retour.etape == "visage" and not retour.image_retenue
    assert retour.criteres[0].code == "visage_unique" and not retour.criteres[0].ok
    assert "Plusieurs visages" in retour.message


def test_un_seul_visage_frontal_qualite_et_plongement(moteur, image_webcam):
    obs = moteur.analyseur.analyser(encoder_jpeg(image_webcam))
    assert obs.nb_visages == 1
    assert abs(obs.lacet) < 15
    echecs = [c for c in obs.criteres_visage if not c.ok]
    assert not echecs, echecs  # une image correcte passe les critères de qualité
    v = obs.plongement()
    assert v.shape == (512,) and v.dtype == np.float32
    assert np.linalg.norm(v) == pytest.approx(1.0, abs=1e-5)


def test_image_illisible_avec_le_vrai_analyseur(moteur):
    session = moteur.nouvelle_session("enrolement", 5, 5)
    retour = session.traiter_image(b"ceci n'est pas un JPEG")
    assert retour.criteres[0].code == "image" and retour.criteres[0].message == "Image illisible"
    assert not session.echouee
    assert session.traiter_image(b"").criteres[0].code == "image"


def test_image_floue_refusee(moteur, image_webcam):
    floue = cv2.GaussianBlur(image_webcam, (0, 0), 6)
    obs = moteur.analyseur.analyser(encoder_jpeg(floue))
    if obs.nb_visages != 1:
        pytest.skip("Visage non détecté sur l'image très floue")
    assert any(c.code == "nettete" and not c.ok for c in obs.criteres_visage)


# ------------------------------------------------------------------------ ArcFace
def test_meme_visage_altere_cosinus_eleve(moteur, image_webcam):
    rng = np.random.default_rng(0)
    altere = cv2.GaussianBlur(image_webcam, (0, 0), 1.0)
    altere = cv2.convertScaleAbs(altere, alpha=1.15, beta=12).astype(np.float64)
    altere = np.clip(altere + rng.normal(0, 5, altere.shape), 0, 255).astype(np.uint8)
    altere = cv2.warpAffine(altere, cv2.getRotationMatrix2D((320, 240), 4, 1.03), (640, 480))
    a = moteur.analyseur.analyser(encoder_jpeg(image_webcam)).plongement()
    b = moteur.analyseur.analyser(encoder_jpeg(altere, 70)).plongement()
    assert float(a @ b) > 0.8


def test_personnes_differentes_cosinus_bas(moteur, image_t1, visages_t1):
    plongements = np.stack([moteur.modeles.plongement(image_t1, v) for v, _, _ in visages_t1])
    cosinus = plongements @ plongements.T
    hors_diagonale = cosinus[~np.eye(len(plongements), dtype=bool)]
    assert hors_diagonale.max() < 0.35


# ------------------------------------------------------------------------ lacet et oreille
def test_lacet_image_miroir_signe_oppose(moteur, image_t1, visages_t1):
    miroir = image_t1[:, ::-1].copy()
    largeur = image_t1.shape[1]
    verifies = 0
    for visage, lm, lacet in visages_t1:
        cx, cy = visage.centre
        # Visage correspondant dans l'image miroir (centre symétrique).
        correspondant = min(moteur.modeles.detecter(miroir),
                            key=lambda v: np.hypot(v.centre[0] - (largeur - cx), v.centre[1] - cy))
        lm_miroir = moteur.modeles.landmarks3d(miroir, correspondant)
        lacet_miroir = moteur.modeles.lacet(lm_miroir)
        if abs(lacet) >= 10:
            assert np.sign(lacet_miroir) == -np.sign(lacet)
            assert abs(abs(lacet_miroir) - abs(lacet)) < 0.25 * abs(lacet) + 3
            assert cote_oreille_visible(lm_miroir) != cote_oreille_visible(lm)
            verifies += 1
    assert verifies >= 2


def test_lacet_coherent_avec_la_position_du_nez(visages_t1):
    """Lacet > 0 ⇔ nez vers la droite de l'image ⇔ oreille droite exposée."""
    for _, lm, lacet in visages_t1:
        if abs(lacet) >= 5:
            assert (lacet > 0) == (cote_oreille_visible(lm) == "droite")


def test_zone_oreille_sur_visage_tourne(moteur, image_t1, visages_t1):
    visage, lm, lacet = max(visages_t1, key=lambda x: abs(x[2]))
    assert abs(lacet) > 30  # t1.jpg contient un visage nettement tourné
    zone = localiser_oreille(lm, image_t1.shape)
    nez_x = float(lm[30, 0])
    centre_zone = (zone.boite[0] + zone.boite[2]) / 2
    # La zone est du côté opposé au nez, derrière le contour de la mâchoire.
    if zone.cote == "droite":
        assert centre_zone < nez_x and centre_zone < lm[0, 0]
    else:
        assert centre_zone > nez_x and centre_zone > lm[16, 0]
    oreille = moteur.analyseur.analyser_oreille(image_t1, lm)
    assert {c.code for c in oreille.criteres} == {"oreille_cadrage", "oreille_taille",
                                                  "oreille_nettete", "oreille_contraste"}
    vecteur = moteur.extracteur_oreille.extraire(cv2.cvtColor(image_t1, cv2.COLOR_BGR2GRAY)[
        int(zone.boite[1]):int(zone.boite[3]), int(zone.boite[0]):int(zone.boite[2])])
    assert vecteur.shape == (moteur.extracteur_oreille.dimension,)


# ------------------------------------------------------------------------ session réelle
def test_session_reelle_etape_visage(moteur, image_webcam):
    """Cinq captures de face réelles (légèrement bruitées) → passage à la rotation."""
    horloge = Horloge()
    session = SessionCapture("enrolement", 5, 5, analyseur=moteur.analyseur, horloge=horloge)
    rng = np.random.default_rng(1)
    for i in range(5):
        horloge.t += 0.5
        bruitee = np.clip(image_webcam + rng.normal(0, 3, image_webcam.shape), 0, 255).astype(np.uint8)
        retour = session.traiter_image(encoder_jpeg(bruitee))
        assert retour.image_retenue, retour.message
    assert retour.etape == "rotation" and retour.captures_visage == 5
    assert retour.message == "Tournez lentement la tête vers la gauche"
    assert retour.cadre_visage is not None and all(0 <= v <= 1 for v in retour.cadre_visage)


def test_temps_de_traitement_par_image(moteur, image_webcam, capsys):
    """Pire cas d'une image : détection + landmarks 3D + qualité + plongement ArcFace."""
    jpeg = encoder_jpeg(image_webcam)
    moteur.analyseur.analyser(jpeg).plongement()  # préchauffage
    durees = []
    for _ in range(7):
        debut = time.perf_counter()
        moteur.analyseur.analyser(jpeg).plongement()
        durees.append((time.perf_counter() - debut) * 1000)
    mediane = statistics.median(durees)
    with capsys.disabled():
        print(f"\n[BioAccess] temps de traitement d'une image 640×480 : médiane {mediane:.0f} ms "
              f"(min {min(durees):.0f} ms, max {max(durees):.0f} ms ; objectif < 300 ms)")
    if mediane >= 300:
        warnings.warn(f"Temps de traitement {mediane:.0f} ms ≥ objectif 300 ms sur ce CPU")
    assert mediane < 1500  # garde-fou large : les machines d'intégration varient
