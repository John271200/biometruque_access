# BioAccess — plateforme d'accès multibiométrique visage + oreille

Mémoire de Master Génie Logiciel (IFRI, Bénin) : sécuriser l'accès à une base de données
par fusion biométrique **visage + oreille** — enrôlement guidé par webcam, gabarits protégés
(BioHashing + AES-256-GCM), authentification par fusion de scores avec garde-fou par
modalité et contrôle de vivacité, base protégée accessible uniquement par jeton biométrique.

## État du projet

Le projet suit une méthode « spec-first » en étapes verrouillées : aucune étape ne démarre
avant la validation explicite de la précédente. Avancement : [`SUIVI.md`](SUIVI.md).

| Étape | Livrable | Statut |
|---|---|---|
| 1 | Cas d'utilisation + points à trancher | **En relecture** — [`docs/cas-utilisation/`](docs/cas-utilisation/00-index.md) |
| 2 | Diagrammes UML (Mermaid) | Non démarré |
| 3 | Contrat d'API OpenAPI | Non démarré |
| 4–5 | Backend FastAPI + tests pytest | Non démarré |
| 6–7 | Frontend Vue 3 + intégration | Non démarré |
| 8 | Docker Compose et déploiement | Non démarré |

## Stack prévue

- **Backend** : FastAPI (Python 3.11), SQLAlchemy, Alembic, PostgreSQL 16
- **Biométrie** : InsightFace buffalo_l (SCRFD + ArcFace, onnxruntime CPU), OpenCV, scikit-image
- **Frontend** : Vue 3 + Vite + TypeScript, Pinia
- **Sécurité** : cryptography (AES-256-GCM), argon2, JWT courte durée
- Tout fonctionne sur CPU, sans GPU.

Les instructions d'installation pas à pas seront ajoutées avec le premier code (étape 4).
