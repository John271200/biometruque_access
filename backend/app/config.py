"""Configuration de l'API (variables d'environnement préfixées BIOACCESS_, fichier backend/.env).

Tous les chemins sont calculés depuis l'emplacement de ce fichier, jamais depuis le
répertoire courant, pour que l'API se comporte de la même façon quel que soit l'endroit
d'où elle est lancée.
"""

from __future__ import annotations

import base64
import binascii
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

journal = logging.getLogger("bioaccess.config")

DOSSIER_BACKEND = Path(__file__).resolve().parent.parent
DOSSIER_DEPOT = DOSSIER_BACKEND.parent
FICHIER_ENV = DOSSIER_BACKEND / ".env"
DOSSIER_FRONTEND_DIST = DOSSIER_DEPOT / "frontend" / "dist"


class ErreurConfiguration(RuntimeError):
    """Configuration inutilisable : l'API refuse de démarrer."""


class Settings(BaseSettings):
    """Paramètres de l'API. Chaque champ se règle via BIOACCESS_<NOM_EN_MAJUSCULES>."""

    model_config = SettingsConfigDict(
        env_prefix="BIOACCESS_",
        env_file=FICHIER_ENV,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "production"] = "dev"
    database_url: str | None = None
    cle_maitresse: str | None = None
    secret_jwt: str | None = None
    dossier_modeles: Path = DOSSIER_BACKEND / "models" / "buffalo_l"
    afficher_scores: bool | None = None
    apercu_oreille: bool | None = None
    cors_origines: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _completer(self) -> "Settings":
        """Valeurs par défaut dépendant de l'environnement et chemins absolus."""
        en_dev = self.env == "dev"
        if self.afficher_scores is None:
            self.afficher_scores = en_dev
        if self.apercu_oreille is None:
            self.apercu_oreille = en_dev
        if not self.database_url:
            chemin = DOSSIER_BACKEND / "donnees" / "bioaccess.db"
            self.database_url = f"sqlite:///{chemin.as_posix()}"
        if not self.dossier_modeles.is_absolute():
            self.dossier_modeles = (DOSSIER_BACKEND / self.dossier_modeles).resolve()
        return self

    @property
    def liste_cors(self) -> list[str]:
        """Origines CORS autorisées (séparées par des virgules dans la variable)."""
        return [o.strip() for o in self.cors_origines.split(",") if o.strip()]

    @property
    def cle_maitresse_octets(self) -> bytes:
        """Clé maîtresse AES-256 décodée (32 octets)."""
        return _decoder_cle(self.cle_maitresse or "")


def _decoder_cle(valeur: str) -> bytes:
    """Décode la clé maîtresse base64 et vérifie qu'elle fait 32 octets."""
    try:
        cle = base64.b64decode(valeur, validate=True)
    except (binascii.Error, ValueError):
        cle = b""
    if len(cle) != 32:
        raise ErreurConfiguration(
            "BIOACCESS_CLE_MAITRESSE doit être l'encodage base64 de 32 octets exactement "
            "(générez-en une avec : python -c \"import base64, os; "
            "print(base64.b64encode(os.urandom(32)).decode())\")."
        )
    return cle


def _ajouter_au_fichier_env(fichier: Path, valeurs: dict[str, str]) -> None:
    """Ajoute des variables générées à la fin du fichier .env (créé s'il n'existe pas)."""
    contenu = fichier.read_text(encoding="utf-8") if fichier.exists() else ""
    lignes = []
    if contenu and not contenu.endswith("\n"):
        lignes.append("")
    horodatage = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lignes.append(f"# Secrets générés automatiquement (dev) le {horodatage} — ne jamais commiter")
    lignes += [f"{nom}={valeur}" for nom, valeur in valeurs.items()]
    with fichier.open("a", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")


def charger_settings(fichier_env: Path | None = FICHIER_ENV) -> Settings:
    """Charge la configuration et gère les secrets manquants.

    - en dev : les secrets absents sont générés, ajoutés au fichier .env et signalés ;
    - en production : l'absence d'un secret empêche le démarrage.
    """
    settings = Settings(_env_file=fichier_env)
    manquants = [nom for nom in ("cle_maitresse", "secret_jwt") if not getattr(settings, nom)]
    if manquants:
        noms = ", ".join(f"BIOACCESS_{n.upper()}" for n in manquants)
        if settings.env == "production":
            raise ErreurConfiguration(
                f"Secret(s) manquant(s) en production : {noms}. Définissez-les dans "
                "l'environnement ou dans backend/.env avant de démarrer l'API."
            )
        generes: dict[str, str] = {}
        if "cle_maitresse" in manquants:
            settings.cle_maitresse = base64.b64encode(secrets.token_bytes(32)).decode()
            generes["BIOACCESS_CLE_MAITRESSE"] = settings.cle_maitresse
        if "secret_jwt" in manquants:
            settings.secret_jwt = secrets.token_urlsafe(48)
            generes["BIOACCESS_SECRET_JWT"] = settings.secret_jwt
        if fichier_env is not None:
            _ajouter_au_fichier_env(Path(fichier_env), generes)
            journal.warning(
                "Secret(s) absent(s) : %s générés et ajoutés à %s (mode dev uniquement). "
                "Conservez ce fichier : sans la clé maîtresse, les gabarits enregistrés "
                "deviennent illisibles.", noms, fichier_env,
            )
        else:
            journal.warning("Secret(s) absent(s) : %s générés pour cette exécution seulement.", noms)
    _decoder_cle(settings.cle_maitresse or "")  # échoue tôt si la clé est mal formée
    return settings
