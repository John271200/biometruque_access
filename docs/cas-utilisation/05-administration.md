# 5. Espace d'administration (UC-13 à UC-18)

> Statut : **BROUILLON v1 — en attente de validation**.

---

## Dispositions communes (UC-13 à UC-18)

Ces dispositions valent pour chacun des six cas d'utilisation ci-dessous et n'y sont pas répétées.

- **Acteur principal** : Administrateur (rôle `admin`). L'accès éventuel du rôle `evaluateur` à UC-16, UC-17 et UC-18 dépend du **point 31**.
- **Préconditions communes** : session « compte » active (UC-07) d'un compte au rôle `admin` ; HTTPS (ou `localhost`).

**Scénarios d'erreur communs**
- **E-ADM.1 Requête d'un compte sans rôle `admin`** (sous réserve du **point 31** pour le rôle `evaluateur`), y compris par saisie directe de l'adresse d'une page ou d'une route d'administration → refus HTTP 403, « Accès réservé aux administrateurs. » ; aucune donnée n'est renvoyée, pas même un nombre de comptes. Journalisation du refus : **point N-5.9**.
- **E-ADM.2 Session expirée** → redirection vers la connexion (UC-07) ; la saisie non validée est perdue, aucune action n'est exécutée.
- **E-ADM.3 Rôle retiré ou compte administrateur supprimé pendant la session** → la requête suivante est refusée (RM-ADM.1).
- **E-ADM.4 Accès en HTTP hors `localhost`** → redirection vers HTTPS ; aucune page d'administration n'est servie en clair.
- **E-ADM.5 Modification concurrente** (un autre administrateur, ou l'utilisateur lui-même, a modifié l'objet visé depuis son affichage) → aucune action exécutée, « Ces informations ont changé depuis leur affichage. Vérifiez-les puis recommencez. », avec l'état à jour.

**Règles métier communes**
- RM-ADM.1 — Le rôle `admin` est vérifié par le serveur à chaque requête. Masquer un menu ou désactiver un bouton n'est jamais un contrôle d'accès.
- RM-ADM.2 — Le rôle `admin` ne donne aucun accès à la base protégée : un administrateur qui veut la consulter s'authentifie biométriquement (UC-08) comme tout utilisateur (§ 1.4, **point 3**).
- RM-ADM.3 — Aucune donnée biométrique ne sort par l'espace d'administration : ni image, ni vecteur, ni BioHash, ni gabarit chiffré, ni jeton personnel, ni empreinte de ces éléments ; ni à l'écran, ni dans une réponse d'API, ni dans un export. Seuls des états, des dates et des scores (nombres) sont manipulés.
- RM-ADM.4 — Toute action d'écriture (UC-14, UC-16, UC-18) est enregistrée dans le journal des actes d'administration, en ajout seul : administrateur auteur, horodatage, action, cible, valeurs avant et après, motif (**point N-5.3**), adresse IP, résultat. Une action échouée est journalisée aussi.
- RM-ADM.5 — Toute action d'écriture est atomique : elle s'applique entièrement ou pas du tout, et elle ne peut pas réussir sans que son entrée de journal soit écrite.
- RM-ADM.6 — Les actes sensibles exigent une confirmation forte (**point N-5.2**) et un motif (**point N-5.3**).
- RM-ADM.7 — Les horodatages sont stockés en UTC ; fuseau d'affichage : **point N-5.1**.
- RM-ADM.8 — Interface en français, sobre et utilisable sur mobile : sur petit écran, les tableaux deviennent des listes de fiches et les graphiques s'empilent verticalement ; aucune action ne dépend du survol à la souris.
- RM-ADM.9 — Listes filtrées, triées et paginées par le serveur. Un paramètre de filtre, de tri ou de pagination invalide est refusé (HTTP 400) et l'interface revient aux valeurs par défaut (**point N-5.4**).

---

## UC-13 — Lister les utilisateurs et leur statut

> **En tant qu'**administrateur, **je veux** voir la liste des comptes avec leur rôle et leurs états de compte, de consentement et d'enrôlement, **afin de** suivre la population enrôlée et repérer les comptes qui demandent une intervention (verrouillés, enrôlement inachevé, consentement retiré).

- **Acteur principal** : Administrateur
- **Préconditions** : dispositions communes.
- **Déclencheur** : ouverture de la page « Utilisateurs » de l'espace d'administration.

**Scénario nominal**
1. Le système affiche la première page des comptes non supprimés, dans l'ordre par défaut (**point N-5.4**), avec le nombre total de comptes.
2. Chaque ligne présente les colonnes de RM-13.1, sans aucune donnée biométrique (RM-13.2).
3. L'administrateur recherche (RM-13.3), filtre (RM-13.4), trie (RM-13.5) ou change de page ; le système renvoie les comptes correspondants et leur nombre.
4. Pour chaque ligne, le système propose les actions compatibles avec l'état du compte et les droits de l'administrateur (RM-13.6).

**Scénarios alternatifs et d'erreur**
- **A-13.1 Aucun résultat** → « Aucun utilisateur ne correspond à ces critères. », avec un bouton « Réinitialiser les filtres ».
- **A-13.2 Propre compte de l'administrateur** → ligne marquée « vous » ; les actions sur soi renvoient vers « Mes données » (UC-06, UC-11, UC-12) (**point N-5.6**).
- **A-13.3 Autres administrateurs** → visibles dans la liste ; actions possibles selon le **point N-5.6**.
- **A-13.4 Verrou expiré entre l'affichage et l'action** → le verrou est levé automatiquement à son échéance (UC-09) ; un clic sur « Déverrouiller » aboutit à E-14.2.
- **E-13.1 Paramètre invalide** (colonne de tri inexistante, page négative, filtre inconnu, adresse modifiée à la main) → RM-ADM.9, « Critères invalides : la liste a été réinitialisée. »
- **E-13.2 Page au-delà de la dernière** (après des suppressions, par exemple) → la dernière page existante est affichée.

**Règles métier**
- RM-13.1 — Colonnes : nom, email, rôle, état du compte, consentement, enrôlement, date d'enrôlement, extracteur d'oreille, dernier accès, échecs récents, verrouillé jusqu'à. Définitions :
  - *date d'enrôlement* : date de finalisation (UC-05) des gabarits en vigueur ; vide s'il n'y en a pas (`NON_ENROLE`, `REVOQUE`) ;
  - *extracteur d'oreille* : identifiant et version de l'extracteur qui a produit le gabarit d'oreille en vigueur ; deux valeurs si le **point 22** prévoit deux gabarits, celle qui sert à la décision étant signalée ;
  - *dernier accès* : date de la dernière consultation de la base protégée (UC-10), même définition qu'en UC-06 ;
  - *échecs récents* : valeur courante du compteur d'échecs qui mène au verrouillage (UC-09 ; fenêtre de comptage : **point 26**) ;
  - *verrouillé jusqu'à* : échéance du verrou en cours, vide si le compte n'est pas verrouillé.
