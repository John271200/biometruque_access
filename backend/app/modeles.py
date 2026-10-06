"""Modèles de données (tables) de l'API BioAccess.

Aucune donnée biométrique en clair n'est stockée : les gabarits sont des BioHash
chiffrés en AES-256-GCM, et le jeton BioHashing est lui aussi chiffré.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, HorodatageUTC, maintenant


def _uuid() -> str:
    return str(uuid.uuid4())


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    nom: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)  # minuscules
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="utilisateur")
    cree_le: Mapped[datetime] = mapped_column(HorodatageUTC, default=maintenant)

    # Consentement : ABSENT | ACCORDE | RETIRE
    consentement_etat: Mapped[str] = mapped_column(String(10), default="ABSENT")
    consentement_version: Mapped[str | None] = mapped_column(String(20))
    consentement_le: Mapped[datetime | None] = mapped_column(HorodatageUTC)
    consentement_ip: Mapped[str | None] = mapped_column(String(45))

    # Enrôlement : NON_ENROLE | ENROLE | REVOQUE
    enrolement_etat: Mapped[str] = mapped_column(String(12), default="NON_ENROLE")
    enrolement_le: Mapped[datetime | None] = mapped_column(HorodatageUTC)
    extracteur_oreille: Mapped[str | None] = mapped_column(String(50))
    cote_oreille: Mapped[str | None] = mapped_column(String(10))

    # Verrouillage après échecs biométriques consécutifs
    echecs_consecutifs: Mapped[int] = mapped_column(Integer, default=0)
    verrouille_jusqua: Mapped[datetime | None] = mapped_column(HorodatageUTC)

    # Seul le dernier jeton « acces » émis est valide
    jeton_acces_jti: Mapped[str | None] = mapped_column(String(64))

    gabarits: Mapped[list["Gabarit"]] = relationship(
        back_populates="utilisateur", cascade="all, delete-orphan", passive_deletes=True
    )
    jeton_biohash: Mapped["JetonBiohash | None"] = relationship(
        back_populates="utilisateur", cascade="all, delete-orphan", passive_deletes=True
    )


class Gabarit(Base):
    """BioHash d'une modalité, chiffré (AAD = « {utilisateur_id}|{modalite} »)."""

    __tablename__ = "gabarits"
    __table_args__ = (UniqueConstraint("utilisateur_id", "modalite"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    utilisateur_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True
    )
    modalite: Mapped[str] = mapped_column(String(10))  # visage | oreille
    extracteur: Mapped[str] = mapped_column(String(50))
    donnees_chiffrees: Mapped[bytes] = mapped_column(LargeBinary)
    cree_le: Mapped[datetime] = mapped_column(HorodatageUTC, default=maintenant)

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="gabarits")


class JetonBiohash(Base):
    """Jeton secret du BioHashing, chiffré (AAD = « {utilisateur_id}|jeton »)."""

    __tablename__ = "jetons_biohash"

    utilisateur_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("utilisateurs.id", ondelete="CASCADE"), primary_key=True
    )
    jeton_chiffre: Mapped[bytes] = mapped_column(LargeBinary)

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="jeton_biohash")


class Tentative(Base):
    """Tentative d'authentification biométrique (jamais d'image ni de vecteur)."""

    __tablename__ = "tentatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    utilisateur_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("utilisateurs.id", ondelete="SET NULL"), index=True
    )
    email_revendique: Mapped[str] = mapped_column(String(254))
    horodatage: Mapped[datetime] = mapped_column(HorodatageUTC, default=maintenant, index=True)
    contexte: Mapped[str] = mapped_column(String(20), default="production")
    score_visage: Mapped[float | None] = mapped_column(Float)
    score_oreille: Mapped[float | None] = mapped_column(Float)
    score_fusion: Mapped[float | None] = mapped_column(Float)
    regles: Mapped[list | None] = mapped_column(JSON)
    accepte: Mapped[bool] = mapped_column(Boolean, default=False)
    raison: Mapped[str | None] = mapped_column(Text)
    duree_ms: Mapped[int | None] = mapped_column(Integer)
    ip: Mapped[str | None] = mapped_column(String(45))
    version_parametres: Mapped[int | None] = mapped_column(Integer)


class AccesBase(Base):
    """Accès à la base protégée (/dossiers) avec un jeton « acces »."""

    __tablename__ = "acces_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    utilisateur_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("utilisateurs.id", ondelete="SET NULL"), index=True
    )
    tentative_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tentatives.id", ondelete="SET NULL")
    )
    horodatage: Mapped[datetime] = mapped_column(HorodatageUTC, default=maintenant)
    ressource: Mapped[str] = mapped_column(String(200))
    ip: Mapped[str | None] = mapped_column(String(45))


class Evenement(Base):
    """Journal d'audit. Ne contient jamais de donnée biométrique ni de mot de passe."""

    __tablename__ = "evenements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    utilisateur_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("utilisateurs.id", ondelete="SET NULL"), index=True
    )
    horodatage: Mapped[datetime] = mapped_column(HorodatageUTC, default=maintenant)
    details: Mapped[dict | None] = mapped_column(JSON)


class JetonRevoque(Base):
    """Jetons JWT révoqués avant leur expiration (déconnexion)."""

    __tablename__ = "jetons_revoques"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expire_le: Mapped[datetime] = mapped_column(HorodatageUTC, index=True)


class DossierPatient(Base):
    """Dossier patient FICTIF de la base protégée de démonstration."""

    __tablename__ = "dossiers_patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    groupe_sanguin: Mapped[str] = mapped_column(String(3))
    medecin: Mapped[str] = mapped_column(String(100))
    antecedents: Mapped[str] = mapped_column(Text)
    traitement: Mapped[str] = mapped_column(Text)
    allergies: Mapped[str] = mapped_column(Text)
    derniere_consultation: Mapped[date] = mapped_column(Date)
    fictif: Mapped[bool] = mapped_column(Boolean, default=True)
