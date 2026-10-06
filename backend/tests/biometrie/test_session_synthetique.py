"""Machine à états de la capture guidée, pilotée par des séquences synthétiques de lacets.

L'analyseur et l'horloge sont injectés : aucune image ni aucun modèle n'est nécessaire.
"""

from __future__ import annotations

import base64
import json

import numpy as np
import pytest

from app.biometrie import RetourImage, SessionCapture
from app.biometrie.oreille import ZoneOreille
from app.biometrie.qualite import ConfigQualite, Critere, critere_frontalite
from app.biometrie.session import Observation, ObservationOreille, compter_inversions

RNG = np.random.default_rng(0)
PERSONNE_A = RNG.standard_normal(512).astype(np.float32)
PERSONNE_A /= np.linalg.norm(PERSONNE_A)
PERSONNE_B = RNG.standard_normal(512).astype(np.float32)
PERSONNE_B /= np.linalg.norm(PERSONNE_B)
OREILLE = RNG.standard_normal(924).astype(np.float32)
OREILLE /= np.linalg.norm(OREILLE)
BBOX = (270.0, 140.0, 370.0, 270.0)


class Horloge:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def avancer(self, secondes: float) -> None:
        self.t += secondes


class AnalyseurFactice:
    """Renvoie l'observation préparée par le test (l'image JPEG est ignorée)."""

    def __init__(self) -> None:
        self.prochaine: Observation | None = None

    def analyser(self, image_jpeg: bytes) -> Observation:
        assert self.prochaine is not None
        obs, self.prochaine = self.prochaine, None
        return obs


def _bruite(v: np.ndarray, niveau: float = 0.01) -> np.ndarray:
    w = v + RNG.normal(0, niveau, v.shape).astype(np.float32)
    return w / np.linalg.norm(w)


def observation(lacet: float = 0.0, *, cote: str | None = None, personne=PERSONNE_A,
                bbox=BBOX, nb_visages: int = 1, qualite_ok: bool = True,
                oreille_ok: bool = True) -> Observation:
    """Observation synthétique ; côté déduit du signe du lacet (nez vers la droite → « droite »)."""
    if nb_visages != 1:
        return Observation(lisible=True, largeur=640, hauteur=480, nb_visages=nb_visages)
    criteres = [Critere("taille", True, "ok"), Critere("centrage", True, "ok"),
                Critere("nettete", qualite_ok, "Image floue" if not qualite_ok else "ok"),
                Critere("eclairage", True, "ok"), critere_frontalite(lacet, ConfigQualite())]
    zone = ZoneOreille(cote="droite", boite=(200.0, 120.0, 260.0, 210.0),
                       boite_complete=(200.0, 120.0, 260.0, 210.0), fraction_dans_image=1.0)
    oreille = ObservationOreille(
        zone=zone,
        criteres=[Critere("oreille_nettete", oreille_ok, "ok" if oreille_ok else "Oreille floue")],
        vecteur=_bruite(OREILLE, 0.02) if oreille_ok else None,
        vignette=np.full((144, 96), 128, dtype=np.uint8),
    )
    plongement = _bruite(personne)
    return Observation(
        lisible=True, largeur=640, hauteur=480, nb_visages=1, bbox=bbox, lacet=lacet,
        cote=cote or ("droite" if lacet >= 0 else "gauche"), criteres_visage=criteres,
        calcul_plongement=lambda: plongement, calcul_oreille=lambda: oreille,
    )


