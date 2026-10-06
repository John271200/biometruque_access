# BioAccess — plateforme d'accès multibiométrique visage + oreille

Mémoire de Master Génie Logiciel (IFRI, Bénin) : sécuriser l'accès à une base de données
par fusion biométrique **visage + oreille**. On s'inscrit, on s'enrôle avec sa webcam
(5 captures du visage, puis on tourne la tête vers la gauche pour présenter l'oreille
droite, 5 captures), puis on s'authentifie de la même façon pour ouvrir une base de
dossiers patients **fictifs** pendant 10 minutes.

> **Statut : MVP fonctionnel** (branche `mvp/plateforme`). Il a été construit avant la
> validation des cas d'utilisation, par choix assumé (voir [`SUIVI.md`](SUIVI.md)). Les
> cas d'utilisation et les décisions à prendre sont dans la pull request de l'étape 1.

## Ce que fait le MVP

| Fonction | Détail |
|---|---|
| Compte | Inscription (Argon2id), connexion, consentement explicite au traitement biométrique |
| Enrôlement guidé | Retour qualité en temps réel (un seul visage, centré, net, bien éclairé, de face), **consignes vocales en français + bip**, car en profil on ne voit plus l'écran |
| Vivacité | Le passage face → profil doit être un mouvement continu : une photo fixe reste bloquée à l'étape « rotation » |
| Gabarits | ArcFace 512-D (visage) + LBP multi-échelles (oreille) → **BioHashing 256 bits** → **AES-256-GCM**. Aucune image ni aucun vecteur en clair n'est conservé |
| Décision | Scores visage et oreille, normalisation z-score, fusion pondérée, **garde-fou par modalité** ; règles R1 vivacité, R2 visage, R3 oreille, R4 fusion, avec le détail affiché |
| Accès | Jeton de 10 minutes, seul accepté par la base protégée ; chaque accès est journalisé |
| Sécurité | Verrouillage 15 min après 5 échecs, révocation (destruction du gabarit et du jeton), suppression complète du compte |

Pas encore fait : espace d'administration, laboratoire d'attaques, rapport CSV/PDF,
protocole d'évaluation, extracteur d'oreille ONNX, Docker Compose.

## Installation sous Windows (pas à pas)

