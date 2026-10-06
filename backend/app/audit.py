"""Journal d'audit (table `evenements`) doublé d'une ligne de journal Python lisible.

Ne jamais y passer de mot de passe, d'image, de vecteur ni de BioHash.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.modeles import Evenement

journal = logging.getLogger("bioaccess.audit")


def journaliser(bdd: Session, type_evenement: str, utilisateur_id: str | None = None,
                **details: Any) -> None:
    """Ajoute un événement d'audit à la transaction en cours (validé par l'appelant)."""
    bdd.add(Evenement(type=type_evenement, utilisateur_id=utilisateur_id, details=details or None))
    complement = " ".join(f"{cle}={valeur}" for cle, valeur in details.items())
    journal.info("%s utilisateur=%s %s", type_evenement, utilisateur_id or "-", complement)
