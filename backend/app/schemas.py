"""Corps de requête (Pydantic) et sérialisation des réponses JSON."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError

from app.db import maintenant
from app.modeles import DossierPatient, Tentative, Utilisateur
from app.securite import manques_mot_de_passe


def normaliser_email(valeur: str) -> str:
    """Valide le format de l'adresse et la renvoie en minuscules."""
    try:
        infos = validate_email(valeur.strip(), check_deliverability=False)
    except EmailNotValidError:
        raise PydanticCustomError("email_invalide", "Adresse email invalide.") from None
    return infos.normalized.lower()


# --- Corps de requête ----------------------------------------------------------------

class CreationCompte(BaseModel):
    nom: str
    email: str
    mot_de_passe: str

    @field_validator("nom")
    @classmethod
    def _nom(cls, v: str) -> str:
        v = " ".join(v.split())
        if not 2 <= len(v) <= 100:
            raise PydanticCustomError("nom_invalide", "Le nom doit contenir entre 2 et 100 caractères.")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normaliser_email(v)

    @field_validator("mot_de_passe")
    @classmethod
    def _mot_de_passe(cls, v: str) -> str:
        manques = manques_mot_de_passe(v)
        if manques:
            raise PydanticCustomError(
                "mot_de_passe_faible",
                "Mot de passe trop faible : il manque {manques}.",
                {"manques": ", ".join(manques)},
            )
        return v


class Connexion(BaseModel):
    email: str
    mot_de_passe: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


class ReponseConsentement(BaseModel):
    accepte: bool
    version: str


class DemandeAuthentification(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normaliser_email(v)


class MotDePasse(BaseModel):
    mot_de_passe: str


class SuppressionCompte(BaseModel):
    mot_de_passe: str
    confirmation: str

    @field_validator("confirmation")
    @classmethod
    def _confirmation(cls, v: str) -> str:
        if v != "SUPPRIMER":
            raise PydanticCustomError(
                "confirmation_invalide", "Saisissez SUPPRIMER (en majuscules) pour confirmer."
            )
        return v


# --- Réponses ------------------------------------------------------------------------

def iso(valeur: datetime | None) -> str | None:
    """Date ISO 8601 en UTC (ou None)."""
    return valeur.isoformat(timespec="seconds") if valeur else None


def verrou_actif(utilisateur: Utilisateur) -> datetime | None:
    """Fin du verrouillage si le compte est encore verrouillé, sinon None."""
    fin = utilisateur.verrouille_jusqua
    return fin if fin and fin > maintenant() else None


def utilisateur_vers_dict(u: Utilisateur) -> dict[str, Any]:
    fin_verrou = verrou_actif(u)
    verrou_expire = u.verrouille_jusqua is not None and fin_verrou is None
    return {
        "id": u.id,
        "nom": u.nom,
        "email": u.email,
        "role": u.role,
        "consentement": {
            "etat": u.consentement_etat,
            "version": u.consentement_version,
            "date": iso(u.consentement_le),
        },
        "enrolement": {
            "etat": u.enrolement_etat,
            "date": iso(u.enrolement_le),
            "extracteur_oreille": u.extracteur_oreille,
            "cote_oreille": u.cote_oreille,
        },
        "verrouille_jusqua": iso(fin_verrou),
        # Un verrou échu remet le compteur à zéro (appliqué en base au prochain essai).
        "echecs_consecutifs": 0 if verrou_expire else u.echecs_consecutifs,
    }


def masquer_nombres(valeur: Any) -> Any:
    """Remplace récursivement les nombres par None (verdicts booléens et textes conservés)."""
    if isinstance(valeur, bool) or valeur is None or isinstance(valeur, str):
        return valeur
    if isinstance(valeur, (int, float)):
        return None
    if isinstance(valeur, dict):
        return {k: masquer_nombres(v) for k, v in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [masquer_nombres(v) for v in valeur]
    return valeur


def tentative_vers_dict(t: Tentative, afficher_scores: bool) -> dict[str, Any]:
    donnees = {
        "horodatage": iso(t.horodatage),
        "decision": "ACCEPTEE" if t.accepte else "REFUSEE",
        "raison": t.raison,
        "score_visage": t.score_visage,
        "score_oreille": t.score_oreille,
        "score_fusion": t.score_fusion,
        "regles": t.regles,
    }
    if not afficher_scores:
        for cle in ("score_visage", "score_oreille", "score_fusion", "regles"):
            donnees[cle] = masquer_nombres(donnees[cle])
    return donnees


def dossier_resume(d: DossierPatient) -> dict[str, Any]:
    return {
        "id": d.id,
        "nom": d.nom,
        "age": d.age,
        "groupe_sanguin": d.groupe_sanguin,
        "medecin": d.medecin,
        "fictif": d.fictif,
    }


def dossier_complet(d: DossierPatient) -> dict[str, Any]:
    return dossier_resume(d) | {
        "antecedents": d.antecedents,
        "traitement": d.traitement,
        "allergies": d.allergies,
        "derniere_consultation": d.derniere_consultation.isoformat(),
    }
