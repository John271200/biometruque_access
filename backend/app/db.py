"""Accès à la base de données (SQLAlchemy 2, SQLite par défaut ou PostgreSQL)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator


def maintenant() -> datetime:
    """Instant présent en UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


class HorodatageUTC(TypeDecorator):
    """Horodatage toujours renvoyé en UTC « aware », quel que soit le moteur SQL.

    SQLite ne conserve pas le fuseau : on y stocke l'heure UTC « naïve » et on
    rajoute le fuseau à la lecture. PostgreSQL utilise `timestamptz`.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, valeur, dialect):
        if valeur is None:
            return None
        if valeur.tzinfo is None:
            valeur = valeur.replace(tzinfo=timezone.utc)
        valeur = valeur.astimezone(timezone.utc)
        return valeur.replace(tzinfo=None) if dialect.name == "sqlite" else valeur

    def process_result_value(self, valeur, dialect):
        if valeur is None:
            return None
        if valeur.tzinfo is None:
            return valeur.replace(tzinfo=timezone.utc)
        return valeur.astimezone(timezone.utc)


class Base(DeclarativeBase):
    """Classe de base des modèles ORM."""


def creer_engine(url: str) -> Engine:
    """Crée le moteur SQL ; pour SQLite, crée le dossier et active les clés étrangères."""
    infos = make_url(url)
    if not infos.drivername.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True)

    if infos.database and infos.database != ":memory:":
        Path(infos.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragmas(connexion, _):
        curseur = connexion.cursor()
        curseur.execute("PRAGMA foreign_keys=ON")  # cascades et SET NULL
        curseur.execute("PRAGMA secure_delete=ON")  # les lignes supprimées sont écrasées
        curseur.close()

    return engine


class BaseDeDonnees:
    """Regroupe le moteur SQL et la fabrique de sessions d'une instance de l'API."""

    def __init__(self, url: str) -> None:
        self.engine = creer_engine(url)
        self.fabrique = sessionmaker(self.engine, expire_on_commit=False)

    def creer_tables(self) -> None:
        """Crée les tables manquantes (pas d'Alembic dans le MVP)."""
        from app import modeles  # noqa: F401  (enregistre les modèles sur Base)

        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self.fabrique()

    def fermer(self) -> None:
        self.engine.dispose()
