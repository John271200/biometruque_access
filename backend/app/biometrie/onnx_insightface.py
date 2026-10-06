"""Modèles InsightFace « buffalo_l » exécutés avec onnxruntime pur (sans le paquet insightface).

Le paquet Python ``insightface`` exige un compilateur C++ sous Windows : on reproduit ici
fidèlement le pré/post-traitement d'insightface 0.7 pour les trois modèles utiles :

- ``det_10g.onnx``   : détecteur SCRFD (boîte englobante + 5 points clés) ;
- ``1k3d68.onnx``    : 68 points de repère 3D (sert au calcul du lacet et à localiser l'oreille) ;
- ``w600k_r50.onnx`` : ArcFace ResNet-50 (plongement de 512 dimensions).

Les modèles buffalo_l sont distribués par InsightFace pour un usage de recherche non
commercial uniquement.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

FICHIERS_MODELES = {
    "detection": "det_10g.onnx",
    "landmarks": "1k3d68.onnx",
    "reconnaissance": "w600k_r50.onnx",
}

# Gabarit ArcFace standard (5 points dans une image 112×112) : œil droit, œil gauche,
# nez, coin droit de la bouche, coin gauche de la bouche (« droit » = côté gauche de l'image).
GABARIT_ARCFACE = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
     [41.5493, 92.3655], [70.7299, 92.2041]],
    dtype=np.float32,
)

# Paires de points 68 symétriques (côté droit du sujet, côté gauche du sujet) utilisées pour
# estimer l'axe « oreille droite → oreille gauche » du visage : contour de la mâchoire,
# sourcils, coins des yeux, ailes du nez, coins de la bouche.
PAIRES_SYMETRIQUES = [
    (0, 16), (1, 15), (2, 14), (3, 13),
    (17, 26), (19, 24), (21, 22),
    (36, 45), (39, 42),
    (31, 35), (48, 54),
]


@dataclass
class VisageDetecte:
    """Visage détecté par SCRFD, en pixels de l'image d'origine."""

    bbox: np.ndarray  # (4,) x1, y1, x2, y2
    score: float
    kps: np.ndarray  # (5, 2) œil droit, œil gauche, nez, bouche droite, bouche gauche

    @property
    def largeur(self) -> float:
        return float(self.bbox[2] - self.bbox[0])

    @property
    def hauteur(self) -> float:
        return float(self.bbox[3] - self.bbox[1])

    @property
    def centre(self) -> tuple[float, float]:
        return float(self.bbox[0] + self.bbox[2]) / 2, float(self.bbox[1] + self.bbox[3]) / 2


# --------------------------------------------------------------------------------------
# Lecture minimale du graphe ONNX (sans le paquet « onnx »)
# --------------------------------------------------------------------------------------

def _lire_varint(f) -> int:
    resultat, decalage = 0, 0
    while True:
        octet = f.read(1)
        if not octet:
            raise EOFError("Fin de fichier ONNX inattendue")
        resultat |= (octet[0] & 0x7F) << decalage
        if not octet[0] & 0x80:
            return resultat
        decalage += 7


def _sauter_champ(f, type_fil: int) -> None:
    if type_fil == 0:
        _lire_varint(f)
    elif type_fil == 1:
        f.seek(8, 1)
    elif type_fil == 2:
        f.seek(_lire_varint(f), 1)
    elif type_fil == 5:
        f.seek(4, 1)
    else:
        raise ValueError(f"Type de champ protobuf non géré : {type_fil}")


def _nom_noeud(octets: bytes) -> str:
    """Extrait le champ ``name`` (n° 3) d'un ``NodeProto`` sérialisé."""
    f = io.BytesIO(octets)
    while f.tell() < len(octets):
        cle = _lire_varint(f)
        champ, type_fil = cle >> 3, cle & 7
        if champ == 3 and type_fil == 2:
            return f.read(_lire_varint(f)).decode("utf-8", errors="replace")
        _sauter_champ(f, type_fil)
    return ""