class Pilote:
    def __init__(self, mode="enrolement", nb_visage=5, nb_oreille=5, cote_attendu=None,
                 apercu=False) -> None:
        self.horloge = Horloge()
        self.analyseur = AnalyseurFactice()
        self.session = SessionCapture(mode, nb_visage, nb_oreille, cote_attendu=cote_attendu,
                                      apercu=apercu, analyseur=self.analyseur, horloge=self.horloge)

    def image(self, obs: Observation, apres: float = 0.3) -> RetourImage:
        self.horloge.avancer(apres)
        self.analyseur.prochaine = obs
        return self.session.traiter_image(b"jpeg factice")

    def visages(self, n: int | None = None) -> RetourImage:
        for _ in range(n or self.session.nb_visage):
            retour = self.image(observation(2.0), apres=0.5)
        return retour

    def rotation(self, lacets, cote=None, pas=0.3) -> RetourImage:
        for lacet in lacets:
            retour = self.image(observation(lacet, cote=cote), apres=pas)
        return retour


# ------------------------------------------------------------------------ parcours nominal
def test_enrolement_nominal_puis_effacement():
    p = Pilote()
    retours = [p.image(observation(2.0), apres=0.5) for _ in range(5)]
    assert all(r.image_retenue for r in retours)
    assert [r.captures_visage for r in retours] == [1, 2, 3, 4, 5]
    assert retours[0].etape == "visage" and retours[-1].etape == "rotation"
    assert retours[-1].message == "Tournez lentement la tête vers la gauche"

    retour = p.rotation([5, 20, 30, 40])
    assert retour.etape == "rotation" and "Continuez" in retour.message
    retour = p.rotation([55])
    assert retour.etape == "oreille"
    assert any(c.code == "vivacite" and c.ok for c in retour.criteres)

    retours = [p.image(observation(60), apres=0.4) for _ in range(5)]
    assert [r.captures_oreille for r in retours] == [1, 2, 3, 4, 5]
    assert retours[-1].etape == "terminee" and p.session.terminee and not p.session.echouee
    assert retours[0].cadre_oreille is not None and retours[0].apercu_oreille is None

    res = p.session.resultat()
    assert res.vecteur_visage.shape == (512,) and res.vecteur_visage.dtype == np.float32
    assert np.linalg.norm(res.vecteur_visage) == pytest.approx(1.0, abs=1e-5)
    assert float(res.vecteur_visage @ PERSONNE_A) > 0.99
    assert res.vecteur_oreille.shape == (924,)
    assert np.linalg.norm(res.vecteur_oreille) == pytest.approx(1.0, abs=1e-5)
    assert res.extracteur_visage == "arcface-w600k-r50" and res.extracteur_oreille == "lbp-v1"
    assert res.cote_oreille == "droite"
    assert res.vivacite.ok
    assert res.vivacite.details["nb_intermediaires"] == 3
    assert res.vivacite.details["inversions"] == 0
    assert set(res.vivacite.details) == {"amplitude", "nb_intermediaires", "inversions", "duree_s"}

    p.session.effacer()
    assert not res.vecteur_visage.any() and not res.vecteur_oreille.any()
    with pytest.raises(RuntimeError):
        p.session.resultat()


def test_retour_image_serialisable_et_cadre_normalise():
    p = Pilote()
    retour = p.image(observation(-3.0), apres=0.5)
    d = retour.to_dict()
    json.dumps(d)
    assert set(d) == {"etape", "captures_visage", "captures_visage_requises", "captures_oreille",
                      "captures_oreille_requises", "image_retenue", "message", "criteres", "lacet",
                      "cadre_visage", "cadre_oreille", "apercu_oreille", "raison_echec"}
    assert d["lacet"] == 3.0  # valeur absolue
    assert d["cadre_visage"] == pytest.approx([270 / 640, 140 / 480, 370 / 640, 270 / 480])
    assert all(set(c) == {"code", "ok", "message"} for c in d["criteres"])


def test_apercu_oreille_jpeg_base64():
    p = Pilote(nb_visage=1, nb_oreille=1, apercu=True)
    p.visages()
    p.rotation([5, 20, 35, 50])
    retour = p.image(observation(60))
    assert retour.etape == "terminee" and retour.apercu_oreille
    assert base64.b64decode(retour.apercu_oreille)[:2] == b"\xff\xd8"  # en-tête JPEG


