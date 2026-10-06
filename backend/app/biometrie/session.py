"""Machine à états de la capture guidée : visage de face → rotation de la tête → oreille.

La rotation sert de **preuve de vivacité** : on suit le même visage image par image (sans
coupure, sans saut, même identité) depuis une position de face jusqu'au profil, en passant
par des positions intermédiaires. Une photo fixe ne tourne pas ; une substitution de photo
ou de personne casse la continuité.

L'analyse d'image (modèles ONNX) et l'horloge sont **injectées** : la machine à états se
teste avec des séquences synthétiques de lacets, sans vraies images.

Aucune image n'est écrite sur disque ; ``effacer()`` met à zéro tous les tableaux.
"""

from __future__ import annotations

import base64
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Callable, Literal, Protocol

import cv2
import numpy as np

from .oreille import Cote, ZoneOreille
from .qualite import Critere, critere_visage_unique

Etape = Literal["visage", "rotation", "oreille", "terminee", "echec"]
EXTRACTEUR_VISAGE = "arcface-w600k-r50"


# ------------------------------------------------------------------------ résultats
@dataclass
class RetourImage:
    etape: Etape
    captures_visage: int
    captures_visage_requises: int
    captures_oreille: int
    captures_oreille_requises: int
    image_retenue: bool
    message: str  # consigne principale à afficher / lire à voix haute
    criteres: list[Critere]
    lacet: float | None  # degrés, valeur absolue
    cadre_visage: list[float] | None  # [x1, y1, x2, y2] normalisés 0–1, image NON miroir
    cadre_oreille: list[float] | None  # idem, zone de l'oreille analysée
    apercu_oreille: str | None  # JPEG base64 de la vignette (si apercu=True), jamais stocké
    raison_echec: str | None

    def to_dict(self) -> dict:
        """Dictionnaire sérialisable en JSON tel quel (types Python natifs uniquement)."""
        d = asdict(self)
        d["lacet"] = None if self.lacet is None else float(self.lacet)
        for cle in ("cadre_visage", "cadre_oreille"):
            if d[cle] is not None:
                d[cle] = [float(v) for v in d[cle]]
        d["criteres"] = [{"code": c.code, "ok": bool(c.ok), "message": c.message}
                         for c in self.criteres]
        return d


@dataclass
class PreuveVivacite:
    ok: bool
    details: dict  # amplitude, nb_intermediaires, inversions, duree_s


@dataclass
class ResultatCapture:
    vecteur_visage: np.ndarray  # 512, float32, L2-normalisé (moyenne des captures)
    vecteur_oreille: np.ndarray  # dimension ≥ 256, float32, L2-normalisé
    extracteur_visage: str  # "arcface-w600k-r50"
    extracteur_oreille: str  # "lbp-v1"
    cote_oreille: Cote
    vivacite: PreuveVivacite


# ------------------------------------------------------------------------ observation
@dataclass
class ObservationOreille:
    zone: ZoneOreille
    criteres: list[Critere]
    vecteur: np.ndarray | None  # calculé seulement si tous les critères passent
    vignette: np.ndarray | None  # vignette en niveaux de gris (pour l'aperçu)


@dataclass
class Observation:
    """Ce que l'analyseur a extrait d'une image (calculs coûteux faits à la demande)."""

    lisible: bool
    largeur: int = 0
    hauteur: int = 0
    nb_visages: int = 0
    bbox: tuple[float, float, float, float] | None = None  # pixels, si un seul visage
    lacet: float | None = None  # degrés, signé (> 0 : nez vers la droite de l'image)
    cote: Cote | None = None  # oreille exposée d'après la géométrie du visage
    criteres_visage: list[Critere] = field(default_factory=list)  # qualité d'une capture de face
    calcul_plongement: Callable[[], np.ndarray] | None = None
    calcul_oreille: Callable[[], ObservationOreille] | None = None
    _cache: dict = field(default_factory=dict, repr=False)

    def plongement(self) -> np.ndarray | None:
        if "plongement" not in self._cache:
            self._cache["plongement"] = self.calcul_plongement() if self.calcul_plongement else None
        return self._cache["plongement"]

    def oreille(self) -> ObservationOreille | None:
        if "oreille" not in self._cache:
            self._cache["oreille"] = self.calcul_oreille() if self.calcul_oreille else None
        return self._cache["oreille"]


