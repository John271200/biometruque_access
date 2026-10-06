# Contrat technique du MVP « parcours biométrique »

> **Écart assumé à la méthode** : l'auteur a choisi, en connaissance de cause, de construire
> un MVP fonctionnel avant la validation des cas d'utilisation (voir `SUIVI.md`). Ce contrat
> fige l'interface entre les trois briques pour qu'elles soient développées en parallèle.
> Les valeurs par défaut reprennent les **recommandations** de
> `docs/cas-utilisation/08-points-a-trancher.md` ; elles restent modifiables.

## 0. Périmètre du MVP

Inclus : inscription, connexion « compte », consentement, enrôlement webcam (visage puis
rotation → oreille), authentification biométrique (fusion + garde-fou + vivacité),
jeton d'accès 10 min, base protégée de dossiers patients **fictifs**, consultation de ses
données, révocation, suppression du compte, journalisation.

Exclus du MVP (étapes suivantes) : espace d'administration, laboratoire d'attaques,
rapport CSV/PDF, protocole d'évaluation, extracteur d'oreille ONNX (l'interface est prête,
seul le LBP est implémenté), Alembic (création des tables au démarrage), Docker Compose.

## 1. Arborescence

```
backend/
  app/
    main.py, config.py, db.py, modeles.py, securite.py, dependances.py   ← API (agent API)
    routes/  sante.py comptes.py consentement.py enrolement.py authentification.py dossiers.py moi.py
    biometrie/                                                           ← moteur (agent biométrie)
      __init__.py      exporte MoteurBiometrique, SessionCapture, RetourImage, ResultatCapture,
                       generer_jeton, biohash, similarite_hamming, Chiffreur, ErreurIntegrite,
                       ParametresDecision, Decision, decider
      onnx_insightface.py   détection SCRFD, landmarks 3D 68 + lacet, ArcFace (onnxruntime pur)
      qualite.py            critères de qualité
      oreille.py            interface ExtracteurOreille + ExtracteurLBP
      session.py            machine à états de la capture guidée + vivacité
      protection.py         BioHashing + AES-256-GCM
      decision.py           z-score, fusion, garde-fou, règles R1–R4
  scripts/telecharger_modeles.py   télécharge buffalo_l dans backend/models/buffalo_l/
  tests/biometrie/  tests/api/
  requirements.txt  pytest.ini
frontend/            Vue 3 + Vite + TypeScript + Pinia + vue-router  ← (agent frontend)
```

**Pas de dépendance au paquet Python `insightface`** : son installation sous Windows exige un
compilateur C++. On utilise directement les modèles ONNX officiels `buffalo_l`
(`det_10g.onnx`, `1k3d68.onnx`, `w600k_r50.onnx`) avec `onnxruntime`, `numpy`,
`opencv-python-headless` et `scikit-image`, qui ont tous des roues Windows pour Python 3.11.

## 2. Interface Python du moteur biométrique (`app.biometrie`)

