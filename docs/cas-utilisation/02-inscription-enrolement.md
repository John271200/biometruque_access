# 2. Inscription, consentement et enrôlement (UC-01 à UC-06)

> Statut : **BROUILLON v1 — en attente de validation**.

---

## UC-01 — Créer un compte

> **En tant que** visiteur, **je veux** créer un compte avec mon nom, mon email et un mot de passe, **afin de** pouvoir ensuite m'enrôler biométriquement et accéder à la base protégée.

- **Acteur principal** : Visiteur
- **Préconditions** : aucune. Service joignable en HTTPS (ou sur `localhost`).
- **Déclencheur** : le visiteur soumet le formulaire d'inscription.

**Scénario nominal**
1. Le visiteur saisit nom complet, email, mot de passe et confirmation du mot de passe.
2. Le système valide le format de chaque champ (RM-01.1 à RM-01.3).
3. Le système vérifie que l'email n'existe pas déjà (RM-01.4).
4. Le système hache le mot de passe avec Argon2id (RM-01.5).
5. Le système crée le compte : état `CREE` (ou `EN_ATTENTE_VERIFICATION`, voir A-01.1), rôle `utilisateur`, consentement `ABSENT`, enrôlement `NON_ENROLE`.
6. Le système journalise la création (sans mot de passe ni hachage).
7. Le système ouvre une session « compte » et redirige vers l'écran de consentement (UC-02).

**Scénarios alternatifs et d'erreur**
- **E-01.1 Email déjà utilisé** → refus. Proposition : message explicite « Cette adresse est déjà associée à un compte ». Le risque d'énumération de comptes est alors accepté et documenté dans le rapport (**point 2bis**).
- **E-01.2 Mot de passe trop faible** → refus avec la liste des critères non satisfaits ; les autres champs restent remplis.
- **E-01.3 Email syntaxiquement invalide** → refus avec message rattaché au champ.
- **E-01.4 Confirmation différente du mot de passe** → refus.
- **A-01.1 Vérification d'email activée** (si **point 1** = oui) → compte `EN_ATTENTE_VERIFICATION`, code à 6 chiffres valable 15 min envoyé par email, 3 essais maximum puis renvoi possible ; consentement et enrôlement bloqués tant que le code n'est pas validé.

**Règles métier**
- RM-01.1 — Nom complet : 2 à 100 caractères, non vide après suppression des espaces de début et de fin.
- RM-01.2 — Email : format valide, 254 caractères maximum, normalisé en minuscules.
- RM-01.3 — Mot de passe : **point 2** — proposition : 12 caractères minimum, au moins une majuscule, une minuscule et un chiffre ; refus des mots de passe les plus courants.
- RM-01.4 — Email unique sur toute la base, après normalisation.
- RM-01.5 — Mot de passe stocké en Argon2id uniquement : jamais en clair, jamais journalisé, jamais renvoyé par l'API.
- RM-01.6 — Aucun compte administrateur ne peut être créé par ce flux (**point 5**).

**Postcondition** : un compte existe, sans consentement, non enrôlé, incapable de s'authentifier biométriquement.

---

## UC-02 — Donner ou refuser son consentement au traitement biométrique

> **En tant que** titulaire de compte, **je veux** lire une information claire puis donner ou refuser mon consentement explicite au traitement de mes données biométriques, **afin de** garder la maîtrise de mes données, conformément au Code du numérique béninois (loi 2017-20) et au RGPD.

- **Acteur principal** : Titulaire de compte
- **Préconditions** : session « compte » active (UC-07) ; email vérifié si le **point 1** est retenu.
- **Déclencheur** : première connexion après inscription, ou accès volontaire à la page « Mes données ».

