# 4. Maîtrise de ses données par l'utilisateur (UC-11 et UC-12)

> Statut : **BROUILLON v1 — en attente de validation**.

---

## UC-11 — Révoquer ses gabarits et se ré-enrôler

> **En tant qu'**utilisateur enrôlé, **je veux** faire détruire mes gabarits et mon jeton actuels puis m'enrôler de nouveau, **afin de** rendre inutilisable un gabarit ou un jeton que je crois compromis, ou de retrouver une reconnaissance fiable après un changement d'apparence ou des échecs répétés.

- **Acteur principal** : Utilisateur enrôlé (il redevient titulaire de compte dès la révocation, puis utilisateur enrôlé à la fin du ré-enrôlement)
- **Préconditions** : session « compte » active (UC-07) ; enrôlement `ENROLE` ; consentement `ACCORDE` ; aucune session d'enrôlement ouverte pour ce compte (E-11.3).
- **Déclencheur** : clic sur « Révoquer et me ré-enrôler » depuis la page « Mes données » (UC-06). Motifs typiques : suspicion de vol du jeton ou de la base, changement d'apparence, échecs d'authentification répétés.

**Scénario nominal**
1. Le système affiche les conséquences de la révocation : destruction définitive des gabarits visage et oreille et du jeton actuels, fin immédiate de tout accès à la base protégée, nécessité d'un ré-enrôlement complet (visage puis oreille) pour le retrouver.
2. L'utilisateur indique le motif de sa demande (**point N-4.2** — proposition : facultatif, choisi dans une liste).
3. L'utilisateur prouve son identité (**point N-4.1** — proposition : ressaisie du mot de passe **et** authentification biométrique réussie, UC-08 ; voie de secours en A-11.1).
4. Le système vérifie cette preuve (RM-11.1).
5. Dans une transaction unique (RM-11.2), le système supprime physiquement les gabarits chiffrés et l'ancien jeton, passe l'enrôlement à `REVOQUE` et ajoute l'événement de révocation au journal (horodatage UTC, initiateur, motif ; aucune donnée biométrique, aucun jeton).
6. Le système invalide immédiatement tous les jetons d'accès biométriques (JWT) émis pour ce compte, y compris celui délivré à l'étape 3 le cas échéant (RM-11.4).
7. Le système affiche « Vos anciens gabarits et votre ancien jeton ont été détruits. Pour accéder de nouveau à la base protégée, ré-enrôlez-vous : la procédure reprend la capture du visage puis de l'oreille. » et propose « Me ré-enrôler maintenant ».
8. L'utilisateur effectue l'enrôlement complet UC-03 → UC-04 → UC-05, sous les mêmes règles qu'un premier enrôlement (RM-11.6) ; UC-05 génère un **nouveau** jeton (RM-11.5).
9. L'enrôlement repasse à `ENROLE` ; l'événement de ré-enrôlement est journalisé et rattaché à la révocation qui le précède.

