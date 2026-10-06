"""Décision : z-score, fusion, règles R1–R4 et raison prioritaire."""

import json

import pytest

from app.biometrie import Decision, ParametresDecision, decider
from app.biometrie.decision import MESSAGES_ECHEC

# Paramètres explicites : les tests ne dépendent pas des valeurs par défaut (provisoires).
P = ParametresDecision(
    poids_visage=0.6, poids_oreille=0.4,
    plancher_visage=0.64, plancher_oreille=0.74, seuil_fusion=2.5,
    moyenne_imposteur_visage=0.52, ecart_type_imposteur_visage=0.04,
    moyenne_imposteur_oreille=0.75, ecart_type_imposteur_oreille=0.05,
)


def _etats(d: Decision) -> dict:
    return {r["code"]: r["ok"] for r in d.regles}


def test_toutes_regles_ok():
    d = decider(0.78, 0.86, True, P)
    assert d.accepte and d.raison is None
    assert [r["code"] for r in d.regles] == ["R1", "R2", "R3", "R4"]
    assert d.z_visage == pytest.approx((0.78 - 0.52) / 0.04)
    assert d.z_oreille == pytest.approx((0.86 - 0.75) / 0.05)
    assert d.score_fusion == pytest.approx(0.6 * d.z_visage + 0.4 * d.z_oreille)


def test_r1_seule_en_echec():
    d = decider(0.78, 0.86, False, P)
    assert not d.accepte
    assert _etats(d) == {"R1": False, "R2": True, "R3": True, "R4": True}
    assert d.raison == "Vivacité non démontrée : le mouvement de tête n'a pas été détecté"


def test_r2_seule_en_echec():
    d = decider(0.63, 0.95, True, P)  # fusion = 0,6 × 2,75 + 0,4 × 4 = 3,25 ≥ 2,5
    assert _etats(d) == {"R1": True, "R2": False, "R3": True, "R4": True}
    assert d.raison == "Le visage ne correspond pas suffisamment au gabarit enrôlé"


def test_r3_seule_en_echec():
    d = decider(0.85, 0.70, True, P)
    assert _etats(d) == {"R1": True, "R2": True, "R3": False, "R4": True}
    assert d.raison == "L'oreille ne correspond pas suffisamment au gabarit enrôlé"


def test_r4_seule_en_echec():
    d = decider(0.65, 0.76, True, P)  # juste au-dessus des planchers : fusion ≈ 2,03
    assert _etats(d) == {"R1": True, "R2": True, "R3": True, "R4": False}
    assert d.raison == "Score de fusion insuffisant"


def test_raison_premiere_regle_en_echec_et_toutes_evaluees():
    d = decider(0.50, 0.60, False, P)
    assert _etats(d) == {"R1": False, "R2": False, "R3": False, "R4": False}
    assert d.raison == MESSAGES_ECHEC["R1"]
    assert decider(0.50, 0.60, True, P).raison == MESSAGES_ECHEC["R2"]
    assert decider(0.80, 0.60, True, P).raison == MESSAGES_ECHEC["R3"]


def test_to_dict_serialisable():
    d = decider(0.7, 0.8, True, P).to_dict()
    texte = json.dumps(d)
    assert set(d) == {"accepte", "score_visage", "score_oreille", "z_visage", "z_oreille",
                      "score_fusion", "regles", "raison"}
    assert all(set(r) == {"code", "libelle", "ok", "valeur", "seuil"} for r in d["regles"])
    assert d["regles"][0]["valeur"] is None and d["regles"][0]["seuil"] is None
    assert "R4" in texte


def test_valeurs_par_defaut_coherentes():
    """Défauts (provisoires) : légitime typique accepté, imposteur typique refusé."""
    defaut = ParametresDecision()
    assert defaut.version == 1 and defaut.poids_visage == 0.6 and defaut.poids_oreille == 0.4
    assert decider(0.75, 0.84, True, defaut).accepte
    assert not decider(0.52, 0.75, True, defaut).accepte
    assert not decider(0.56, 0.95, True, defaut).accepte  # sosie + oreille parfaite : R2


def test_ecart_type_nul_refuse():
    with pytest.raises(ValueError):
        decider(0.7, 0.8, True, ParametresDecision(ecart_type_imposteur_visage=0.0))