**Scénario nominal**
1. Le système affiche l'écran de consentement : finalité (contrôle d'accès à une base de démonstration dans le cadre d'un mémoire de Master), nature des données (images de visage et d'oreille, gabarits protégés), durée de conservation (RM-02.2), destinataires, droit de retrait et de suppression, identité et coordonnées du responsable de traitement (**point 8**).
2. Le titulaire coche une case **non pré-cochée** puis clique sur « Je consens ».
3. Le système enregistre l'horodatage, la version du texte de consentement, l'adresse IP et l'identifiant du compte.
4. Le consentement passe à `ACCORDE` ; l'enrôlement (UC-03) est débloqué.

**Scénarios alternatifs et d'erreur**
- **A-02.1 Refus** → aucun enrôlement possible. Le compte reste utilisable uniquement pour consulter ses données (UC-06) et se supprimer (UC-12). Message : « Sans consentement, l'enrôlement biométrique est impossible. Vous pouvez supprimer votre compte à tout moment. »
- **A-02.2 Retrait du consentement après enrôlement** → destruction obligatoire et immédiate des gabarits, journalisée ; le sort du compte dépend du **point 7** (UC-11 ou UC-12).
- **A-02.3 Nouvelle version du texte de consentement** → le consentement est redemandé au prochain accès ; un refus vaut retrait (A-02.2).
- **A-02.4 Consentement « recherche » distinct** (si **point 21** = oui) → seconde case, séparée et facultative, pour la conservation chiffrée des images aux fins du protocole d'évaluation (UC-21) ; la refuser ne bloque pas l'enrôlement.
- **E-02.1 Accès à l'enrôlement sans consentement** → refus (HTTP 403) avec message explicite ; aucune capture n'est acceptée.

**Règles métier**
- RM-02.1 — Le consentement est explicite, spécifique, horodaté et versionné. Pas de case pré-cochée, pas de consentement implicite par simple usage.
- RM-02.2 — Durée de conservation des gabarits : **point 6** — proposition : destruction automatique 12 mois après le dernier accès réussi, ou à la date de soutenance pour les volontaires.
- RM-02.3 — Le retrait est aussi simple que l'octroi : un bouton, une confirmation.
- RM-02.4 — L'historique des consentements (événements, pas données biométriques) est conservé comme preuve de conformité, même après destruction des gabarits (durée : **point 9**).

**Postcondition** : consentement `ACCORDE` (enrôlement ouvert) ou refus enregistré (enrôlement fermé).

---

## UC-03 — S'enrôler, étape visage (5 captures guidées)

> **En tant que** titulaire de compte consentant, **je veux** être guidé pendant la capture de 5 images de mon visage de face, **afin de** constituer un gabarit visage de qualité suffisante pour être reconnu plus tard.

- **Acteur principal** : Titulaire de compte consentant
- **Préconditions** : consentement `ACCORDE` ; webcam autorisée par le navigateur ; enrôlement `NON_ENROLE` ou `REVOQUE` (RM-03.6) ; contexte sécurisé (HTTPS ou `localhost`).
- **Déclencheur** : clic sur « Démarrer l'enrôlement ».

**Scénario nominal**
1. Le navigateur ouvre le flux vidéo et affiche un cadre-guide ovale centré.
2. Le navigateur envoie des images au serveur à cadence régulière (**point 13bis** — proposition : 3 images/seconde).
3. Pour chaque image, le serveur évalue 5 critères de qualité (RM-03.1) et renvoie pour chacun `ok` ou `à corriger`, avec un message d'action (« rapprochez-vous », « plus de lumière de face », « une seule personne dans le cadre »).
4. Quand les 5 critères sont satisfaits, le serveur retient l'image et incrémente le compteur (1/5 … 5/5).
5. Un écart minimal est imposé entre deux captures retenues (RM-03.3) pour éviter 5 images quasi identiques.
6. À 5/5, le système conserve les 5 plongements en mémoire de session d'enrôlement et enchaîne sur l'étape oreille (UC-04) **sans couper le flux vidéo**.