def premiers_noeuds_onnx(chemin: Path, nombre: int = 8) -> list[str]:
    """Noms des ``nombre`` premiers nœuds du graphe (``ModelProto.graph.node[:nombre]``).

    Lecture protobuf minimale et séquentielle : seuls les premiers octets du fichier sont
    lus (les nœuds sont sérialisés avant les poids).
    """
    noms: list[str] = []
    with open(chemin, "rb") as f:
        taille = os.fstat(f.fileno()).st_size
        while f.tell() < taille:
            cle = _lire_varint(f)
            champ, type_fil = cle >> 3, cle & 7
            if champ == 7 and type_fil == 2:  # ModelProto.graph
                fin_graphe = f.tell() + _lire_varint(f)
                while f.tell() < fin_graphe and len(noms) < nombre:
                    cle = _lire_varint(f)
                    champ, type_fil = cle >> 3, cle & 7
                    if champ == 1 and type_fil == 2:  # GraphProto.node
                        noms.append(_nom_noeud(f.read(_lire_varint(f))))
                    else:
                        _sauter_champ(f, type_fil)
                return noms
            _sauter_champ(f, type_fil)
    return noms


def normalisation_insightface(chemin: Path, ecart_type_defaut: float) -> tuple[float, float]:
    """Détermine ``(input_mean, input_std)`` exactement comme insightface 0.7.

    Si des nœuds ``Sub``/``_minus`` ET ``Mul``/``_mul`` figurent parmi les 8 premiers nœuds
    (ou un nœud ``bn_data`` parmi les 3 premiers), la normalisation est intégrée au graphe
    (modèles convertis depuis MXNet) : moyenne 0, écart-type 1. Sinon : 127,5 et
    ``ecart_type_defaut`` (128 pour les landmarks, 127,5 pour ArcFace).
    """
    try:
        noms = premiers_noeuds_onnx(chemin, 8)
    except (EOFError, ValueError):
        noms = []
    trouve_sub = any(n.startswith("Sub") or n.startswith("_minus") for n in noms)
    trouve_mul = any(n.startswith("Mul") or n.startswith("_mul") for n in noms)
    if any(n == "bn_data" for n in noms[:3]):
        trouve_sub = trouve_mul = True
    if trouve_sub and trouve_mul:
        return 0.0, 1.0
    return 127.5, ecart_type_defaut


# --------------------------------------------------------------------------------------
# Outils géométriques
# --------------------------------------------------------------------------------------

def _blob(image_bgr: np.ndarray, moyenne: float, ecart_type: float) -> np.ndarray:
    """Équivalent de ``cv2.dnn.blobFromImage(img, 1/std, taille, (m, m, m), swapRB=True)``
    pour une image déjà à la bonne taille : BGR → RGB, ``(x − m) / std``, NCHW float32."""
    rgb = image_bgr[:, :, ::-1].astype(np.float32)
    return ((rgb - moyenne) / ecart_type).transpose(2, 0, 1)[np.newaxis].copy()


def similitude_umeyama(source: np.ndarray, cible: np.ndarray) -> np.ndarray:
    """Similitude (rotation + échelle + translation) aux moindres carrés, méthode d'Umeyama.

    Même calcul que ``skimage.transform.SimilarityTransform.estimate`` utilisé par
    insightface ; renvoie la matrice affine 2×3.
    """
    src = np.asarray(source, dtype=np.float64)
    dst = np.asarray(cible, dtype=np.float64)
    n, dim = src.shape
    moy_src, moy_dst = src.mean(axis=0), dst.mean(axis=0)
    src_c, dst_c = src - moy_src, dst - moy_dst
    covariance = dst_c.T @ src_c / n
    d = np.ones(dim)
    if np.linalg.det(covariance) < 0:
        d[dim - 1] = -1
    u, s, vt = np.linalg.svd(covariance)
    rang = np.linalg.matrix_rank(covariance)
    t = np.eye(dim + 1)
    if rang == 0:
        return t[:dim]
    if rang == dim - 1:
        if np.linalg.det(u) * np.linalg.det(vt) > 0:
            t[:dim, :dim] = u @ vt
        else:
            s_ = d[dim - 1]
            d[dim - 1] = -1
            t[:dim, :dim] = u @ np.diag(d) @ vt
            d[dim - 1] = s_
    else:
        t[:dim, :dim] = u @ np.diag(d) @ vt
    variance_src = src_c.var(axis=0).sum()
    echelle = (s @ d) / variance_src
    t[:dim, dim] = moy_dst - echelle * (t[:dim, :dim] @ moy_src)
    t[:dim, :dim] *= echelle
    return t[:dim]