# ------------------------------------------------------------------------ étape visage
def test_intervalle_minimal_entre_captures_de_face():
    p = Pilote()
    assert p.image(observation(), apres=0.5).image_retenue
    retour = p.image(observation(), apres=0.1)
    assert not retour.image_retenue and retour.captures_visage == 1
    assert p.image(observation(), apres=0.35).image_retenue


def test_qualite_insuffisante_pas_de_capture():
    p = Pilote()
    retour = p.image(observation(qualite_ok=False), apres=0.5)
    assert not retour.image_retenue and retour.message == "Image floue"
    retour = p.image(observation(25.0), apres=0.5)
    assert not retour.image_retenue and retour.message == "Regardez droit vers la caméra"


def test_plusieurs_visages_refus_explicite():
    p = Pilote()
    retour = p.image(observation(nb_visages=3), apres=0.5)
    assert not retour.image_retenue
    assert retour.criteres[0].code == "visage_unique" and not retour.criteres[0].ok
    assert "Plusieurs visages" in retour.message


def test_identite_incoherente_entre_captures_echec():
    p = Pilote()
    p.image(observation(), apres=0.5)
    retour = p.image(observation(personne=PERSONNE_B), apres=0.5)
    assert retour.etape == "echec" and p.session.echouee
    assert retour.raison_echec == "Les captures ne correspondent pas à une même personne"
    # Une session échouée le reste.
    assert p.image(observation()).etape == "echec"


def test_image_illisible_pas_d_exception():
    p = Pilote()
    retour = p.image(Observation(lisible=False))
    assert retour.etape == "visage"
    assert retour.criteres == [Critere("image", False, "Image illisible")]


# ------------------------------------------------------------------------ rotation / vivacité
def test_rotation_trop_rapide_puis_reprise():
    p = Pilote()
    p.visages()
    retour = p.rotation([5, 50])  # du face au profil sans position intermédiaire
    assert retour.etape == "rotation"
    assert retour.message == ("Mouvement trop rapide : revenez face à la caméra puis tournez "
                              "plus lentement")
    retour = p.rotation([55])  # toujours de profil : il faut revenir de face
    assert retour.etape == "rotation" and "Revenez face à la caméra" in retour.message
    retour = p.rotation([4, 18, 30, 42, 50])
    assert retour.etape == "oreille"


def test_perte_du_visage_pendant_la_rotation():
    p = Pilote()
    p.visages()
    p.rotation([5, 20])
    retour = p.image(observation(nb_visages=0), apres=0.5)  # perte brève : tolérée
    assert retour.etape == "rotation" and not retour.criteres[0].ok
    retour = p.image(observation(nb_visages=0), apres=1.5)  # > 1,5 s depuis la dernière détection
    assert retour.etape == "rotation" and retour.message.startswith("Visage perdu")
    retour = p.rotation([30])  # la séquence a été remise à zéro
    assert "Revenez face à la caméra" in retour.message
    assert p.rotation([3, 20, 30, 50]).etape == "oreille"


def test_photo_fixe_qui_ne_tourne_jamais_delai_puis_echec():
    p = Pilote()
    p.visages()
    retour = None
    for _ in range(130):
        retour = p.image(observation(1.0), apres=1.0)
        if retour.etape == "echec":
            break
    assert retour.etape == "echec" and p.session.echouee
    assert retour.raison_echec.startswith("Délai dépassé")
    with pytest.raises(RuntimeError):
        p.session.resultat()


def test_cote_inattendu_en_authentification():
    p = Pilote("authentification", 3, 3, cote_attendu="droite")
    p.visages()
    retour = p.rotation([-20], cote="gauche")
    assert retour.message == "Tournez la tête vers la gauche"
    assert any(c.code == "cote" and not c.ok for c in retour.criteres)
    retour = p.rotation([-30, -50], cote="gauche")
    assert retour.etape == "rotation"  # jamais de passage à l'oreille du mauvais côté
    assert p.rotation([3, 20, 30, 50]).etape == "oreille"
    for _ in range(3):
        retour = p.image(observation(60), apres=0.4)
    assert retour.etape == "terminee"
    assert p.session.resultat().cote_oreille == "droite"