**Scénarios alternatifs et d'erreur**
- **E-03.1 Aucun visage détecté** → capture non retenue, « Aucun visage détecté : placez-vous face à la caméra ».
- **E-03.2 Plusieurs visages détectés** → refus explicite, « Plusieurs visages détectés : isolez-vous ». Jamais de sélection automatique du plus grand visage.
- **E-03.3 Netteté insuffisante** → « Image floue : restez immobile et nettoyez l'objectif ».
- **E-03.4 Éclairage insuffisant ou contre-jour** → « Trop sombre » / « Trop de lumière derrière vous ».
- **E-03.5 Visage trop petit ou hors du cadre** → message directionnel (« rapprochez-vous », « décalez-vous vers la gauche »).
- **E-03.6 Visage non frontal** (lacet ou tangage hors plage) → « Regardez droit vers la caméra ».
- **E-03.7 Incohérence d'identité entre les 5 captures** → l'enrôlement entier est annulé (RM-03.4), « Les captures ne correspondent pas à une même personne ».
- **E-03.8 Webcam refusée ou contexte non sécurisé** → message expliquant comment autoriser la caméra et que le HTTPS est requis hors `localhost`.
- **A-03.1 Abandon ou expiration de la session d'enrôlement** → session détruite, aucune donnée persistée (RM-03.5).

