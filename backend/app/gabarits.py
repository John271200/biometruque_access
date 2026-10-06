"""Stockage protégé des gabarits : BioHashing + chiffrement AES-256-GCM.

AAD = « {utilisateur_id}|{modalite} » pour un gabarit et « {utilisateur_id}|jeton » pour
le jeton BioHashing : un blob recopié sur un autre compte ou une autre modalité est rejeté.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.biometrie import Chiffreur, ErreurIntegrite, biohash, generer_jeton
from app.modeles import Gabarit, JetonBiohash, Utilisateur

MODALITES = ("visage", "oreille")


def aad(utilisateur_id: str, objet: str) -> bytes:
    return f"{utilisateur_id}|{objet}".encode()


def enregistrer_gabarits(bdd: Session, chiffreur: Chiffreur, utilisateur: Utilisateur,
                         resultat) -> None:
    """Calcule les BioHash des vecteurs d'enrôlement et les stocke chiffrés (sans valider)."""
    jeton = generer_jeton()
    vecteurs = {"visage": resultat.vecteur_visage, "oreille": resultat.vecteur_oreille}
    extracteurs = {"visage": resultat.extracteur_visage, "oreille": resultat.extracteur_oreille}
    detruire_gabarits(bdd, utilisateur.id)
    for modalite in MODALITES:
        code = biohash(vecteurs[modalite], jeton, modalite)
        bdd.add(Gabarit(
            utilisateur_id=utilisateur.id,
            modalite=modalite,
            extracteur=extracteurs[modalite],
            donnees_chiffrees=chiffreur.chiffrer(code, aad(utilisateur.id, modalite)),
        ))
    bdd.add(JetonBiohash(utilisateur_id=utilisateur.id,
                         jeton_chiffre=chiffreur.chiffrer(jeton, aad(utilisateur.id, "jeton"))))


@dataclass
class References:
    """Jeton et BioHash de référence déchiffrés (gardés en mémoire le temps d'une décision)."""

    jeton: bytes
    codes: dict[str, bytes]


def charger_references(bdd: Session, chiffreur: Chiffreur, utilisateur_id: str) -> References:
    """Déchiffre le jeton et les gabarits. Lève ErreurIntegrite si un élément manque ou est altéré."""
    ligne_jeton = bdd.get(JetonBiohash, utilisateur_id)
    gabarits = {g.modalite: g for g in bdd.scalars(
        select(Gabarit).where(Gabarit.utilisateur_id == utilisateur_id))}
    if ligne_jeton is None or set(gabarits) != set(MODALITES):
        raise ErreurIntegrite("gabarits incomplets")
    jeton = chiffreur.dechiffrer(ligne_jeton.jeton_chiffre, aad(utilisateur_id, "jeton"))
    codes = {m: chiffreur.dechiffrer(gabarits[m].donnees_chiffrees, aad(utilisateur_id, m))
             for m in MODALITES}
    return References(jeton, codes)


def detruire_gabarits(bdd: Session, utilisateur_id: str) -> None:
    """Supprime effectivement les gabarits et le jeton BioHashing (sans valider)."""
    bdd.execute(delete(Gabarit).where(Gabarit.utilisateur_id == utilisateur_id))
    bdd.execute(delete(JetonBiohash).where(JetonBiohash.utilisateur_id == utilisateur_id))