def _nms(dets: np.ndarray, seuil: float) -> list[int]:
    """Suppression des non-maxima (identique à SCRFD.nms d'insightface)."""
    x1, y1, x2, y2, scores = dets[:, 0], dets[:, 1], dets[:, 2], dets[:, 3], dets[:, 4]
    aires = (x2 - x1 + 1) * (y2 - y1 + 1)
    ordre = scores.argsort()[::-1]
    garder = []
    while ordre.size > 0:
        i = ordre[0]
        garder.append(int(i))
        xx1 = np.maximum(x1[i], x1[ordre[1:]])
        yy1 = np.maximum(y1[i], y1[ordre[1:]])
        xx2 = np.minimum(x2[i], x2[ordre[1:]])
        yy2 = np.minimum(y2[i], y2[ordre[1:]])
        inter = np.maximum(0.0, xx2 - xx1 + 1) * np.maximum(0.0, yy2 - yy1 + 1)
        recouvrement = inter / (aires[i] + aires[ordre[1:]] - inter)
        ordre = ordre[np.where(recouvrement <= seuil)[0] + 1]
    return garder


def lacet_depuis_landmarks(landmarks3d: np.ndarray) -> float:
    """Lacet (yaw) en degrés calculé directement à partir des 68 points 3D.

    On estime l'axe transversal du visage (côté droit du sujet → côté gauche du sujet) en
    sommant les vecteurs de paires de points symétriques (mâchoire, sourcils, yeux, nez,
    bouche). Le lacet est l'angle entre cet axe et le plan de l'image :
    ``atan2(composante z, norme de la composante (x, y))`` — insensible au roulis.

    Convention de signe (image NON miroir) : lacet > 0 quand le nez part vers la droite de
    l'image (l'utilisateur tourne la tête vers SA gauche et montre son oreille droite).
    """
    lm = np.asarray(landmarks3d, dtype=np.float64)
    axe = np.zeros(3)
    for droite, gauche in PAIRES_SYMETRIQUES:
        axe += lm[gauche] - lm[droite]
    # Dans la sortie de 1k3d68, z est une profondeur qui croît en s'éloignant de la caméra,
    # à la même échelle que x et y : quand l'utilisateur tourne vers sa gauche, son côté
    # gauche recule (z plus grand) et le lacet est positif. Vérifié par les tests sur
    # t1.jpg (image miroir → lacet opposé ; cohérence avec la position du nez).
    return float(np.degrees(np.arctan2(axe[2], np.hypot(axe[0], axe[1]))))


# --------------------------------------------------------------------------------------
# Chargement et exécution des modèles
# --------------------------------------------------------------------------------------

