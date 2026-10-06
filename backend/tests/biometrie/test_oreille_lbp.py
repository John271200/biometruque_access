"""Extracteur d'oreille LBP « lbp-v1 » et localisation de la zone de l'oreille."""

import numpy as np
import pytest
from skimage import data

from app.biometrie.oreille import (ExtracteurLBP, ExtracteurOreille, GeometrieOreille,
                                   cote_oreille_visible, localiser_oreille)


@pytest.fixture(scope="module")
def extracteur():
    return ExtracteurLBP()


def _vignettes():
    """Vignettes de textures naturelles (pas d'oreilles réelles : aucune photo dans le dépôt)."""
    chat = (data.chelsea()[50:194, 100:196] @ [0.299, 0.587, 0.114]).astype(np.uint8)
    return [data.camera()[60:204, 200:296], data.moon()[100:244, 100:196],
            data.brick()[100:244, 100:196], chat]


def _bruitee(vignette, rng):
    v = vignette.astype(np.float64) * 1.05 + rng.normal(0, 4, vignette.shape)
    return np.clip(v, 0, 255).astype(np.uint8)


def test_interface_et_dimension(extracteur):
    assert isinstance(extracteur, ExtracteurOreille)
    assert extracteur.nom == "lbp-v1"
    assert extracteur.dimension >= 256  # BioHash 256 bits
    v = extracteur.extraire(_vignettes()[0])
    assert v.shape == (extracteur.dimension,) and v.dtype == np.float32
    assert np.linalg.norm(v) == pytest.approx(1.0, abs=1e-5)
    assert abs(float(v.mean())) < 1e-3  # centrage avant normalisation


def test_independant_de_la_taille_et_couleur(extracteur):
    vignette = _vignettes()[0]
    couleur = np.repeat(vignette[:, :, None], 3, axis=2)
    assert np.allclose(extracteur.extraire(couleur), extracteur.extraire(vignette))
    grande = np.kron(vignette, np.ones((2, 2), dtype=np.uint8))
    assert float(extracteur.extraire(grande) @ extracteur.extraire(vignette)) > 0.9


def test_stabilite_meme_vignette_bruitee_vs_vignette_differente(extracteur):
    rng = np.random.default_rng(0)
    vignettes = _vignettes()
    vecteurs = [extracteur.extraire(v) for v in vignettes]
    for i, v in enumerate(vignettes):
        meme = float(extracteur.extraire(_bruitee(v, rng)) @ vecteurs[i])
        autres = [float(vecteurs[i] @ vecteurs[j]) for j in range(len(vignettes)) if j != i]
        assert meme > 0.8
        assert meme > max(autres) + 0.1


def test_vignette_vide_refusee(extracteur):
    with pytest.raises(ValueError):
        extracteur.extraire(np.zeros((0, 0), dtype=np.uint8))


def _landmarks_synthetiques(decalage_nez: float) -> np.ndarray:
    """68 points 2D grossiers d'un visage de 200 px de haut centré en (300, 250)."""
    lm = np.zeros((68, 3), dtype=np.float32)
    lm[0:17, 0] = np.linspace(220, 380, 17)  # mâchoire : 0 à gauche de l'image, 16 à droite
    lm[0:17, 1] = 220 + 100 * np.sin(np.linspace(0, np.pi, 17))
    lm[17:27] = [300, 170, 0]
    lm[19, :2], lm[24, :2] = (270, 170), (330, 170)
    lm[36:42] = [270, 200, 0]
    lm[42:48] = [330, 200, 0]
    lm[30, :2] = (300 + decalage_nez, 250)
    lm[8, :2] = (300, 320)
    return lm


def test_cote_par_la_geometrie_et_zone_derriere_la_machoire():
    # Nez vers la droite de l'image : l'utilisateur tourne vers SA gauche → oreille droite,
    # visible à gauche de la tête sur l'image (derrière le point de contour 0).
    lm = _landmarks_synthetiques(+25)
    assert cote_oreille_visible(lm) == "droite"
    zone = localiser_oreille(lm, (480, 640, 3))
    assert zone.cote == "droite"
    assert zone.boite[2] <= lm[0, 0] + 0.06 * 150 and zone.boite[0] < lm[0, 0]
    hauteur_visage = 150.0  # sourcils (170) → menton (320)
    g = GeometrieOreille()
    assert zone.boite[3] - zone.boite[1] == pytest.approx((g.au_dessus + g.au_dessous) * hauteur_visage)
    assert zone.fraction_dans_image == pytest.approx(1.0)

    lm = _landmarks_synthetiques(-25)
    assert cote_oreille_visible(lm) == "gauche"
    zone = localiser_oreille(lm, (480, 640, 3))
    assert zone.boite[0] >= lm[16, 0] - 0.06 * 150 and zone.boite[2] > lm[16, 0]


def test_zone_bornee_a_l_image():
    lm = _landmarks_synthetiques(+25)
    lm[:, 0] -= 200  # visage collé au bord gauche : l'oreille sort du cadre
    zone = localiser_oreille(lm, (480, 640, 3))
    assert zone.boite[0] == 0.0
    assert zone.fraction_dans_image < 0.8