```python
class MoteurBiometrique:
    def __init__(self, dossier_modeles: Path, extracteur_oreille: str = "lbp") -> None
        # charge les modèles une seule fois ; lève FileNotFoundError avec un message
        # français clair si les .onnx sont absents (« lancez python scripts/telecharger_modeles.py »)
    def nouvelle_session(self, mode: Literal["enrolement", "authentification"],
                         nb_visage: int, nb_oreille: int,
                         cote_attendu: Literal["droite", "gauche"] | None = None,
                         apercu: bool = False) -> "SessionCapture"

class SessionCapture:
    id: str                                   # uuid4 hex
    def traiter_image(self, image_jpeg: bytes) -> "RetourImage"   # synchrone, thread-safe par session
    terminee: bool                            # toutes les captures + vivacité OK
    echouee: bool                             # échec définitif (identité incohérente, délai…)
    def resultat(self) -> "ResultatCapture"   # uniquement si terminee
    def effacer(self) -> None                 # met à zéro tous les tableaux en mémoire

@dataclass
class Critere:   code: str; ok: bool; message: str      # message français actionnable

@dataclass
class RetourImage:
    etape: Literal["visage", "rotation", "oreille", "terminee", "echec"]
    captures_visage: int;  captures_visage_requises: int
    captures_oreille: int; captures_oreille_requises: int
    image_retenue: bool
    message: str                              # consigne principale à afficher / lire à voix haute
    criteres: list[Critere]
    lacet: float | None                       # degrés, valeur absolue
    cadre_visage: list[float] | None          # [x1, y1, x2, y2] normalisés 0–1, image NON miroir
    cadre_oreille: list[float] | None         # idem, zone de l'oreille analysée
    apercu_oreille: str | None                # JPEG base64 de la vignette (si apercu=True), jamais stocké
    raison_echec: str | None
    def to_dict(self) -> dict                 # sérialisable JSON tel quel

@dataclass
class PreuveVivacite: ok: bool; details: dict  # amplitude, nb_intermediaires, inversions, duree_s

@dataclass
class ResultatCapture:
    vecteur_visage: np.ndarray                # 512, float32, L2-normalisé (moyenne des captures)
    vecteur_oreille: np.ndarray               # dimension ≥ 256, float32, L2-normalisé
    extracteur_visage: str                    # "arcface-w600k-r50"
    extracteur_oreille: str                   # "lbp-v1"
    cote_oreille: Literal["droite", "gauche"]
    vivacite: PreuveVivacite

# protection.py
def generer_jeton() -> bytes                                   # 32 octets aléatoires (secrets)
def biohash(vecteur: np.ndarray, jeton: bytes, modalite: str, nb_bits: int = 256) -> bytes  # 32 octets
def similarite_hamming(a: bytes, b: bytes) -> float            # 1 - distance_hamming / nb_bits
class ErreurIntegrite(Exception)
class Chiffreur:
    def __init__(self, cle_maitresse: bytes)                   # 32 octets, sinon ValueError
    def chiffrer(self, donnees: bytes, aad: bytes) -> bytes    # nonce(12) || chiffré || tag
    def dechiffrer(self, blob: bytes, aad: bytes) -> bytes     # ErreurIntegrite si altéré

# decision.py
@dataclass
class ParametresDecision:
    version: int = 1
    poids_visage: float = 0.6; poids_oreille: float = 0.4
    plancher_visage: float; plancher_oreille: float; seuil_fusion: float   # valeurs par défaut documentées
    moyenne_imposteur_visage: float; ecart_type_imposteur_visage: float  # paramètres z-score figés
    moyenne_imposteur_oreille: float; ecart_type_imposteur_oreille: float
@dataclass
class Decision:
    accepte: bool
    score_visage: float; score_oreille: float
    z_visage: float; z_oreille: float; score_fusion: float
    regles: list[dict]      # [{"code": "R1", "libelle": "Vivacité", "ok": bool, "valeur": float|None, "seuil": float|None}, …R4]
    raison: str | None      # message français de la première règle en échec
    def to_dict(self) -> dict
def decider(score_visage: float, score_oreille: float, vivacite_ok: bool,
            params: ParametresDecision) -> Decision   # évalue TOUTES les règles R1–R4
```

Règles : **R1** vivacité, **R2** score visage ≥ plancher, **R3** score oreille ≥ plancher,
**R4** fusion `w_v·z_v + w_o·z_o ≥ seuil` avec `z = (score − moyenne_imposteur) / écart_type_imposteur`.
Accès accordé seulement si les quatre passent.

## 3. API HTTP (préfixe `/api`, JSON, messages en français)

Erreurs : `{"detail": {"code": "CODE_MACHINE", "message": "Phrase française actionnable", "champs": {…}?}}`
(les 422 de validation sont convertis à ce format, `champs` = message par champ).
Authentification : en-tête `Authorization: Bearer <jeton>`. Deux types de jetons JWT :
`compte` (60 min, gestion de son espace) et `acces` (10 min, **seul** accepté par `/api/dossiers`).