**Règles métier**
- RM-03.1 — Cinq critères de qualité, tous bloquants (valeurs : **point 13**, propositions entre parenthèses) :
  1. un visage détecté, et un seul (score de détection SCRFD ≥ 0,6) ;
  2. visage centré dans le cadre-guide (centre du visage dans les 25 % centraux de l'image) ;
  3. taille minimale (largeur du visage ≥ 120 px) ;
  4. netteté (variance du Laplacien ≥ 100) ;
  5. éclairage (luminance moyenne entre 60 et 200, écart-type ≥ 25).
- RM-03.2 — Exactement 5 captures retenues.
- RM-03.3 — Au moins 500 ms entre deux captures retenues (**point 13**).
- RM-03.4 — Cohérence interne : la similarité cosinus de chaque paire parmi les 5 plongements doit dépasser un plancher (proposition 0,70), sinon annulation.
- RM-03.5 — Aucune image n'est écrite sur disque pendant cette étape : tout reste en mémoire de session.
- RM-03.6 — Un utilisateur déjà `ENROLE` ne peut pas se ré-enrôler sans révoquer d'abord (UC-11).
- RM-03.7 — Le contrôle qualité fait foi **côté serveur** ; un client modifié ne peut pas déclarer une image « bonne ».

**Postcondition** : 5 plongements visage valides en session d'enrôlement ; étape oreille débloquée.

---

## UC-04 — S'enrôler, étape oreille droite par rotation de la tête

> **En tant que** titulaire de compte consentant, **je veux** tourner la tête vers la gauche pour présenter mon oreille droite dans un cadre-guide, **afin de** constituer un gabarit d'oreille, ce mouvement continu servant en même temps de preuve de vivacité.

- **Acteur principal** : Titulaire de compte consentant
- **Préconditions** : UC-03 terminé dans la **même session vidéo continue** (RM-04.6).
- **Déclencheur** : fin de l'étape visage, affichage de la consigne « Tournez lentement la tête vers la gauche ».

**Scénario nominal**
1. Le système affiche un cadre-guide rectangulaire à l'emplacement attendu de l'oreille droite et un indicateur d'angle en temps réel.
2. L'utilisateur tourne la tête progressivement vers la gauche, sans interrompre le flux.
3. Le serveur estime le lacet image par image et vérifie la continuité du mouvement (RM-04.5) : c'est le contrôle de vivacité.
4. Quand le lacet entre dans la plage de profil attendue (RM-04.1), le serveur recadre la zone du cadre-guide et évalue la qualité de la vignette d'oreille (RM-04.2).
5. Les vignettes conformes sont retenues ; 5 captures sont collectées comme en UC-03.
6. À 5/5, le système enchaîne sur la finalisation (UC-05).

**Scénarios alternatifs et d'erreur**
- **E-04.1 Angle insuffisant** → « Tournez davantage la tête vers la gauche », avec indicateur de progression.
- **E-04.2 Angle excessif** → « Vous avez trop tourné, revenez légèrement ».
- **E-04.3 Oreille hors du cadre-guide** → « Alignez votre oreille sur le cadre ».
- **E-04.4 Oreille masquée** (cheveux, bonnet, écouteurs) → le critère de texture/contraste échoue → « Dégagez votre oreille : cheveux, bonnet ou écouteurs ». Ce cas est aussi un scénario du laboratoire d'attaques (UC-19).
- **E-04.5 Netteté insuffisante** (flou de mouvement) → « Tournez plus lentement ».
- **E-04.6 Rotation discontinue ou absente** (image figée, photo imprimée, saut d'angle) → échec de vivacité, enrôlement annulé, « Mouvement de tête non détecté, recommencez ».
- **E-04.7 Changement de personne pendant la rotation** → rupture de suivi du visage (RM-04.4) → annulation.
- **E-04.8 Délai dépassé** (proposition : 60 s pour l'étape, **point 14**) → annulation, possibilité de recommencer depuis UC-03.
- **A-04.1 Échecs répétés** (proposition : 3 enrôlements avortés, **point 14**) → enrôlement suspendu 10 minutes, page d'aide « bien se placer » proposée.

**Règles métier**
- RM-04.1 — Plage de lacet du profil : **point 13** — proposition : entre 60° et 100° par rapport au frontal ; la convention de signe d'InsightFace sera fixée et testée.
- RM-04.2 — Qualité de la vignette d'oreille : taille minimale après recadrage (proposition 64 × 96 px), netteté (Laplacien ≥ seuil), contraste local suffisant (détection d'occultation), cadre-guide suffisamment rempli.
- RM-04.3 — Exactement 5 captures retenues, au moins 500 ms entre deux.
- RM-04.4 — Continuité d'identité : le plongement visage reste comparable tant que le visage est détectable ; au-delà, la continuité est garantie par le suivi de la boîte englobante image par image (pas de saut au-delà d'un seuil).
- RM-04.5 — Vivacité : **point 17** — proposition : au moins 8 images intermédiaires entre frontal et profil, lacet globalement monotone (au plus 2 inversions), amplitude ≥ 50°, durée du mouvement entre 1,5 s et 15 s.
- RM-04.6 — L'étape oreille suit l'étape visage dans la même session vidéo continue ; toute interruption du flux invalide la vivacité et impose de reprendre à UC-03.
- RM-04.7 — Oreille **droite** uniquement en v1 (**point 12**).

**Postcondition** : 5 vignettes d'oreille valides et une preuve de vivacité en session d'enrôlement.

---

## UC-05 — Finaliser l'enrôlement : extraction, protection, destruction des images

> **En tant que** titulaire de compte, **je veux** que mes captures soient transformées en gabarits protégés puis que les images soient détruites, **afin qu'**aucune donnée biométrique exploitable ne subsiste si la base est compromise.

- **Acteur principal** : Titulaire de compte (traitement déclenché automatiquement par le système)
- **Préconditions** : UC-03 et UC-04 réussis dans la même session ; consentement `ACCORDE`.
- **Déclencheur** : 5e capture d'oreille retenue.

**Scénario nominal**
1. Le système agrège les 5 plongements ArcFace 512-D du visage (RM-05.1).
2. Le système calcule les 5 descripteurs d'oreille avec l'extracteur actif (UC-18) et les agrège de la même façon.
3. Le système génère un jeton personnel aléatoire (RM-05.2) et en dérive la base orthonormée de BioHashing.
4. Le système projette chaque vecteur agrégé sur cette base et binarise le résultat en 256 bits (RM-05.3).
5. Le système chiffre chaque BioHash en AES-256-GCM avec la clé maîtresse (RM-05.4).
6. Le système enregistre : gabarit visage chiffré, gabarit oreille chiffré, identifiant de l'extracteur d'oreille, version du schéma de protection, horodatage.
7. Le système efface de la mémoire images, vecteurs en clair et BioHash en clair (RM-05.5).
8. L'enrôlement passe à `ENROLE`. Un récapitulatif sans aucune image s'affiche (date, modalités, extracteur utilisé).

**Scénarios alternatifs et d'erreur**
- **E-05.1 Échec d'extraction** (modèle indisponible, image corrompue) → aucun enrôlement partiel, l'état reste `NON_ENROLE`, message « Traitement impossible, veuillez recommencer » ; erreur technique journalisée sans donnée biométrique.
- **E-05.2 Clé maîtresse absente ou invalide** → enrôlement refusé, alerte administrateur, service en mode « enrôlement indisponible ». Jamais de stockage en clair en solution de repli.
- **E-05.3 Échec d'écriture en base** → transaction annulée, aucun gabarit orphelin, mémoire purgée.
- **A-05.1 Consentement « recherche » accordé** (**point 21**) → les images sont enregistrées chiffrées dans un espace séparé, avec date de destruction, sous un pseudonyme « volontaire n° ». Elles ne servent jamais à l'authentification.
- **A-05.2 Deux extracteurs d'oreille en parallèle** (**point 22**) → deux gabarits d'oreille sont produits et stockés ; un seul est « actif pour la décision ».

**Règles métier**
- RM-05.1 — Agrégation des 5 captures : **point 11** — proposition : moyenne des vecteurs L2-normalisés, renormalisation, puis **un seul** BioHash par modalité (la binarisation interdit de moyenner après coup).
- RM-05.2 — Jeton personnel : 32 octets aléatoires cryptographiquement sûrs, propre à chaque utilisateur ; lieu de stockage : **point 19**.
- RM-05.3 — BioHash : projection sur base orthonormée dérivée du jeton, binarisation par seuillage, 256 bits (**point 20**).
- RM-05.4 — Chiffrement AES-256-GCM obligatoire avant persistance. Clé maîtresse en variable d'environnement en développement, coffre de secrets en production. Données additionnelles authentifiées incluant l'identifiant utilisateur et la modalité, pour empêcher la substitution d'un gabarit par un autre.
- RM-05.5 — Après finalisation : aucune image brute, aucun vecteur en clair, aucun BioHash en clair n'est conservé (hors espace « recherche » consenti séparément, A-05.1).
- RM-05.6 — Enrôlement atomique : visage **et** oreille, ou rien (**point 10**).

**Postcondition** : enrôlement `ENROLE`, deux gabarits chiffrés en base, aucune image conservée.

---

## UC-06 — Consulter l'état de son enrôlement et ses données

> **En tant que** titulaire de compte, **je veux** voir quelles données me concernant sont détenues et depuis quand, **afin d'**exercer mon droit d'information.

- **Acteur principal** : Titulaire de compte
- **Préconditions** : session « compte » active (UC-07).
- **Déclencheur** : ouverture de la page « Mes données ».

**Scénario nominal**
1. Le système affiche : nom, email, date et version du consentement, état d'enrôlement, date d'enrôlement, modalités enrôlées, extracteur d'oreille utilisé, date de destruction prévue, nombre de tentatives d'authentification réussies et échouées, date du dernier accès à la base protégée.
2. Le système propose les actions « Révoquer et me ré-enrôler » (UC-11), « Retirer mon consentement » (UC-02 A-02.2) et « Supprimer mon compte » (UC-12).

**Scénarios alternatifs et d'erreur**
- **E-06.1 Session expirée** → redirection vers la connexion (UC-07).

**Règles métier**
- RM-06.1 — Aucune image, aucun gabarit, aucun vecteur n'est jamais restitué, même à son propriétaire.
- RM-06.2 — Un utilisateur ne voit que ses propres données.
