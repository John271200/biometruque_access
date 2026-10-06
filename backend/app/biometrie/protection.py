"""Protection des gabarits biométriques : BioHashing + chiffrement AES-256-GCM.

Deux mécanismes complémentaires (point 19 des points à trancher) :

1. **BioHashing** (gabarit révocable) : le vecteur biométrique est projeté sur une base
   aléatoire orthonormée dérivée d'un jeton secret propre à l'utilisateur, puis binarisé.
   Révoquer = tirer un nouveau jeton : le nouveau code n'a statistiquement plus rien à voir
   avec l'ancien, alors que la biométrie, elle, ne change pas.
2. **AES-256-GCM** : chiffrement authentifié de ce qui est stocké en base (jeton BioHashing,
   codes…). Toute altération du chiffré, du nonce ou des données associées (AAD) est
   détectée au déchiffrement.

Propriété utilisée pour calibrer la décision (voir ``decision.py``) — hachage par
hyperplans aléatoires (Charikar, 2002) : chaque bit vaut ``signe(<v, r_i>)`` où ``r_i`` est
une direction aléatoire uniformément répartie sur la sphère. Pour deux vecteurs séparés
par un angle θ, la probabilité qu'un hyperplan aléatoire les sépare vaut θ/π, donc

    P(bit différent) = θ / π     et     E[similarité de Hamming] = 1 − θ / π.

L'orthonormalisation (QR) des directions ne change pas cette loi marginale (chaque colonne
d'une matrice orthonormée « de Haar » reste uniforme sur la sphère) ; elle évite seulement
que deux bits soient redondants.
"""

from __future__ import annotations

import hashlib
import secrets

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TAILLE_JETON = 32  # octets
TAILLE_CLE = 32  # octets (AES-256)
TAILLE_NONCE = 12  # octets (recommandation NIST pour GCM)
TAILLE_TAG = 16  # octets (tag d'authentification GCM)


def generer_jeton() -> bytes:
    """Tire un jeton BioHashing de 32 octets avec un générateur cryptographique."""
    return secrets.token_bytes(TAILLE_JETON)


def _base_projection(jeton: bytes, modalite: str, dimension: int, nb_bits: int) -> np.ndarray:
    """Construit la base de projection orthonormée ``dimension × nb_bits``.

    La graine est ``sha256(jeton + modalite)`` : un même jeton donne deux bases
    indépendantes pour le visage et pour l'oreille.
    """
    graine = int.from_bytes(hashlib.sha256(jeton + modalite.encode("utf-8")).digest(), "big")
    generateur = np.random.default_rng(graine)
    gaussienne = generateur.standard_normal((dimension, nb_bits))
    q, r = np.linalg.qr(gaussienne)  # q : colonnes orthonormées
    # Décomposition QR rendue unique (diagonale de R positive) : le résultat ne dépend
    # plus des conventions de signe de la bibliothèque LAPACK utilisée (Windows/Linux).
    signes = np.sign(np.diag(r))
    signes[signes == 0] = 1.0
    return q * signes


def biohash(vecteur: np.ndarray, jeton: bytes, modalite: str, nb_bits: int = 256) -> bytes:
    """Calcule le code BioHashing (``nb_bits // 8`` octets, 32 octets par défaut).

    Projection du vecteur sur la base aléatoire orthonormée puis binarisation au seuil 0
    (bit = 1 si la projection est positive). Le signe d'une projection ne dépend pas de la
    norme du vecteur : inutile de le normaliser au préalable.
    """
    v = np.asarray(vecteur, dtype=np.float64)
    if v.ndim != 1:
        raise ValueError("Le vecteur biométrique doit être à une dimension.")
    if nb_bits <= 0 or nb_bits % 8 != 0:
        raise ValueError("Le nombre de bits doit être un multiple positif de 8.")
    if v.shape[0] < nb_bits:
        raise ValueError(
            f"Dimension du vecteur insuffisante pour le BioHashing : {v.shape[0]} < {nb_bits} "
            "(la base orthonormée exige au moins autant de composantes que de bits)."
        )
    if not np.all(np.isfinite(v)):
        raise ValueError("Le vecteur biométrique contient des valeurs non finies.")
    if not isinstance(jeton, (bytes, bytearray)) or len(jeton) == 0:
        raise ValueError("Le jeton BioHashing doit être une suite d'octets non vide.")
    base = _base_projection(bytes(jeton), modalite, v.shape[0], nb_bits)
    bits = (v @ base) > 0.0
    return np.packbits(bits.astype(np.uint8)).tobytes()


def similarite_hamming(a: bytes, b: bytes) -> float:
    """Similarité de Hamming normalisée : ``1 − distance_hamming / nb_bits`` (entre 0 et 1)."""
    if len(a) != len(b):
        raise ValueError("Les deux codes BioHashing n'ont pas la même longueur.")
    if len(a) == 0:
        raise ValueError("Codes BioHashing vides.")
    xa = np.frombuffer(bytes(a), dtype=np.uint8)
    xb = np.frombuffer(bytes(b), dtype=np.uint8)
    distance = int(np.unpackbits(np.bitwise_xor(xa, xb)).sum())
    return 1.0 - distance / (8 * len(a))


class ErreurIntegrite(Exception):
    """Le blob chiffré, son nonce ou ses données associées (AAD) ont été altérés,
    ou la clé est incorrecte."""


class Chiffreur:
    """Chiffrement authentifié AES-256-GCM.

    Format du blob : ``nonce (12 octets) || chiffré || tag (16 octets)``.
    Le nonce est tiré aléatoirement à chaque chiffrement (jamais réutilisé avec la même
    clé en pratique : 96 bits aléatoires). L'AAD (ex. ``"{utilisateur_id}|{modalite}"``)
    n'est pas chiffrée mais authentifiée : un blob recopié sur un autre utilisateur ou une
    autre modalité est refusé.
    """

    def __init__(self, cle_maitresse: bytes) -> None:
        if not isinstance(cle_maitresse, (bytes, bytearray)) or len(cle_maitresse) != TAILLE_CLE:
            raise ValueError("La clé maîtresse doit faire exactement 32 octets (AES-256).")
        self._aead = AESGCM(bytes(cle_maitresse))

    def chiffrer(self, donnees: bytes, aad: bytes) -> bytes:
        nonce = secrets.token_bytes(TAILLE_NONCE)
        return nonce + self._aead.encrypt(nonce, bytes(donnees), bytes(aad))

    def dechiffrer(self, blob: bytes, aad: bytes) -> bytes:
        if len(blob) < TAILLE_NONCE + TAILLE_TAG:
            raise ErreurIntegrite("Données chiffrées tronquées ou corrompues.")
        nonce, chiffre = bytes(blob[:TAILLE_NONCE]), bytes(blob[TAILLE_NONCE:])
        try:
            return self._aead.decrypt(nonce, chiffre, bytes(aad))
        except InvalidTag as exc:
            raise ErreurIntegrite(
                "Échec du contrôle d'intégrité : données altérées, mauvaise clé ou mauvaise AAD."
            ) from exc
