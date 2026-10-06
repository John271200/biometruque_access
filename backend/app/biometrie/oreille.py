"""Oreille : localisation de la zone à partir des landmarks 3D et extraction de caractéristiques.

L'interface ``ExtracteurOreille`` permet de brancher plus tard un extracteur appris (ONNX) ;
le MVP n'implémente que ``ExtracteurLBP`` (« lbp-v1 »), descripteur de texture classique
en reconnaissance de l'oreille.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

import cv2
import numpy as np
from skimage.feature import local_binary_pattern

from .qualite import en_gris

Cote = Literal["droite", "gauche"]


@runtime_checkable
class ExtracteurOreille(Protocol):
    """Contrat d'un extracteur de caractéristiques d'oreille."""

    nom: str  # identifiant versionné, enregistré avec le gabarit (ex. « lbp-v1 »)
    dimension: int  # dimension du vecteur produit (≥ 256 pour le BioHashing 256 bits)

    def extraire(self, vignette_gris: np.ndarray) -> np.ndarray:
        """Vecteur float32 L2-normalisé de taille ``dimension``."""
        ...


class ExtracteurLBP:
    """Motifs binaires locaux (LBP) uniformes multi-échelles, histogrammes par blocs.

    Chaîne : vignette en niveaux de gris → taille fixe 96×144 (largeur × hauteur) →
    léger lissage gaussien (σ = 1 px, atténue le bruit de capteur que l'égalisation
    amplifierait) → égalisation locale CLAHE → LBP uniformes à deux échelles →
    histogrammes normalisés sur une grille 3 × 4 blocs → racine carrée (noyau de
    Hellinger) → centrage (soustraction de la moyenne des composantes) → normalisation L2.

    Échelles : (8 voisins, rayon 1) en LBP uniforme classique « u2 » à 59 classes
    (``nri_uniform`` de scikit-image, sensible à l'orientation des contours du pavillon) et
    (16 voisins, rayon 2) en uniforme invariant par rotation à 18 classes (``uniform``).
    Dimension : 12 blocs × (59 + 18) classes = 924 (≥ 256 exigé par le BioHashing).

    Choix mesuré sur des vignettes de textures (zones latérales des visages de t1.jpg et
    images de scikit-image, pas de vraies oreilles) : séparation légitime / imposteur
    d' ≈ 3,2 contre ≈ 2,3 avec la variante 10 + 18 classes invariante par rotation, puis
    ≈ 3,9 avec le lissage préalable (sans lui, une zone peu texturée bruitée devient
    méconnaissable : cosinus 0,57 avec l'originale, contre 0,93 avec lissage).

    Le centrage retire la composante commune à tous les histogrammes (direction « tous
    les bins égaux ») et augmente le contraste angulaire entre deux oreilles ; un centrage
    sur une moyenne de population (apprise sur de vraies oreilles) serait plus efficace :
    piste d'amélioration une fois un jeu de captures disponible.
    """

    nom = "lbp-v1"
    taille = (96, 144)  # (largeur, hauteur) de la vignette normalisée
    grille = (3, 4)  # (colonnes, lignes) de blocs
    # (nombre de voisins P, rayon R, méthode scikit-image, nombre de classes)
    echelles = ((8, 1, "nri_uniform", 59), (16, 2, "uniform", 18))
    lissage_sigma = 1.0  # pixels, sur la vignette 96×144
    clahe_limite = 2.0
    clahe_tuiles = (4, 4)

    def __init__(self) -> None:
        nb_blocs = self.grille[0] * self.grille[1]
        self.dimension = nb_blocs * sum(nb for _, _, _, nb in self.echelles)

    def normaliser_vignette(self, vignette_gris: np.ndarray) -> np.ndarray:
        """Vignette 96×144 égalisée (CLAHE), uint8 — c'est aussi l'aperçu montré à l'utilisateur."""
        gris = en_gris(np.asarray(vignette_gris))
        if gris.dtype != np.uint8:
            gris = np.clip(gris, 0, 255).astype(np.uint8)
        if gris.size == 0:
            raise ValueError("Vignette d'oreille vide.")
        redim = cv2.resize(gris, self.taille, interpolation=cv2.INTER_AREA)
        lisse = cv2.GaussianBlur(redim, (0, 0), self.lissage_sigma)
        clahe = cv2.createCLAHE(clipLimit=self.clahe_limite, tileGridSize=self.clahe_tuiles)
        return clahe.apply(lisse)

    def extraire(self, vignette_gris: np.ndarray) -> np.ndarray:
        image = self.normaliser_vignette(vignette_gris)
        h, w = image.shape
        bords_x = np.linspace(0, w, self.grille[0] + 1).astype(int)
        bords_y = np.linspace(0, h, self.grille[1] + 1).astype(int)
        histogrammes = []
        for p, r, methode, nb_classes in self.echelles:
            codes = local_binary_pattern(image, p, r, method=methode).astype(np.int64)
            for i in range(self.grille[1]):
                for j in range(self.grille[0]):
                    bloc = codes[bords_y[i]:bords_y[i + 1], bords_x[j]:bords_x[j + 1]]
                    hist = np.bincount(bloc.ravel(), minlength=nb_classes)[:nb_classes]
                    histogrammes.append(hist.astype(np.float64) / max(bloc.size, 1))
        vecteur = np.sqrt(np.concatenate(histogrammes))  # noyau de Hellinger
        vecteur -= vecteur.mean()  # centrage
        norme = np.linalg.norm(vecteur)
        if norme < 1e-12:
            raise ValueError("Vignette d'oreille sans texture exploitable.")
        return (vecteur / norme).astype(np.float32)


EXTRACTEURS_OREILLE = {"lbp": ExtracteurLBP}


# ------------------------------------------------------------------------ localisation
@dataclass
class GeometrieOreille:
    """Position de la zone de l'oreille, en fractions de la hauteur du visage ``H``.

    ``H`` = distance entre le milieu des sourcils (points 19 et 24) et le menton (point 8).
    Repères anatomiques : l'oreille mesure ≈ 0,5 H (du niveau des sourcils à la base du
    nez), ≈ 0,3 H de large, et son bord avant (tragus) touche le point de contour de la
    mâchoire situé à hauteur des yeux (point 0 côté droit du sujet, 16 côté gauche).
    Les marges absorbent l'imprécision des landmarks en pose de profil.
    VALEURS NON VALIDÉES sur de vraies images de profil : à ajuster sur captures réelles.
    """

    recouvrement: float = 0.05  # la zone empiète de 0,05 H sur la joue (côté nez)
    profondeur: float = 0.42  # puis s'étend de 0,42 H vers l'arrière de la tête
    au_dessus: float = 0.25  # bord haut : 0,25 H au-dessus du point de contour
    au_dessous: float = 0.45  # bord bas : 0,45 H au-dessous (lobe compris)


@dataclass
class ZoneOreille:
    cote: Cote  # oreille du sujet visible à l'image
    boite: tuple[float, float, float, float]  # bornée à l'image (pixels)
    boite_complete: tuple[float, float, float, float]  # avant bornage
    fraction_dans_image: float  # aire bornée / aire complète

    @property
    def largeur(self) -> float:
        return self.boite[2] - self.boite[0]

    @property
    def hauteur(self) -> float:
        return self.boite[3] - self.boite[1]


def cote_oreille_visible(landmarks3d: np.ndarray) -> Cote:
    """Côté de l'oreille exposée, déterminé par la géométrie (pas par le signe du lacet).

    Image NON miroir : si l'utilisateur tourne la tête vers SA gauche, son nez part vers la
    droite de l'image et c'est son oreille DROITE qui devient visible (côté gauche de la
    tête à l'image) ; et inversement.
    """
    lm = np.asarray(landmarks3d)
    milieu_yeux_x = float(lm[36:48, 0].mean())
    return "droite" if float(lm[30, 0]) > milieu_yeux_x else "gauche"


def localiser_oreille(landmarks3d: np.ndarray, forme_image: tuple[int, ...],
                      geometrie: GeometrieOreille | None = None) -> ZoneOreille:
    """Zone rectangulaire de l'oreille visible, à partir des 68 points 3D."""
    g = geometrie or GeometrieOreille()
    lm = np.asarray(landmarks3d, dtype=np.float64)
    cote = cote_oreille_visible(lm)
    hauteur_visage = float(np.linalg.norm(lm[8, :2] - (lm[19, :2] + lm[24, :2]) / 2))
    hauteur_visage = max(hauteur_visage, 1.0)
    # Oreille droite du sujet : contour 0, l'arrière de la tête est vers la gauche de l'image.
    x0, y0 = (lm[0, 0], lm[0, 1]) if cote == "droite" else (lm[16, 0], lm[16, 1])
    sens = -1.0 if cote == "droite" else 1.0
    xa = x0 - sens * g.recouvrement * hauteur_visage
    xb = x0 + sens * g.profondeur * hauteur_visage
    complete = (float(min(xa, xb)), float(y0 - g.au_dessus * hauteur_visage),
                float(max(xa, xb)), float(y0 + g.au_dessous * hauteur_visage))
    h, w = forme_image[:2]
    bornee = (max(complete[0], 0.0), max(complete[1], 0.0),
              min(complete[2], float(w)), min(complete[3], float(h)))
    aire = (complete[2] - complete[0]) * (complete[3] - complete[1])
    aire_bornee = max(bornee[2] - bornee[0], 0.0) * max(bornee[3] - bornee[1], 0.0)
    return ZoneOreille(cote=cote, boite=bornee, boite_complete=complete,
                       fraction_dans_image=float(aire_bornee / aire) if aire > 0 else 0.0)