| Méthode | Route | Jeton | Corps | Réponse |
|---|---|---|---|---|
| GET | `/sante` | — | — | `{statut, modeles_charges, version}` |
| POST | `/comptes` | — | `{nom, email, mot_de_passe}` | 201 `Utilisateur` · 409 `EMAIL_DEJA_UTILISE` |
| POST | `/session` | — | `{email, mot_de_passe}` | `{jeton_compte, expire_dans, utilisateur: Utilisateur}` · 401 `IDENTIFIANTS_INVALIDES` |
| DELETE | `/session` | compte | — | 204 |
| GET | `/moi` | compte | — | `Utilisateur` |
| GET | `/consentement/texte` | — | — | `{version, titre, paragraphes: [str], responsable}` |
| POST | `/consentement` | compte | `{accepte: bool, version}` | `Utilisateur` |
| DELETE | `/consentement` | compte | — | `Utilisateur` (gabarits détruits) |
| POST | `/enrolement/sessions` | compte | — | 201 `SessionInfo` · 403 `CONSENTEMENT_REQUIS` · 409 `DEJA_ENROLE` |
| POST | `/enrolement/sessions/{id}/images` | compte | octets `image/jpeg` | `RetourImage` (+ `utilisateur` quand `etape="terminee"`) |
| DELETE | `/enrolement/sessions/{id}` | compte | — | 204 |
| POST | `/authentification/sessions` | — | `{email}` | 201 `SessionInfo` · 404 `COMPTE_NON_ENROLE` · 423 `COMPTE_VERROUILLE` (+ `verrouille_jusqua`) |
| POST | `/authentification/sessions/{id}/images` | — | octets `image/jpeg` | `RetourImage` (+ `decision`, et si accepté `jeton_acces`, `expire_dans` quand `etape="terminee"`) |
| DELETE | `/authentification/sessions/{id}` | — | — | 204 |
| GET | `/dossiers` | **acces** | — | `{dossiers: [DossierResume], expire_dans}` · 401 `JETON_EXPIRE`/`JETON_INVALIDE` · 403 `JETON_ACCES_REQUIS` |
| GET | `/dossiers/{id}` | **acces** | — | `Dossier` |
| GET | `/moi/tentatives` | compte | — | `{tentatives: [Tentative]}` (20 dernières) |
| POST | `/moi/revocation` | compte | `{mot_de_passe}` | `Utilisateur` (gabarits + jeton BioHashing détruits) |
| DELETE | `/moi` | compte | `{mot_de_passe, confirmation: "SUPPRIMER"}` | 204 |

Schémas :
- `Utilisateur` = `{id, nom, email, role, consentement: {etat, version, date}, enrolement: {etat, date, extracteur_oreille, cote_oreille}, verrouille_jusqua, echecs_consecutifs}` — états : `ABSENT|ACCORDE|RETIRE`, `NON_ENROLE|ENROLE|REVOQUE`. Dates ISO 8601 UTC.
- `SessionInfo` = `{session_id, etape: "visage", captures_visage_requises, captures_oreille_requises, cote_attendu, expire_dans}`
- `RetourImage` = `RetourImage.to_dict()` ci-dessus.
- `decision` = `Decision.to_dict()` ; en production (`BIOACCESS_AFFICHER_SCORES=false`) les champs numériques sont remplacés par `null`, les verdicts des règles et la raison restent (point 27 c).
- `DossierResume` = `{id, nom, age, groupe_sanguin, medecin}` ; `Dossier` = résumé + `{antecedents, traitement, allergies, derniere_consultation}` — **données fictives**.
- `Tentative` = `{horodatage, decision, raison, score_visage, score_oreille, score_fusion, regles}`.

Règles de l'API :
- Images : `Content-Type: image/jpeg`, 2 Mo maximum (413 `IMAGE_TROP_GRANDE`), une seule image traitée à la fois par session (409 `IMAGE_EN_COURS`), session expirée après 120 s d'inactivité (404 `SESSION_INTROUVABLE`).
- Enrôlement : 5 captures visage + 5 captures oreille ; authentification : 3 + 3, côté attendu = celui de l'enrôlement.
- Verrouillage : 5 échecs consécutifs (décision refusée ou échec de vivacité) → 15 min ; un succès remet le compteur à zéro.
- Un seul jeton `acces` valide par utilisateur (le dernier émis) ; révocation et suppression invalident tout.
- Chaque tentative d'authentification et chaque accès à `/dossiers` sont journalisés (sans image ni vecteur).
- Le jeton BioHashing est stocké chiffré en base (point 19 a). AAD AES-GCM = `"{utilisateur_id}|{modalite}"`.
- En production, le backend sert le frontend compilé (`frontend/dist`) sur `/` ; en développement, Vite (port 5173) relaie `/api` vers `http://localhost:8000`.