- RM-13.2 — Ni gabarit, ni jeton BioHashing, ni vecteur, ni image, ni hachage du mot de passe ne sont affichés ou renvoyés par l'API (RM-ADM.3, RM-01.5). Seules la présence d'un gabarit, sa date et son extracteur sont visibles.
- RM-13.3 — Recherche : texte libre, par sous-chaîne, sur le nom et l'email, insensible à la casse.
- RM-13.4 — Filtres combinables (tous doivent être satisfaits) : rôle, état du compte, consentement, enrôlement, extracteur d'oreille, verrouillé (oui / non), période d'enrôlement, période de dernier accès.
- RM-13.5 — Tri croissant ou décroissant sur chaque colonne, avec un tri secondaire sur l'identifiant interne pour que l'ordre reste stable d'une page à l'autre.
- RM-13.6 — Actions par ligne, chacune proposée seulement si l'état la permet :
  - « Voir ses tentatives » → UC-15 filtré sur ce compte (toujours proposée) ;
  - « Déverrouiller » → compte `VERROUILLE_TEMPORAIREMENT` (UC-14, A-14.2) ;
  - « Révoquer les gabarits » → enrôlement `ENROLE` (UC-14) ;
  - « Supprimer le compte » → sous réserve de RM-14.6 et du **point N-5.6** (UC-14, A-14.1) ;
  - « Changer le rôle » → seulement si le **point N-5.5** introduit cette action.

  Une action bloquée par une protection est affichée désactivée, avec sa raison écrite en clair (ex. « Dernier administrateur »). Le serveur revérifie l'état et les droits au moment de l'exécution (RM-ADM.1).
- RM-13.7 — La liste ne modifie rien. La modification du nom, de l'email ou du mot de passe d'un utilisateur par un administrateur ne fait pas partie du cahier des charges.
- RM-13.8 — Les comptes `SUPPRIME` n'apparaissent pas ; leur trace résiduelle dans les journaux relève du **point 9**.

**Postcondition** : aucun état modifié ; la vue reflète l'état des comptes au moment de la requête.

---

## UC-14 — Révoquer ou supprimer un utilisateur

> **En tant qu'**administrateur, **je veux** révoquer les gabarits d'un utilisateur, supprimer entièrement son compte ou lever son verrouillage, **afin de** réagir à une compromission suspectée, exécuter une demande d'effacement reçue hors de l'application ou débloquer un utilisateur légitime.

- **Acteur principal** : Administrateur
- **Préconditions** : dispositions communes ; compte cible existant, non `SUPPRIME` ; état compatible avec l'action (RM-13.6).
- **Déclencheur** : choix d'une action sur une ligne de la liste (UC-13).

**Scénario nominal** (révocation administrative)
1. L'administrateur choisit « Révoquer les gabarits » sur la ligne d'un utilisateur `ENROLE`.
2. Le système relit l'état courant du compte et vérifie que l'action est permise (RM-14.6, RM-14.7, **point N-5.6**).
3. Le système affiche l'écran de confirmation : nom, email et rôle de la cible ; conséquences en clair (« Les gabarits visage et oreille et le jeton de cet utilisateur seront détruits définitivement. Ses accès en cours à la base protégée seront coupés. Il devra se ré-enrôler pour s'authentifier. ») ; champ motif (**point N-5.3**).
4. L'administrateur saisit le motif et confirme selon le **point N-5.2**.
5. Le système exécute la révocation (RM-14.1) en une seule transaction.
6. Le système journalise l'acte (RM-14.8) et informe l'utilisateur selon le **point N-5.7**.
7. Le système affiche « Gabarits révoqués. [Nom] devra se ré-enrôler pour s'authentifier. » ; la ligne passe à `REVOQUE`.

**Scénarios alternatifs et d'erreur**
- **A-14.1 Suppression complète** → mêmes étapes 2 à 6 ; l'écran de confirmation annonce « Le compte de [Nom] et toutes ses données seront supprimés définitivement. Cette action est irréversible. » ; effets de RM-14.2 ; message final « Compte supprimé. » ; la ligne disparaît de la liste.
- **A-14.2 Déverrouillage manuel** (**point 26** — proposition : autorisé, motif obligatoire, confirmation simple) → sur un compte `VERROUILLE_TEMPORAIREMENT`, effets de RM-14.3 ; message « Compte déverrouillé. Le compteur d'échecs est remis à zéro. »
- **A-14.3 Demande d'effacement reçue hors de l'application** (email, courrier) → l'administrateur exécute A-14.1 avec le motif « demande de l'utilisateur ». La vérification de l'identité du demandeur incombe au responsable de traitement (**point 8**) et précède l'action.
- **A-14.4 Cible en cours d'enrôlement** (session UC-03 ou UC-04 ouverte) au moment d'une suppression → la session d'enrôlement est détruite et la finalisation (UC-05) refusée ; aucun gabarit ne peut apparaître après la suppression.
- **A-14.5 Cible titulaire d'un JWT valide ou en cours d'authentification** → RM-14.4 ; sa requête suivante sur la base protégée est refusée avec « Votre accès a été révoqué. »
- **A-14.6 Changement de rôle** (seulement si le **point N-5.5** l'introduit) → même déroulé, sous les protections RM-14.6 et RM-14.7.
- **E-14.1 Cible introuvable ou déjà supprimée** → HTTP 404, « Ce compte n'existe plus. »
- **E-14.2 État incompatible** → aucun effet ; « Ce compte n'est pas enrôlé : il n'y a rien à révoquer. » ou « Ce compte n'est plus verrouillé (verrou expiré à 14 h 32). »
- **E-14.3 Dernier administrateur** → « Impossible : ce compte est le dernier administrateur. » (RM-14.6)
- **E-14.4 Action sur son propre compte** → « Pour votre propre compte, utilisez la page « Mes données ». » (**point N-5.6**)
- **E-14.5 Action non autorisée sur un autre administrateur** → HTTP 403, « Cette action sur un compte administrateur n'est pas disponible dans l'interface. » (**point N-5.6**)
- **E-14.6 Motif absent ou non conforme** → refus rattaché au champ motif ; aucune action.
- **E-14.7 Confirmation forte incorrecte** (email de la cible mal ressaisi, mot de passe de l'administrateur faux) → refus, aucune action ; les échecs de mot de passe comptent pour la protection du compte administrateur (UC-07).
- **E-14.8 Échec technique en cours d'exécution** → transaction annulée, état inchangé, aucune destruction partielle (jamais un gabarit détruit avec un jeton conservé, ni l'inverse) ; « L'opération a échoué, aucune modification n'a été faite. Réessayez. » ; échec journalisé.
- **E-14.9 État modifié entre-temps** (l'utilisateur s'est révoqué via UC-11 ou supprimé via UC-12, un autre administrateur a agi) → E-ADM.5.
- **E-14.10 Double soumission** (double clic, renvoi réseau) → l'action n'est exécutée qu'une fois ; la seconde demande reçoit le résultat de la première.

**Règles métier**
- RM-14.1 — Révocation administrative = mêmes effets techniques que UC-11 : destruction définitive des gabarits visage et oreille (tous extracteurs confondus, RM-18.7) et du jeton BioHashing ; invalidation des JWT de la cible (RM-14.4) ; enrôlement → `REVOQUE`. Le compte reste `ACTIF`, le consentement inchangé, et la session « compte » de la cible reste valide puisqu'elle en a besoin pour se ré-enrôler. Le ré-enrôlement (UC-03 à UC-05) génère un nouveau jeton.
- RM-14.2 — Suppression administrative = mêmes effets que UC-12 : destruction des gabarits, du jeton, des données de compte (nom, email, hachage du mot de passe) et des éventuelles images de l'espace « recherche » (**point 21**) ; invalidation des JWT et fermeture de toutes les sessions de la cible ; compte → `SUPPRIME`. L'historique des consentements est conservé comme preuve (RM-02.4, **point 9**) ; le sort des entrées de journal qui la concernent relève du **point 9**.
- RM-14.3 — Déverrouillage : compte → `ACTIF`, compteur d'échecs à zéro, échéance du verrou effacée. Il redonne un crédit complet d'essais à l'utilisateur, mais aussi à un attaquant qui viserait ce compte : c'est pourquoi il est motivé et journalisé.
- RM-14.4 — Après une révocation ou une suppression, tout JWT émis à partir des gabarits détruits est refusé, y compris celui qu'une authentification déjà en cours délivrerait juste après l'instant de révocation.
- RM-14.5 — La révocation n'empêche pas le ré-enrôlement. En cas de soupçon d'usurpation à l'enrôlement (une personne enrôlée sous le compte d'une autre), l'action adaptée est la suppression.
- RM-14.6 — Le système refuse toute opération qui laisserait le service sans compte `admin` non supprimé : suppression ou rétrogradation du dernier administrateur. La même protection s'applique à UC-12 et aux commandes passées sur le serveur.
- RM-14.7 — Un administrateur ne peut pas modifier son propre rôle.
- RM-14.8 — Journalisation (RM-ADM.4) : qui (administrateur), quoi (révocation, suppression, déverrouillage, changement de rôle), sur qui (identifiant interne de la cible), quand, motif, état avant et après. La présence de l'email de la cible dans ce journal après une suppression relève du **point 9**.
- RM-14.9 — Aucune de ces actions ne donne à l'administrateur accès aux données biométriques de la cible ; la destruction des gabarits ne passe pas par leur déchiffrement.

