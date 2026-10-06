"""Moteur biométrique BioAccess : fusion visage (ArcFace) + oreille (LBP).

Interface figée par ``docs/mvp/CONTRAT-MVP.md`` (section 2).
"""

from .decision import Decision, ParametresDecision, decider
from .moteur import MoteurBiometrique
from .protection import Chiffreur, ErreurIntegrite, biohash, generer_jeton, similarite_hamming
from .session import ResultatCapture, RetourImage, SessionCapture

__all__ = [
    "MoteurBiometrique",
    "SessionCapture",
    "RetourImage",
    "ResultatCapture",
    "generer_jeton",
    "biohash",
    "similarite_hamming",
    "Chiffreur",
    "ErreurIntegrite",
    "ParametresDecision",
    "Decision",
    "decider",
]
