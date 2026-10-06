# BioAccess — Cas d'utilisation (étape 1)

> Statut : **BROUILLON v1 — en attente de validation explicite**. Rien n'est figé : toute
> valeur marquée « proposition » renvoie à un point de [`08-points-a-trancher.md`](08-points-a-trancher.md).

## Comment lire ce dossier

Chaque cas d'utilisation suit le même gabarit : *user story* (« En tant que… je veux… afin
de… »), acteur principal, préconditions, déclencheur, scénario nominal numéroté, scénarios
alternatifs (`A-xx.n`) et d'erreur (`E-xx.n`), règles métier (`RM-xx.n`), postcondition.
Les cas sont numérotés **dans l'ordre réel d'usage** de la plateforme : c'est aussi l'ordre
dans lequel les endpoints seront développés à l'étape 4.

| Fichier | Contenu |
|---|---|
| [`01-perimetre-acteurs.md`](01-perimetre-acteurs.md) | Acteurs, états d'un compte, deux niveaux d'accès |
| [`02-inscription-enrolement.md`](02-inscription-enrolement.md) | UC-01 à UC-06 |
| [`03-authentification-acces.md`](03-authentification-acces.md) | UC-07 à UC-10 |
| [`04-maitrise-des-donnees.md`](04-maitrise-des-donnees.md) | UC-11 et UC-12 |
| [`05-administration.md`](05-administration.md) | UC-13 à UC-18 |
| [`06-laboratoire-evaluation.md`](06-laboratoire-evaluation.md) | UC-19 à UC-21 |
| [`07-regles-transversales.md`](07-regles-transversales.md) | Règles transversales (RT) et hors périmètre v1 |
| [`08-points-a-trancher.md`](08-points-a-trancher.md) | **Toutes les décisions qui t'appartiennent** |

## Liste des cas d'utilisation

| N° | Cas d'utilisation | Acteur principal | Brief § |
|---|---|---|---|
| UC-01 | Créer un compte | Visiteur | 1 |
| UC-02 | Donner ou refuser son consentement biométrique | Titulaire de compte | 1 |
| UC-03 | S'enrôler — étape visage (5 captures guidées) | Titulaire consentant | 2 |
| UC-04 | S'enrôler — étape oreille droite par rotation de la tête | Titulaire consentant | 2 |
| UC-05 | Finaliser l'enrôlement : extraction, BioHashing, chiffrement, destruction | Système (pour le titulaire) | 3 |
| UC-06 | Consulter l'état de son enrôlement et ses données | Titulaire de compte | 1, 3 |
| UC-07 | Se connecter à son espace compte (email + mot de passe) | Titulaire de compte | 1 |
| UC-08 | S'authentifier biométriquement (fusion + garde-fou + vivacité) | Utilisateur enrôlé | 4 |
| UC-09 | Être verrouillé temporairement après 5 échecs | Utilisateur enrôlé | 4 |
| UC-10 | Consulter la base protégée avec le jeton biométrique | Utilisateur enrôlé | 5 |
| UC-11 | Révoquer ses gabarits et se ré-enrôler | Utilisateur enrôlé | 3 |
| UC-12 | Supprimer son compte (droit à l'effacement) | Titulaire de compte | 1, 6 |
| UC-13 | Lister les utilisateurs et leur statut | Administrateur | 6 |
| UC-14 | Révoquer ou supprimer un utilisateur | Administrateur | 6 |
| UC-15 | Consulter le journal des tentatives | Administrateur | 6 |
| UC-16 | Régler les paramètres de décision (FAR cible, planchers, poids) | Administrateur | 6 |
| UC-17 | Consulter le tableau de bord de performance | Administrateur | 6 |
| UC-18 | Choisir l'extracteur d'oreille actif | Administrateur | 3 |
| UC-19 | Mener une tentative étiquetée en laboratoire d'attaques | Évaluateur | 7 |
| UC-20 | Exporter le rapport d'attaques (CSV, PDF) | Évaluateur | 7 |
| UC-21 | Exécuter le protocole d'évaluation | Évaluateur | 8 |

*Brief § = section du cahier des charges initial dont le cas d'utilisation découle.*