class Analyseur(Protocol):
    def analyser(self, image_jpeg: bytes) -> Observation: ...


@dataclass
class ParametresSession:
    """Paramètres de la capture guidée (proposition, à ajuster après essais réels)."""

    delai_global_s: float = 120.0  # au-delà : échec définitif
    intervalle_visage_s: float = 0.4  # écart minimal entre deux captures de face retenues
    intervalle_oreille_s: float = 0.3  # écart minimal entre deux captures d'oreille
    cosinus_coherence_visage: float = 0.6  # chaque capture de face vs la première
    cosinus_continuite: float = 0.35  # pendant la rotation, vs le gabarit de la session
    lacet_controle_identite: float = 40.0  # contrôle d'identité tant que |lacet| < 40°
    lacet_frontal: float = 15.0  # |lacet| < 15° : position de face
    lacet_profil: float = 45.0  # |lacet| ≥ 45° : profil atteint
    lacet_oreille_max: float = 90.0
    nb_intermediaires_min: int = 2  # images entre 15° et 45° pendant la rotation
    inversions_max: int = 2  # changements de sens tolérés pendant la rotation
    tolerance_inversion_deg: float = 3.0  # variation ignorée (bruit du lacet)
    duree_rotation_max_s: float = 10.0  # de la dernière image de face au profil
    perte_visage_max_s: float = 1.5  # perte du visage tolérée pendant le suivi
    deplacement_max: float = 0.6  # saut du centre du visage entre deux images (× largeur)


def compter_inversions(valeurs: list[float], tolerance: float) -> int:
    """Nombre de changements de sens d'une suite de lacets (variations < tolérance ignorées)."""
    inversions, sens = 0, 0
    reference = valeurs[0] if valeurs else 0.0
    for v in valeurs[1:]:
        delta = v - reference
        if abs(delta) < tolerance:
            continue
        nouveau = 1 if delta > 0 else -1
        if sens and nouveau != sens:
            inversions += 1
        sens, reference = nouveau, v
    return inversions


def _moyenne_normalisee(vecteurs: list[np.ndarray]) -> np.ndarray:
    moyenne = np.mean(np.stack(vecteurs).astype(np.float64), axis=0)
    return (moyenne / max(np.linalg.norm(moyenne), 1e-12)).astype(np.float32)


def _direction(cote_oreille: Cote | None) -> str:
    """Sens de rotation de la tête qui expose l'oreille demandée (droite → tourner à gauche)."""
    return "droite" if cote_oreille == "gauche" else "gauche"