**Postcondition** : selon l'action, gabarits et jeton détruits (`REVOQUE`), compte supprimé (`SUPPRIME`) ou compte déverrouillé (`ACTIF`, compteur à zéro), et acte journalisé ; en cas d'échec, aucun changement.

---

## UC-15 — Consulter le journal des tentatives

> **En tant qu'**administrateur, **je veux** consulter et filtrer le journal des tentatives d'authentification biométrique, avec les scores et le verdict de chaque règle, **afin de** comprendre les refus, repérer les attaques et vérifier que la politique de décision en vigueur est bien appliquée.

- **Acteur principal** : Administrateur
- **Préconditions** : dispositions communes.
- **Déclencheur** : ouverture de la page « Journal des tentatives », ou action « Voir ses tentatives » depuis UC-13 (filtre utilisateur prérempli).

**Scénario nominal**
1. Le système affiche les tentatives de la période par défaut, les plus récentes en premier, paginées (**point N-5.4**).
2. Chaque ligne résume une tentative ; colonnes de la vue condensée : **point N-5.4**.
3. L'administrateur combine des filtres (RM-15.3) ; le système renvoie les tentatives correspondantes et leur nombre.
4. L'administrateur ouvre une tentative ; le système en affiche le détail complet (RM-15.2).
5. Depuis le détail, l'administrateur peut ouvrir la version des paramètres de décision appliquée (UC-16) et, pour une tentative acceptée, les accès à la base protégée faits avec le JWT délivré (**point N-5.8**).

**Scénarios alternatifs et d'erreur**
- **A-15.1 Tentative sans score** (compte inconnu, non enrôlé ou verrouillé ; échec de vivacité ou de qualité avant comparaison) → les scores absents s'affichent « non calculé », avec la règle qui a arrêté le traitement. Calculer et journaliser quand même les scores après un premier échec : **point 25** — proposition : oui après un échec de vivacité ou de plancher, pour que le laboratoire mesure ce qu'une attaque aurait obtenu (la décision restant celle de la première règle en échec) ; jamais pour un compte inconnu, non enrôlé ou verrouillé.
- **A-15.2 Compte supprimé depuis la tentative** → affichage selon le **point 9** — proposition : le journal ne contient que l'identifiant interne du compte, et l'email affiché est obtenu par jointure avec la table des comptes ; après suppression, l'entrée s'affiche « compte supprimé n° 42 » sans que le journal soit modifié.
- **A-15.3 Email revendiqué inconnu** → tentative journalisée avec la raison « compte inconnu » ; conservation de l'adresse saisie en clair, ou sous forme d'empreinte à clé qui permet de regrouper les essais sans garder l'adresse : **point 9**.
- **A-15.4 Tentatives du laboratoire** (UC-19) → **point 33** — proposition : même journal, contexte « laboratoire » et étiquette obligatoires, filtre par défaut « production » sur cette page.
- **A-15.5 Vérification d'intégrité** → selon le **point N-5.10**.
- **A-15.6 Export** → selon le **point N-5.9**.
- **E-15.1 Période invalide** (début postérieur à la fin) → « La date de début doit précéder la date de fin. » ; filtre non appliqué.
- **E-15.2 Aucune tentative** → « Aucune tentative ne correspond à ces filtres. »
- **E-15.3 Tentative de modification ou de suppression par l'API** → HTTP 405, aucune modification ; traçabilité de l'événement : **point N-5.9**.