def test_enrolement_cote_libre_enregistre():
    p = Pilote()
    p.visages()
    assert p.rotation([-5, -20, -30, -50], cote="gauche").etape == "oreille"
    for _ in range(5):
        retour = p.image(observation(-60, cote="gauche"), apres=0.4)
    assert retour.etape == "terminee"
    assert p.session.resultat().cote_oreille == "gauche"


def test_rotation_trop_lente():
    p = Pilote()
    p.visages()
    p.rotation([5, 20], pas=0.3)
    retour = p.rotation([30], pas=10.0)
    assert retour.message.startswith("Rotation trop lente")
    assert p.rotation([4, 20, 30, 50]).etape == "oreille"


def test_mouvement_irregulier():
    p = Pilote()
    p.visages()
    retour = p.rotation([5, 20, 35, 20, 35, 20, 35, 50])
    assert retour.message.startswith("Mouvement irrégulier")
    assert retour.etape == "rotation"


def test_saut_brusque_du_visage():
    p = Pilote()
    p.visages()
    p.rotation([5, 20])
    loin = (BBOX[0] + 200, BBOX[1], BBOX[2] + 200, BBOX[3])
    retour = p.image(observation(25, bbox=loin))
    assert retour.message.startswith("Mouvement trop brusque")
    assert "Revenez face" in p.image(observation(30, bbox=loin)).message


def test_changement_d_identite_pendant_la_rotation():
    p = Pilote()
    p.visages()
    p.rotation([5, 20])
    retour = p.image(observation(30, personne=PERSONNE_B))
    assert "ne correspond plus" in retour.message
    assert any(c.code == "identite" and not c.ok for c in retour.criteres)
    assert retour.etape == "rotation"


# ------------------------------------------------------------------------ étape oreille
def test_etape_oreille_consignes():
    p = Pilote()
    p.visages()
    p.rotation([5, 20, 30, 50])
    retour = p.image(observation(35))
    assert retour.message == "Tournez encore un peu la tête vers la gauche" and not retour.image_retenue
    retour = p.image(observation(nb_visages=0))
    assert retour.message == "Tournez un peu moins la tête"
    retour = p.image(observation(60, oreille_ok=False))
    assert retour.message == "Oreille floue" and not retour.image_retenue
    assert p.image(observation(60)).image_retenue
    assert not p.image(observation(60), apres=0.1).image_retenue  # 300 ms minimum


def test_incident_a_l_etape_oreille_refaire_la_rotation():
    p = Pilote()
    p.visages()
    p.rotation([5, 20, 30, 50])
    assert p.image(observation(60)).captures_oreille == 1
    retour = p.image(observation(nb_visages=2))
    assert retour.etape == "rotation" and retour.captures_oreille == 0


def test_compter_inversions():
    assert compter_inversions([5, 20, 30, 40, 50], 3) == 0
    assert compter_inversions([5, 20, 19, 30, 50], 3) == 0  # bruit ignoré
    assert compter_inversions([5, 20, 10, 30, 50], 3) == 2


def test_parametres_invalides():
    with pytest.raises(ValueError):
        SessionCapture("inconnu", 5, 5, analyseur=AnalyseurFactice())
    with pytest.raises(ValueError):
        SessionCapture("enrolement", 0, 5, analyseur=AnalyseurFactice())
    with pytest.raises(ValueError):
        SessionCapture("enrolement", 5, 5)  # analyseur requis


def test_effacement_en_cours_de_session():
    p = Pilote()
    p.visages(2)
    p.session.effacer()
    retour = p.image(observation())
    assert retour.etape == "echec" and retour.raison_echec == "Session annulée"
    assert retour.captures_visage == 0