**Scénarios alternatifs et d'erreur**
- **E-11.1 Preuve d'identité refusée** (mot de passe incorrect ou authentification biométrique échouée) → rien n'est détruit, « Vérification d'identité échouée : vos gabarits n'ont pas été modifiés. Vérifiez votre mot de passe ; si la reconnaissance biométrique ne fonctionne plus, utilisez la procédure de secours. » Un échec biométrique compte comme une tentative ordinaire pour le verrouillage (UC-09) : sinon, l'écran de révocation permettrait d'essayer des présentations sans limite.
- **E-11.2 Aucun gabarit actif** (enrôlement `NON_ENROLE` ou déjà `REVOQUE`) → l'action n'est pas proposée ; une requête directe est refusée, « Vous n'avez aucun gabarit actif à révoquer. Lancez directement l'enrôlement depuis la page Mes données. »
- **E-11.3 Enrôlement déjà en cours pour ce compte** (autre onglet ou autre appareil, typiquement juste après une première révocation) → refus, l'enrôlement en cours n'est pas interrompu, « Un enrôlement est déjà en cours pour votre compte. Terminez-le ou attendez son expiration, puis réessayez. Si vous n'êtes pas à l'origine de cet enrôlement, contactez l'administrateur. » Les accès concurrents entre révocation et finalisation sont exclus par RM-11.7.
- **E-11.4 Échec de la destruction** (erreur de base de données, arrêt du service pendant l'opération) → transaction annulée : enrôlement toujours `ENROLE`, gabarits et jeton intacts, aucun état intermédiaire possible (gabarit sans jeton, jeton sans gabarit, état `REVOQUE` avec un gabarit restant). Message : « La révocation n'a pas pu aboutir : vos gabarits actuels sont toujours actifs. Réessayez dans quelques instants ; si le problème persiste, contactez l'administrateur. » Erreur technique journalisée sans donnée biométrique.
- **E-11.5 Échec du ré-enrôlement** (qualité, vivacité, délai ou extraction : E-03.x, E-04.x, E-05.x) → l'état reste `REVOQUE` ; l'ancien gabarit n'est jamais restauré ; l'utilisateur recommence dans les limites du **point 14**. Si la clé maîtresse est indisponible (E-05.2), le ré-enrôlement attend sa remise en service ; la destruction elle-même n'en dépend pas, puisqu'elle n'exige aucun déchiffrement.
- **A-11.1 Biométrie inutilisable** (changement d'apparence, échecs répétés, compte verrouillé par UC-09) → voie de secours du **point N-4.1** (proposition : mot de passe + code à usage unique envoyé par email si le point 1 est retenu, sinon demande validée par un administrateur via UC-14). La révocation ne lève pas un verrouillage en cours et ne remet pas à zéro le compteur d'échecs (**point 26** — proposition), pour ne pas servir à contourner UC-09.
- **A-11.2 Révocation sans ré-enrôlement** (abandon après l'étape 7, ou aucun retour) → état stable `REVOQUE`, sans échéance propre (conservation d'un compte sans gabarit : **point N-4.7**). Toute authentification biométrique (UC-08) échoue et la base protégée (UC-10) reste inaccessible ; le message affiché sur l'écran public d'authentification relève du **point 27** (proposition : ne pas y révéler l'état « révoqué », indiqué seulement dans la page « Mes données »). La session « compte » reste utilisable pour UC-06, UC-02, UC-12 et pour lancer le ré-enrôlement à tout moment.
- **A-11.3 Motif « suspicion de compromission de la base »** → en plus de la révocation individuelle, l'administrateur est alerté (**point N-4.2**). La rotation de la clé maîtresse (**point N-7.3**) et une révocation collective relèvent de l'administration (UC-14), pas de ce cas d'utilisation.
- **A-11.4 Nouvelle version du texte de consentement entre-temps** → le consentement est redemandé avant l'étape 8 (A-02.3) ; un refus vaut retrait (A-02.2) et l'enrôlement reste fermé.
- **A-11.5 Révocation à l'initiative d'un administrateur** (UC-14) → mêmes effets techniques (étapes 5 et 6), initiateur `administrateur` au journal ; l'utilisateur découvre l'état `REVOQUE` dans « Mes données » et, selon le **point N-4.6**, par email.

**Règles métier**
- RM-11.1 — Preuve d'identité préalable : **point N-4.1** — proposition : ressaisie du mot de passe et authentification biométrique réussie depuis moins de 5 minutes, avec la voie de secours d'A-11.1. Une session « compte » déjà ouverte ne suffit jamais à elle seule : sinon, quiconque trouve une session laissée ouverte pourrait remplacer la biométrie du titulaire par la sienne.
- RM-11.2 — Destruction effective : dans une seule transaction, suppression physique de tous les gabarits du compte (visage, oreille et, le cas échéant, second gabarit d'oreille du **point 22**) et de l'ancien jeton, passage à `REVOQUE` et journalisation. Un drapeau « révoqué » ou « inactif » laissant le gabarit en base n'est pas conforme au brief. Les copies résiduelles hors de la base active (espace disque non encore réutilisé par PostgreSQL, sauvegardes) restent chiffrées en AES-256-GCM et disparaissent avec la rotation des sauvegardes (**point N-7.6**).
- RM-11.3 — Ancien jeton : s'il est détenu côté utilisateur (**point 19**), sa destruction côté serveur signifie qu'il n'est plus accepté nulle part ; l'utilisateur est invité à détruire son ancien support.
- RM-11.4 — Tous les JWT d'accès biométrique émis avant la révocation sont invalidés immédiatement (mécanisme : **point 4**). La session « compte » courante est conservée pour permettre le ré-enrôlement ; sort des autres sessions « compte » du même titulaire : **point 4** — proposition : fermées.
- RM-11.5 — Le nouveau jeton est généré par UC-05 (étape 3) au moment du ré-enrôlement, aléatoirement et indépendamment de l'ancien : jamais dérivé de lui, jamais réutilisé. Entre la révocation et le ré-enrôlement, le compte n'a aucun jeton.
- RM-11.6 — Le ré-enrôlement est un enrôlement complet : mêmes contrôles de qualité, de vivacité, de cohérence et d'atomicité (UC-03 à UC-05) ; rien n'est repris de l'ancien enrôlement ; l'extracteur d'oreille est celui qui est actif au moment du ré-enrôlement (UC-18) et peut différer de l'ancien.
- RM-11.7 — La destruction précède le ré-enrôlement (RM-03.6). L'absence d'accès biométrique entre les deux est voulue : un gabarit suspecté compromis ne doit pas rester utilisable pendant le ré-enrôlement. La révocation et la finalisation d'un enrôlement (UC-05) d'un même compte ne s'exécutent jamais simultanément, de sorte qu'aucun gabarit ne peut être finalisé avec un jeton détruit entre-temps.
- RM-11.8 — Révocabilité : un BioHash calculé sur le même visage (ou la même oreille) avec le nouveau jeton doit être non corrélé à l'ancien ; un ancien gabarit dérobé, même déchiffré, ne doit pas produire plus de correspondances avec le nouveau que le gabarit d'une autre personne. Cette propriété (renouvelabilité et non-corrélation au sens de la norme ISO/IEC 24745) est vérifiée hors production, l'ancien gabarit n'existant plus en production : par un test automatisé et dans le protocole d'évaluation (UC-21) ; c'est aussi un scénario candidat du laboratoire d'attaques (UC-19, **point 32**). Critère chiffré : **point 20** — proposition : distance de Hamming normalisée moyenne entre ancien et nouveau BioHash d'une même personne comprise entre 0,45 et 0,55, et distribution de ces distances non distinguable de celle des comparaisons entre personnes différentes.
- RM-11.9 — Révocation et retrait du consentement sont distincts : la révocation laisse le consentement `ACCORDE` en vue du ré-enrôlement ; le retrait (A-02.2) détruit aussi les gabarits mais ferme l'enrôlement.
- RM-11.10 — Révocation et ré-enrôlement sont journalisés (horodatage UTC, initiateur, motif, résultat), sans gabarit, jeton ni donnée biométrique (RT-18).

**Postcondition** : les anciens gabarits et l'ancien jeton n'existent plus dans la base active et aucun JWT émis avant la révocation n'est valide ; l'enrôlement est soit `ENROLE` avec de nouveaux gabarits non corrélés aux anciens, soit `REVOQUE` de façon stable (A-11.2).

---

## UC-12 — Supprimer son compte (droit à l'effacement)

> **En tant que** titulaire de compte, **je veux** supprimer définitivement mon compte et les données qui me concernent, **afin d'**exercer mon droit à l'effacement.

- **Acteur principal** : Titulaire de compte, quel que soit son état de consentement et d'enrôlement (utilisateur enrôlé et administrateur compris, pour leur propre compte)
- **Préconditions** : session « compte » active (UC-07).
- **Déclencheur** : clic sur « Supprimer mon compte » depuis la page « Mes données » (UC-06), ou enchaînement après un refus de consentement (A-02.1) ou un retrait si le **point 7** retient la suppression du compte entier.

**Scénario nominal**
1. Le système affiche un récapitulatif : données qui seront effacées (RM-12.3 a), éléments conservés sous forme non directement identifiante avec leur durée et leur justification (RM-12.3 b), caractère immédiat et définitif de l'opération (**point N-4.4**), possibilité de se réinscrire plus tard avec la même adresse.
2. Le titulaire ressaisit son mot de passe, tape le mot de confirmation (**point N-4.3** — proposition : « SUPPRIMER ») puis clique sur « Supprimer définitivement mon compte ».
3. Le système vérifie le mot de passe et le mot de confirmation, puis s'assure que le titulaire n'est pas le dernier administrateur (RM-12.7).
4. Dans une transaction unique (RM-12.4), le système :
   - supprime physiquement le compte, les gabarits, le jeton et les autres données de RM-12.3 a ;
   - réduit l'historique des consentements à l'enregistrement minimal du **point N-4.5** ;
   - détruit la correspondance entre le compte et son pseudonyme de journal, ce qui rend les entrées existantes non rattachables sans les modifier (**point 9**, RT-17) ;
   - invalide toutes les sessions « compte » et tous les JWT du compte (mécanisme : **point 4**) ;
   - ajoute au journal l'événement « suppression de compte » (pseudonyme, horodatage UTC, initiateur `utilisateur`).
5. Le système détruit toute session d'enrôlement encore ouverte pour ce compte et en purge la mémoire (A-12.1).
6. Le système ferme la session et affiche l'accusé de suppression (RM-12.9) : « Votre compte et vos données biométriques ont été supprimés le [date] à [heure]. Vous pouvez vous réinscrire à tout moment avec la même adresse : il s'agira d'un nouveau compte. »
7. L'adresse email est immédiatement disponible pour une nouvelle inscription (UC-01).

**Scénarios alternatifs et d'erreur**
- **E-12.1 Mot de passe incorrect** → rien n'est effacé, « Mot de passe incorrect : votre compte n'a pas été supprimé. » Les échecs répétés sont limités comme à la connexion (UC-07, **point 26**).
- **E-12.2 Mot de confirmation absent ou erroné** → le bouton de suppression reste inactif ; une requête directe est refusée, « Saisissez SUPPRIMER pour confirmer la suppression. »
- **E-12.3 Dernier administrateur** → refus, rien n'est effacé, « Vous êtes le dernier administrateur : supprimer ce compte rendrait la plateforme inadministrable. Un autre compte doit d'abord recevoir le rôle administrateur ; recommencez ensuite. » Attribution du rôle administrateur : **point 5**.
- **E-12.4 Échec technique pendant l'effacement** → transaction annulée, aucune donnée effacée, sessions intactes, « La suppression n'a pas pu aboutir et aucune donnée n'a été effacée. Réessayez dans quelques instants ; si le problème persiste, contactez l'administrateur. » Erreur journalisée sans donnée personnelle.
- **E-12.5 Session « compte » expirée pendant la confirmation** → redirection vers UC-07, rien n'est effacé, « Votre session a expiré : reconnectez-vous pour confirmer la suppression. »
- **A-12.1 Enrôlement en cours** (autre onglet ou appareil) → contrairement à la révocation (E-11.3), la suppression l'emporte : la session d'enrôlement est détruite et sa finalisation devient impossible (même exclusivité que RM-11.7).
- **A-12.2 Compte non enrôlé, révoqué ou sans consentement** → même scénario ; les catégories de données absentes sont simplement ignorées.
- **A-12.3 Compte verrouillé** (UC-09) → la suppression reste possible dès lors que la session « compte » est accessible pendant le verrouillage (**point 26**) : elle n'exige aucune authentification biométrique (RM-12.1).
- **A-12.4 Délai de grâce** (si le **point N-4.4** retient cette option) → gabarits et jeton sont détruits immédiatement dans tous les cas ; le reste du compte est désactivé puis effacé à l'échéance ; une reconnexion avant l'échéance annule la suppression et le compte repart `NON_ENROLE`.
- **A-12.5 Accusé par email** (si le **point N-4.6** le retient) → l'adresse n'est utilisée que pour cet unique envoi, puis n'est plus conservée.
- **A-12.6 Ré-inscription ultérieure avec la même adresse** → UC-01 nominal ; le nouveau compte ne récupère rien de l'ancien (ni consentement, ni gabarit, ni historique visible dans UC-06) ; l'enregistrement minimal de consentement (**point N-4.5**) ne sert jamais à relier les deux comptes.
- **A-12.7 Suppression par un administrateur** (UC-14) → mêmes effets (étapes 4 et 5), initiateur `administrateur` au journal.
- **A-12.8 Administrateur qui n'est pas le dernier** → suppression autorisée ; ses actions passées (réglages des seuils, révocations, suppressions) restent au journal sous son pseudonyme.

**Règles métier**
- RM-12.1 — Le droit à l'effacement est ouvert à tout titulaire, quel que soit son état de consentement ou d'enrôlement, et ne dépend jamais d'une authentification biométrique : une personne qui a refusé le consentement, révoqué ses gabarits ou changé d'apparence doit pouvoir partir.
- RM-12.2 — Confirmation forte : **point N-4.3** — proposition : ressaisie du mot de passe + saisie du mot « SUPPRIMER ».
- RM-12.3 — Périmètre de l'effacement :
  - a. **Effacé physiquement** : nom, email, hachage du mot de passe, rôle ; gabarits chiffrés de toutes les modalités et de tous les extracteurs (**point 22**) ; jeton (**point 19**) ; sessions « compte », JWT et sessions d'enrôlement ; compteurs d'échecs et état de verrouillage ; adresse IP enregistrée lors du consentement ; images « recherche », pseudonyme de volontaire et scores individuels d'évaluation (**point 21** — proposition : effacés avec le compte) ; correspondance entre le compte et son pseudonyme de journal.
  - b. **Conservé sous forme non directement identifiante** : enregistrement minimal de l'historique des consentements (**point N-4.5**, qui résout la contradiction apparente entre RM-02.4 et l'effacement) ; entrées du journal, devenues non rattachables (**point 9**) ; sauvegardes, jusqu'à leur rotation (**point N-7.6**) ; résultats agrégés d'évaluation déjà calculés, qui ne contiennent aucune donnée individuelle.
- RM-12.4 — Effacement atomique : tout le périmètre de RM-12.3 a, ou rien. Jamais de gabarit, de jeton ni d'image « recherche » orphelin d'un compte supprimé.
- RM-12.5 — Effet : **point N-4.4** — proposition : immédiat et irréversible. Quel que soit le choix, gabarits et jeton sont détruits immédiatement, comme lors d'un retrait de consentement (A-02.2).
- RM-12.6 — Toutes les sessions « compte » et tous les JWT du compte sont invalidés au moment de la suppression (mécanisme : **point 4**).
- RM-12.7 — Le dernier administrateur ne peut pas supprimer son propre compte : la plateforme conserve toujours au moins un compte administrateur.
- RM-12.8 — La ré-inscription avec la même adresse est autorisée ; l'adresse n'est plus conservée en clair après la suppression (seule une empreinte à clé peut subsister, **point N-4.5**).
- RM-12.9 — Un accusé de suppression est toujours affiché : date et heure, catégories effacées, catégories conservées avec leur durée et leur justification ; aucune donnée biométrique. Envoi par email : **point N-4.6**.
- RM-12.10 — Un éventuel enregistrement résiduel (**point N-4.5**) ne contient ni nom ni email en clair. L'état `SUPPRIME` (§1.3) ne qualifie que cet enregistrement résiduel ou, si le **point N-4.4** retient un délai de grâce, le compte en attente de purge.
- RM-12.11 — La suppression est journalisée sous le pseudonyme du compte, avec l'initiateur ; jamais avec le nom ou l'email (RT-18).

**Postcondition** : hors délai de grâce (A-12.4), la base active ne contient plus aucune donnée biométrique ni aucune donnée directement identifiante de la personne ; l'adresse email est libre ; seuls subsistent les éléments de RM-12.3 b.

---

## Nouveaux points à trancher (section 4)

### N-4.1 — Preuve d'identité exigée avant une révocation (UC-11)
- **Question** : que doit fournir l'utilisateur, en plus de sa session « compte », pour révoquer ses gabarits ?
- **Options** :
  - (a) ressaisie du mot de passe seule : possible dans tous les cas, mais quiconque connaît le mot de passe peut détruire les gabarits du titulaire puis enrôler son propre visage à sa place (prise de contrôle de l'identité biométrique) ;
  - (b) authentification biométrique seule (UC-08) : impossible précisément quand le motif est un changement d'apparence ou des échecs répétés ;
  - (c) les deux, toujours : la plus sûre, mais bloque les mêmes cas que (b) ;
  - (d) les deux quand la biométrie fonctionne ; sinon mot de passe + voie de secours : code à usage unique envoyé par email si le point 1 est retenu, à défaut validation de la demande par un administrateur (UC-14).
- **Recommandation** : (d). C'est la seule option qui couvre tous les motifs sans permettre à un simple voleur de mot de passe de substituer sa biométrie à celle du titulaire ; le risque résiduel (vol simultané du mot de passe et de la boîte mail) est à documenter dans le rapport.

### N-4.2 — Motif de révocation et suites données (UC-11)
- **Question** : demande-t-on un motif, et un motif déclenche-t-il une action particulière ?
- **Options** : (a) aucun motif ; (b) motif facultatif choisi dans une liste (vol ou perte du jeton, suspicion de compromission de la base, changement d'apparence, échecs répétés, autre), enregistré au journal ; (c) même liste, motif obligatoire.
- **Recommandation** : (b), le motif « suspicion de compromission de la base » déclenchant en plus une alerte visible dans le tableau de bord administrateur (UC-17), car une fuite de la base concerne tous les utilisateurs et appelle une rotation de clé (**point N-7.3**) qu'un utilisateur ne peut pas déclencher. Les motifs alimentent aussi l'analyse du mémoire (part des révocations dues au changement d'apparence).

### N-4.3 — Forme de la confirmation de suppression (UC-12)
- **Question** : quelle confirmation exiger avant d'effacer un compte ?
- **Options** : (a) un simple bouton de confirmation ; (b) ressaisie du mot de passe ; (c) ressaisie du mot de passe + saisie d'un mot de confirmation (« SUPPRIMER ») ; (d) comme (c), plus une authentification biométrique.
- **Recommandation** : (c). Le mot de passe empêche qu'une session laissée ouverte suffise à effacer un compte et le mot à saisir écarte le clic accidentel ; (d) est exclu parce que l'effacement doit rester possible sans gabarit utilisable (RM-12.1).

### N-4.4 — Effet immédiat ou délai de grâce (UC-12)
- **Question** : la suppression prend-elle effet immédiatement ou après un délai pendant lequel elle peut être annulée ?
- **Options** : (a) immédiate et irréversible ; (b) délai de grâce (par exemple 7 jours) : gabarits et jeton détruits tout de suite, reste du compte désactivé puis effacé à l'échéance, annulation par reconnexion ; (c) délai de grâce portant aussi sur les gabarits.
- **Recommandation** : (a). Une suppression par erreur ne coûte qu'une nouvelle inscription et un enrôlement de quelques minutes, alors qu'un délai de grâce ajoute un état intermédiaire, une purge planifiée et complique la preuve de l'effacement ; (c) est à exclure dans tous les cas, les gabarits devant disparaître sans délai comme lors d'un retrait de consentement (A-02.2).

### N-4.5 — Sort de l'historique des consentements après suppression (UC-12)
- **Question** : RM-02.4 conserve l'historique des consentements comme preuve de conformité, alors que UC-12 efface les données de la personne. Que conserve-t-on, et sous quelle forme ?
- **Options** :
  - (a) tout effacer, historique compris : effacement total, mais plus aucune preuve que les traitements passés étaient consentis ;
  - (b) conserver l'historique tel quel (nom, email, IP) pendant une durée limitée ;
  - (c) conserver un enregistrement minimal : versions du texte accepté, horodatages d'octroi, de retrait et de suppression, rattachés à une empreinte à clé (HMAC) de l'email au lieu de l'email lui-même, sans nom ni IP, purgé au terme de la durée du **point 9**.
- **Recommandation** : (c). La preuve reste opposable (l'empreinte se recalcule à partir de l'adresse d'une personne qui conteste) sans conserver de donnée directement identifiante ; l'enregistrement reste une donnée pseudonymisée, non anonyme, dont la conservation s'appuie sur l'exception « constatation, exercice ou défense de droits en justice » du RGPD (art. 17.3.e), l'équivalent dans la loi 2017-20 étant à vérifier avec l'encadrant.

### N-4.6 — Notification par email des opérations sensibles (UC-11, UC-12)
- **Question** : la révocation (y compris par un administrateur) et la suppression donnent-elles lieu à un email ?
- **Options** : (a) aucun email : information à l'écran seulement, accusé de suppression téléchargeable ; (b) email d'alerte à chaque révocation et accusé de suppression par email ; (c) accusé de suppression par email seulement.
- **Recommandation** : (b) si un canal d'envoi d'email existe (point 1 retenu), car c'est le seul moyen pour le titulaire légitime d'apprendre qu'un tiers connaissant son mot de passe a agi sur son compte ; sinon (a).

### N-4.7 — Conservation d'un compte sans gabarit actif
- **Question** : combien de temps conserver un compte inactif sans gabarit actif (`NON_ENROLE`, `REVOQUE`, consentement refusé ou retiré) ?
- **Options** : (a) sans limite, jusqu'à suppression par le titulaire ou un administrateur ; (b) suppression automatique (effets d'UC-12, sans confirmation) après une durée d'inactivité, précédée d'un avertissement par email si un canal existe ; (c) suppression de tous les comptes de volontaires à une date fixe (fin du protocole ou soutenance).
- **Recommandation** : (b), avec la même durée que celle retenue au **point 6** pour les gabarits, pour qu'aucune donnée de compte ne survive plus longtemps que les gabarits eux-mêmes (minimisation) ; cette durée est annoncée dans le texte de consentement (**point 8**).
