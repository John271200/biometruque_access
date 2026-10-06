"""Critères de qualité des captures (visage de face et vignette d'oreille).

Chaque critère renvoie un ``Critere(code, ok, message)`` dont le message, en français, dit
à l'utilisateur quoi faire. Toutes les constantes sont regroupées dans ``ConfigQualite``.
Les seuils sont volontairement **tolérants** : une webcam de portable donne des images un
peu floues et mal éclairées, qui doivent passer si elles sont exploitables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np


@dataclass
class Critere:
    code: str
    ok: bool
    message: str  # message français actionnable


@dataclass
class ConfigQualite:
    """Seuils de qualité (provisoires, à ajuster sur de vraies captures webcam)."""

    # --- Visage -------------------------------------------------------------------
    # Taille : plus petit côté de la boîte en pixels ET hauteur relative à l'image.
    # Webcam 640×480 à 60 cm : visage ≈ 180 px (≈ 0,37 de la hauteur) ; à 1 m ≈ 110 px.
    taille_min_px: float = 80.0
    taille_min_relative: float = 0.15
    # Centrage : le centre de la boîte doit rester à moins de 25 % (de la largeur / hauteur
    # de l'image) du centre de l'image.
    decentrage_max: float = 0.25
    # Netteté : variance du Laplacien sur le recadrage du visage redimensionné à
    # 112×112 (taille fixe → mesure indépendante de la distance à la caméra).
    # Mesuré sur les visages (~100 px) de t1.jpg : nets ≈ 110–220 ; même image en demi-
    # résolution (webcam médiocre) ≈ 38–63 ; flou gaussien σ = 1,5 px ≈ 22–38 ;
    # σ = 3 px ≈ 7–15. Seuil tolérant : 25 (une webcam de portable correcte passe).
    taille_nettete_visage: int = 112
    nettete_min_visage: float = 25.0
    # Éclairage : moyenne et écart-type des niveaux de gris du recadrage du visage.
    luminosite_min: float = 45.0
    luminosite_max: float = 215.0
    contraste_min_visage: float = 18.0
    # Frontalité : |lacet| maximal pour une capture « de face » (degrés).
    lacet_frontal_max: float = 15.0

    # --- Vignette d'oreille --------------------------------------------------------
    # Part minimale de la zone de l'oreille située dans l'image (le reste est hors cadre).
    oreille_fraction_min: float = 0.8
    # Dimensions minimales de la zone (pixels) : en dessous, la texture n'est pas exploitable.
    oreille_largeur_min_px: float = 32.0
    oreille_hauteur_min_px: float = 48.0
    # Netteté de la vignette redimensionnée à la taille de l'extracteur (96×144) ; même
    # ordre de grandeur que pour le visage, un peu plus tolérant (peau lisse du pavillon).
    taille_nettete_oreille: tuple[int, int] = (96, 144)  # (largeur, hauteur)
    nettete_min_oreille: float = 20.0
    # Anti-occultation : une oreille cachée par des cheveux, un bonnet ou un écouteur
    # donne une zone sombre et peu contrastée ; une oreille visible présente un contraste
    # marqué (pavillon / ombres / peau). Écart-type minimal des niveaux de gris.
    contraste_min_oreille: float = 20.0
    luminosite_min_oreille: float = 35.0


# ---------------------------------------------------------------------------- mesures
def recadrer(image: np.ndarray, boite: Sequence[float]) -> np.ndarray:
    """Recadrage borné à l'image (renvoie une image vide si la boîte est hors champ)."""
    h, w = image.shape[:2]
    x1, y1 = max(int(round(boite[0])), 0), max(int(round(boite[1])), 0)
    x2, y2 = min(int(round(boite[2])), w), min(int(round(boite[3])), h)
    if x2 <= x1 or y2 <= y1:
        return image[0:0, 0:0]
    return image[y1:y2, x1:x2]


def en_gris(image: np.ndarray) -> np.ndarray:
    if image.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    return image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def mesure_nettete(gris: np.ndarray, taille: tuple[int, int]) -> float:
    """Variance du Laplacien après redimensionnement à une taille fixe (largeur, hauteur)."""
    if gris.size == 0:
        return 0.0
    redim = cv2.resize(gris, taille, interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(redim, cv2.CV_64F).var())


# ---------------------------------------------------------------------------- visage
def critere_visage_unique(nb_visages: int) -> Critere:
    if nb_visages == 0:
        return Critere("visage_unique", False, "Aucun visage détecté : placez-vous face à la caméra")
    if nb_visages > 1:
        return Critere("visage_unique", False,
                       "Plusieurs visages détectés : une seule personne doit apparaître à l'image")
    return Critere("visage_unique", True, "Un seul visage détecté")