**Prérequis, à installer une seule fois** : [Python 3.11](https://www.python.org/downloads/)
(cocher « Add python.exe to PATH »), [Node.js 22 LTS](https://nodejs.org/),
[Git](https://git-scm.com/), une webcam, environ 1 Go d'espace disque. Aucun GPU ni
compilateur C++ n'est nécessaire.

### Méthode simple (recommandée)

1. Ouvrir **PowerShell** et récupérer le projet dans un dossier du disque F: (Git demande
   de se connecter à GitHub la première fois, car le dépôt est privé) :
   ```powershell
   git clone -b mvp/plateforme https://github.com/John271200/biometruque_access.git F:\biometruque_access
   ```
2. Dans l'Explorateur, ouvrir `F:\biometruque_access` et **double-cliquer sur `demarrer.bat`**.

Le script vérifie Python et Node.js, crée l'environnement Python, installe les
dépendances, télécharge les modèles (≈ 280 Mo), construit l'interface, lance le serveur
et **ouvre le navigateur tout seul**. La première fois, comptez 5 à 10 minutes ; ensuite,
quelques secondes. Pour arrêter, fermez la fenêtre noire. Pour mettre à jour le projet :
`git pull` dans `F:\biometruque_access`, puis double-clic sur `demarrer.bat`.

### Méthode manuelle (équivalente)

```powershell
cd F:\biometruque_access\backend
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\telecharger_modeles.py
cd ..\frontend
npm install
npm run build
cd ..\backend
.venv\Scripts\python -m uvicorn app.main:app
```

Avec la méthode manuelle, ouvrir ensuite **http://localhost:8000** dans Chrome ou Edge ; dans les deux cas, autoriser la caméra.
Au premier lancement, le serveur crée `backend\.env` (clé maîtresse AES et secret JWT
générés automatiquement) et la base SQLite `backend\donnees\bioaccess.db`.

Pour repartir de zéro : arrêter le serveur (Ctrl+C) et supprimer `backend\donnees\`.
Ne supprime pas `backend\.env` tant que des gabarits existent : sans la clé maîtresse,
ils deviennent illisibles.

## Bien réussir son enrôlement

1. **Lumière de face** (pas de fenêtre derrière soi), un seul visage dans le champ.
2. **Dégager l'oreille droite** : cheveux derrière l'oreille, pas d'écouteurs ni de bonnet.
3. Après les 5 captures du visage, **tourner lentement la tête vers la gauche** (environ 2 à
   3 secondes) jusqu'au profil, puis **tenir la position** : un bip retentit à chaque
   capture de l'oreille. Inutile de regarder l'écran, la voix guide.
4. Trop rapide ? Le système demande de revenir de face et de recommencer plus lentement.

## Mode développement

Deux terminaux :

```powershell
# Terminal 1 — API avec rechargement automatique (port 8000)
cd backend ; .venv\Scripts\python -m uvicorn app.main:app --reload
# Terminal 2 — interface avec rechargement à chaud (http://localhost:5173)
cd frontend ; npm run dev
```

Documentation interactive de l'API : http://localhost:8000/api/docs

## Tests

```powershell
cd backend
.venv\Scripts\python -m pytest -q        # 125 tests : moteur biométrique + API
```

## Configuration (`backend\.env`, préfixe `BIOACCESS_`)

| Variable | Défaut | Rôle |
|---|---|---|
| `ENV` | `dev` | En `production`, le serveur refuse de démarrer sans clés explicites |
| `DATABASE_URL` | SQLite local | PostgreSQL : `postgresql+psycopg://user:mdp@hote:5432/bioaccess` |
| `CLE_MAITRESSE` | générée en dev | Clé AES-256 (base64, 32 octets) ; en production : coffre de secrets |
| `SECRET_JWT` | généré en dev | Signature des jetons |
| `AFFICHER_SCORES` | `true` en dev | Affiche les scores chiffrés ; en production seuls les verdicts des règles sont montrés |
| `APERCU_OREILLE` | `true` en dev | Renvoie la vignette de l'oreille analysée (jamais stockée) |

## Limites connues (à traiter avant la soutenance)

- **Seuils provisoires.** Le plancher visage (0,64) est solide : sur des photos réelles,
  des personnes différentes obtiennent 0,47 à 0,57, même avec le jeton de la victime. Les
  paramètres de l'**oreille** (LBP) ne sont pas calibrés sur de vraies captures de profil,
  et des oreilles différentes se ressemblent déjà beaucoup (≈ 0,75) : à recalibrer avec tes
  propres captures (protocole d'évaluation).
- **Localisation de l'oreille** : heuristique dérivée des landmarks 3D, à vérifier avec ta
  webcam (le cadre bleu et la vignette montrent la zone analysée).
- **Révocation avec le seul mot de passe** : un voleur de mot de passe pourrait révoquer
  puis enrôler son propre visage (points N-3.14 et N-4.1 à trancher).
- **Vivacité** : une vidéo rejouée de la personne qui tourne la tête, ou une photo
  pivotée à la main, ne sont pas spécifiquement détectées (point 16).
- Les modèles InsightFace sont réservés à un usage de recherche non commercial.

## Stack

FastAPI (Python 3.11), SQLAlchemy 2, SQLite / PostgreSQL 16 · InsightFace buffalo_l en
**onnxruntime pur** (SCRFD, landmarks 3D, ArcFace — sans le paquet `insightface`, qui exige
un compilateur C++ sous Windows), OpenCV, scikit-image · Vue 3 + Vite + TypeScript + Pinia ·
cryptography (AES-256-GCM), argon2, JWT.

Contrat technique entre les briques : [`docs/mvp/CONTRAT-MVP.md`](docs/mvp/CONTRAT-MVP.md).
