"""Mots de passe (Argon2id), jetons JWT (HS256) et règles de saisie des comptes."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.erreurs import ErreurAPI

DUREE_JETON = {
    "compte": timedelta(minutes=60),
    "acces": timedelta(minutes=10),
}
ALGORITHME = "HS256"

_hacheur = PasswordHasher()  # Argon2id avec les paramètres recommandés par argon2-cffi
_HASH_LEURRE = _hacheur.hash("mot-de-passe-leurre-pour-temps-constant")


# --- Mots de passe -------------------------------------------------------------------

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hacheur.hash(mot_de_passe)


def verifier_mot_de_passe(hash_stocke: str | None, mot_de_passe: str) -> bool:
    """Vérifie un mot de passe. Sans hash (compte inconnu), calcule quand même un leurre
    pour que la durée de réponse ne révèle pas l'existence du compte."""
    try:
        return _hacheur.verify(hash_stocke or _HASH_LEURRE, mot_de_passe) and hash_stocke is not None
    except (VerificationError, InvalidHashError):
        return False


def manques_mot_de_passe(mot_de_passe: str) -> list[str]:
    """Liste ce qui manque au mot de passe pour respecter la politique (vide si conforme)."""
    manques = []
    if len(mot_de_passe) < 12:
        manques.append("au moins 12 caractères")
    if not re.search(r"[A-ZÀ-ÖØ-Þ]", mot_de_passe):
        manques.append("une majuscule")
    if not re.search(r"[a-zß-öø-ÿ]", mot_de_passe):
        manques.append("une minuscule")
    if not re.search(r"\d", mot_de_passe):
        manques.append("un chiffre")
    return manques


# --- Jetons JWT ----------------------------------------------------------------------

@dataclass
class JetonEmis:
    jeton: str
    jti: str
    expire_le: datetime
    expire_dans: int  # secondes


def creer_jeton(
    secret: str,
    type_jeton: str,
    utilisateur_id: str,
    tentative_id: int | None = None,
    duree: timedelta | None = None,
) -> JetonEmis:
    """Émet un jeton `compte` (60 min) ou `acces` (10 min, lié à une tentative)."""
    debut = datetime.now(timezone.utc)
    duree = duree if duree is not None else DUREE_JETON[type_jeton]
    jti = uuid.uuid4().hex
    contenu = {
        "type": type_jeton,
        "sub": utilisateur_id,
        "jti": jti,
        "iat": debut,
        "exp": debut + duree,
    }
    if type_jeton == "acces":
        contenu["tentative"] = tentative_id
    jeton = jwt.encode(contenu, secret, algorithm=ALGORITHME)
    return JetonEmis(jeton, jti, debut + duree, max(0, int(duree.total_seconds())))


def decoder_jeton(secret: str, jeton: str) -> dict:
    """Décode et vérifie un jeton. Lève 401 JETON_EXPIRE ou JETON_INVALIDE."""
    try:
        contenu = jwt.decode(
            jeton, secret, algorithms=[ALGORITHME],
            options={"require": ["exp", "sub", "jti", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise ErreurAPI(401, "JETON_EXPIRE", "Votre jeton a expiré. Reconnectez-vous.") from None
    except jwt.PyJWTError:
        raise ErreurAPI(401, "JETON_INVALIDE", "Jeton d'authentification invalide.") from None
    if contenu.get("type") not in DUREE_JETON:
        raise ErreurAPI(401, "JETON_INVALIDE", "Jeton d'authentification invalide.")
    return contenu


def secondes_restantes(contenu: dict) -> int:
    """Secondes avant l'expiration d'un jeton décodé (jamais négatif)."""
    reste = int(contenu["exp"]) - int(datetime.now(timezone.utc).timestamp())
    return max(0, reste)
