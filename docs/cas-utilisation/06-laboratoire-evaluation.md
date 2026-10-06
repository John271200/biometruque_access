# 6. Laboratoire d'attaques et protocole d'évaluation (UC-19 à UC-21)

> Statut : **BROUILLON v1 — en attente de validation**.

---

## UC-19 — Mener une tentative étiquetée en laboratoire d'attaques

> **En tant qu'**évaluateur, **je veux** lancer en mode laboratoire une tentative d'authentification contre un compte enrôlé, en déclarant avant la capture s'il s'agit d'une présentation légitime, d'un imposteur ou d'une attaque, **afin de** mesurer, tentative par tentative, quelle règle de décision arrête quel type d'attaque.

- **Acteur principal** : Évaluateur
- **Préconditions** : session « compte » active avec le rôle `evaluateur` (ou `admin` selon le **point 31**) ; mode laboratoire activé, c'est-à-dire une campagne ouverte (RM-19.2) ; au moins un compte cible `ENROLE` et éligible (RM-19.9) ; webcam autorisée ; contexte sécurisé (HTTPS ou `localhost`).
- **Déclencheur** : clic sur « Nouvelle tentative » dans l'écran « Laboratoire d'attaques ».

**Scénario nominal**
1. L'évaluateur ouvre l'écran « Laboratoire d'attaques » et sélectionne une campagne ouverte, ou en crée une (**point N-6.1**). Un bandeau permanent s'affiche : « Mode laboratoire — aucune tentative n'ouvre l'accès à la base protégée ».
2. L'évaluateur choisit le compte cible, c'est-à-dire l'identité revendiquée, parmi les comptes enrôlés éligibles (RM-19.9).
3. L'évaluateur choisit l'étiquette, catégorie et type (RM-19.4), et peut décrire brièvement l'instrument d'attaque (« photo A4 couleur, imprimante laser »).
4. L'évaluateur confirme. Le système fige le contexte de la tentative : campagne, compte cible, étiquette, version active des paramètres de décision, extracteur d'oreille actif (RM-19.3, RM-19.7). Ce contexte n'est plus modifiable pendant la tentative.
5. La personne testée, ou l'instrument d'attaque, se présente devant la webcam. La capture guidée face → profil se déroule exactement comme en UC-08 : mêmes contrôles qualité, même contrôle de vivacité (RM-19.1).
6. Le serveur calcule le score visage et le score oreille, les normalise (z-score), calcule le score fusionné (somme pondérée), puis évalue R1 (vivacité), R2 (plancher visage), R3 (plancher oreille) et R4 (seuil de fusion) avec la version figée des paramètres (RM-19.12).
7. Le système affiche le résultat complet : scores bruts et normalisés, verdict de chaque règle (valeur mesurée, seuil, réussie ou échouée), décision (« Acceptée » ou « Refusée »), raison du refus, temps de traitement serveur (RM-19.6).
8. Aucun jeton d'accès n'est délivré et l'état du compte cible n'est pas modifié (RM-19.8).
9. Le système journalise la tentative avec le drapeau `laboratoire` (RM-19.10).
10. Le système efface de la mémoire images, vecteurs et BioHash de la tentative (RM-19.11).
11. Le système propose « Nouvelle tentative » : campagne et compte cible sont conservés ; l'étiquette précédente est pré-remplie mais doit être confirmée de nouveau (**point N-6.3**).

**Scénarios alternatifs et d'erreur**
- **E-19.1 Rôle non autorisé** → refus (HTTP 403), « Le laboratoire d'attaques est réservé au rôle évaluateur. » Le refus est journalisé.
- **E-19.2 Mode laboratoire non activé** (aucune campagne ouverte) → le bouton « Nouvelle tentative » est indisponible ; une requête directe est refusée : « Ouvrez ou sélectionnez une campagne de laboratoire avant de lancer une tentative. »
- **E-19.3 Étiquette manquante ou incohérente** → la capture ne démarre pas : « Choisissez une catégorie et un type avant de lancer la tentative. » ou « Le type “photo imprimée” n'est possible qu'avec la catégorie “attaque”. »
- **E-19.4 Compte cible sans gabarit actif** (`NON_ENROLE`, `REVOQUE`, `SUPPRIME`, consentement retiré) → « Ce compte n'a pas de gabarit actif : choisissez un compte enrôlé. »
- **E-19.5 Compte cible non éligible** (participation au laboratoire non acceptée, **point N-6.4**) → « Le titulaire de ce compte n'a pas accepté d'être ciblé par le laboratoire. »
- **E-19.6 Tentative sans décision** → **point N-6.5** — proposition : une interruption due à l'évaluateur ou à une panne (annulation, onglet fermé, flux coupé, erreur serveur) est journalisée avec le statut `INCOMPLETE` et sa cause, exclue des taux et comptée à part dans le rapport ; un échec dû à la présentation elle-même (aucun visage détecté, plusieurs visages, oreille introuvable, délai de vivacité dépassé) est traité exactement comme en UC-08 et compte comme un refus (« rejet avant décision »).
- **A-19.1 Compte cible verrouillé** (`VERROUILLE_TEMPORAIREMENT`, UC-09) → **point N-6.2** — proposition : la tentative reste possible puisqu'elle ne délivre aucun accès ; le verrouillage n'est ni levé ni prolongé.
- **A-19.2 Paramètres de décision modifiés pendant la campagne** (UC-16) → la tentative en cours garde la version figée à l'étape 4 ; à la suivante, le système avertit : « Les paramètres de décision ont changé (version 4 → 5) : les prochaines tentatives utiliseront la version 5. »
- **A-19.3 Deux extracteurs d'oreille en parallèle** (si **point 22** = coexistence) → le score oreille est calculé avec les deux extracteurs ; seul l'extracteur actif participe à la décision, l'autre score est enregistré pour comparaison dans UC-20.
- **A-19.4 Étiquette erronée constatée après coup** → **point N-6.3** — proposition : correction par l'évaluateur avec motif obligatoire, enregistrée comme un nouvel événement du journal ; l'étiquette d'origine reste visible.