class ModelesInsightface:
    """Charge une seule fois les trois modèles ONNX et expose les traitements utiles.

    Les appels sont sûrs en multi-thread (``InferenceSession.run`` l'est).
    """

    taille_detection = 640
    seuil_detection = 0.5
    seuil_nms = 0.4
    taille_landmarks = 192
    taille_arcface = 112

    def __init__(self, dossier_modeles: Path | str) -> None:
        dossier = Path(dossier_modeles)
        manquants = [nom for nom in FICHIERS_MODELES.values() if not (dossier / nom).is_file()]
        if manquants:
            raise FileNotFoundError(
                f"Modèle(s) biométrique(s) introuvable(s) dans « {dossier} » : "
                f"{', '.join(manquants)}. Depuis le dossier « backend », lancez "
                "« python scripts/telecharger_modeles.py » pour télécharger buffalo_l."
            )
        options = ort.SessionOptions()
        options.intra_op_num_threads = min(4, os.cpu_count() or 1)
        options.log_severity_level = 3
        # Pas d'attente active des threads entre deux exécutions : les trois modèles
        # s'enchaînent et les threads « en rotation » d'un modèle ralentissaient le suivant
        # (mesuré : ≈ 345 ms → ≈ 230 ms pour la chaîne complète sur 4 cœurs).
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")

        def charger(cle: str) -> ort.InferenceSession:
            return ort.InferenceSession(
                str(dossier / FICHIERS_MODELES[cle]), sess_options=options,
                providers=["CPUExecutionProvider"],
            )

        # SCRFD : normalisation fixe (127,5 ; 128) dans insightface.
        self._det = charger("detection")
        self._det_entree = self._det.get_inputs()[0].name
        self._det_sorties = [o.name for o in self._det.get_outputs()]
        if len(self._det_sorties) != 9:
            raise ValueError("det_10g.onnx inattendu : 9 sorties (3 pas × score/boîte/points) attendues.")
        self._pas = (8, 16, 32)
        self._nb_ancres = 2
        self._centres: dict[tuple[int, int, int], np.ndarray] = {}

        self._lmk = charger("landmarks")
        self._lmk_entree = self._lmk.get_inputs()[0].name
        self._lmk_moyenne, self._lmk_ecart = normalisation_insightface(
            dossier / FICHIERS_MODELES["landmarks"], 128.0)

        self._rec = charger("reconnaissance")
        self._rec_entree = self._rec.get_inputs()[0].name
        self._rec_moyenne, self._rec_ecart = normalisation_insightface(
            dossier / FICHIERS_MODELES["reconnaissance"], 127.5)

    # ---------------------------------------------------------------- détection SCRFD
    def detecter(self, image_bgr: np.ndarray) -> list[VisageDetecte]:
        """Détecte les visages (score ≥ 0,5, NMS 0,4), triés par score décroissant."""
        taille = self.taille_detection
        h, w = image_bgr.shape[:2]
        # Redimensionnement avec conservation du ratio dans un carré 640×640 (remplissage noir).
        if h / w > 1.0:
            nouvelle_h, nouvelle_l = taille, int(taille / (h / w))
        else:
            nouvelle_l, nouvelle_h = taille, int(taille * (h / w))
        nouvelle_l, nouvelle_h = max(nouvelle_l, 1), max(nouvelle_h, 1)
        echelle = nouvelle_h / h
        image_det = np.zeros((taille, taille, 3), dtype=np.uint8)
        image_det[:nouvelle_h, :nouvelle_l] = cv2.resize(image_bgr, (nouvelle_l, nouvelle_h))

        sorties = self._det.run(self._det_sorties, {self._det_entree: _blob(image_det, 127.5, 128.0)})
        sorties = [s[0] if s.ndim == 3 else s for s in sorties]
        scores_l, boites_l, points_l = [], [], []
        for i, pas in enumerate(self._pas):
            scores = sorties[i].reshape(-1)
            boites = sorties[i + 3] * pas
            points = sorties[i + 6] * pas
            centres = self._centres_ancres(taille // pas, taille // pas, pas)
            positifs = np.where(scores >= self.seuil_detection)[0]
            if positifs.size == 0:
                continue
            c = centres[positifs]
            d = boites[positifs]
            scores_l.append(scores[positifs])
            boites_l.append(np.stack([c[:, 0] - d[:, 0], c[:, 1] - d[:, 1],
                                      c[:, 0] + d[:, 2], c[:, 1] + d[:, 3]], axis=-1))
            k = points[positifs]
            kps = np.empty((len(positifs), 5, 2), dtype=np.float32)
            kps[:, :, 0] = c[:, 0:1] + k[:, 0::2]
            kps[:, :, 1] = c[:, 1:2] + k[:, 1::2]
            points_l.append(kps)
        if not scores_l:
            return []
        scores = np.concatenate(scores_l)
        boites = np.concatenate(boites_l) / echelle
        points = np.concatenate(points_l) / echelle
        ordre = scores.argsort()[::-1]
        dets = np.hstack([boites, scores[:, None]]).astype(np.float32)[ordre]
        points = points[ordre]
        garder = _nms(dets, self.seuil_nms)
        return [VisageDetecte(bbox=dets[i, :4].copy(), score=float(dets[i, 4]), kps=points[i].copy())
                for i in garder]

    def _centres_ancres(self, hauteur: int, largeur: int, pas: int) -> np.ndarray:
        cle = (hauteur, largeur, pas)
        if cle not in self._centres:
            centres = np.stack(np.mgrid[:hauteur, :largeur][::-1], axis=-1).astype(np.float32)
            centres = (centres * pas).reshape(-1, 2)
            centres = np.stack([centres] * self._nb_ancres, axis=1).reshape(-1, 2)
            self._centres[cle] = centres
        return self._centres[cle]

    # ---------------------------------------------------------------- landmarks 3D
    def landmarks3d(self, image_bgr: np.ndarray, visage: VisageDetecte) -> np.ndarray:
        """68 points 3D (x, y en pixels de l'image ; z à la même échelle)."""
        taille = self.taille_landmarks
        x1, y1, x2, y2 = (float(v) for v in visage.bbox)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        echelle = taille / (max(x2 - x1, y2 - y1) * 1.5)
        # Transformation de face_align.transform (rotation nulle).
        m = np.array([[echelle, 0.0, taille / 2 - cx * echelle],
                      [0.0, echelle, taille / 2 - cy * echelle]], dtype=np.float64)
        recadrage = cv2.warpAffine(image_bgr, m, (taille, taille), borderValue=0.0)
        pred = self._lmk.run(None, {self._lmk_entree: _blob(recadrage, self._lmk_moyenne,
                                                            self._lmk_ecart)})[0][0]
        pred = pred.reshape(-1, 3)[-68:].astype(np.float64)  # 3309 = 1103 × 3 : 68 derniers
        pred[:, 0:2] += 1
        pred[:, 0:3] *= taille // 2
        # Inverse de la transformation (comme trans_points3d) : z mis à la même échelle.
        im = cv2.invertAffineTransform(m)
        resultat = np.empty_like(pred)
        resultat[:, 0:2] = pred[:, 0:2] @ im[:, :2].T + im[:, 2]
        resultat[:, 2] = pred[:, 2] * np.hypot(im[0, 0], im[0, 1])
        return resultat.astype(np.float32)

    @staticmethod
    def lacet(landmarks3d: np.ndarray) -> float:
        return lacet_depuis_landmarks(landmarks3d)

    # ---------------------------------------------------------------- ArcFace
    def aligner(self, image_bgr: np.ndarray, visage: VisageDetecte) -> np.ndarray:
        """``norm_crop`` d'insightface : alignement 112×112 sur le gabarit ArcFace."""
        m = similitude_umeyama(visage.kps, GABARIT_ARCFACE)
        return cv2.warpAffine(image_bgr, m, (self.taille_arcface, self.taille_arcface),
                              borderValue=0.0)

    def plongement(self, image_bgr: np.ndarray, visage: VisageDetecte) -> np.ndarray:
        """Plongement ArcFace de 512 dimensions, L2-normalisé (float32)."""
        aligne = self.aligner(image_bgr, visage)
        sortie = self._rec.run(None, {self._rec_entree: _blob(aligne, self._rec_moyenne,
                                                              self._rec_ecart)})[0]
        vecteur = sortie.reshape(-1).astype(np.float64)
        vecteur /= max(np.linalg.norm(vecteur), 1e-12)
        return vecteur.astype(np.float32)
