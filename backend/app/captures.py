"""Sessions de capture biométrique en cours, gardées en mémoire.

Chaque session est protégée par un verrou global, expire après 120 s d'inactivité
(nettoyage paresseux à chaque accès) et ne traite qu'une image à la fois.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.erreurs import ErreurAPI

DUREE_INACTIVITE_S = 120


def _introuvable() -> ErreurAPI:
    return ErreurAPI(
        404, "SESSION_INTROUVABLE",
        "Session de capture introuvable ou expirée. Recommencez la capture.",
    )


@dataclass
class EntreeSession:
    session: Any                     # SessionCapture du moteur biométrique
    mode: str                        # "enrolement" | "authentification"
    utilisateur_id: str
    email: str
    derniere_activite: float
    en_cours: bool = False           # une image est en cours de traitement
    abandonnee: bool = False         # supprimée pendant le traitement d'une image


class GestionnaireSessions:
    """Registre thread-safe des sessions de capture."""

    def __init__(self, duree_inactivite: float = DUREE_INACTIVITE_S,
                 horloge: Callable[[], float] = time.monotonic) -> None:
        self.duree_inactivite = duree_inactivite
        self._horloge = horloge
        self._verrou = threading.Lock()
        self._sessions: dict[str, EntreeSession] = {}

    # -- utilitaires internes (appelés sous verrou) --
    def _nettoyer(self) -> None:
        limite = self._horloge() - self.duree_inactivite
        for cle in [c for c, e in self._sessions.items() if not e.en_cours and e.derniere_activite < limite]:
            self._effacer(self._sessions.pop(cle))

    @staticmethod
    def _effacer(entree: EntreeSession) -> None:
        try:
            entree.session.effacer()
        except Exception:  # l'effacement ne doit jamais bloquer le nettoyage
            pass

    # -- API publique --
    def ajouter(self, session: Any, mode: str, utilisateur_id: str, email: str) -> EntreeSession:
        """Enregistre une nouvelle session ; remplace la session du même mode de l'utilisateur."""
        with self._verrou:
            self._nettoyer()
            for cle, e in list(self._sessions.items()):
                if e.mode == mode and e.utilisateur_id == utilisateur_id and not e.en_cours:
                    self._effacer(self._sessions.pop(cle))
            entree = EntreeSession(session, mode, utilisateur_id, email, self._horloge())
            self._sessions[session.id] = entree
            return entree

    def reserver(self, session_id: str, mode: str, proprietaire: str | None = None) -> EntreeSession:
        """Marque la session comme occupée pour traiter une image (404 / 409 sinon)."""
        with self._verrou:
            self._nettoyer()
            entree = self._sessions.get(session_id)
            if entree is None or entree.mode != mode or (
                proprietaire is not None and entree.utilisateur_id != proprietaire
            ):
                raise _introuvable()
            if entree.en_cours:
                raise ErreurAPI(
                    409, "IMAGE_EN_COURS",
                    "Une image est déjà en cours d'analyse pour cette session. Patientez.",
                )
            entree.en_cours = True
            entree.derniere_activite = self._horloge()
            return entree

    def liberer(self, entree: EntreeSession) -> None:
        with self._verrou:
            entree.en_cours = False
            entree.derniere_activite = self._horloge()

    def retirer(self, entree: EntreeSession) -> None:
        """Retire la session du registre et efface ses données en mémoire."""
        with self._verrou:
            if self._sessions.get(entree.session.id) is entree:
                del self._sessions[entree.session.id]
        self._effacer(entree)

    def abandonner(self, session_id: str, mode: str, proprietaire: str | None = None) -> None:
        """Abandon volontaire (idempotent). Une session occupée est effacée après son image."""
        with self._verrou:
            self._nettoyer()
            entree = self._sessions.get(session_id)
            if entree is None or entree.mode != mode or (
                proprietaire is not None and entree.utilisateur_id != proprietaire
            ):
                return
            if entree.en_cours:
                entree.abandonnee = True
                return
            del self._sessions[session_id]
        self._effacer(entree)

    def retirer_utilisateur(self, utilisateur_id: str) -> None:
        """Supprime toutes les sessions d'un utilisateur (révocation, suppression…)."""
        with self._verrou:
            for cle, e in list(self._sessions.items()):
                if e.utilisateur_id == utilisateur_id:
                    if e.en_cours:
                        e.abandonnee = True
                    else:
                        self._effacer(self._sessions.pop(cle))

    def obtenir(self, session_id: str) -> EntreeSession | None:
        with self._verrou:
            self._nettoyer()
            return self._sessions.get(session_id)

    def vider(self) -> None:
        with self._verrou:
            entrees = list(self._sessions.values())
            self._sessions.clear()
        for entree in entrees:
            self._effacer(entree)


TAILLE_MAX_IMAGE = 2 * 1024 * 1024  # 2 Mo


def _trop_grande() -> ErreurAPI:
    return ErreurAPI(413, "IMAGE_TROP_GRANDE",
                     "Image trop volumineuse (2 Mo maximum). Réduisez la résolution de la capture.")


async def lire_image_jpeg(request) -> bytes:
    """Lit le corps d'une requête d'image : JPEG uniquement, 2 Mo maximum."""
    type_contenu = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if type_contenu != "image/jpeg":
        raise ErreurAPI(415, "FORMAT_NON_SUPPORTE",
                        "Format d'image non pris en charge : envoyez une image JPEG (Content-Type: image/jpeg).")
    longueur = request.headers.get("content-length")
    if longueur and longueur.isdigit() and int(longueur) > TAILLE_MAX_IMAGE:
        raise _trop_grande()
    octets = await request.body()
    if len(octets) > TAILLE_MAX_IMAGE:
        raise _trop_grande()
    if not octets:
        raise ErreurAPI(400, "IMAGE_VIDE", "Aucune image reçue : le corps de la requête est vide.")
    return octets


def info_session(session_id: str, nb_visage: int, nb_oreille: int, cote_attendu: str | None,
                 expire_dans: float) -> dict:
    """Corps `SessionInfo` renvoyé à la création d'une session de capture."""
    return {
        "session_id": session_id,
        "etape": "visage",
        "captures_visage_requises": nb_visage,
        "captures_oreille_requises": nb_oreille,
        "cote_attendu": cote_attendu,
        "expire_dans": int(expire_dans),
    }