# ------------------------------------------------------------------------ session
class SessionCapture:
    """Session de capture guidée (enrôlement ou authentification).

    ``traiter_image`` est synchrone et protégé par un verrou : une session peut être
    utilisée depuis plusieurs threads, les images sont traitées une par une.
    """

    def __init__(
        self,
        mode: Literal["enrolement", "authentification"],
        nb_visage: int,
        nb_oreille: int,
        cote_attendu: Cote | None = None,
        apercu: bool = False,
        analyseur: Analyseur | None = None,
        horloge: Callable[[], float] | None = None,
        parametres: ParametresSession | None = None,
        extracteur_oreille: str = "lbp-v1",
    ) -> None:
        if mode not in ("enrolement", "authentification"):
            raise ValueError("Mode de session inconnu (attendu : enrolement ou authentification).")
        if nb_visage < 1 or nb_oreille < 1:
            raise ValueError("Il faut au moins une capture de visage et une capture d'oreille.")
        if cote_attendu not in (None, "droite", "gauche"):
            raise ValueError("Côté attendu invalide (droite, gauche ou None).")
        if analyseur is None:
            raise ValueError("Analyseur requis : créez la session avec MoteurBiometrique.nouvelle_session().")
        self.id = uuid.uuid4().hex
        self.mode = mode
        self.nb_visage = int(nb_visage)
        self.nb_oreille = int(nb_oreille)
        self.cote_attendu = cote_attendu
        self.apercu = apercu
        self._analyseur = analyseur
        self._horloge = horloge or time.monotonic
        self.p = parametres or ParametresSession()
        self._extracteur_oreille = extracteur_oreille
        self._verrou = threading.Lock()

        self.etape: Etape = "visage"
        self._debut = self._horloge()
        self._raison_echec: str | None = None
        self._plongements: list[np.ndarray] = []
        self._vecteurs_oreille: list[np.ndarray] = []
        self._gabarit: np.ndarray | None = None
        self._t_capture_visage: float | None = None
        self._t_capture_oreille: float | None = None
        # Suivi image par image (continuité).
        self._t_detection: float | None = None
        self._bbox: tuple[float, float, float, float] | None = None
        self._dernier_lacet: float | None = None
        # Séquence de rotation en cours (None = attendre une position de face).
        self._seq_debut: float | None = None
        self._seq_lacets: list[float] = []
        self._seq_cote: Cote | None = None
        self._cote: Cote | None = cote_attendu
        self._vivacite: PreuveVivacite | None = None
        self._resultat: ResultatCapture | None = None
        self._efface = False

    # ---------------------------------------------------------------- état public
    @property
    def terminee(self) -> bool:
        return self.etape == "terminee"

    @property
    def echouee(self) -> bool:
        return self.etape == "echec"

    def traiter_image(self, image_jpeg: bytes) -> RetourImage:
        with self._verrou:
            if self.etape == "terminee":
                return self._retour("Capture terminée", [Critere("session", True, "Capture terminée")])
            if self.etape == "echec":
                raison = self._raison_echec or "Capture échouée"
                return self._retour(raison, [Critere("session", False, raison)])
            t = self._horloge()
            if t - self._debut > self.p.delai_global_s:
                return self._echouer(
                    f"Délai dépassé : la capture n'a pas abouti en {self.p.delai_global_s:.0f} secondes")
            obs = self._analyseur.analyser(image_jpeg)
            if not obs.lisible:
                critere = Critere("image", False, "Image illisible")
                return self._retour("Image illisible : renvoyez une image JPEG valide", [critere])
            if self.etape == "visage":
                return self._etape_visage(obs, t)
            if self.etape == "rotation":
                return self._etape_rotation(obs, t)
            return self._etape_oreille(obs, t)

    def resultat(self) -> ResultatCapture:
        with self._verrou:
            if self.etape != "terminee" or self._efface:
                raise RuntimeError("Capture non terminée (ou effacée) : aucun résultat disponible.")
            if self._resultat is None:
                self._resultat = ResultatCapture(
                    vecteur_visage=_moyenne_normalisee(self._plongements),
                    vecteur_oreille=_moyenne_normalisee(self._vecteurs_oreille),
                    extracteur_visage=EXTRACTEUR_VISAGE,
                    extracteur_oreille=self._extracteur_oreille,
                    cote_oreille=self._cote,
                    vivacite=self._vivacite,
                )
            return self._resultat

    def effacer(self) -> None:
        """Met à zéro tous les tableaux en mémoire (y compris ceux du résultat renvoyé)."""
        with self._verrou:
            tableaux = [*self._plongements, *self._vecteurs_oreille]
            if self._gabarit is not None:
                tableaux.append(self._gabarit)
            if self._resultat is not None:
                tableaux += [self._resultat.vecteur_visage, self._resultat.vecteur_oreille]
            for tableau in tableaux:
                tableau.fill(0)
            self._plongements.clear()
            self._vecteurs_oreille.clear()
            self._efface = True
            if self.etape != "terminee":  # session interrompue : plus aucune image acceptée
                self.etape = "echec"
                self._raison_echec = self._raison_echec or "Session annulée"

    # ---------------------------------------------------------------- étape visage
    def _etape_visage(self, obs: Observation, t: float) -> RetourImage:
        if obs.nb_visages != 1:
            critere = critere_visage_unique(obs.nb_visages)
            return self._retour(critere.message, [critere], obs)
        criteres = [critere_visage_unique(1), *obs.criteres_visage]
        echecs = [c for c in criteres if not c.ok]
        if echecs:
            return self._retour(echecs[0].message, criteres, obs)
        if self._t_capture_visage is not None and t - self._t_capture_visage < self.p.intervalle_visage_s:
            return self._retour("Ne bougez pas, capture en cours…", criteres, obs)
        plongement = obs.plongement()
        if self._plongements:
            cosinus = float(np.dot(plongement, self._plongements[0]))
            if cosinus < self.p.cosinus_coherence_visage:
                return self._echouer("Les captures ne correspondent pas à une même personne", obs, criteres)
        self._plongements.append(np.array(plongement, dtype=np.float32, copy=True))
        self._t_capture_visage = t
        self._suivre(obs, t)
        if len(self._plongements) < self.nb_visage:
            message = (f"Capture {len(self._plongements)}/{self.nb_visage} réussie : "
                       "restez face à la caméra")
            return self._retour(message, criteres, obs, image_retenue=True)
        # Toutes les captures de face sont faites : gabarit de session, puis rotation.
        self._gabarit = _moyenne_normalisee(self._plongements)
        self.etape = "rotation"
        self._demarrer_sequence(t, abs(obs.lacet or 0.0))
        return self._retour(self._consigne(), criteres, obs, image_retenue=True)

    # ---------------------------------------------------------------- étape rotation
    def _etape_rotation(self, obs: Observation, t: float) -> RetourImage:
        incident = self._continuite(obs, t)
        if incident is not None:
            return incident
        lacet = abs(obs.lacet or 0.0)
        criteres = [critere_visage_unique(1)]
        controle = self._controle_identite(obs, lacet, criteres)
        if controle is not None:
            self._reinitialiser_sequence()
            return self._retour(controle, criteres, obs)

        if lacet < self.p.lacet_frontal:
            self._demarrer_sequence(t, lacet)
            criteres.append(Critere("rotation", False, self._consigne()))
            return self._retour(self._consigne(), criteres, obs)
        if self._seq_debut is None:
            message = f"Revenez face à la caméra puis tournez lentement la tête vers la {self._sens()}"
            criteres.append(Critere("rotation", False, message))
            return self._retour(message, criteres, obs)

        # Côté présenté (géométrie du visage) : imposé en authentification, libre à l'enrôlement.
        cote_vise = self.cote_attendu or self._seq_cote
        if cote_vise is not None and obs.cote != cote_vise:
            self._reinitialiser_sequence()
            message = f"Tournez la tête vers la {_direction(cote_vise)}"
            criteres.append(Critere("cote", False, message))
            return self._retour(message, criteres, obs)
        self._seq_cote = obs.cote
        criteres.append(Critere("cote", True, "Bon côté"))

        duree = t - self._seq_debut
        if duree > self.p.duree_rotation_max_s:
            self._reinitialiser_sequence()
            message = ("Rotation trop lente : revenez face à la caméra puis tournez la tête "
                       f"en moins de {self.p.duree_rotation_max_s:.0f} secondes")
            criteres.append(Critere("rotation", False, message))
            return self._retour(message, criteres, obs)

        self._seq_lacets.append(lacet)
        if lacet < self.p.lacet_profil:
            message = f"Continuez à tourner lentement la tête vers la {self._sens()}"
            criteres.append(Critere("rotation", False, message))
            return self._retour(message, criteres, obs)

        # Profil atteint : vérification de la preuve de vivacité.
        intermediaires = sum(1 for v in self._seq_lacets
                             if self.p.lacet_frontal <= v < self.p.lacet_profil)
        inversions = compter_inversions(self._seq_lacets, self.p.tolerance_inversion_deg)
        if intermediaires < self.p.nb_intermediaires_min:
            self._reinitialiser_sequence()
            message = "Mouvement trop rapide : revenez face à la caméra puis tournez plus lentement"
            criteres.append(Critere("vivacite", False, message))
            return self._retour(message, criteres, obs)
        if inversions > self.p.inversions_max:
            self._reinitialiser_sequence()
            message = ("Mouvement irrégulier : revenez face à la caméra puis tournez la tête "
                       "d'un seul mouvement")
            criteres.append(Critere("vivacite", False, message))
            return self._retour(message, criteres, obs)

        self._vivacite = PreuveVivacite(ok=True, details={
            "amplitude": float(lacet - self._seq_lacets[0]),
            "nb_intermediaires": int(intermediaires),
            "inversions": int(inversions),
            "duree_s": float(duree),
        })
        self._cote = self._seq_cote
        self.etape = "oreille"
        criteres.append(Critere("vivacite", True, "Mouvement de tête validé"))
        return self._retour("Mouvement validé : gardez la tête tournée, capture de l'oreille…",
                            criteres, obs)

    # ---------------------------------------------------------------- étape oreille
    def _etape_oreille(self, obs: Observation, t: float) -> RetourImage:
        incident = self._continuite(obs, t)
        if incident is not None:
            return incident
        lacet = abs(obs.lacet or 0.0)
        criteres = [critere_visage_unique(1)]
        controle = self._controle_identite(obs, lacet, criteres)
        if controle is not None:
            return self._revenir_rotation(controle, criteres, obs)
        if obs.cote != self._cote:
            message = f"Tournez la tête vers la {self._sens()}"
            criteres.append(Critere("cote", False, message))
            return self._retour(message, criteres, obs)
        if lacet < self.p.lacet_profil:
            message = f"Tournez encore un peu la tête vers la {self._sens()}"
            criteres.append(Critere("profil", False, message))
            return self._retour(message, criteres, obs)
        if lacet > self.p.lacet_oreille_max:
            message = "Tournez un peu moins la tête"
            criteres.append(Critere("profil", False, message))
            return self._retour(message, criteres, obs)
        criteres.append(Critere("profil", True, "Tête bien de profil"))

        oreille = obs.oreille()
        if oreille is None:
            criteres.append(Critere("oreille_cadrage", False, "Oreille introuvable : tournez un peu moins la tête"))
            return self._retour(criteres[-1].message, criteres, obs)
        criteres += oreille.criteres
        echecs = [c for c in criteres if not c.ok]
        if echecs:
            return self._retour(echecs[0].message, criteres, obs, oreille=oreille)
        if self._t_capture_oreille is not None and t - self._t_capture_oreille < self.p.intervalle_oreille_s:
            return self._retour("Ne bougez pas, capture de l'oreille en cours…", criteres, obs,
                                oreille=oreille)
        self._vecteurs_oreille.append(np.array(oreille.vecteur, dtype=np.float32, copy=True))
        self._t_capture_oreille = t
        if len(self._vecteurs_oreille) < self.nb_oreille:
            message = (f"Oreille {len(self._vecteurs_oreille)}/{self.nb_oreille} capturée : "
                       "gardez la tête tournée")
        else:
            self.etape = "terminee"
            message = "Capture terminée : vous pouvez revenir face à la caméra"
        return self._retour(message, criteres, obs, image_retenue=True, oreille=oreille)

    # ---------------------------------------------------------------- outils internes
    def _sens(self) -> str:
        return _direction(self.cote_attendu or self._cote or self._seq_cote)

    def _consigne(self) -> str:
        return f"Tournez lentement la tête vers la {self._sens()}"

    def _suivre(self, obs: Observation, t: float) -> None:
        self._bbox = obs.bbox
        self._t_detection = t
        self._dernier_lacet = abs(obs.lacet) if obs.lacet is not None else None

    def _demarrer_sequence(self, t: float, lacet: float) -> None:
        self._seq_debut = t
        self._seq_lacets = [lacet]
        self._seq_cote = None

    def _reinitialiser_sequence(self) -> None:
        self._seq_debut = None
        self._seq_lacets = []
        self._seq_cote = None

    def _continuite(self, obs: Observation, t: float) -> RetourImage | None:
        """Suivi du même visage d'une image à l'autre (rotation et oreille).

        Renvoie un retour à afficher si l'image ne permet pas de poursuivre, sinon None.
        """
        if obs.nb_visages == 0:
            if self._t_detection is not None and t - self._t_detection <= self.p.perte_visage_max_s:
                message = ("Tournez un peu moins la tête"
                           if self.etape == "oreille" or (self._dernier_lacet or 0) >= 30
                           else "Visage non détecté : restez dans le champ de la caméra")
                return self._retour(message, [Critere("visage_unique", False, message)], obs)
            self._bbox = None
            self._t_detection = None
            return self._revenir_rotation(
                f"Visage perdu : revenez face à la caméra puis tournez lentement la tête vers la {self._sens()}",
                [Critere("visage_unique", False, "Aucun visage détecté")], obs)
        if obs.nb_visages > 1:
            critere = critere_visage_unique(obs.nb_visages)
            return self._revenir_rotation(critere.message, [critere], obs)
        precedente = self._bbox
        self._suivre(obs, t)
        if precedente is not None and obs.bbox is not None:
            largeur = max(precedente[2] - precedente[0], 1.0)
            dx = (obs.bbox[0] + obs.bbox[2] - precedente[0] - precedente[2]) / 2
            dy = (obs.bbox[1] + obs.bbox[3] - precedente[1] - precedente[3]) / 2
            if np.hypot(dx, dy) > self.p.deplacement_max * largeur:
                return self._revenir_rotation(
                    "Mouvement trop brusque : revenez face à la caméra puis tournez lentement la tête",
                    [Critere("continuite", False, "Le visage a changé brusquement de position")], obs)
        return None

    def _controle_identite(self, obs: Observation, lacet: float, criteres: list[Critere]) -> str | None:
        """Contrôle de continuité d'identité tant que le visage est peu tourné."""
        if lacet >= self.p.lacet_controle_identite or self._gabarit is None:
            return None
        plongement = obs.plongement()
        if plongement is None:
            return None
        if float(np.dot(plongement, self._gabarit)) < self.p.cosinus_continuite:
            message = "Le visage ne correspond plus à celui capturé : revenez face à la caméra"
            criteres.append(Critere("identite", False, message))
            return message
        criteres.append(Critere("identite", True, "Même personne"))
        return None

    def _revenir_rotation(self, message: str, criteres: list[Critere], obs: Observation) -> RetourImage:
        """Incident de suivi : la rotation (preuve de vivacité) doit être refaite.

        À l'étape oreille, les captures d'oreille déjà faites sont abandonnées : toutes
        les captures d'oreille doivent suivre une même rotation ininterrompue.
        """
        if self.etape == "oreille":
            for vecteur in self._vecteurs_oreille:
                vecteur.fill(0)
            self._vecteurs_oreille.clear()
            self._t_capture_oreille = None
            self._vivacite = None
            self._cote = self.cote_attendu
            self.etape = "rotation"
        self._reinitialiser_sequence()
        return self._retour(message, criteres, obs)

    def _echouer(self, raison: str, obs: Observation | None = None,
                 criteres: list[Critere] | None = None) -> RetourImage:
        self.etape = "echec"
        self._raison_echec = raison
        return self._retour(raison, [*(criteres or []), Critere("session", False, raison)], obs)

    def _retour(self, message: str, criteres: list[Critere], obs: Observation | None = None,
                image_retenue: bool = False, oreille: ObservationOreille | None = None) -> RetourImage:
        cadre_visage = cadre_oreille = None
        lacet = None
        if obs is not None and obs.lisible and obs.largeur > 0 and obs.hauteur > 0:
            if obs.bbox is not None:
                cadre_visage = _normaliser(obs.bbox, obs.largeur, obs.hauteur)
            if obs.lacet is not None:
                lacet = float(abs(obs.lacet))
            if oreille is not None:
                cadre_oreille = _normaliser(oreille.zone.boite, obs.largeur, obs.hauteur)
        apercu = None
        if self.apercu and oreille is not None and oreille.vignette is not None and oreille.vignette.size:
            ok, tampon = cv2.imencode(".jpg", oreille.vignette, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                apercu = base64.b64encode(tampon.tobytes()).decode("ascii")
        return RetourImage(
            etape=self.etape,
            captures_visage=len(self._plongements),
            captures_visage_requises=self.nb_visage,
            captures_oreille=len(self._vecteurs_oreille),
            captures_oreille_requises=self.nb_oreille,
            image_retenue=image_retenue,
            message=message,
            criteres=list(criteres),
            lacet=lacet,
            cadre_visage=cadre_visage,
            cadre_oreille=cadre_oreille,
            apercu_oreille=apercu,
            raison_echec=self._raison_echec if self.etape == "echec" else None,
        )


def _normaliser(boite, largeur: int, hauteur: int) -> list[float]:
    x1, y1, x2, y2 = (float(v) for v in boite)
    return [min(max(x1 / largeur, 0.0), 1.0), min(max(y1 / hauteur, 0.0), 1.0),
            min(max(x2 / largeur, 0.0), 1.0), min(max(y2 / hauteur, 0.0), 1.0)]
