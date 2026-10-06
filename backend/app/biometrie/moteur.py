"""Point d'entrée du moteur biométrique : chargement des modèles et création des sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from .onnx_insightface import ModelesInsightface, VisageDetecte
from .oreille import (EXTRACTEURS_OREILLE, Cote, ExtracteurOreille, GeometrieOreille,
                      cote_oreille_visible, localiser_oreille)
from .qualite import ConfigQualite, en_gris, evaluer_oreille, evaluer_visage, recadrer
from .session import Observation, ObservationOreille, ParametresSession, SessionCapture

TAILLE_APERCU = (96, 144)  # (largeur, hauteur) de la vignette d'oreille renvoyée en aperçu


def decoder_jpeg(image_jpeg: bytes) -> np.ndarray | None:
    """Décode une image JPEG en mémoire (BGR). Renvoie None si l'image est illisible."""
    if not image_jpeg:
        return None
    try:
        image = cv2.imdecode(np.frombuffer(image_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    except cv2.error:
        return None
    if image is None or image.ndim != 3 or min(image.shape[:2]) < 16:
        return None
    return image


class AnalyseurImages:
    """Analyse réelle d'une image : détection, landmarks 3D, lacet, qualité ; le plongement
    ArcFace et la vignette d'oreille ne sont calculés que si la session en a besoin."""

    def __init__(self, modeles: ModelesInsightface, extracteur: ExtracteurOreille,
                 config: ConfigQualite | None = None, geometrie: GeometrieOreille | None = None) -> None:
        self.modeles = modeles
        self.extracteur = extracteur
        self.config = config or ConfigQualite()
        self.geometrie = geometrie or GeometrieOreille()

    def analyser(self, image_jpeg: bytes) -> Observation:
        image = decoder_jpeg(image_jpeg)
        if image is None:
            return Observation(lisible=False)
        return self.analyser_image(image)

    def analyser_image(self, image: np.ndarray) -> Observation:
        h, w = image.shape[:2]
        visages = self.modeles.detecter(image)
        obs = Observation(lisible=True, largeur=w, hauteur=h, nb_visages=len(visages))
        if len(visages) != 1:
            return obs  # aucun ou plusieurs visages : refus explicite, jamais « le plus grand »
        visage = visages[0]
        landmarks = self.modeles.landmarks3d(image, visage)
        obs.bbox = tuple(float(v) for v in visage.bbox)
        obs.lacet = self.modeles.lacet(landmarks)
        obs.cote = cote_oreille_visible(landmarks)
        obs.criteres_visage = evaluer_visage(image, visage.bbox, obs.lacet, self.config)
        obs.calcul_plongement = lambda: self.modeles.plongement(image, visage)
        obs.calcul_oreille = lambda: self.analyser_oreille(image, landmarks)
        return obs

    def analyser_oreille(self, image: np.ndarray, landmarks: np.ndarray) -> ObservationOreille:
        zone = localiser_oreille(landmarks, image.shape, self.geometrie)
        gris = en_gris(recadrer(image, zone.boite))
        criteres = evaluer_oreille(gris, zone.largeur, zone.hauteur, zone.fraction_dans_image, self.config)
        vecteur = self.extracteur.extraire(gris) if all(c.ok for c in criteres) else None
        vignette = cv2.resize(gris, TAILLE_APERCU, interpolation=cv2.INTER_AREA) if gris.size else None
        return ObservationOreille(zone=zone, criteres=criteres, vecteur=vecteur, vignette=vignette)


class MoteurBiometrique:
    """Charge les modèles une seule fois et fabrique les sessions de capture."""

    def __init__(self, dossier_modeles: Path, extracteur_oreille: str = "lbp") -> None:
        if extracteur_oreille not in EXTRACTEURS_OREILLE:
            raise ValueError(
                f"Extracteur d'oreille inconnu : « {extracteur_oreille} » "
                f"(disponibles : {', '.join(EXTRACTEURS_OREILLE)}).")
        self.modeles = ModelesInsightface(Path(dossier_modeles))  # FileNotFoundError si absent
        self.extracteur_oreille: ExtracteurOreille = EXTRACTEURS_OREILLE[extracteur_oreille]()
        self.config_qualite = ConfigQualite()
        self.parametres_session = ParametresSession()
        self.analyseur = AnalyseurImages(self.modeles, self.extracteur_oreille, self.config_qualite)

    def nouvelle_session(
        self,
        mode: Literal["enrolement", "authentification"],
        nb_visage: int,
        nb_oreille: int,
        cote_attendu: Cote | None = None,
        apercu: bool = False,
    ) -> SessionCapture:
        return SessionCapture(
            mode=mode, nb_visage=nb_visage, nb_oreille=nb_oreille, cote_attendu=cote_attendu,
            apercu=apercu, analyseur=self.analyseur, parametres=self.parametres_session,
            extracteur_oreille=self.extracteur_oreille.nom,
        )

    # Accès directs, utiles aux tests et aux futurs outils d'évaluation.
    def detecter(self, image: np.ndarray) -> list[VisageDetecte]:
        return self.modeles.detecter(image)