def critere_frontalite(lacet: float | None, config: ConfigQualite) -> Critere:
    if lacet is None or abs(lacet) > config.lacet_frontal_max:
        return Critere("frontalite", False, "Regardez droit vers la caméra")
    return Critere("frontalite", True, "Visage bien de face")


def evaluer_visage(image_bgr: np.ndarray, bbox: Sequence[float], lacet: float | None,
                   config: ConfigQualite) -> list[Critere]:
    """Critères d'une capture de face pour un visage unique déjà détecté.

    (Le critère « un seul visage » est évalué en amont : plusieurs visages = refus
    explicite, on ne choisit jamais « le plus grand ».)
    """
    h, w = image_bgr.shape[:2]
    x1, y1, x2, y2 = (float(v) for v in bbox)
    criteres: list[Critere] = []

    if min(x2 - x1, y2 - y1) < config.taille_min_px or (y2 - y1) / h < config.taille_min_relative:
        criteres.append(Critere("taille", False, "Visage trop petit : rapprochez-vous de la caméra"))
    else:
        criteres.append(Critere("taille", True, "Distance à la caméra correcte"))

    cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
    if abs(cx - 0.5) > config.decentrage_max or abs(cy - 0.5) > config.decentrage_max:
        criteres.append(Critere("centrage", False,
                                "Visage décentré : placez votre visage au centre de l'image"))
    else:
        criteres.append(Critere("centrage", True, "Visage bien centré"))

    gris = en_gris(recadrer(image_bgr, bbox))
    taille = (config.taille_nettete_visage, config.taille_nettete_visage)
    if mesure_nettete(gris, taille) < config.nettete_min_visage:
        criteres.append(Critere("nettete", False,
                                "Image floue : restez immobile et vérifiez que l'objectif est propre"))
    else:
        criteres.append(Critere("nettete", True, "Image nette"))

    moyenne = float(gris.mean()) if gris.size else 0.0
    ecart = float(gris.std()) if gris.size else 0.0
    if moyenne < config.luminosite_min:
        criteres.append(Critere("eclairage", False,
                                "Visage trop sombre : éclairez votre visage (lampe ou fenêtre face à vous)"))
    elif moyenne > config.luminosite_max:
        criteres.append(Critere("eclairage", False,
                                "Visage surexposé : évitez la lumière directe et le contre-jour"))
    elif ecart < config.contraste_min_visage:
        criteres.append(Critere("eclairage", False,
                                "Contraste insuffisant : améliorez l'éclairage de votre visage"))
    else:
        criteres.append(Critere("eclairage", True, "Éclairage correct"))

    criteres.append(critere_frontalite(lacet, config))
    return criteres


# ---------------------------------------------------------------------------- oreille
def evaluer_oreille(vignette_gris: np.ndarray, largeur_zone: float, hauteur_zone: float,
                    fraction_dans_image: float, config: ConfigQualite) -> list[Critere]:
    """Critères de la vignette d'oreille (zone déjà localisée et bornée à l'image)."""
    criteres: list[Critere] = []
    if fraction_dans_image < config.oreille_fraction_min:
        criteres.append(Critere("oreille_cadrage", False,
                                "Oreille hors du cadre : décalez-vous pour que votre oreille soit dans l'image"))
    else:
        criteres.append(Critere("oreille_cadrage", True, "Oreille dans le cadre"))

    if largeur_zone < config.oreille_largeur_min_px or hauteur_zone < config.oreille_hauteur_min_px:
        criteres.append(Critere("oreille_taille", False,
                                "Oreille trop petite à l'image : rapprochez-vous de la caméra"))
    else:
        criteres.append(Critere("oreille_taille", True, "Taille de l'oreille correcte"))

    if mesure_nettete(vignette_gris, config.taille_nettete_oreille) < config.nettete_min_oreille:
        criteres.append(Critere("oreille_nettete", False, "Oreille floue : restez immobile un instant"))
    else:
        criteres.append(Critere("oreille_nettete", True, "Oreille nette"))

    moyenne = float(vignette_gris.mean()) if vignette_gris.size else 0.0
    ecart = float(vignette_gris.std()) if vignette_gris.size else 0.0
    if ecart < config.contraste_min_oreille or moyenne < config.luminosite_min_oreille:
        criteres.append(Critere(
            "oreille_contraste", False,
            "Oreille masquée ou mal éclairée : dégagez-la (cheveux, écouteurs, bonnet) et éclairez-la"))
    else:
        criteres.append(Critere("oreille_contraste", True, "Oreille dégagée"))
    return criteres