**Règles métier**
- RM-15.1 — Journal en lecture seule : aucune entrée ne peut être modifiée ni supprimée depuis l'interface ou l'API, quel que soit le rôle. Seules les purges automatiques de la politique de conservation (**point 9**) font disparaître des entrées, et chaque purge est elle-même journalisée.
- RM-15.2 — Contenu d'une entrée :
  - horodatage (stocké en UTC, affiché selon le **point N-5.1**) ;
  - utilisateur revendiqué (email saisi, relié au compte s'il existe) ;
  - contexte (production ou laboratoire) et, pour le laboratoire, étiquette (légitime, imposteur, attaque ; type d'attaque : **point 32**) ;
  - scores bruts visage et oreille (similarité tirée de la distance de Hamming, **point 20**), scores normalisés (z-score, **point 23**), score fusionné ;
  - verdict de chaque règle : `réussie`, `échouée` ou `non évaluée` (liste et ordre des règles : **point 25**) ;
  - décision (acceptée ou refusée) et raison, c'est-à-dire la règle déterminante ;
  - durée de traitement côté serveur, en millisecondes, de la réception de la capture à la décision ;
  - numéro de la version des paramètres de décision appliquée (UC-16) et identifiant de l'extracteur d'oreille utilisé (UC-18) ;
  - adresse IP ;
  - pour une tentative acceptée, l'identifiant du JWT délivré, jamais le JWT lui-même.
- RM-15.3 — Filtres combinables : période ; utilisateur (email ou nom, par sous-chaîne) ; décision ; règle ayant causé le refus ; contexte ; étiquette du laboratoire ; adresse IP (exacte ou par préfixe). Filtres supplémentaires : **point N-5.4**.
- RM-15.4 — Le journal contient toujours le détail complet, quoi qu'il soit montré à l'utilisateur en cas d'échec (**point 27**) : la discrétion envers l'utilisateur ne réduit pas l'information de l'administrateur.
- RM-15.5 — Aucune donnée biométrique dans le journal (RM-ADM.3) : uniquement des scores et des verdicts.
- RM-15.6 — Les scores bruts sont conservés tels quels. Ils permettent de recalculer le score fusionné et la décision sous n'importe quelle version de paramètres : l'aperçu d'UC-16 et le tableau de bord d'UC-17 reposent sur eux.
- RM-15.7 — Les accès à la base protégée (UC-10) et les actes d'administration (RM-ADM.4) sont journalisés eux aussi ; leur présentation (même écran ou écrans séparés) relève du **point N-5.8**.

**Postcondition** : aucune modification ; le journal est inchangé.

---

## UC-16 — Régler les paramètres de décision

> **En tant qu'**administrateur, **je veux** régler le FAR cible, le plancher de chaque modalité et les poids de fusion en voyant leur effet estimé avant de les appliquer, **afin d'**ajuster le compromis entre sécurité et confort d'usage à partir des données réelles, avec la possibilité de revenir en arrière.

- **Acteur principal** : Administrateur (qui peut modifier : **points 30 et 31** — proposition : rôle `admin` seulement)
- **Préconditions** : dispositions communes ; une version de paramètres active existe pour l'extracteur d'oreille actif (au minimum la version initiale, RM-16.10).
- **Déclencheur** : ouverture de la page « Paramètres de décision ».

**Scénario nominal**
1. Le système affiche la version active : numéro, auteur, date, motif, extracteur d'oreille concerné, FAR cible, seuil de fusion qui en est dérivé, plancher visage, plancher oreille, poids visage et poids oreille, paramètres de normalisation, ainsi que la source, la période et l'effectif des scores qui ont servi à dériver le seuil.
2. L'administrateur modifie une ou plusieurs valeurs réglables (RM-16.1) ; les bornes sont contrôlées à la saisie puis de nouveau par le serveur (RM-16.3 à RM-16.5).
3. L'administrateur demande l'aperçu. Sur les tentatives étiquetées disponibles (source : **point N-5.13** ; extracteur actif ; période modifiable), le système recalcule à partir des scores bruts journalisés (RM-15.6) : scores normalisés, scores fusionnés avec les nouveaux poids, seuil dérivé du FAR cible (RM-16.6), puis FAR et FRR estimés au niveau du score et au niveau de la décision (RM-17.3).
4. Le système présente côte à côte la version active et la proposition : seuil, FAR et FRR estimés, part des tentatives légitimes refusées par chaque plancher, effectifs utilisés. Si le FAR estimé augmente, un avertissement l'annonce (**point 30** — proposition : avertissement non bloquant).
5. L'administrateur saisit le motif (**point N-5.3**) et confirme (**point N-5.2**).
6. Le système crée une nouvelle version immuable (RM-16.8), identique à celle de l'aperçu (RM-16.9), et la rend active de manière atomique.
7. Le système journalise l'acte (RM-ADM.4) avec les valeurs avant et après.
8. Le système affiche « Version 7 active depuis 10 h 42. Elle s'applique aux authentifications qui commencent à partir de maintenant. »

**Scénarios alternatifs et d'erreur**
- **A-16.1 Retour à une version antérieure** (**point 30** — proposition : autorisé) → l'administrateur ouvre l'historique, choisit la version k, voit l'aperçu de k sur les données actuelles à côté de la version active, motive et confirme. Le système crée une version n+1 qui reprend exactement les valeurs de k, seuil figé compris : l'historique reste linéaire, aucune version n'est modifiée ni « réactivée ».
- **A-16.2 Scores imposteurs insuffisants** (effectif sous le minimum du **point N-5.12**) → l'aperçu affiche « Données insuffisantes : 84 scores imposteurs disponibles, 300 nécessaires pour un FAR cible de 1 %. » et aucun seuil dérivé ne peut être appliqué. Repli possible : version dont le seuil provient des valeurs par défaut (**point 24**) ou des distributions de la démonstration ORL + IIT Delhi (**point 36**), marquée « non calibrée » ; cette mention reste affichée ici et sur le tableau de bord (UC-17) tant qu'aucune version calibrée n'est active.
- **A-16.3 FAR cible trop petit pour l'effectif disponible** → « Avec 300 scores imposteurs, le plus petit FAR vérifiable est d'environ 1 %. Choisissez un FAR cible d'au moins 1 % ou collectez davantage de tentatives imposteurs. » (**point N-5.12**)
- **A-16.4 Aucune tentative légitime étiquetée** → l'aperçu affiche le seuil et le FAR estimé, avec « FRR : données insuffisantes » ; application possible avec avertissement (**point N-5.12**).
- **A-16.5 Recalcul de la normalisation** (si le **point 23** retient une calibration figée) → action « Recalculer la normalisation » : moyennes et écarts-types recalculés sur les données étiquetées choisies, intégrés à la proposition et visibles dans l'aperçu ; le seuil est alors forcément redérivé (RM-16.7).
- **A-16.6 Préparer les paramètres d'un extracteur non actif** (si le **point N-5.15** retient une lignée par extracteur) → l'administrateur choisit l'extracteur ; l'aperçu porte sur les scores étiquetés de cet extracteur, qui n'existent que si le **point 22** fait calculer les deux scores d'oreille, ou à partir des images « recherche » (**point 21**) ; la version créée ne devient active qu'avec l'extracteur (UC-18).
- **A-16.7 Abandon avant confirmation** → aucune version créée.
- **E-16.1 Valeur hors bornes** → message rattaché au champ, par exemple « Le plancher visage doit être compris entre 0 et 1. » ou « Le FAR cible doit être compris entre 0,01 % et 10 %. » (bornes : **point 30**).
- **E-16.2 Somme des poids différente de 1** (requête forgée : l'interface n'offre qu'un curseur) → HTTP 400, « La somme des poids doit valoir 1. »
- **E-16.3 Aucune différence avec la version active** → « Aucune modification à enregistrer. » ; aucune version créée.
- **E-16.4 Valeurs modifiées après l'aperçu, ou aperçu absent** → refus, « Lancez l'aperçu avec ces valeurs avant de les appliquer. » (RM-16.9)
- **E-16.5 Version active changée entre-temps** (autre administrateur, changement d'extracteur UC-18) → E-ADM.5, « La version active a changé (version 8, par … à 10 h 40). Rechargez la page avant de modifier. »
- **E-16.6 Aperçu impossible** (erreur de calcul, délai dépassé) → « Aperçu impossible pour le moment ; aucun paramètre n'a été modifié. »
- **E-16.7 Échec à l'activation** → transaction annulée, la version précédente reste active, échec journalisé.

**Règles métier**
- RM-16.1 — Paramètres réglables : FAR cible, plancher visage, plancher oreille, poids visage (le poids oreille s'en déduit). Paramètres affichés mais non saisissables : seuil de fusion (dérivé, RM-16.6) et paramètres de normalisation z-score (calculés, **point 23**).
- RM-16.2 — Rappel de la décision : chaque score de modalité est normalisé (z-score), le score fusionné est la somme pondérée des scores normalisés, et l'acceptation exige que toutes les règles soient satisfaites, dont plancher visage, plancher oreille et seuil de fusion (autres règles et ordre : **point 25**).
- RM-16.3 — Poids : poids visage + poids oreille = 1, chacun ≥ 0. Bornes exactes : **point 30** — proposition : chaque poids dans [0,1 ; 0,9] ; la comparaison avec une modalité seule se fait dans le tableau de bord (EER par modalité), pas en désactivant une modalité en production.
- RM-16.4 — Planchers : nombres dans [0 ; 1], exprimés sur l'échelle du score brut (**point N-5.11**).
- RM-16.5 — FAR cible : nombre strictement compris entre 0 et 1, saisi en pourcentage. Bornes : **point 30** — proposition : de 0,01 % à 10 % ; le minimum réellement vérifiable dépend de l'effectif (**point N-5.12**).
- RM-16.6 — Seuil de fusion : quantile d'ordre (1 − FAR cible) de la distribution des scores fusionnés imposteurs, calculés avec les poids et la normalisation de la version proposée. Source des scores imposteurs : **point N-5.13** ; effectif minimal, égalités, figement et repli : **point N-5.12**.
- RM-16.7 — Toute modification des poids ou de la normalisation redérive le seuil : un seuil calculé sur une autre échelle de score fusionné n'a pas de sens et n'est jamais conservé.
- RM-16.8 — Versionnement : chaque jeu de paramètres est une version immuable portant un numéro croissant, l'auteur, la date, le motif, l'extracteur d'oreille concerné, toutes les valeurs (seuil dérivé et paramètres de normalisation compris), la source, la période et les effectifs des données de calibration, et la version précédente. Aucune version n'est modifiée ni supprimée.
- RM-16.9 — Aucune application sans aperçu : la version créée est exactement celle que l'aperçu a évaluée.
- RM-16.10 — Une version initiale existe dès l'installation (valeurs : **point 24**, éventuellement tirées de la démonstration, **point 36**), marquée « non calibrée ».
- RM-16.11 — Effet immédiat : toute authentification qui commence après l'activation applique la nouvelle version ; une authentification en cours garde la version lue à son début ; chaque tentative journalise la version appliquée (RM-15.2). Les JWT déjà délivrés restent valides jusqu'à leur expiration (**point 30** — proposition : oui, soit 10 minutes au plus).
- RM-16.12 — Une seule version active à la fois par extracteur d'oreille (**point N-5.15**).

**Postcondition** : une nouvelle version active, journalisée, appliquée aux authentifications suivantes ; ou aucun changement.

---

## UC-17 — Consulter le tableau de bord de performance

> **En tant qu'**administrateur, **je veux** voir les distributions des scores légitimes et imposteurs ainsi que les FAR, FRR et EER estimés par modalité et pour la fusion, **afin de** mesurer la performance réelle du système sur nos propres captures et de justifier les réglages d'UC-16 et UC-18.

- **Acteur principal** : Administrateur (ou Évaluateur, **point 31**)
- **Préconditions** : dispositions communes.
- **Déclencheur** : ouverture de la page « Tableau de bord ».

> **Difficulté de fond : la vérité terrain.** En production, on ne sait pas qui a réellement présenté son visage et son oreille : un refus peut venir d'un imposteur ou d'un utilisateur légitime mal capturé, un succès peut être un imposteur accepté. Or les distributions « légitime / imposteur » et tous les taux d'erreur exigent de le savoir. Ce tableau de bord ne calcule donc rien sans étiquettes de vérité terrain (RM-17.1) ; leur origine est le **point N-5.13**.

**Scénario nominal**
1. L'administrateur choisit la période, l'extracteur d'oreille (un seul à la fois, RM-17.5), le contexte et la version de paramètres de référence (par défaut : la version active).
2. Le système sélectionne les scores porteurs d'une étiquette de vérité terrain (RM-17.1) et affiche, pour chaque indicateur, l'effectif utilisé : nombre de scores légitimes, de scores imposteurs et de comptes distincts.
3. Le système affiche trois histogrammes superposant scores légitimes et imposteurs : visage (score brut, plancher visage tracé), oreille (score brut, plancher oreille tracé), fusion (score fusionné recalculé avec la version de référence, seuil tracé).
4. Le système affiche FAR et FRR au seuil courant, au niveau du score pour chaque modalité et pour la fusion, puis au niveau de la décision complète (RM-17.3), chacun avec son incertitude (**point N-5.14**).
5. Si les effectifs le permettent (RM-17.4), le système affiche l'EER du visage seul, de l'oreille seule et de la fusion, avec le seuil correspondant, ainsi que les courbes DET (**point N-5.14**).
6. Le système affiche à part, à titre descriptif, la distribution des scores des tentatives de production non étiquetées, par décision (acceptées, refusées) et par raison de refus, avec la mention « Décisions du système, pas une vérité terrain » (RM-17.2).

**Scénarios alternatifs et d'erreur**
- **A-17.1 Effectif insuffisant pour un indicateur** → l'indicateur est remplacé par « Données insuffisantes (légitimes : 12, imposteurs : 4 ; minimum : 30 de chaque) » ; les autres restent affichés.
- **A-17.2 Une seule classe disponible** (des légitimes seulement) → FRR affiché ; FAR et EER « Données insuffisantes ».
- **A-17.3 Période couvrant plusieurs versions de paramètres** → les scores fusionnés sont recalculés avec la version de référence choisie (RM-17.6) ; la répartition des tentatives selon la version réellement appliquée est indiquée.
- **A-17.4 Version de référence « non calibrée »** (RM-16.10) → bandeau « Paramètres non calibrés sur nos captures ».
- **A-17.5 Tentatives étiquetées « attaque »** → **point 33** — proposition : exclues du FAR, du FRR et de l'EER, qui mesurent des imposteurs sans artifice, et présentées à part (taux d'acceptation par type d'attaque, au sens de l'ISO/IEC 30107-3) ; rapport détaillé : UC-20.
- **A-17.6 Tentatives de comptes supprimés depuis** → **point 9** — proposition : conservées comme scores anonymes (étiquette, contexte, version, sans lien avec un compte), ce qui préserve les statistiques ; à valider au regard du droit à l'effacement.
- **E-17.1 Aucune donnée étiquetée sur la période** → « Aucune donnée étiquetée sur cette période. Les mesures de performance proviennent des tentatives étiquetées du laboratoire (UC-19) et du protocole d'évaluation (UC-21). » (formulation à ajuster selon le **point N-5.13**)
- **E-17.2 Période invalide** → comme E-15.1.
- **E-17.3 Calcul trop long** → « Le calcul n'a pas abouti. Réduisez la période et réessayez. »

**Règles métier**
- RM-17.1 — Un score n'entre dans une distribution « légitime » ou « imposteur » que s'il porte une étiquette de vérité terrain indépendante de la décision du système. La décision ne sert jamais d'étiquette : toutes les tentatives acceptées ont un score au-dessus du seuil, donc les tenir pour légitimes donnerait un FRR nul par construction et rangerait les imposteurs acceptés parmi les légitimes.
- RM-17.2 — Les tentatives de production sans étiquette n'alimentent qu'une vue descriptive, jamais un FAR, un FRR ni un EER.
- RM-17.3 — Deux niveaux d'indicateurs, toujours nommés à l'écran :
  1. **niveau score** — taux de fausse correspondance et de fausse non-correspondance (FMR / FNMR au sens de l'ISO/IEC 19795-1), au plancher pour chaque modalité et au seuil pour la fusion, calculés sur les tentatives qui ont un score ;
  2. **niveau décision** — part des imposteurs acceptés (FAR) et part des légitimes refusés pour quelque raison que ce soit (FRR : vivacité, qualité, plancher, seuil), calculées sur toutes les tentatives étiquetées.
- RM-17.4 — EER : taux au seuil où les deux erreurs du niveau score sont égales (interpolation entre deux seuils voisins), affiché avec ce seuil. Un taux n'est affiché que si l'effectif minimal du **point N-5.14** est atteint ; chaque indicateur affiche toujours son effectif.
- RM-17.5 — Les scores d'oreille de deux extracteurs différents ne sont jamais mélangés dans une même distribution ou un même calcul, pas plus que les scores fusionnés qui en dépendent : le tableau de bord porte sur un extracteur à la fois. Les scores visage sont communs à tous les extracteurs.
- RM-17.6 — Les scores fusionnés sont recalculés à partir des scores bruts journalisés (RM-15.6) avec une seule version de paramètres ; des scores fusionnés calculés sous des versions différentes ne sont jamais mélangés.
- RM-17.7 — Mélange laboratoire / production : **point 33**, en cohérence avec le **point N-5.13** ; les effectifs sont toujours ventilés par contexte.
- RM-17.8 — Le tableau de bord est en lecture seule ; les réglages passent par UC-16 et UC-18. Période par défaut : **point N-5.4**.

**Postcondition** : aucune modification ; indicateurs affichés avec leur source et leur effectif, ou « Données insuffisantes ».

---

## UC-18 — Choisir l'extracteur d'oreille actif

> **En tant qu'**administrateur, **je veux** choisir l'implémentation d'extraction de l'oreille utilisée pour les enrôlements et les décisions, **afin de** retenir la plus performante après évaluation sur nos propres captures, sans rendre inutilisables les gabarits déjà enregistrés.

- **Acteur principal** : Administrateur (ou Évaluateur, **point 31**)
- **Préconditions** : dispositions communes ; au moins deux extracteurs installés sur le serveur.
- **Déclencheur** : ouverture de la page « Extracteur d'oreille ».

**Scénario nominal**
1. Le système liste les extracteurs installés : identifiant et version (ex. LBP multi-échelles par blocs v1, DINOv2 small ONNX v1), statut (actif, disponible, indisponible), nombre d'utilisateurs `ENROLE` dont le gabarit d'oreille servant à la décision provient de cet extracteur, nombre d'utilisateurs disposant d'un gabarit pour cet extracteur (**point 22**), EER oreille et effectif issus d'UC-17, ou « non mesuré ».
2. L'administrateur choisit un extracteur candidat.
3. Le système vérifie que le candidat se charge et produit un descripteur de la dimension attendue.
4. Le système affiche l'analyse d'impact : utilisateurs qui basculent immédiatement (gabarit pour le candidat présent), utilisateurs sans gabarit compatible et ce qui leur arrivera (**point N-5.16**), version de paramètres de décision qui deviendra active (**point N-5.15**).
5. L'administrateur saisit le motif (**point N-5.3**) et confirme (**point N-5.2**).
6. Le système applique le changement de manière atomique : extracteur actif, version de paramètres associée, traitement des utilisateurs concernés (**point N-5.16**).
7. Le système journalise l'acte (RM-18.8).
8. Le système affiche « Extracteur actif : DINOv2 small ONNX v1, depuis 15 h 05. 12 utilisateurs ont basculé, 3 devront renouveler leur enrôlement. »

**Scénarios alternatifs et d'erreur**
- **A-18.1 Aucune performance mesurée pour le candidat** → avertissement « Aucune performance mesurée pour cet extracteur sur vos captures. » ; changement bloqué ou permis après confirmation explicite selon le **point N-5.16**.
- **A-18.2 Utilisateurs sans gabarit compatible** → traités selon le **point N-5.16**. S'ils doivent se ré-enrôler, leur authentification biométrique est refusée avec « Votre enrôlement doit être renouvelé : connectez-vous à votre espace compte pour vous ré-enrôler. », consigne reprise à leur connexion (UC-07). Ce refus ne compte pas comme un échec pour le verrouillage (**point 26** — proposition : le verrouillage sanctionne des tentatives, pas une décision de l'administrateur).
- **A-18.3 Retour à l'extracteur précédent** → même déroulé et même analyse d'impact : les utilisateurs enrôlés entre-temps avec le seul nouvel extracteur deviennent à leur tour incompatibles.
- **A-18.4 Enrôlement en cours au moment du changement** → la finalisation (UC-05) utilise l'extracteur actif au moment où elle commence, avec la version de paramètres de celui-ci.
- **A-18.5 Authentification en cours** → elle se termine avec l'extracteur et la version de paramètres lus à son début (RM-16.11).
- **E-18.1 Candidat indisponible** (fichier de modèle absent, échec de chargement, dimension inattendue) → « L'extracteur « … » ne peut pas être chargé. Aucun changement n'a été effectué. » ; statut « indisponible » dans la liste.
- **E-18.2 Candidat déjà actif** → « Cet extracteur est déjà actif. »
- **E-18.3 Aucune version de paramètres pour le candidat** (si le **point N-5.15** retient une lignée par extracteur) → « Aucun paramètre de décision n'existe pour cet extracteur. Définissez-les dans « Paramètres de décision » avant de l'activer. » (UC-16, A-16.6) ; repli possible sur une version « non calibrée » (RM-16.10).
- **E-18.4 Changement bloqué par la politique retenue** (**point N-5.16**, option a) → « 3 utilisateurs n'ont aucun gabarit pour cet extracteur : changement impossible tant qu'ils ne sont pas ré-enrôlés. », avec accès à la liste filtrée (UC-13).
- **E-18.5 Changement concurrent** → E-ADM.5.
- **E-18.6 Échec pendant l'application** → transaction annulée ; extracteur, paramètres et états des utilisateurs inchangés ; échec journalisé.

**Règles métier**
- RM-18.1 — Un seul extracteur d'oreille actif à la fois. Il sert à tous les nouveaux enrôlements (UC-05) et, pour la décision, selon le **point N-5.16**.
- RM-18.2 — Un extracteur est identifié par son nom et sa version. Toute modification de ses paramètres (rayons, voisinages et grille de blocs du LBP) ou de ses poids (fichier ONNX) produit un nouvel identifiant et constitue un changement d'extracteur.
- RM-18.3 — Un descripteur d'oreille n'est jamais comparé à un gabarit produit par un autre extracteur : les espaces de représentation sont incomparables. Faute de gabarit compatible, le système refuse la comparaison plutôt que de produire un score dénué de sens.
- RM-18.4 — Chaque gabarit d'oreille porte l'identifiant de l'extracteur qui l'a produit (UC-05, étape 6) ; chaque tentative journalise l'extracteur utilisé (RM-15.2).
- RM-18.5 — Le changement s'applique aux authentifications et aux finalisations d'enrôlement qui commencent après lui, jamais à une opération en cours.
- RM-18.6 — Plancher oreille, normalisation et seuil de fusion dépendent de la distribution des scores d'oreille, donc de l'extracteur ; rattachement des versions de paramètres aux extracteurs : **point N-5.15**.
- RM-18.7 — Révocation (UC-11, UC-14) et suppression (UC-12, UC-14) détruisent tous les gabarits d'oreille de l'utilisateur, quel que soit l'extracteur.
- RM-18.8 — Journalisation (RM-ADM.4) : auteur, date, ancien et nouvel extracteur, motif, version de paramètres activée, nombre d'utilisateurs basculés et nombre d'utilisateurs devant renouveler leur enrôlement.
- RM-18.9 — Qui décide : **point 31** (administrateur seul, ou aussi l'évaluateur).
- RM-18.10 — Hors périmètre : installer un nouvel extracteur (implémentation future) relève du déploiement sur le serveur ; l'interface choisit parmi les extracteurs installés et ne permet pas de téléverser un modèle.

**Postcondition** : nouvel extracteur actif avec sa version de paramètres, utilisateurs concernés basculés ou invités à renouveler leur enrôlement, acte journalisé ; ou aucun changement.

---

## Nouveaux points à trancher (section 5)

### N-5.1 — Fuseau d'affichage des horodatages
- **Question** : en quelle heure afficher les horodatages, stockés en UTC (RM-ADM.7) ?
- **Options** : (a) UTC ; (b) heure du Bénin (UTC+1, sans heure d'été) ; (c) fuseau du navigateur.
- **Recommandation** : (b), avec la mention « UTC+1 » à l'écran, et l'UTC au format ISO 8601 dans les exports. Volontaires, administrateur et jury sont au Bénin et l'absence d'heure d'été écarte toute ambiguïté, alors que (c) ferait varier une même capture d'écran selon le poste.

### N-5.2 — Confirmation forte des actes sensibles
- **Question** : en quoi consiste la « confirmation forte », et l'administrateur doit-il se ré-authentifier ?
- **Options** : (a) simple boîte de confirmation ; (b) ressaisie de l'email de la cible ; (c) ressaisie du mot de passe de l'administrateur ; (d) authentification biométrique de l'administrateur (UC-08) juste avant l'acte.
- **Recommandation** : suppression : (b) + (c) ; révocation, paramètres de décision et extracteur : (c) ; déverrouillage : (a). Une session administrateur dérobée (onglet resté ouvert, cookie volé) ne doit pas suffire pour effacer des comptes ou affaiblir la politique de décision ; (d) serait cohérent avec le sujet mais suppose un administrateur enrôlé : extension possible.

### N-5.3 — Motif des actes administratifs
- **Question** : le motif est-il obligatoire, et sous quelle forme ?
- **Options** : (a) facultatif ; (b) obligatoire, texte libre ; (c) obligatoire, choisi dans une liste propre à chaque action (ex. « demande de l'utilisateur », « compromission suspectée », « fin de participation au protocole », « test », « autre »), avec une précision libre exigée pour « autre ».
- **Recommandation** : (c), précision limitée à 500 caractères sous l'avertissement « N'indiquez aucune donnée sensible ». La liste rend le journal exploitable ; et comme le motif survit à la suppression du compte visé, il ne doit pas devenir un dépôt de données personnelles.

### N-5.4 — Réglages d'ergonomie des listes et des vues
- **Question** : tailles de page, tris et périodes par défaut, colonnes condensées, filtres supplémentaires.
- **Options** : les valeurs proposées ci-dessous, ou d'autres.
- **Recommandation** : 25 lignes par page (10, 25, 50 ou 100 au choix) ; utilisateurs triés par date de création décroissante ; journal trié du plus récent au plus ancien sur les 7 derniers jours, vue condensée réduite à horodatage, utilisateur revendiqué, contexte, décision, raison et score fusionné ; filtres supplémentaires « version des paramètres » et « extracteur » dans le journal ; tableau de bord et aperçu d'UC-16 sur toute la période disponible, les données étiquetées étant rares. Choix sans enjeu de sécurité ; les deux filtres supplémentaires servent à comparer l'avant et l'après d'un réglage.

### N-5.5 — Gestion des rôles depuis l'interface
- **Question** : peut-on promouvoir ou rétrograder un compte (`utilisateur`, `evaluateur`, `admin`) depuis l'espace d'administration ?
- **Options** : (a) non en v1 : rôles attribués par une commande sur le serveur, comme le premier administrateur (**point 5**) ; (b) action « Changer le rôle » dans UC-14, sous les protections RM-14.6 et RM-14.7.
- **Recommandation** : (a). La v1 compte un ou deux administrateurs, et un mot de passe administrateur volé ne permet alors pas de créer d'autres administrateurs. RM-14.6 et RM-14.7 s'appliquent aussi à la commande serveur.

### N-5.6 — Actions sur un autre administrateur ou sur soi-même
- **Question** : un administrateur voit-il les autres administrateurs, et peut-il agir sur eux ou sur son propre compte via UC-14 ?
- **Options** : (a) visibles, aucune action possible sur un administrateur ; (b) visibles, toutes actions sauf sur soi ; (c) visibles ; déverrouillage et révocation autorisés, suppression interdite depuis l'interface ; sur soi-même, renvoi vers UC-11 et UC-12.
- **Recommandation** : (c). Déverrouiller ou révoquer un collègue répond à un blocage ou à une compromission ; interdire la suppression empêche un compte administrateur compromis d'évincer les autres. Agir sur soi passe par le parcours ordinaire, soumis à RM-14.6.

### N-5.7 — Information de l'utilisateur visé
- **Question** : l'utilisateur est-il informé d'une révocation, d'une suppression ou d'un déverrouillage décidé par un administrateur ?
- **Options** : (a) non ; (b) message affiché à sa prochaine connexion (UC-07) ; (c) email ; (d) (b) pour la révocation et le déverrouillage, (c) pour la suppression.
- **Recommandation** : (d) si l'application envoie des emails (**point 1**) ; sinon (b), et pour une suppression, information hors application par le responsable de traitement (**point 8**), puisqu'un compte supprimé ne peut plus afficher de message. Le droit à l'information de la personne le justifie ; seule la catégorie du motif est communiquée, jamais la précision libre.

### N-5.8 — Organisation des journaux consultables
- **Question** : comment présenter le journal des tentatives (UC-08), celui des accès à la base protégée (UC-10) et celui des actes d'administration ?
- **Options** : (a) trois écrans séparés ; (b) un écran « Journaux » à trois onglets partageant le filtre de période ; (c) une chronologie unique mêlant tout.
- **Recommandation** : (b), avec un lien dans les deux sens entre une tentative acceptée et les accès faits avec le JWT qu'elle a délivré. Ce lien répond directement à « qui a accédé, quand, avec quels scores et quelle décision » ; (c) noierait les tentatives dans les accès.

### N-5.9 — Export des journaux et traçabilité des consultations
- **Question** : peut-on exporter le journal, et quelles consultations ou tentatives d'accès faut-il journaliser ?
- **Options** : export : (a) aucun ; (b) CSV de la vue filtrée, emails en clair ; (c) CSV de la vue filtrée, comptes désignés par leur identifiant interne. Traçabilité : (d) exports seulement ; (e) exports, refus HTTP 403 de l'espace d'administration et requêtes d'écriture sur le journal ; (f) toute consultation.
- **Recommandation** : (c) + (e), avec un plafond de 10 000 lignes, des horodatages UTC en ISO 8601 et la neutralisation des cellules commençant par =, +, - ou @ (injection de formules à l'ouverture dans un tableur). L'export sert aux analyses du mémoire sans faire sortir d'identités ; journaliser chaque affichage (f) produirait surtout du bruit. Le rapport d'attaques reste l'objet d'UC-20.

### N-5.10 — Intégrité du journal
- **Question** : comment montrer qu'aucune entrée n'a été modifiée ou supprimée, y compris directement dans la base ?
- **Options** : (a) droits de base de données seulement (le compte applicatif ne peut qu'insérer et lire) ; (b) (a) + chaînage : chaque entrée contient l'empreinte de la précédente, et une action « Vérifier l'intégrité » signale toute rupture ; (c) (b) + publication périodique de la dernière empreinte hors du serveur.
- **Recommandation** : (b), peu coûteux et démontrable en soutenance (une ligne modifiée à la main fait apparaître la rupture). Les purges du **point 9** doivent laisser une entrée de reprise portant l'empreinte de la dernière entrée purgée, faute de quoi elles casseraient la chaîne.

### N-5.11 — Échelle des planchers
- **Question** : les planchers portent-ils sur le score brut (similarité dans [0 ; 1]) ou sur le score normalisé (z-score) ?
- **Options** : (a) score brut ; (b) score normalisé.
- **Recommandation** : (a). Un plancher est un garde-fou absolu (« cette modalité ressemble au moins à ce point »), lisible par un jury, naturellement borné dans [0 ; 1], et il garde son sens quand la normalisation est recalculée (**point 23**).

### N-5.12 — Dérivation du seuil de fusion à partir du FAR cible
- **Question** : effectif minimal de scores imposteurs, traitement des égalités, figement du seuil, repli, cas sans données légitimes.
- **Options** : effectif : (a) minimum fixe ; (b) au moins ⌈3 / FAR cible⌉ scores imposteurs (règle de 3 : aucune fausse acceptation sur N essais borne le FAR à 3/N avec 95 % de confiance), soit 300 pour 1 % et 3 000 pour 0,1 %. Figement : (c) seuil calculé à l'activation et figé dans la version ; (d) seuil recalculé en continu.
- **Recommandation** : (b) + (c). Le seuil est la plus petite valeur t telle que la part des scores imposteurs ≥ t ne dépasse pas le FAR cible (acceptation si score ≥ t) ; il est calculé sur tous les scores imposteurs sans tenir compte des planchers (choix prudent : les planchers ne peuvent que réduire le FAR réel). Figé, il rend chaque décision reproductible à partir de sa version. Sous l'effectif minimal, repli sur une version « non calibrée » (**points 24 et 36**) ; sans donnée légitime, application permise avec l'avertissement « FRR inconnu ». Le FAR estimé sur les scores mêmes qui ont servi à dériver le seuil est optimiste : dès que l'effectif le permet, dériver sur une moitié et estimer sur l'autre. Avec 10 à 15 volontaires, quelques centaines à un millier de scores imposteurs sont réalistes : un FAR cible nettement inférieur à 1 % ne sera pas vérifiable.

### N-5.13 — Source de la vérité terrain (UC-16, UC-17)
- **Question** : d'où viennent les étiquettes « légitime » et « imposteur », alors qu'en production la vérité d'une tentative est inconnue ?
- **Options** :
  - (a) seulement les tentatives étiquetées du laboratoire (UC-19) et du protocole d'évaluation (UC-21) ;
  - (b) scores imposteurs générés en comparant chaque capture authentifiée aux gabarits des autres utilisateurs, en deux variantes :
    - (b1) BioHash de la capture calculé avec le jeton de son porteur et comparé au gabarit d'un autre utilisateur, protégé par un autre jeton. Les deux projections étant indépendantes, la similarité tourne autour de 0,5 quelle que soit la ressemblance des personnes : séparation artificielle et EER quasi nul, donc trompeur (critique classique de BioHashing, Kong et al., 2006) ;
    - (b2) scénario « jeton volé » : la capture est projetée avec le jeton de la cible, puis comparée au gabarit de celle-ci ; le score reflète alors la ressemblance biométrique réelle. C'est le pire cas honnête, et c'est précisément ce que subit le système lors d'une vraie tentative imposteur si les jetons sont conservés côté serveur (**point 19**). Contraintes : le vecteur en clair n'existe qu'en mémoire pendant la tentative (RM-05.5), donc ces scores doivent être calculés sur le moment, en déchiffrant des gabarits tiers, et stockés à part comme « imposteurs simulés » ; en production, cela élargit l'exposition des gabarits et dépasse la finalité d'authentification consentie ;
  - (c) étiquetage a posteriori : l'utilisateur confirme « c'était moi » pour un refus ou signale « ce n'était pas moi » pour un succès, l'administrateur étiquette selon le contexte. Étiquettes déclaratives, rares et biaisées (un imposteur ne s'étiquette jamais) ; UC-06 devrait alors détailler les tentatives.
- **Recommandation** : (a) + (b2) limité aux sessions du laboratoire et du protocole, ou recalculé hors ligne sur les images « recherche » si le **point 21** est retenu (ce qui permet aussi de comparer les deux extracteurs pour UC-18) ; (b1) exclu ; (c) seulement comme signal d'alerte, jamais pour les statistiques. Ces tentatives sont des captures réelles faites sur la plateforme réelle par les volontaires : l'exigence « calculés sur les tentatives réelles » est tenue sans raisonnement circulaire, et la production reste visible dans la vue descriptive (RM-17.2).

### N-5.14 — Effectifs minimaux et incertitude affichée
- **Question** : à partir de quels effectifs afficher FAR, FRR, EER et courbes DET, et faut-il afficher une incertitude ?
- **Options** : (a) toujours afficher ; (b) seuil fixe d'effectif ; (c) (b) + intervalle de confiance à 95 % sur chaque taux.
- **Recommandation** : (c) : au moins 30 scores légitimes et 30 scores imposteurs (seuil pragmatique), intervalle de Wilson sur FAR et FRR, taux nul affiché « < 3/N », courbes DET dès que l'EER est affiché. La « règle de 30 » de Doddington (30 erreurs observées pour une précision de ± 30 %) montre qu'avec ces effectifs des taux de quelques pourcents resteront imprécis ; de plus, les tentatives d'une même personne ne sont pas indépendantes, donc les intervalles sont optimistes : le nombre de comptes distincts figure à côté de chaque effectif.

### N-5.15 — Paramètres de décision et extracteur d'oreille
- **Question** : un seul jeu de paramètres pour tout le système, ou un par extracteur ?
- **Options** : (a) jeu unique, à revalider à chaque changement d'extracteur ; (b) une lignée de versions par extracteur, la version active étant celle de l'extracteur actif ; (c) jeu unique pour le visage, jeu par extracteur pour l'oreille.
- **Recommandation** : (b). Plancher oreille, normalisation de l'oreille et donc seuil de fusion dépendent de l'extracteur : avec (a), des valeurs calibrées pour le LBP s'appliqueraient aux scores ONNX dès la bascule ; (c) n'apporte rien puisque le seuil de fusion dépend des deux modalités.

### N-5.16 — Bascule d'extracteur quand des utilisateurs sont déjà enrôlés
- **Question** : que faire des utilisateurs dont le gabarit d'oreille provient de l'ancien extracteur, et peut-on activer un extracteur dont la performance n'a pas été mesurée ?
- **Options** : (a) bloquer le changement tant qu'un utilisateur `ENROLE` n'a pas de gabarit pour le candidat ; (b) imposer le ré-enrôlement des utilisateurs concernés, par révocation automatique ou par un nouvel état d'enrôlement « à renouveler » (à formaliser à l'étape 2) ; (c) basculer les utilisateurs qui ont les deux gabarits (**point 22**), les autres relevant de (a), (b) ou (d) ; (d) extracteur par utilisateur : chacun reste décidé avec l'extracteur de son gabarit, l'extracteur « actif » ne gouvernant que les nouveaux enrôlements.
- **Recommandation** : deux gabarits pendant la phase d'évaluation (**point 22**), puis (c) + (b) avec l'état « à renouveler » plutôt qu'une révocation : les anciens gabarits restent intacts, et un retour à l'ancien extracteur (A-18.3) rend ces utilisateurs de nouveau opérationnels sans rien refaire. (a) seul figerait le système dès le premier enrôlé ; (d) multiplie les jeux de paramètres actifs et brouille le tableau de bord. Extracteur non mesuré : activation permise avec confirmation explicite pendant le développement, interdite une fois le protocole d'évaluation (UC-21) commencé.
