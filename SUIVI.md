# Suivi de projet — BioAccess

Cocher au fur et à mesure des validations. Une case cochée = un artefact réellement produit **et validé explicitement**, pas seulement commencé.

- [ ] **1. Cas d'utilisation** — liste complète, validée explicitement *(en relecture)*
- [ ] **2. Diagrammes UML** — cas d'utilisation, séquence d'enrôlement, séquence d'authentification, modèle de données (Mermaid), validés
- [ ] **3. Contrat d'API** — OpenAPI complet, posé avant le premier endpoint
- [ ] **4. Backend** — endpoints développés un par un, chacun avec tests pytest et documentation
- [ ] **5. Validation complète du backend** — tous les tests verts + scénario de bout en bout
- [ ] **6. Frontend** — design system, composants et pages validés sur mocks du contrat
- [ ] **7. Intégration** — backend et frontend réels connectés, écarts corrigés
- [ ] **8. Déploiement** — Docker Compose (api, frontend, postgres), vérifié en conditions réelles

## Règle de gouvernance

Aucune décision sur les règles métier, le modèle de données ou l'architecture n'est prise
sans validation de l'auteur : toute valeur non décidée est marquée « proposition » et
renvoie à un point de [`docs/cas-utilisation/08-points-a-trancher.md`](docs/cas-utilisation/08-points-a-trancher.md).

## Notes / écarts assumés

(Consigner ici toute étape sautée délibérément, avec la raison et le risque accepté.)