**Règles métier**
- RM-19.1 — Pipeline identique à UC-08 : même capture guidée, mêmes contrôles qualité, même vivacité, même normalisation, même fusion, mêmes règles R1 à R4. Aucune règle n'est désactivée, allégée ou contournée en mode laboratoire : un résultat de laboratoire n'a de valeur que s'il est la décision que UC-08 aurait rendue.
- RM-19.2 — Le mode laboratoire est explicite : activé par l'évaluateur, signalé en permanence à l'écran, et chaque tentative est rattachée à une campagne (**point N-6.1** — proposition : campagne nommée avec nom, objectif, dates d'ouverture et de fermeture ; laboratoire entièrement désactivable par configuration dans un déploiement réel).
- RM-19.3 — L'étiquette est choisie **avant** la capture et figée pendant la tentative, pour qu'aucune étiquette ne puisse être choisie au vu du résultat.
- RM-19.4 — Structure de l'étiquette : une **catégorie** parmi `legitime`, `imposteur`, `attaque` (imposée par le brief) et un **type** pris dans une liste fermée (**point 32** — proposition : `aucun` (présentation normale), `photo_imprimee`, `ecran_telephone_photo`, `ecran_telephone_video`, `visage_masque`, `oreille_cachee_cheveux`). « Imposteur réel » = catégorie `imposteur` + type `aucun` ; `photo_imprimee` et `ecran_telephone_*` exigent la catégorie `attaque`. Séparer catégorie et type lève une ambiguïté : une oreille cachée par les cheveux chez le titulaire légitime mesure la robustesse (un refus est alors un faux rejet), alors que chez un imposteur elle mesure une dissimulation.
- RM-19.5 — Seul l'évaluateur étiquette. La personne testée n'a aucune interaction avec le système en dehors de la caméra : elle ne se connecte pas et ne choisit rien. Aucune tentative UC-08 ordinaire ne peut recevoir d'étiquette, ni avant ni après coup : un attaquant ne peut pas faire passer ses propres tentatives pour des tests.
- RM-19.6 — Le résultat complet est toujours affiché en laboratoire, quel que soit le niveau de détail retenu pour la réponse d'échec de UC-08 (**point 27**) : la décision est identique, seul l'affichage diffère.
- RM-19.7 — Chaque tentative enregistre l'identifiant de version des paramètres de décision appliqués (seuils, poids, planchers, paramètres z-score) et l'extracteur d'oreille utilisé pour la décision ; sans eux, les taux de UC-20 ne sont pas interprétables.
- RM-19.8 — Effets sur le compte cible : **point N-6.2** — proposition : aucun JWT délivré même si la décision est « Acceptée », compteur d'échecs de UC-09 non incrémenté, verrouillage ni déclenché ni levé.
- RM-19.9 — Comptes ciblables et participants : **point N-6.4** — proposition : seuls les comptes `ENROLE` dont le titulaire a accepté une clause « laboratoire » distincte sont ciblables ; toute personne qui joue l'imposteur, et toute personne dont la photo sert d'instrument d'attaque, a donné un accord écrit préalable.
- RM-19.10 — Journalisation : chaque tentative est enregistrée avec le drapeau `laboratoire`, la campagne, l'évaluateur, le pseudonyme du compte cible (**point N-6.7**), l'étiquette, les scores, le verdict de chaque règle, la décision, la raison, la version des paramètres, l'extracteur, le temps de traitement et le statut. Même journal ou journal séparé, prise en compte dans le tableau de bord : **point 33** — proposition : même journal d'audit en ajout seul ; tentatives `laboratoire` exclues par défaut du tableau de bord (UC-17, filtre activable) et des compteurs de UC-06 et UC-09 ; le titulaire voit toutefois dans UC-06 le nombre de tentatives de laboratoire ayant ciblé son compte.
- RM-19.11 — Aucune image, aucun vecteur, aucun BioHash de la tentative n'est conservé après la décision, quelle que soit la personne présentée : titulaire, imposteur ou photo d'un tiers. Les tentatives de laboratoire n'alimentent jamais l'espace « recherche » de UC-21.
- RM-19.12 — Le rapport par règle (UC-20) exige que les quatre règles soient évaluées à chaque tentative, même quand l'une a déjà échoué (**point 25** — proposition : évaluation complète de R1 à R4 sans court-circuit, en UC-08 comme en laboratoire, la décision restant la conjonction des quatre). En cas d'échec d'acquisition, les règles sans score sont notées « non évaluable ».

**Hypothèses à vérifier**

Ce tableau n'est pas une règle : il énonce ce que chaque règle est censée arrêter. L'intérêt du rapport (UC-20) est précisément de montrer quelle règle arrête réellement quelle attaque, et lesquelles passent.

| Étiquette | Règle censée arrêter la tentative | Raison |
|---|---|---|
| `attaque` / `photo_imprimee` | R1 ; à défaut R3 | Une feuille, même inclinée, ne produit pas de rotation de tête continue ni de profil ; une photo de face ne montre pas l'oreille |
| `attaque` / `ecran_telephone_photo` | R1 ; à défaut R3 | Idem |
| `attaque` / `ecran_telephone_video` (vidéo de la victime tournant la tête) | R1 seulement si le mouvement demandé n'est pas prévisible (**point 16**, **point 17**) ; sinon R2 à R4 peuvent passer | Rejeu du mouvement d'enrôlement : le cas le plus instructif pour la soutenance |
| `visage_masque` | R2, ou rejet avant décision si le visage n'est plus détecté | Vérifie qu'une oreille seule ne suffit pas |
| `oreille_cachee_cheveux` | R3, ou rejet avant décision si l'oreille est introuvable | Vérifie qu'un visage seul ne suffit pas : raison d'être du garde-fou |
| `imposteur` / `aucun` | R4, souvent aussi R2 et R3 | Biométrie différente |
| `legitime` / `aucun` | Aucune | Un refus est un faux rejet |

**Postcondition** : une tentative étiquetée, rattachée à une campagne et à une version des paramètres, est journalisée avec le drapeau `laboratoire` ; aucun accès n'a été délivré, l'état du compte cible est inchangé et aucune image n'est conservée.

---

## UC-20 — Exporter le rapport d'attaques (CSV, PDF)

> **En tant qu'**évaluateur, **je veux** exporter en CSV et en PDF un rapport des tentatives du laboratoire donnant le taux d'acceptation par type d'attaque et par règle de décision, **afin de** présenter en soutenance des résultats vérifiables sur ce que chaque règle arrête.

- **Acteur principal** : Évaluateur
- **Préconditions** : session « compte » active avec le rôle `evaluateur` (ou `admin` selon le **point 31**) ; au moins une tentative de laboratoire journalisée (UC-19).
- **Déclencheur** : clic sur « Exporter le rapport » dans l'écran « Laboratoire d'attaques ».

**Scénario nominal**
1. Le système affiche les filtres : période, campagne(s), version des paramètres de décision, extracteur d'oreille utilisé pour la décision, catégorie et type d'étiquette. Par défaut : toutes les tentatives de la campagne courante.
2. L'évaluateur choisit les filtres et le ou les formats (CSV, PDF).
3. Le système sélectionne les tentatives de laboratoire correspondantes, avec leur étiquette en vigueur (corrigée le cas échéant, **point N-6.3**).
4. Pour chaque version des paramètres présente dans la sélection et pour chaque étiquette (catégorie × type), le système calcule : nombre de tentatives, nombre d'acceptations, taux d'acceptation avec son intervalle de confiance (RM-20.1, RM-20.2, RM-20.4) ; pour chaque règle R1 à R4, son taux d'échec et son taux de rejet exclusif (RM-20.3) ; le nombre de rejets avant décision.
5. Le système signale chaque effectif trop faible (RM-20.4).
6. Le système génère les fichiers demandés : archive CSV (RM-20.8), PDF (RM-20.9).
7. Le système journalise l'export (RM-20.7) et le navigateur télécharge les fichiers.

**Scénarios alternatifs et d'erreur**
- **E-20.1 Rôle non autorisé** → refus (HTTP 403), « L'export du rapport d'attaques est réservé au rôle évaluateur. »
- **E-20.2 Aucune tentative ne correspond aux filtres** → aucun fichier généré, « Aucune tentative de laboratoire ne correspond à ces filtres. »
- **E-20.3 Échec de génération du PDF** → le CSV reste téléchargeable, « Le PDF n'a pas pu être généré ; l'export CSV est disponible. » L'erreur technique est journalisée.
- **A-20.1 Sélection couvrant plusieurs versions des paramètres** → tableaux produits séparément pour chaque version (RM-20.5), avec l'avertissement « La sélection couvre 2 versions des paramètres de décision : les taux sont présentés séparément pour chaque version. »
- **A-20.2 Effectif insuffisant** → l'export est produit ; chaque ligne concernée est marquée « Effectif insuffisant (n = 6) : taux indicatif, non interprétable statistiquement. »
- **A-20.3 Tentatives incomplètes dans la sélection** → exclues des taux ; leur nombre et leurs causes figurent sur une ligne séparée (**point N-6.5**).
- **A-20.4 Étiquettes corrigées** → les tentatives sont comptées sous l'étiquette corrigée ; le détail CSV montre l'étiquette d'origine, l'étiquette corrigée et le motif (**point N-6.3**).

**Règles métier**
- RM-20.1 — Taux d'acceptation d'une étiquette = tentatives acceptées / tentatives complètes portant cette étiquette, rejets avant décision inclus au dénominateur (imposé par le brief : « taux d'acceptation par type d'attaque et par règle de décision »).
- RM-20.2 — Lecture du taux d'acceptation selon la catégorie :
  - `attaque` : taux de réussite de l'attaque. Au sens de l'ISO/IEC 30107-3, c'est l'IAPAR (taux d'acceptation des présentations d'attaque d'imposteur, mesuré sur le système complet) ; la proportion de ces attaques qui passent R1 est assimilable à l'APCER du sous-système de vivacité pour cette espèce d'instrument d'attaque.
  - `legitime` : 1 − FRR observé en laboratoire ; la proportion de présentations légitimes rejetées par R1 est assimilable au BPCER du sous-système de vivacité.
  - `imposteur` : FAR observé pour des imposteurs présents devant la caméra.
  Le rapport précise que ces mesures reprennent la terminologie de la norme sans constituer une évaluation de conformité.
- RM-20.3 — Taux par règle (**point 34** — proposition) : pour chaque étiquette et chaque règle Rk, le **taux d'échec de Rk** (proportion des tentatives où Rk a échoué, que d'autres règles aient échoué ou non) et le **taux de rejet exclusif de Rk** (proportion où Rk est la seule règle en échec : sans elle, la tentative aurait été acceptée). Le second montre quelle règle est réellement indispensable contre quelle attaque. Les rejets avant décision forment une colonne à part. Ces taux supposent l'évaluation complète des quatre règles (RM-19.12).
- RM-20.4 — Petits effectifs (**point N-6.12** — proposition) : chaque taux est accompagné de son intervalle de confiance à 95 % (méthode de Wilson) ; avertissement sous 10 tentatives ; un taux nul n'est jamais présenté seul : « 0 acceptation sur 20 » s'écrit « 0 % (IC 95 % : 0 à 16 %) ».
- RM-20.5 — Les taux ne sont jamais agrégés entre versions différentes des paramètres de décision, ni entre extracteurs d'oreille différents (**point 34** — proposition) : un taux qui mêle deux jeux de seuils ne décrit aucun système réel.
- RM-20.6 — L'export ne contient que des scores numériques, verdicts, décisions, étiquettes et métadonnées. Jamais d'image, de vecteur, de BioHash, de jeton personnel ni de clé. Les personnes sont désignées par pseudonyme, jamais par nom ni email (**point N-6.7**).
- RM-20.7 — Chaque export est journalisé : évaluateur, horodatage, filtres, formats, nombre de tentatives incluses, empreinte SHA-256 de chaque fichier produit (**point N-6.6**), ce qui permet de prouver en soutenance que le rapport présenté n'a pas été retouché.
- RM-20.8 — Format CSV : **point N-6.6** — proposition : archive ZIP contenant `tentatives.csv` (une ligne par tentative : identifiant, horodatage, campagne, pseudonymes, catégorie, type, étiquette d'origine si corrigée, scores bruts et normalisés, score fusionné, verdict R1 à R4, décision, raison, version des paramètres, extracteur, temps de traitement, statut), `synthese.csv` (exactement les chiffres des tableaux du PDF) et `contexte.txt` (filtres, versions, date de génération). Aucune copie conservée sur le serveur.
- RM-20.9 — Contenu du PDF : **point 34** — proposition, dans cet ordre : (1) contexte : objet, campagnes, période, évaluateur, date de génération ; (2) paramètres appliqués : version, seuils, poids, planchers, paramètres z-score, critères de vivacité, extracteur d'oreille ; (3) description des instruments d'attaque ; (4) tableau des taux d'acceptation par étiquette avec intervalles de confiance ; (5) matrice étiquette × règle (taux d'échec et de rejet exclusif) ; (6) graphiques : taux d'acceptation par étiquette avec intervalles, distribution des scores fusionnés par catégorie avec le seuil R4 ; (7) temps de traitement (médiane et 95e centile) comparé à l'objectif de 2 s sur CPU ; (8) limites : effectifs, un seul évaluateur, conditions de laboratoire, absence d'évaluation de conformité ISO/IEC 30107-3.
- RM-20.10 — Seules les tentatives étiquetées du laboratoire alimentent le rapport ; les authentifications réelles (UC-08) n'y figurent jamais, puisqu'elles ne portent pas d'étiquette (RM-19.5).

**Postcondition** : fichiers CSV et/ou PDF téléchargés, export journalisé avec les empreintes des fichiers ; aucune donnée du journal n'est modifiée.

---

## UC-21 — Exécuter le protocole d'évaluation

> **En tant qu'**évaluateur, **je veux** exécuter un script qui calcule EER, FAR, FRR et courbes DET pour le visage seul, l'oreille seule avec chacun des deux extracteurs, la fusion et la fusion avec garde-fou, à partir des captures de 10 à 15 volontaires consentants, **afin de** mesurer objectivement l'apport de la fusion et du garde-fou, et de choisir l'extracteur d'oreille sur nos propres captures.

- **Acteur principal** : Évaluateur (exécution en ligne de commande, hors interface web — **point N-6.8**)
- **Préconditions** : accès à la machine qui héberge l'espace « recherche » et à sa clé de déchiffrement (**point 21**) ; captures de 10 à 15 volontaires ayant accordé le consentement « recherche » (UC-02 A-02.4), collectées selon le protocole de collecte (RM-21.4) ; modèles disponibles aux versions déclarées (ArcFace, LBP, modèle ONNX) ; fichier de configuration de l'exécution (source des données, graine aléatoire, configurations, scénarios, répertoire de sortie).
- **Déclencheur** : l'évaluateur lance le script avec ce fichier de configuration.

**Scénario nominal**
1. Le script lit la configuration et vérifie la présence de la graine, des versions et empreintes des modèles, et de la version de référence des paramètres de décision (RM-21.10).
2. Le script liste les volontaires de l'espace « recherche » et vérifie pour chacun que le consentement « recherche » est `ACCORDE` et que la date de destruction n'est pas dépassée (E-21.1, E-21.6).
3. Le script déchiffre les captures en mémoire et vérifie leur intégrité (E-21.3).
4. Le script vérifie l'effectif : au moins 10 volontaires exploitables, chacun avec au moins 2 sessions (E-21.2).
5. Le script répartit les volontaires en plis de calibration et de test à partir de la graine (RM-21.7).
6. Pour chaque capture, le script calcule le plongement ArcFace, le descripteur LBP et le plongement ONNX ; les échecs d'acquisition sont comptés (E-21.4).
7. Le script construit les gabarits de référence et les comparaisons légitimes et imposteurs (RM-21.5).
8. Le script calcule les scores de chaque configuration (RM-21.1) dans chaque scénario de protection (RM-21.6).
9. Sur les plis de calibration, le script estime paramètres z-score, poids et seuils ; sur les plis de test, il calcule FAR et FRR au point de fonctionnement, EER et courbes DET, avec leurs intervalles de confiance (RM-21.7 à RM-21.9).
10. Le script mesure sur CPU le temps d'extraction et de décision de chaque configuration, au regard de la contrainte d'authentification en moins de 2 s.
11. Le script écrit les sorties : tableau récapitulatif CSV, figures DET, manifeste de reproductibilité, recommandation d'extracteur d'oreille (RM-21.11, RM-21.12).
12. Le script efface de la mémoire et du disque toutes les images et tous les vecteurs déchiffrés, puis journalise l'exécution (évaluateur, horodatage, graine, versions, effectif, empreintes des sorties), sans aucune donnée biométrique.

**Scénarios alternatifs et d'erreur**
- **E-21.1 Volontaire sans consentement « recherche »** (absent ou retiré) → volontaire exclu et listé dans le manifeste : « Volontaire V04 exclu : consentement recherche absent ou retiré. » Si des données subsistent malgré un retrait, le script ne les lit pas et signale l'anomalie : « Données de recherche présentes malgré le retrait du consentement (V04) : destruction requise. »
- **E-21.2 Données insuffisantes** → un volontaire n'ayant qu'une session est exclu des comparaisons légitimes ; s'il reste moins de 10 volontaires exploitables, arrêt (**point N-6.9** — proposition) : « Données insuffisantes : 8 volontaires exploitables, 10 requis par le protocole. »
- **E-21.3 Capture corrompue** (échec de déchiffrement, d'intégrité ou de lecture) → capture exclue, comptée et listée, jamais ignorée en silence : « Capture V07-S2-03 illisible (échec du contrôle d'intégrité) : exclue. » Un volontaire qui perd ainsi une session entière relève de E-21.2.
- **E-21.4 Échec d'acquisition** (aucun visage détecté, oreille introuvable, qualité insuffisante) → la capture n'est pas retirée en silence : elle est comptée dans le taux d'échec d'acquisition (FTA) et, pour une comparaison légitime, comme un faux rejet au niveau système (**point N-6.8**).
- **E-21.5 Modèle absent ou différent de la version déclarée** → arrêt : « Le modèle d'oreille ONNX déclaré est introuvable ou son empreinte diffère : exécution arrêtée. »
- **E-21.6 Date de destruction dépassée** → données non lues, anomalie signalée : « Données de V02 au-delà de leur date de destruction : destruction requise. »
- **E-21.7 Graine absente** → arrêt : « Graine aléatoire manquante : exécution non reproductible, arrêt. »
- **A-21.1 Exécution sur les bases publiques ORL + IIT Delhi** (**point 36**) → mêmes calculs sur des utilisateurs « chimériques » (association, fixée par la graine, d'un sujet ORL et d'un sujet IIT Delhi) ; résultats étiquetés « bases publiques », jamais mélangés avec ceux des volontaires (RM-21.15).
- **A-21.2 Ré-exécution** avec les mêmes données, la même graine et les mêmes versions → mêmes tableaux ; tout écart est signalé comme anomalie.
- **A-21.3 Sous-ensemble de configurations** → autorisé ; le manifeste indique ce qui a été calculé et ce qui ne l'a pas été.

**Règles métier**
- RM-21.1 — Configurations évaluées (imposées par le brief) : visage seul, oreille seule avec l'extracteur LBP, oreille seule avec l'extracteur ONNX, fusion, fusion + garde-fou. Proposition (**point 22**) : fusion et fusion + garde-fou déclinées pour chaque extracteur d'oreille, soit 7 configurations.
- RM-21.2 — Mesures (imposées par le brief) : EER, FAR, FRR et courbe DET pour chaque configuration. FAR et FRR sont donnés au point de fonctionnement défini par les seuils (RM-21.7) ; l'EER est donné en complément, car il ne correspond à aucun réglage déployé.
- RM-21.3 — Données d'entrée (**point 21**). Pour recalculer chaque configuration, notamment les deux extracteurs d'oreille, le protocole a besoin d'images ou au moins de vecteurs conservés après l'enrôlement, ce qui contredit « aucune image brute ni aucun vecteur en clair n'est conservé ». Trois voies :
  - (a) images conservées dans l'espace « recherche » (UC-05 A-05.1) : consentement distinct, chiffrement avec une clé distincte de la clé maîtresse de production, pseudonyme, date de destruction ; rejouable pour tout extracteur, y compris futur ;
  - (b) vecteurs de toutes les configurations calculés au moment de la capture puis conservés chiffrés, sans image : rejouable pour la normalisation, la fusion, les seuils et le BioHashing, mais pas pour un nouvel extracteur ; ce sont toujours des données biométriques, soumises au même consentement ;
  - (c) scores seulement, calculés à la fin de la collecte, puis destruction de tout le reste : aucun rejeu possible ; et comme les deux sessions sont espacées dans le temps, des données doivent de toute façon être conservées entre elles.
  Proposition : (a), seule voie qui permet de comparer honnêtement les deux extracteurs sur les mêmes captures ; (b) en repli. Dans tous les cas, l'espace « recherche » est la seule exception à la règle de non-conservation, et le script ne lit jamais les gabarits de production.
- RM-21.4 — Protocole de collecte : **point N-6.9** — proposition : au moins 2 sessions par volontaire espacées d'au moins 24 h (idéalement une semaine) ; par session, une séquence d'enrôlement complète (5 captures visage + 5 captures oreille, comme UC-03 et UC-04) et 3 séquences d'authentification (comme UC-08) ; conditions consignées sous forme d'étiquettes non biométriques (éclairage, lunettes, cheveux attachés ou libres).
- RM-21.5 — Comparaisons (**point N-6.9** — proposition) : légitimes = gabarit agrégé de la session 1 (même agrégation qu'en production, **point 11**) contre les captures d'authentification de la session 2 du même volontaire, et inversement ; imposteurs « zéro effort » = gabarit de chaque volontaire contre les captures d'authentification de tous les autres volontaires ; les paires intra-session sont exclues des comparaisons légitimes, car elles donnent des scores trop optimistes.
- RM-21.6 — BioHashing et jetons (règle proposée, **point N-6.10**) : avec un jeton différent par utilisateur, les scores imposteurs sont artificiellement éloignés et l'EER tombe presque à 0. Ce résultat, régulièrement critiqué dans la littérature, mesure surtout le secret du jeton. Le rapport présente donc obligatoirement, pour chaque configuration, trois scénarios : « sans BioHashing » (vecteurs bruts, référence), « jeton secret » (chacun son jeton) et « jeton volé » (l'imposteur utilise le jeton de sa victime). Le scénario « jeton secret » n'est jamais présenté seul. Le scénario « jeton volé » n'a rien de théorique si le jeton est stocké sur le serveur (**point 19**). Calcul du score BioHash : **point 20**.
- RM-21.7 — Séparation calibration / test (**point N-6.11** — proposition) : paramètres z-score (**point 23**), poids et planchers (**point 24**) et seuil de fusion sont estimés sur des volontaires distincts de ceux sur lesquels ils sont évalués (validation croisée par volontaire, 5 plis) ; on rapporte la moyenne et la dispersion entre plis. Les résultats obtenus avec la version de production des paramètres sont présentés à part, avec la mention « paramètres réglés sur une partie des mêmes volontaires » lorsque c'est le cas.
- RM-21.8 — Petit effectif (**point N-6.12**) : 10 à 15 volontaires donnent 45 à 105 paires d'imposteurs distinctes, et les comparaisons d'une même paire ne sont pas indépendantes. Les intervalles de confiance sont calculés en rééchantillonnant les volontaires (bootstrap par personne), pas les comparaisons. Aucun FAR n'est annoncé en dessous de ce que l'effectif permet de mesurer : sans aucune fausse acceptation sur environ 100 paires indépendantes, la borne supérieure à 95 % reste d'environ 3 % (règle de trois), et d'environ 7 % avec 10 volontaires. On écrit « FAR ≤ 3 % (IC 95 %) », jamais « FAR = 0 % ». Chaque chiffre est accompagné du nombre de volontaires et de comparaisons dont il est issu.
- RM-21.9 — Courbe DET de la fusion + garde-fou : **point N-6.13** — proposition : balayage du seul seuil de fusion (R4), les planchers R2 et R3 restant fixés aux valeurs de la version des paramètres ; la courbe est tronquée (le FRR ne descend pas sous le taux de rejet des planchers), ce que la figure indique ; si FAR et FRR ne se croisent pas, le rapport écrit « EER non atteint » au lieu d'extrapoler.
- RM-21.10 — Reproductibilité : graine aléatoire fixée et consignée ; versions et empreintes des modèles (ArcFace buffalo_l, paramètres LBP, fichier ONNX), version des paramètres de décision, version du script, liste pseudonymisée des volontaires inclus et exclus, captures exclues avec leur motif. Le tout est consigné dans un manifeste joint aux sorties.
- RM-21.11 — Sorties : **point N-6.8** — proposition : `resultats.csv` (une ligne par configuration × scénario de protection : EER, FAR et FRR au point de fonctionnement avec intervalles, FTA, nombre de volontaires et de comparaisons, temps CPU médian et 95e centile) ; une figure DET par scénario superposant les configurations, en PNG et en PDF ; `manifeste.json` ; `recommandation.txt`. FAR et FRR sont mesurés au niveau système, échecs d'acquisition inclus (ISO/IEC 19795-1), le FTA étant aussi donné à part.
- RM-21.12 — Le script **recommande** un extracteur d'oreille, il ne décide pas : le choix est fait par une personne dans UC-18 (brief : « on choisira la meilleure après évaluation sur nos propres captures »). Le script ne modifie jamais les paramètres de production. Critère de recommandation : **point N-6.14**.
- RM-21.13 — Les sorties ne contiennent que des scores, des métriques et des pseudonymes (**point N-6.7**) : aucune image, aucun vecteur, aucun BioHash, aucun jeton.
- RM-21.14 — Périmètre : le protocole mesure la reconnaissance sur des présentations authentiques et des imposteurs « zéro effort ». La vivacité (R1) et les attaques de présentation relèvent du laboratoire (UC-19, UC-20). Les deux rapports sont complémentaires ; aucun ne remplace l'autre.
- RM-21.15 — Bases publiques (**point 36** — proposition) : le même script accepte en entrée les bases ORL et IIT Delhi, pour comparer avec la démo existante. Les limites sont écrites dans le rapport : utilisateurs chimériques (hypothèse d'indépendance entre visage et oreille), images ORL en niveaux de gris et en basse résolution, oreilles IIT Delhi acquises avec un autre capteur et dans d'autres conditions que la webcam, aucune vivacité.

**Postcondition** : le répertoire de sortie contient le tableau CSV, les figures DET, le manifeste et la recommandation ; aucune image ni aucun vecteur déchiffré ne subsiste hors de l'espace « recherche » chiffré ; l'exécution est journalisée ; les paramètres de production sont inchangés.

---

## Nouveaux points à trancher (section 6)

**N-6.1 — Forme du mode laboratoire**
- Question : le mode laboratoire est-il un simple interrupteur ou s'organise-t-il en campagnes nommées ? Doit-il exister dans un déploiement réel ?
- Options : (a) interrupteur global ; (b) campagnes nommées (nom, objectif, dates d'ouverture et de fermeture) ouvertes et fermées par l'évaluateur ; (c) comme (b), plus une option de configuration qui retire entièrement le laboratoire hors démonstration.
- Recommandation : (c). La campagne sert de filtre naturel au rapport (UC-20) et de contexte en soutenance ; pouvoir retirer le laboratoire d'un déploiement réel supprime une surface d'attaque inutile.

**N-6.2 — Effets d'une tentative de laboratoire sur le compte ciblé**
- Question : une tentative acceptée en laboratoire délivre-t-elle un JWT ? Une tentative refusée incrémente-t-elle le compteur de UC-09 ? Peut-on cibler un compte verrouillé ?
- Options : (a) aucun JWT, aucun incrément, cible verrouillée autorisée, verrouillage ni levé ni prolongé ; (b) comportement identique à UC-08 ; (c) aucun JWT, mais incrément du compteur.
- Recommandation : (a), à articuler avec le **point 26**. Le laboratoire mesure une décision, il n'ouvre pas d'accès ; incrémenter le compteur verrouillerait le volontaire au milieu d'une campagne, et les tentatives suivantes seraient refusées pour une raison étrangère aux règles R1 à R4.

**N-6.3 — Fiabilité de l'étiquetage**
- Question : comment prévenir et corriger les erreurs d'étiquette ?
- Options : (a) étiquette définitive ; (b) correction a posteriori par l'évaluateur, motif obligatoire, enregistrée comme un nouvel événement du journal (l'original reste visible) ; (c) pas de correction, seulement l'invalidation de la tentative.
- Recommandation : (b), plus la reconfirmation explicite de l'étiquette à chaque tentative (UC-19, étape 11). Les erreurs de saisie sont inévitables en séance, et un journal en ajout seul impose un événement de correction plutôt qu'une modification.

**N-6.4 — Consentement des participants au laboratoire**
- Question : quel accord faut-il du titulaire du compte ciblé, de la personne qui joue l'imposteur (parfois sans compte) et de la personne dont la photo sert d'instrument d'attaque ?
- Options : (a) aucun accord spécifique ; (b) clause « laboratoire » distincte et facultative dans UC-02 pour être ciblable, plus formulaire écrit signé pour les personnes sans compte ; (c) formulaire écrit pour tous, hors système.
- Recommandation : (b). (a) traiterait des données biométriques sans base légale ; (b) garde la preuve dans le système quand c'est possible. Les instruments physiques (tirages, photos sur téléphone) sont aussi des données biométriques : ils sont détruits en fin de campagne, et cette destruction est consignée. Responsable de traitement : **point 8**.

**N-6.5 — Tentatives interrompues et échecs d'acquisition**
- Question : que faire d'une tentative qui n'aboutit pas à une décision ?
- Options : (a) l'ignorer ; (b) la journaliser `INCOMPLETE`, l'exclure des taux et la compter à part ; (c) la compter comme un refus.
- Recommandation : selon la cause. Interruption imputable à l'évaluateur ou à une panne → (b). Échec imputable à la présentation (visage masqué non détecté, oreille introuvable, délai de vivacité dépassé) → (c), « rejet avant décision », comme UC-08 l'aurait traité. Exclure ces échecs retirerait du dénominateur les attaques bloquées le plus tôt, ce qui gonflerait leur taux de réussite apparent, et embellirait le FRR des présentations légitimes.

**N-6.6 — Format de l'export CSV**
- Question : un seul fichier agrégé, le détail par tentative, ou les deux ?
- Options : (a) agrégé seul ; (b) détail seul ; (c) archive ZIP avec `tentatives.csv`, `synthese.csv` et `contexte.txt`.
- Recommandation : (c), en UTF-8 avec BOM, séparateur `;` et virgule décimale (ouverture directe dans Excel en français), empreinte SHA-256 de chaque fichier journalisée, aucune copie conservée sur le serveur. Le détail permet à un membre du jury de recalculer chaque taux dans un tableur ; la synthèse garantit que le CSV et le PDF donnent exactement les mêmes chiffres.

**N-6.7 — Pseudonymisation des personnes**
- Question : comment désigner les personnes dans les exports du laboratoire et les sorties du protocole ?
- Options : (a) pseudonyme stable par personne (« V01 » pour un volontaire inscrit, « I01 » pour un imposteur sans compte), table de correspondance en base accessible au seul évaluateur ; (b) pseudonyme recalculé à chaque export ; (c) noms en clair.
- Recommandation : (a). Un pseudonyme stable permet de suivre la même personne entre laboratoire, rapport et protocole ; la table de correspondance est détruite avec les données de recherche (**point 6**). (c) est exclu pour un rapport destiné à être diffusé.

**N-6.8 — Mode d'exécution et sorties du protocole**
- Question : le protocole se lance-t-il en ligne de commande ou depuis l'interface d'administration ? Quelles sorties, et quelle définition de FAR et FRR ?
- Options : (a) script en ligne de commande sur la machine qui héberge l'espace « recherche », hors interface web ; (b) bouton dans l'interface d'administration, calcul en tâche de fond.
- Recommandation : (a). C'est ce que dit le brief (« script »), aucun point d'accès HTTP n'expose l'espace « recherche », et un calcul de plusieurs minutes ne bloque pas le serveur. Sorties selon RM-21.11 ; FAR et FRR au niveau système (ISO/IEC 19795-1), échecs d'acquisition inclus et FTA rapporté à part, car retirer ces échecs embellirait le FRR.

**N-6.9 — Protocole de collecte et constitution des comparaisons**
- Question : combien de sessions et de captures par volontaire, dans quelles conditions, avec quel effectif minimal et quelles paires ?
- Options : (a) une session unique ; (b) deux sessions espacées d'au moins 24 h ; (c) trois sessions ou plus sur plusieurs semaines.
- Recommandation : (b), avec le détail de RM-21.4 et RM-21.5 et un arrêt sous 10 volontaires exploitables (bas de la fourchette du brief). Une session unique surestime nettement les performances (même éclairage, même coiffure) ; (c) serait préférable mais difficile à tenir avec des camarades de promotion avant la soutenance.

**N-6.10 — Scénarios de protection rapportés**
- Question : quels scénarios BioHashing le protocole présente-t-il ?
- Options : (a) « jeton secret » seul ; (b) « jeton volé » seul ; (c) « sans BioHashing », « jeton secret » et « jeton volé ».
- Recommandation : (c). « Jeton secret » mesure surtout le secret du jeton, « jeton volé » mesure ce que la biométrie protégée apporte réellement, et « sans BioHashing » chiffre la perte de performance due à la projection et à la binarisation sur 256 bits.

**N-6.11 — Séparation calibration / test**
- Question : sur quelles données estimer les paramètres z-score, les poids, les planchers et le seuil de fusion évalués par le protocole ?
- Options : (a) sur toutes les données ; (b) validation croisée par volontaire à 5 plis ; (c) un volontaire laissé de côté à chaque tour (leave-one-subject-out).
- Recommandation : (b) ; (c) est plus stable avec 10 volontaires mais multiplie les calculs. Aucun volontaire ne doit servir à la fois à régler et à évaluer, sinon l'EER mesuré est optimiste.

**N-6.12 — Statistiques sur petits effectifs**
- Question : quels intervalles de confiance et quels seuils d'alerte pour le laboratoire (UC-20) et le protocole (UC-21) ?
- Options : (a) taux bruts sans intervalle ; (b) intervalles de Wilson à 95 % pour les taux du laboratoire, bootstrap par volontaire pour le protocole, alerte sous 10 tentatives, borne supérieure systématique pour un taux nul ; (c) intervalles exacts de Clopper-Pearson partout.
- Recommandation : (b). Wilson reste fiable sur de petits effectifs et pour des taux proches de 0 ; le bootstrap par personne respecte la dépendance entre les comparaisons d'un même volontaire, que Wilson ou Clopper-Pearson ignoreraient.

**N-6.13 — Courbe DET de « fusion + garde-fou »**
- Question : comment tracer la courbe DET et calculer l'EER d'une décision qui combine un seuil de fusion et deux planchers ?
- Options : (a) planchers fixés, balayage du seul seuil de fusion ; (b) balayage conjoint des trois seuils, enveloppe des meilleurs points ; (c) pas de courbe, seulement le point de fonctionnement.
- Recommandation : (a). Les planchers sont une politique de sécurité, pas un réglage de fonctionnement ; (b) choisirait les planchers a posteriori sur les données de test, ce qui réintroduit le biais d'optimisme.

**N-6.14 — Critère de recommandation de l'extracteur d'oreille**
- Question : sur quel critère le script recommande-t-il LBP ou ONNX pour UC-18 ?
- Options : (a) plus faible EER en oreille seule ; (b) plus faible EER (ou, s'il n'est pas atteint, plus faible FRR au point de fonctionnement) de la configuration « fusion + garde-fou » en scénario « jeton volé », sous la contrainte d'une authentification en moins de 2 s sur CPU ; (c) choix libre de l'évaluateur au vu des tableaux.
- Recommandation : (b), avec une règle de départage : si les intervalles de confiance se chevauchent, la différence n'est pas démontrée et le script recommande LBP (référence, plus léger, explicable en soutenance). C'est la configuration réellement déployée qui compte, et « jeton volé » est le seul scénario qui mesure la biométrie plutôt que le jeton.
