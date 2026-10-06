# 1. Périmètre et acteurs

> Statut : **BROUILLON v1 — en attente de validation**. Les valeurs marquées « proposition » ne sont pas décidées : elles renvoient à un point de `08-points-a-trancher.md`.

## 1.1 Acteurs principaux (humains)

| Acteur | Définition | Comment il est reconnu |
|---|---|---|
| **Visiteur** | Personne non encore inscrite | Aucune identification |
| **Titulaire de compte** | Compte créé, enrôlement non terminé ou révoqué | Email + mot de passe (session « compte », UC-07) |
| **Utilisateur enrôlé** | Compte avec gabarits visage + oreille actifs | Email (+ mot de passe selon point 3), puis capture biométrique (UC-08) |
| **Administrateur** | Gère les utilisateurs et les seuils, consulte les journaux et le tableau de bord | Email + mot de passe + rôle `admin` |
| **Évaluateur** | Le chercheur (toi en soutenance) : mène les tentatives étiquetées du laboratoire d'attaques et le protocole d'évaluation | Rôle `evaluateur` — rôle distinct ou fusionné avec `admin` : **point 31** |

## 1.2 Acteurs secondaires (systèmes)

| Acteur | Rôle |
|---|---|
| **Navigateur / webcam** | Capture `getUserMedia`, envoi des images au serveur, affichage du retour qualité en temps réel |
| **Moteur biométrique** | InsightFace buffalo_l (SCRFD détection, ArcFace plongement 512-D, estimation de pose), OpenCV / scikit-image pour la qualité et le LBP |
| **Extracteur d'oreille** | Implémentation interchangeable : (a) LBP multi-échelles par blocs (référence), (b) plongement ONNX d'un modèle de vision généraliste (ex. DINOv2 small) |
| **Protecteur de gabarits** | BioHashing (projection sur base orthonormée issue d'un jeton personnel, binarisation 256 bits), puis chiffrement AES-256-GCM |
| **Magasin de données** | PostgreSQL 16 : comptes, consentements, gabarits chiffrés, journaux, paramètres de décision |
| **Journal d'audit** | Enregistrement en ajout seul : qui, quand, scores, décision, règle déterminante |

## 1.3 États d'un compte (vocabulaire utilisé dans les cas d'utilisation)

| Axe | Valeurs |
|---|---|
| Compte | `CREE`, `EN_ATTENTE_VERIFICATION` (si point 1 = oui), `ACTIF`, `VERROUILLE_TEMPORAIREMENT`, `SUPPRIME` |
| Consentement | `ABSENT`, `ACCORDE`, `RETIRE` |
| Enrôlement | `NON_ENROLE`, `ENROLE`, `REVOQUE` |

> Ces états sont une **proposition de vocabulaire** pour rendre les cas d'utilisation précis. Ils seront formalisés (ou modifiés) à l'étape 2, modèle de données.

## 1.4 Deux niveaux d'accès (proposition — point 3)

1. **Session « compte »** (email + mot de passe) : permet uniquement de gérer son profil, son consentement, son enrôlement, sa révocation et sa suppression. **Elle ne donne jamais accès à la base protégée.**
2. **Jeton d'accès biométrique** (JWT 10 min, délivré par UC-08) : seul moyen d'accéder à la base protégée (UC-10).
