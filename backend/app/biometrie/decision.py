"""Décision d'authentification : normalisation z-score, fusion et règles R1–R4.

Règles (contrat MVP, section 2) — l'accès n'est accordé que si les quatre passent :

- **R1** vivacité démontrée (rotation de la tête suivie en continu) ;
- **R2** garde-fou visage : ``score_visage ≥ plancher_visage`` ;
- **R3** garde-fou oreille : ``score_oreille ≥ plancher_oreille`` ;
- **R4** fusion : ``w_v·z_v + w_o·z_o ≥ seuil_fusion`` avec
  ``z = (score − moyenne_imposteur) / écart_type_imposteur``.

Les scores sont des similarités de Hamming entre codes BioHashing (``protection.py``) :
``E[score] = 1 − θ/π`` où θ est l'angle entre le vecteur enrôlé et le vecteur présenté.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ParametresDecision:
    """Paramètres de décision — **valeurs PROVISOIRES** (point 24 des points à trancher).

    Elles sont déduites de la relation ``score = 1 − θ/π`` du BioHashing et d'ordres de
    grandeur publiés pour ArcFace ; elles DOIVENT être recalibrées sur de vraies captures
    webcam (distributions légitimes / imposteurs mesurées) avant toute évaluation.

    Repères pour le visage (ArcFace w600k_r50, code de 256 bits) :

    ======================  ===========  =======================
    cosinus ArcFace          angle θ      similarité attendue
    ======================  ===========  =======================
    0,0 (inconnu typique)    90°          0,500
    0,2 (sosie)              78,5°        0,564
    0,43                     64,5°        0,640  ← plancher
    0,6 (légitime webcam)    53,1°        0,705
    0,8 (légitime net)       36,9°        0,795
    ======================  ===========  =======================

    Écart-type binomial sur 256 bits : √(0,25/256) ≈ 0,031 (au plus).
    """

    version: int = 1

    # Poids de la fusion : le visage (ArcFace) est bien plus discriminant que l'oreille LBP.
    poids_visage: float = 0.6
    poids_oreille: float = 0.4

    # R2 — plancher visage 0,64 ≈ cosinus 0,43 : environ 4 écarts-types au-dessus d'un
    # imposteur typique (0,50–0,52) et 2,5 au-dessus d'un sosie (0,564), tout en laissant
    # passer un légitime webcam (≈ 0,70–0,80, écart-type ≈ 0,03). C'est le garde-fou
    # principal (avec la vivacité).
    plancher_visage: float = 0.64

    # R3 — plancher oreille PRUDENT mais atteignable par un légitime. Les histogrammes LBP
    # (même centrés) se ressemblent beaucoup d'un individu à l'autre. Mesures sur des
    # vignettes de textures (PAS de vraies oreilles) : textures différentes ≈ 0,73
    # (écart-type 0,05), zones voisines de visages différents ≈ 0,76 ; même vignette
    # recapturée (décalage ±3 px, échelle ±5 %, luminosité ±10 %, JPEG) ≈ 0,88 avec un
    # bruit faible (5 % < 0,83) et ≈ 0,84 avec un bruit de webcam marqué (5 % < 0,75).
    # Des oreilles différentes se ressemblant plus que des textures quelconques, on retient
    # une moyenne imposteur de 0,75 ; le plancher 0,74 n'écarte que les oreilles nettement
    # différentes ou mal cadrées et laisse une large marge au légitime. La sécurité repose
    # d'abord sur le visage et la vivacité. Valeurs à recalibrer IMPÉRATIVEMENT sur de
    # vraies captures de profil (la localisation de l'oreille n'a pas été validée sur des
    # images réelles de profil).
    plancher_oreille: float = 0.74

    # R4 — seuil de fusion en « écarts-types au-dessus de la population imposteur » : un
    # légitime typique obtient z_v ≈ 4,5–7 (score visage 0,70–0,80) et z_o ≈ 1–2,5
    # (score oreille 0,80–0,88), soit une fusion ≈ 3–5 ; un imposteur typique ≈ 0. Un
    # utilisateur tout juste au-dessus des deux planchers (0,6 × 3,0 + 0,4 × (−0,2) ≈ 1,7)
    # est refusé : il faut une marge nette sur au moins une modalité (ex. visage 0,70 et
    # oreille 0,76 → 0,6 × 4,5 + 0,4 × 0,2 ≈ 2,8 : accepté).
    seuil_fusion: float = 2.5

    # Paramètres z-score « imposteurs » figés (à remplacer par les valeurs mesurées).
    # Visage : moyenne 0,52 (cosinus imposteur ≈ 0,05–0,1) ; écart-type 0,04 = bruit
    # binomial (0,031) + dispersion des cosinus imposteurs.
    moyenne_imposteur_visage: float = 0.52
    ecart_type_imposteur_visage: float = 0.04
    # Oreille LBP : moyenne 0,75 et écart-type 0,05 (voir R3 ; ordre de grandeur mesuré
    # sur des vignettes de textures, pas sur de vraies oreilles).
    moyenne_imposteur_oreille: float = 0.75
    ecart_type_imposteur_oreille: float = 0.05


@dataclass
class Decision:
    accepte: bool
    score_visage: float
    score_oreille: float
    z_visage: float
    z_oreille: float
    score_fusion: float
    regles: list[dict] = field(default_factory=list)
    raison: str | None = None

    def to_dict(self) -> dict:
        """Représentation sérialisable en JSON telle quelle."""
        return asdict(self)


MESSAGES_ECHEC = {
    "R1": "Vivacité non démontrée : le mouvement de tête n'a pas été détecté",
    "R2": "Le visage ne correspond pas suffisamment au gabarit enrôlé",
    "R3": "L'oreille ne correspond pas suffisamment au gabarit enrôlé",
    "R4": "Score de fusion insuffisant",
}


def _z(score: float, moyenne: float, ecart_type: float) -> float:
    if ecart_type <= 0:
        raise ValueError("L'écart-type imposteur doit être strictement positif.")
    return (score - moyenne) / ecart_type


def decider(
    score_visage: float, score_oreille: float, vivacite_ok: bool, params: ParametresDecision
) -> Decision:
    """Évalue TOUJOURS les quatre règles ; la raison est celle de la première en échec."""
    score_visage = float(score_visage)
    score_oreille = float(score_oreille)
    z_v = _z(score_visage, params.moyenne_imposteur_visage, params.ecart_type_imposteur_visage)
    z_o = _z(score_oreille, params.moyenne_imposteur_oreille, params.ecart_type_imposteur_oreille)
    fusion = params.poids_visage * z_v + params.poids_oreille * z_o

    regles = [
        {"code": "R1", "libelle": "Vivacité", "ok": bool(vivacite_ok),
         "valeur": None, "seuil": None},
        {"code": "R2", "libelle": "Garde-fou visage", "ok": score_visage >= params.plancher_visage,
         "valeur": score_visage, "seuil": float(params.plancher_visage)},
        {"code": "R3", "libelle": "Garde-fou oreille",
         "ok": score_oreille >= params.plancher_oreille,
         "valeur": score_oreille, "seuil": float(params.plancher_oreille)},
        {"code": "R4", "libelle": "Fusion des scores", "ok": fusion >= params.seuil_fusion,
         "valeur": float(fusion), "seuil": float(params.seuil_fusion)},
    ]
    premiere_en_echec = next((r for r in regles if not r["ok"]), None)
    return Decision(
        accepte=premiere_en_echec is None,
        score_visage=score_visage,
        score_oreille=score_oreille,
        z_visage=float(z_v),
        z_oreille=float(z_o),
        score_fusion=float(fusion),
        regles=regles,
        raison=MESSAGES_ECHEC[premiere_en_echec["code"]] if premiere_en_echec else None,
    )
