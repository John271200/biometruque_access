"""Génération déterministe des dossiers patients FICTIFS de la base protégée.

Les noms, pathologies et traitements sont tirés au hasard (graine fixe) dans des listes
génériques : toute ressemblance avec une personne réelle serait fortuite.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modeles import DossierPatient

NB_DOSSIERS = 50
GRAINE = 20260101

PRENOMS = [
    "Koffi", "Afiavi", "Comlan", "Sènami", "Mawulé", "Rachidatou", "Fifamè", "Codjo",
    "Ayaba", "Gildas", "Bénédicte", "Rodrigue", "Nafissatou", "Euloge", "Prudence",
    "Ulrich", "Chimène", "Arnaud", "Aïcha", "Romaric", "Hermine", "Serge", "Mariam",
    "Fortuné", "Léa", "Thomas", "Camille", "Hugo", "Inès", "Julien",
]
NOMS = [
    "Adjovi", "Houngbédji", "Agossou", "Dossou", "Zinsou", "Ahouansou", "Gbaguidi",
    "Hounkpatin", "Kpadonou", "Sossou", "Tossou", "Akpovi", "Chabi", "Sanni",
    "Yessoufou", "Djossou", "Assogba", "Hounsa", "Lokossou", "Dansou", "Martin",
    "Bernard", "Dubois", "Lefèvre", "Moreau",
]
MEDECINS = [
    "Dr Adéchina Aïkpé", "Dr Clarisse Hounyo", "Dr Mathias Gnonlonfoun",
    "Dr Pélagie Ahoyo", "Dr Sylvain Kiki", "Dr Hélène Laurent", "Dr Yacoubou Bio",
]
GROUPES = ["O+"] * 9 + ["A+"] * 6 + ["B+"] * 5 + ["AB+"] * 1 + ["O-", "A-", "B-", "AB-"]
ANTECEDENTS = [
    "Aucun antécédent notable", "Paludisme récurrent", "Hypertension artérielle",
    "Diabète de type 2", "Asthme depuis l'enfance", "Drépanocytose (AS)",
    "Appendicectomie (2015)", "Fracture du radius (2019)", "Gastrite chronique",
    "Anémie ferriprive", "Migraine", "Hépatite B (porteur inactif)",
]
TRAITEMENTS = [
    "Aucun traitement en cours", "Amlodipine 5 mg/j", "Metformine 850 mg 2x/j",
    "Salbutamol à la demande", "Acide folique 5 mg/j", "Fer + vitamine C 1x/j",
    "Oméprazole 20 mg/j", "Paracétamol à la demande", "Artéméther-luméfantrine (cure)",
]
ALLERGIES = [
    "Aucune allergie connue", "Pénicilline", "Arachides", "Sulfamides",
    "Pollens", "Aspirine", "Fruits de mer", "Latex",
]


def generer_dossiers(nombre: int = NB_DOSSIERS) -> list[DossierPatient]:
    """Construit la liste des dossiers fictifs (toujours la même pour une graine donnée)."""
    alea = random.Random(GRAINE)
    debut = date(2025, 1, 1)
    dossiers = []
    for numero in range(1, nombre + 1):
        nb_antecedents = alea.choice([1, 1, 2])
        antecedents = alea.sample(ANTECEDENTS, nb_antecedents)
        if "Aucun antécédent notable" in antecedents and len(antecedents) > 1:
            antecedents.remove("Aucun antécédent notable")
        dossiers.append(
            DossierPatient(
                id=numero,
                nom=f"{alea.choice(PRENOMS)} {alea.choice(NOMS).upper()}",
                age=alea.randint(1, 92),
                groupe_sanguin=alea.choice(GROUPES),
                medecin=alea.choice(MEDECINS),
                antecedents=" ; ".join(antecedents),
                traitement=alea.choice(TRAITEMENTS),
                allergies=alea.choice(ALLERGIES),
                derniere_consultation=debut + timedelta(days=alea.randint(0, 540)),
                fictif=True,
            )
        )
    return dossiers


def peupler_dossiers(bdd: Session) -> int:
    """Insère les dossiers fictifs si la table est vide. Renvoie le nombre inséré."""
    if bdd.scalar(select(func.count()).select_from(DossierPatient)):
        return 0
    dossiers = generer_dossiers()
    bdd.add_all(dossiers)
    bdd.commit()
    return len(dossiers)
