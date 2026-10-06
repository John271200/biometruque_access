"""Faux moteur biométrique et helpers de parcours pour les tests de l'API.

Le `FakeMoteur` respecte l'interface `MoteurBiometrique.nouvelle_session` du contrat et
renvoie des `RetourImage` / `ResultatCapture` réels du module `app.biometrie` (si
importable) ; l'API utilise les vraies fonctions `biohash`, `Chiffreur` et `decider`.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

import numpy as np

try:  # vrais objets du moteur si le module est importable
    from app.biometrie import ResultatCapture, RetourImage
    from app.biometrie.session import PreuveVivacite
except ImportError:  # pragma: no cover - repli minimal conforme au contrat
    from dataclasses import asdict

    @dataclass
    class RetourImage:  # type: ignore[no-redef]
        etape: str
        captures_visage: int
        captures_visage_requises: int
        captures_oreille: int
        captures_oreille_requises: int
        image_retenue: bool
        message: str
        criteres: list
        lacet: float | None
        cadre_visage: list | None
        cadre_oreille: list | None
        apercu_oreille: str | None
        raison_echec: str | None

        def to_dict(self) -> dict:
            return asdict(self)

    @dataclass
    class PreuveVivacite:  # type: ignore[no-redef]
        ok: bool
        details: dict

    @dataclass
    class ResultatCapture:  # type: ignore[no-redef]
        vecteur_visage: np.ndarray
        vecteur_oreille: np.ndarray
        extracteur_visage: str
        extracteur_oreille: str
        cote_oreille: str
        vivacite: PreuveVivacite


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 128 + b"\xff\xd9"  # le faux moteur ne décode pas
MOT_DE_PASSE = "MotDePasse2026"
DIM_VISAGE, DIM_OREILLE = 512, 256


def vecteur(graine: int, dim: int) -> np.ndarray:
    """Vecteur aléatoire L2-normalisé (float32)."""
    v = np.random.default_rng(graine).standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def proche(v: np.ndarray, graine: int, bruit: float = 0.05) -> np.ndarray:
    """Vecteur proche de `v` (même personne, autre capture)."""
    w = v + bruit * np.random.default_rng(graine).standard_normal(v.shape[0]).astype(np.float32) / np.sqrt(v.shape[0])
    return (w / np.linalg.norm(w)).astype(np.float32)


@dataclass
class Programme:
    """Comportement des prochaines sessions créées par le faux moteur."""

    vecteur_visage: np.ndarray = field(default_factory=lambda: vecteur(1, DIM_VISAGE))
    vecteur_oreille: np.ndarray = field(default_factory=lambda: vecteur(2, DIM_OREILLE))
    cote: str = "droite"
    vivacite_ok: bool = True
    echec_a: int | None = None              # numéro de l'image qui fait échouer la session
    raison_echec: str = "Vivacité non démontrée : rotation de la tête non détectée."
    attente: threading.Event | None = None  # bloque traiter_image jusqu'au signal
    entree: threading.Event | None = None   # signalé quand traiter_image commence


class FakeSession:
    """Fausse `SessionCapture` : se termine après nb_visage + nb_oreille images."""

    def __init__(self, programme: Programme, mode: str, nb_visage: int, nb_oreille: int,
                 cote_attendu: str | None, apercu: bool) -> None:
        self.id = uuid.uuid4().hex
        self.mode, self.nb_visage, self.nb_oreille = mode, nb_visage, nb_oreille
        self.cote_attendu, self.apercu = cote_attendu, apercu
        self.programme = programme
        self.images = 0
        self.terminee = False
        self.echouee = False
        self.effacee = False
        self._verrou = threading.Lock()

    def _retour(self, etape: str, message: str, raison: str | None = None) -> RetourImage:
        return RetourImage(
            etape=etape,
            captures_visage=min(self.images, self.nb_visage),
            captures_visage_requises=self.nb_visage,
            captures_oreille=max(0, min(self.images - self.nb_visage, self.nb_oreille)),
            captures_oreille_requises=self.nb_oreille,
            image_retenue=etape != "echec",
            message=message,
            criteres=[],
            lacet=12.5,
            cadre_visage=[0.3, 0.2, 0.7, 0.8],
            cadre_oreille=None,
            apercu_oreille=None,
            raison_echec=raison,
        )

    def traiter_image(self, image_jpeg: bytes) -> RetourImage:
        p = self.programme
        if p.entree is not None:
            p.entree.set()
        if p.attente is not None:
            p.attente.wait(timeout=5)
        with self._verrou:
            self.images += 1
            if p.echec_a is not None and self.images >= p.echec_a:
                self.echouee = True
                return self._retour("echec", p.raison_echec, p.raison_echec)
            if self.images >= self.nb_visage + self.nb_oreille:
                self.terminee = True
                return self._retour("terminee", "Capture terminée.")
            if self.images < self.nb_visage:
                return self._retour("visage", "Regardez la caméra.")
            return self._retour("oreille", "Tournez la tête pour montrer votre oreille.")

    def resultat(self) -> ResultatCapture:
        assert self.terminee and not self.effacee
        p = self.programme
        return ResultatCapture(
            vecteur_visage=p.vecteur_visage.copy(),
            vecteur_oreille=p.vecteur_oreille.copy(),
            extracteur_visage="arcface-w600k-r50",
            extracteur_oreille="lbp-v1",
            cote_oreille=self.cote_attendu or p.cote,
            vivacite=PreuveVivacite(ok=p.vivacite_ok, details={}),
        )

    def effacer(self) -> None:
        self.effacee = True


class FakeMoteur:
    """Faux `MoteurBiometrique` programmable."""

    def __init__(self) -> None:
        self.programme = Programme()
        self.sessions: list[FakeSession] = []

    def programmer(self, **valeurs) -> None:
        self.programme = Programme(**valeurs)

    def nouvelle_session(self, mode, nb_visage, nb_oreille, cote_attendu=None, apercu=False):
        session = FakeSession(self.programme, mode, nb_visage, nb_oreille, cote_attendu, apercu)
        self.sessions.append(session)
        return session


# --- Helpers de parcours ---------------------------------------------------------------

def entete(jeton: str) -> dict:
    return {"Authorization": f"Bearer {jeton}"}


def inscrire(client, email="awa@exemple.bj", nom="Awa Dossou", mot_de_passe=MOT_DE_PASSE) -> dict:
    r = client.post("/api/comptes", json={"nom": nom, "email": email, "mot_de_passe": mot_de_passe})
    assert r.status_code == 201, r.text
    return r.json()


def connecter(client, email="awa@exemple.bj", mot_de_passe=MOT_DE_PASSE) -> str:
    r = client.post("/api/session", json={"email": email, "mot_de_passe": mot_de_passe})
    assert r.status_code == 200, r.text
    return r.json()["jeton_compte"]


def consentir(client, jeton: str) -> dict:
    version = client.get("/api/consentement/texte").json()["version"]
    r = client.post("/api/consentement", json={"accepte": True, "version": version},
                    headers=entete(jeton))
    assert r.status_code == 200, r.text
    return r.json()


def envoyer(client, url: str, jeton: str | None = None, contenu: bytes = JPEG,
            type_contenu: str = "image/jpeg"):
    entetes = {"Content-Type": type_contenu}
    if jeton:
        entetes |= entete(jeton)
    return client.post(url, content=contenu, headers=entetes)


def enroler(client, jeton: str) -> dict:
    """Enrôlement complet (5 + 5 images) ; renvoie la dernière réponse."""
    r = client.post("/api/enrolement/sessions", headers=entete(jeton))
    assert r.status_code == 201, r.text
    sid = r.json()["session_id"]
    for _ in range(10):
        r = envoyer(client, f"/api/enrolement/sessions/{sid}/images", jeton)
        assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["etape"] == "terminee"
    return corps


def compte_enrole(client, email="awa@exemple.bj") -> str:
    """Inscription + connexion + consentement + enrôlement ; renvoie le jeton compte."""
    inscrire(client, email=email)
    jeton = connecter(client, email=email)
    consentir(client, jeton)
    enroler(client, jeton)
    return jeton


def authentifier(client, email="awa@exemple.bj", nb_images: int = 6):
    """Authentification complète ; renvoie la dernière réponse HTTP."""
    r = client.post("/api/authentification/sessions", json={"email": email})
    assert r.status_code == 201, r.text
    sid = r.json()["session_id"]
    for _ in range(nb_images):
        r = envoyer(client, f"/api/authentification/sessions/{sid}/images")
        if r.status_code != 200 or r.json()["etape"] in ("terminee", "echec"):
            break
    return r


def imposteur(moteur: FakeMoteur) -> None:
    """Les prochaines sessions présenteront une autre personne."""
    moteur.programmer(vecteur_visage=vecteur(101, DIM_VISAGE), vecteur_oreille=vecteur(102, DIM_OREILLE))


def legitime(moteur: FakeMoteur, graine: int = 7) -> None:
    """Les prochaines sessions présenteront la personne enrôlée (captures légèrement différentes)."""
    base = Programme()
    moteur.programmer(vecteur_visage=proche(base.vecteur_visage, graine),
                      vecteur_oreille=proche(base.vecteur_oreille, graine + 1))
