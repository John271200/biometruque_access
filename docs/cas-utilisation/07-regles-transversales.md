# 7. Règles métier transversales et hors périmètre

> Statut : **BROUILLON v1 — en attente de validation**.

Ces règles s'appliquent à tous les cas d'utilisation (UC-01 à UC-21) et ne sont pas répétées dans chacun d'eux.

---

## 7.1 Règles transversales

### Sécurité

- **RT-01 — HTTPS obligatoire hors `localhost`.** Hors `localhost`, le frontend et l'API ne sont accessibles qu'en HTTPS : exigence du brief et condition technique, les navigateurs refusant `getUserMedia` hors contexte sécurisé. Aucun mot de passe, jeton ni image ne transite en clair. Redirection HTTP → HTTPS, version minimale de TLS et en-tête HSTS : **point N-7.1** — proposition : redirection systématique, TLS 1.2 minimum, HSTS activé hors `localhost`. Origine du certificat selon le contexte (poste de développement, réseau de la soutenance, serveur public) : **point N-7.2**.
- **RT-02 — Secrets hors du code et des journaux.** La clé maîtresse, la clé de signature des JWT, le mot de passe PostgreSQL, toute clé d'empreinte (HMAC) et, le cas échéant, les identifiants d'envoi d'email n'apparaissent jamais dans le code source, le dépôt (**point 35**), les images Docker, les journaux, les messages d'erreur ni les réponses de l'API. La clé maîtresse est fournie par variable d'environnement en développement et par un coffre de secrets en production (brief) ; le même mécanisme est proposé pour les autres secrets. Le dépôt ne contient qu'un fichier d'exemple sans valeur réelle. Coffre retenu : **point N-7.2**. Rotation de la clé maîtresse : **point N-7.3**.
- **RT-03 — Aucun repli en l'absence de clé maîtresse.** Si la clé maîtresse est absente ou invalide, le système ne génère pas de clé, n'utilise aucune valeur par défaut et ne stocke rien en clair : enrôlement et authentification biométrique sont indisponibles et l'administrateur est alerté (E-05.2). Les fonctions qui n'exigent aucun déchiffrement restent disponibles, notamment la consultation de ses données (UC-06) et la suppression de compte (UC-12).
- **RT-04 — Aucune donnée biométrique en clair au repos ni dans les journaux.** Au repos n'existent que des gabarits BioHash chiffrés en AES-256-GCM (RM-05.4) et, si le **point 21** est retenu, des images « recherche » chiffrées dans un espace séparé. Images, plongements, descripteurs d'oreille et BioHash en clair ne sont jamais écrits en base, sur disque (fichiers temporaires compris), dans les journaux, dans les traces d'erreur ni dans les réponses de l'API (RM-06.1). En transit, ils ne circulent que sous TLS (RT-01).
- **RT-05 — Contrôles et décisions côté serveur.** Qualité, vivacité, extraction, fusion, décision, verrouillage et validité des jetons sont calculés et vérifiés exclusivement par le serveur ; le navigateur capture et affiche le retour (RM-03.7). Toute valeur déclarée par le client (score, angle, « qualité ok », horodatage) est ignorée. Paramètres de décision (seuils, poids, planchers) : **point N-7.1** — proposition : jamais communiqués aux non-administrateurs. Détail renvoyé en cas d'échec : **point 27**.
- **RT-06 — Contrôle d'accès à chaque requête.** Le rôle (`utilisateur`, `admin`, `evaluateur` selon le **point 31**) et la propriété des données sont vérifiés côté serveur à chaque requête ; un utilisateur n'accède qu'à ses propres données (RM-06.2). Selon la proposition du **point 3**, la base protégée n'est accessible qu'avec un jeton d'accès biométrique valide, jamais avec la seule session « compte ».
- **RT-07 — Effacement de la mémoire.** Images, vecteurs et BioHash en clair n'existent qu'en mémoire vive, le temps d'une session de capture ou d'une décision, et sont effacés dès sa fin (succès, échec, abandon ou expiration) : aucune référence conservée, tampons modifiables remis à zéro, aucune session de capture placée dans un cache partagé ni en base. Vidages mémoire (core dumps) du conteneur `api` : **point N-7.1** — proposition : désactivés. Limite à documenter dans le rapport : en Python, l'effacement des objets immuables et des copies internes aux bibliothèques n'est pas garanti ; la règle réduit la fenêtre d'exposition sans pouvoir l'annuler.
- **RT-08 — Horloge et horodatage.** Tous les horodatages sont produits par le serveur et stockés en UTC (ISO 8601) ; aucun horodatage fourni par le client n'est retenu. L'horloge de l'hôte est synchronisée (NTP), car l'expiration des JWT (10 min), le verrouillage, les délais d'enrôlement et l'ordre du journal en dépendent. Fuseau d'affichage : **point N-7.1** — proposition : fuseau du navigateur pour les utilisateurs, UTC explicite dans le journal administrateur et les exports.
- **RT-09 — Journal en ajout seul.** L'application ne peut qu'ajouter des entrées au journal d'audit, jamais les modifier ni les supprimer, administrateur compris (§1.2). Mécanisme et détection d'une altération faite directement en base : **point N-7.4**. L'anonymisation après suppression d'un compte (UC-12) ne doit pas contredire cette règle : **point 9** — proposition : pseudonymisation à la source (RT-17), qui rend les entrées non rattachables sans les réécrire. La seule suppression admise est la purge à l'échéance de la durée de conservation, hors de l'application (**point N-7.4**).

### Protection des données

- **RT-10 — Minimisation.** Seules sont collectées : nom complet, email, mot de passe (haché), données de consentement (UC-02), captures biométriques transitoires, gabarits protégés et événements de journal. Aucune autre donnée n'est demandée (date de naissance, téléphone, photo de profil, localisation). Les images ne survivent ni à l'enrôlement ni à l'authentification (RM-05.5), sauf consentement « recherche » distinct (**point 21**).
- **RT-11 — Finalité unique.** Les données biométriques servent exclusivement à vérifier que la personne présente est le titulaire du compte revendiqué (vérification 1:1), pour contrôler l'accès à la base protégée de démonstration. Elles ne servent jamais à identifier une personne parmi les inscrits (1:N, hors périmètre, 7.2) ni à aucun autre usage ; la conservation d'images pour l'évaluation (UC-21) exige le consentement « recherche » distinct (**point 21**).
- **RT-12 — Droits de la personne.** Chaque droit a son chemin dans l'application, en libre-service :
  - information : écran de consentement (UC-02) et RT-13 ;
  - accès : page « Mes données » (UC-06) ;
  - retrait du consentement : UC-02 A-02.2 (portée : **point 7**) ;
  - renouvellement des gabarits : UC-11 ;
  - effacement : UC-12 ;
  - rectification : aucun cas d'utilisation ne la couvre aujourd'hui (**point N-7.5**).

  L'accès, le retrait et l'effacement ne dépendent jamais d'une authentification biométrique réussie ; pour la révocation, voir le **point N-4.1**.
- **RT-13 — Information.** Avant toute collecte biométrique, l'écran de consentement présente les mentions d'UC-02 (finalité, données, durée, destinataires, droits, responsable de traitement : **point 8**). Information avant même l'inscription : **point N-7.1** — proposition : page publique « Confidentialité » reprenant le texte en vigueur et sa version.
- **RT-14 — Durées de conservation.** Chaque catégorie de données a une durée de conservation définie ; celles qui concernent la personne figurent dans le texte de consentement (**point 8**).

  | Donnée | Durée | Référence |
  |---|---|---|
  | Images et vecteurs en clair | durée de la session de capture ou de la décision | RM-03.5, RM-05.5 (ferme) |
  | Jeton d'accès biométrique (JWT) | 10 minutes | brief (ferme) ; renouvellement : point 4 |
  | Gabarits chiffrés et jeton BioHashing | à décider | point 6 |
  | Compte sans gabarit actif | à décider | point N-4.7 |
  | Historique des consentements | à décider | points N-4.5 et 9 |
  | Journaux | à décider | point 9 |
  | Images « recherche » | à décider | point 21 |
  | Sauvegardes | à décider | point N-7.6 |

- **RT-15 — Cadre juridique.** Les données biométriques sont des données sensibles au sens du RGPD et la loi 2017-20 (Code du numérique) encadre elle aussi spécifiquement leur traitement ; le projet s'inscrit dans l'esprit de ces deux textes (brief). Les formalités éventuelles auprès de l'Autorité de protection des données personnelles (APDP) et les conséquences d'un hébergement hors du Bénin sont à vérifier avec l'encadrant (**points 8** et **N-7.2**).

### Journalisation

- **RT-16 — Événements journalisés au minimum.**

  | Événement | Cas d'utilisation | Précisions |
  |---|---|---|
  | Création de compte | UC-01 | sans mot de passe ni hachage |
  | Consentement accordé, refusé, retiré, redemandé | UC-02 | version du texte |
  | Enrôlement : démarrage, annulation, finalisation | UC-03 à UC-05 | motif d'annulation (qualité, vivacité, délai, incohérence) ; extracteur utilisé |
  | Révocation et ré-enrôlement | UC-11, UC-14 | initiateur ; motif (point N-4.2) |
  | Suppression de compte | UC-12, UC-14 | initiateur ; pseudonyme uniquement |
  | Tentative d'authentification biométrique | UC-08 | champs de RT-17 |
  | Verrouillage (et levée) | UC-09 | nombre d'échecs, durée |
  | Accès à la base protégée | UC-10 | identifiant du dossier consulté (granularité : point 29) |
  | Modification des paramètres de décision | UC-16 | ancienne et nouvelle valeur, auteur |
  | Export de rapport | UC-20 | type de rapport, auteur |

  Ajouts : **point N-7.1** — proposition : connexion au compte réussie ou échouée (UC-07), vérification d'email (point 1), changement d'extracteur actif (UC-18), tentative étiquetée du laboratoire (UC-19, articulation : point 33), erreur de sécurité (clé maîtresse absente, échec de vérification AES-GCM, signature de JWT invalide).
- **RT-17 — Contenu d'une entrée.**
  - Champs communs : identifiant d'entrée, horodatage UTC, type d'événement, acteur (pseudonyme de compte et rôle, ou « anonyme »), cible (pseudonyme de compte ou identifiant de dossier), résultat (succès, échec, refus, erreur), motif ou règle déterminante, identifiant de corrélation de la requête, version des paramètres de décision en vigueur, adresse IP (**point N-7.1** — proposition : tronquée, dernier octet masqué en IPv4, préfixe /48 en IPv6), empreinte de chaînage (**point N-7.4**).
  - Champs propres à une tentative d'authentification : score visage, score oreille, scores normalisés (**point 23**), score fusionné, seuils et planchers appliqués (**point 24**), règle déterminante (**point 25**), résultat de vivacité et critère en échec (**point 17**), extracteur d'oreille actif, durée de traitement serveur (RT-20).
  - Pseudonymisation à la source (**point 9** — proposition) : un compte est désigné dans le journal par un pseudonyme aléatoire, jamais par son nom ni son email ; la table de correspondance est tenue hors du journal, sert au filtrage par utilisateur (UC-15) et est détruite à la suppression du compte (UC-12). Une tentative visant une adresse inconnue est enregistrée avec une empreinte à clé (HMAC) de l'adresse, jamais l'adresse elle-même (**point N-7.1**).
- **RT-18 — Contenu interdit.** Ne figurent jamais, ni dans le journal d'audit ni dans les journaux techniques des conteneurs : mot de passe (même erroné) et son hachage ; JWT, jeton BioHashing, code de vérification ; clés et secrets ; images (y compris encodées dans un corps de requête), plongements, descripteurs, BioHash en clair ou chiffrés ; nom et email en clair ; contenu des dossiers de la base protégée (seul l'identifiant du dossier est journalisé). Les gestionnaires d'erreurs n'enregistrent jamais le corps des requêtes. Vérification : **point N-7.1** — proposition : un test automatisé recherche ces contenus dans les journaux produits par la suite de tests.
- **RT-19 — Accès au journal.** Lecture réservée aux administrateurs (UC-15) ; l'évaluateur consulte les tentatives étiquetées du laboratoire (**points 31** et **33**). Les exports sont eux-mêmes journalisés (RT-16). Durée de conservation : **point 9**.

### Performance

- **RT-20 — Authentification en moins de 2 secondes sur CPU.** Exigence du brief, sans GPU. Ce qui est mesuré, sur quelle machine et avec quelle statistique : **point N-7.7** — proposition : temps perçu entre la fin de la capture guidée et l'affichage de la décision, au 95e centile, sur une machine de référence, un utilisateur à la fois. Condition nécessaire : les modèles (InsightFace buffalo_l, extracteur d'oreille) sont chargés une seule fois au démarrage de l'API, jamais à chaque requête. La durée de traitement serveur est journalisée à chaque tentative (RT-17) et alimente le tableau de bord (UC-17).
- **RT-21 — Fluidité de la capture et de l'enrôlement.** **Point N-7.7** — proposition : retour qualité en moins de 300 ms par image côté serveur, pour suivre la cadence de capture (**point 13bis**) ; finalisation d'un enrôlement (UC-05) en moins de 5 secondes.

### Ergonomie

- **RT-22 — Français.** Interface, messages (y compris les erreurs renvoyées par l'API et affichées), emails éventuels et documentation sont en français. Aucun message technique brut, trace d'erreur ou message de bibliothèque en anglais n'est montré à l'utilisateur.
- **RT-23 — Sobriété.** Interface sobre et professionnelle (brief), sans effet décoratif. Pendant la capture, le flux vidéo et le cadre-guide occupent l'essentiel de l'écran ; **point N-7.1** — proposition : une seule consigne d'action affichée à la fois (la plus prioritaire), l'état des critères de qualité restant visible sous forme compacte.
- **RT-24 — Mobile.** Toutes les pages sont utilisables sur mobile (brief) ; **point N-7.1** — proposition : mise en page fonctionnelle dès 360 px de large, cibles tactiles d'au moins 44 × 44 px. Particularités de la capture sur mobile (caméra frontale, orientation, performances) : **point 15**.
- **RT-25 — Messages actionnables.** Chaque message dit ce qui s'est passé et ce que la personne peut faire, sur le modèle « constat : action » (« Image floue : restez immobile et nettoyez l'objectif »). Jamais de code d'erreur seul, jamais de formulation culpabilisante ; un message d'échec d'authentification ne révèle pas plus que ce que fixe le **point 27** (voir aussi le **point 2bis**).
- **RT-26 — Accessibilité clavier et contrastes.** Toutes les actions sont réalisables au clavier, avec un focus visible et un ordre de tabulation logique. L'état d'un critère de qualité n'est jamais signalé par la seule couleur (texte ou icône en plus). **Point N-7.1** — proposition : contrastes conformes au niveau AA des WCAG 2.1 (4,5:1 pour le texte courant), consignes de capture annoncées aux lecteurs d'écran.
- **RT-27 — Confirmation des actions destructrices.** Révocation (UC-11), suppression (UC-12, UC-14) et retrait du consentement (A-02.2) exigent une confirmation explicite qui énonce leurs conséquences ; le retrait reste aussi simple que l'octroi (RM-02.3). Modification des paramètres de décision (UC-16) : **point N-7.1** — proposition : même confirmation.

### Exploitation

- **RT-28 — CPU uniquement.** Toute l'inférence s'exécute sur CPU (onnxruntime, fournisseur CPU) ; aucune dépendance GPU ou CUDA dans les images ; les objectifs de performance sont mesurés sans GPU (RT-20).
- **RT-29 — Docker Compose à trois services.** `api` (FastAPI, Python 3.11), `frontend` (Vue 3 compilé), `postgres` (PostgreSQL 16) ; le README mène à une instance fonctionnelle par une seule commande de démarrage ; les données PostgreSQL sont sur un volume persistant. **Point N-7.1** — propositions : migrations Alembic appliquées au démarrage d'`api`, modèles intégrés à l'image lors de sa construction (démonstration possible sans Internet), versions des dépendances figées.
- **RT-30 — README pas à pas.** Exigence du brief. **Point N-7.1** — proposition de contenu minimal : prérequis, configuration des secrets, démarrage, création du premier administrateur (**point 5**), accès HTTPS depuis un téléphone (**point N-7.2**), scénario de démonstration, réinitialisation des données, dépannage de la caméra.
- **RT-31 — Code commenté en français.** Exigence du brief : commentaires et docstrings en français. Langue des identifiants : **point N-7.1** — proposition : anglais, conformément aux conventions de Python et de TypeScript.
- **RT-32 — Sauvegardes.** Existence, fréquence et durée de conservation des sauvegardes, et effet sur le délai réel d'effacement (UC-11, UC-12) : **point N-7.6**.
- **RT-33 — Licence des modèles.** Chaque modèle embarqué (détection, visage, oreille) est utilisé conformément à sa licence, indiquée dans le README : **point N-7.8**.

---

## 7.2 Hors périmètre v1

Chaque exclusion est **à confirmer** (**point N-7.9**). Les lignes H-09 et H-10 ne figurent pas dans la liste initiale : elles sont ajoutées parce qu'aucun cas d'utilisation ne les couvre.

| # | Élément exclu de la v1 | Ce que fait la v1 à la place | Conséquence à accepter |
|---|---|---|---|
| H-01 | Récupération du mot de passe par email | Rien : le titulaire qui a oublié son mot de passe s'adresse à l'administrateur, qui peut supprimer son compte (UC-14) ; il se réinscrit ensuite | Un oubli coûte une ré-inscription et un ré-enrôlement |
| H-02 | Authentification multifacteur non biométrique (TOTP) | Mot de passe pour la session « compte », biométrie pour la base protégée | La session « compte » repose sur le seul mot de passe |
| H-03 | Multi-organisation | Une seule organisation, une seule base protégée | Aucun cloisonnement entre organisations |
| H-04 | Oreille gauche | Oreille droite uniquement (**point 12**) | Une personne dont l'oreille droite est absente, abîmée ou impossible à dégager ne peut pas s'enrôler |
| H-05 | Application mobile native | Application web adaptée au mobile (**point 15**) | Dépendance au support de la caméra par le navigateur mobile |
| H-06 | Identification 1:N | Vérification 1:1 sur l'email revendiqué | L'email doit être saisi à chaque authentification |
| H-07 | Modification des dossiers de la base protégée | Lecture seule (**points 28** et **29**) | Aucune démonstration de droits d'écriture |
| H-08 | Internationalisation | Français uniquement | Interface inutilisable pour une personne non francophone |
| H-09 (ajout) | Changement de mot de passe par le titulaire | Aucun cas d'utilisation ne le prévoit | Un titulaire qui soupçonne le vol de son mot de passe ne peut que supprimer son compte |
| H-10 (ajout) | Détection d'attaque de présentation par un modèle dédié | Défi de mouvement uniquement (RM-04.5, **point 17**) | Le rejeu d'une vidéo du geste complet n'est pas détecté par conception : à mesurer au laboratoire (**point 32**) |

---

## Nouveaux points à trancher (section 7)

### N-7.1 — Réglages transverses à valider en bloc
- **Question** : les propositions ci-dessous, de faible coût et réversibles, sont-elles acceptées ?

  | Réf. | Règle | Proposition | Alternative principale |
  |---|---|---|---|
  | a | RT-01 | Redirection HTTP → HTTPS, TLS 1.2 minimum, HSTS hors `localhost` | TLS 1.3 seul (exclut des navigateurs anciens) |
  | b | RT-05 | Paramètres de décision jamais communiqués aux non-administrateurs | Les publier (transparence, mais aide à l'attaque) |
  | c | RT-07 | Vidages mémoire désactivés dans le conteneur `api` | Les conserver pour le débogage |
  | d | RT-08 | Fuseau du navigateur à l'écran ; UTC explicite dans le journal administrateur et les exports | Heure du Bénin (UTC+1) partout |
  | e | RT-13 | Page publique « Confidentialité » versionnée | Information sur l'écran de consentement seulement |
  | f | RT-16 | Événements ajoutés : connexion au compte, vérification d'email, changement d'extracteur, tentative étiquetée, erreur de sécurité | Liste minimale seulement |
  | g | RT-17 | Adresse IP tronquée dans le journal | IP complète (meilleure investigation, donnée plus identifiante) ou aucune IP |
  | h | RT-17 | Adresse inconnue journalisée sous forme d'empreinte HMAC | Ne rien journaliser de l'adresse |
  | i | RT-18 | Test automatisé de non-fuite dans les journaux | Relecture manuelle |
  | j | RT-23 | Une seule consigne d'action à la fois, état des critères visible en compact | Liste détaillée de tous les critères |
  | k | RT-24 | Largeur minimale 360 px, cibles tactiles d'au moins 44 × 44 px | — |
  | l | RT-26 | Contrastes WCAG 2.1 niveau AA, consignes annoncées aux lecteurs d'écran | — |
  | m | RT-27 | Confirmation explicite avant modification des paramètres de décision | Enregistrement direct |
  | n | RT-29 | Migrations Alembic au démarrage, modèles intégrés à l'image, dépendances figées | Migrations manuelles, modèles téléchargés au premier lancement |
  | o | RT-30 | Contenu minimal du README listé en RT-30 | — |
  | p | RT-31 | Identifiants de code en anglais | Identifiants en français |

- **Options** : accepter le bloc, ou rejeter des lignes une à une.
- **Recommandation** : accepter le bloc ; ces réglages sont indépendants, chacun peut être rejeté isolément sans effet sur les autres.

### N-7.2 — Cible de déploiement, certificat TLS et coffre de secrets
- **Question** : où la plateforme est-elle déployée (démonstration, soutenance, au-delà), d'où vient le certificat HTTPS et quel coffre de secrets utilise-t-on en production ?
- **Options** :
  - (a) poste local uniquement (`localhost`) : aucun certificat nécessaire, mais aucun téléphone ne peut se connecter ;
  - (b) réseau local de la soutenance, certificat émis par une autorité locale (par exemple mkcert) installée sur les appareils de démonstration ; secrets en variables d'environnement ;
  - (c) serveur public (VPS) avec nom de domaine et certificat Let's Encrypt, TLS terminé par le conteneur `frontend` (par exemple un serveur Caddy qui obtient et renouvelle le certificat lui-même, sans quatrième service), secrets fournis par les secrets Docker Compose (fichiers hors dépôt montés en lecture seule) ;
  - (d) comme (c), avec un coffre dédié (HashiCorp Vault ou service équivalent).
- **Recommandation** : (c), avec (b) en secours le jour de la soutenance pour ne pas dépendre d'Internet ; les secrets Docker Compose sont une forme minimale de coffre, à présenter comme telle, (d) ne se justifiant que si l'encadrant exige un vrai coffre. Un hébergement hors du Bénin peut constituer un transfert de données à l'étranger : à vérifier avant d'y enrôler des volontaires (RT-15).

### N-7.3 — Rotation de la clé maîtresse
- **Question** : comment changer la clé maîtresse (compromission suspectée, A-11.3, ou renouvellement) sans perdre les gabarits ?
- **Options** : (a) aucune rotation en v1 : changer de clé impose de détruire tous les gabarits et de faire ré-enrôler tout le monde ; (b) version de clé enregistrée avec chaque gabarit dès la v1 et procédure manuelle documentée de rechiffrement (déchiffrer avec l'ancienne clé, chiffrer avec la nouvelle, dans une transaction) ; (c) comme (b), automatisée et périodique.
- **Recommandation** : (b), car enregistrer la version de clé ne coûte rien au moment de concevoir le modèle de données et évite une migration ultérieure. Si la base **et** la clé ont fuité ensemble, le rechiffrement ne suffit pas : seule la révocation (UC-11, nouveau jeton) rend les gabarits volés inutilisables, ce qui est précisément le rôle du BioHashing.

### N-7.4 — Mécanisme d'ajout seul et détection d'altération du journal
- **Question** : comment garantir que le journal n'est jamais modifié, y compris par un accès direct à la base ?
- **Options** : (a) droits PostgreSQL : le rôle utilisé par l'API n'a que les droits d'insertion et de lecture sur le journal ; (b) comme (a), plus un chaînage : chaque entrée contient l'empreinte SHA-256 de l'entrée précédente, et une vérification de la chaîne est proposée dans UC-15 ; (c) comme (b), plus une publication périodique de la dernière empreinte hors de la plateforme (export signé).
- **Recommandation** : (b) : les droits empêchent une API compromise de réécrire l'historique et le chaînage rend détectable une modification faite directement en base, pour quelques lignes de code ; (c) dépasse le besoin du mémoire. La purge à échéance (**point 9**) est exécutée par un rôle de maintenance distinct et journalisée, et la vérification repart de la plus ancienne entrée conservée.

### N-7.5 — Droit de rectification
- **Question** : aucun cas d'utilisation ne permet de corriger son nom ou son email ; comment ce droit s'exerce-t-il ?
- **Options** : (a) modification du nom en libre-service dans « Mes données » (UC-06), email non modifiable : la personne supprime son compte et se réinscrit ; (b) nom et email modifiables en libre-service, l'email avec vérification par code (point 1) ; (c) demande adressée au responsable de traitement (point 8), traitée hors de l'application.
- **Recommandation** : (a). Corriger le nom ne coûte presque rien, alors que changer l'email revient à changer l'identifiant revendiqué à l'authentification et exige une vérification (point 1) que la v1 ne garantit pas ; le texte d'information indique la marche à suivre pour l'email.

### N-7.6 — Sauvegardes et délai réel d'effacement
- **Question** : la v1 sauvegarde-t-elle la base, et pour combien de temps ? Toute donnée effacée (UC-11, UC-12, A-02.2) subsiste dans les sauvegardes jusqu'à leur rotation.
- **Options** : (a) aucune sauvegarde : l'effacement est immédiat et complet, mais une panne fait tout perdre, y compris les données du protocole d'évaluation ; (b) sauvegarde chiffrée quotidienne conservée 7 jours, délai annoncé dans le texte de consentement ; (c) conservation longue (30 jours ou plus).
- **Recommandation** : (b) dès que des volontaires réels sont enrôlés, en annonçant que l'effacement devient total au plus 7 jours après la demande, et en rejouant à partir du journal, après toute restauration, les révocations et suppressions postérieures à la sauvegarde ; (a) suffit tant que la plateforme ne contient que des comptes de test.

### N-7.7 — Mesure des exigences de performance
- **Question** : que signifie précisément « authentification en moins de 2 s sur CPU » ?
- **Options** : (a) temps de traitement serveur seul (réception des images retenues → décision) ; (b) temps perçu : de la fin de la capture guidée (dernière image utile prise) à l'affichage de la décision, réseau compris, hors temps de capture humaine ; (c) durée totale de la séance, saisie de l'email et geste compris.
- **Recommandation** : (b), au 95e centile sur au moins 100 authentifications réelles du protocole (UC-21), un utilisateur à la fois, sur une machine de référence décrite dans le mémoire (proposition : ordinateur portable 4 cœurs, 8 Go de mémoire, sans GPU) ; (a) est journalisé à chaque tentative pour le diagnostic, (c) dépend du geste humain et ne peut pas être garanti par le logiciel. Cibles secondaires proposées : retour qualité en moins de 300 ms par image, finalisation d'enrôlement en moins de 5 s (RT-21).

### N-7.8 — Licence des modèles pré-entraînés
- **Question** : selon le dépôt officiel d'InsightFace, le code est sous licence MIT mais les modèles pré-entraînés fournis (dont buffalo_l) sont réservés à un usage de recherche non commercial (à revérifier lors de l'intégration). La plateforme « déployable » sera-t-elle utilisée hors du cadre académique ?
- **Options** : (a) usage académique uniquement en v1, contrainte écrite dans le README et le mémoire ; (b) prévoir dès la v1 des modèles dont la licence permet un usage réel.
- **Recommandation** : (a) : le mémoire et la démonstration relèvent de la recherche non commerciale ; tout usage réel ultérieur imposerait de revoir les modèles, y compris l'extracteur d'oreille ONNX, dont la licence est à vérifier au moment de son choix (UC-18, **point 22**).

### N-7.9 — Confirmation du hors-périmètre v1
- **Question** : chaque exclusion du tableau 7.2 est-elle confirmée ?
- **Options** : pour chaque ligne, confirmer l'exclusion ou réintégrer l'élément dans la v1.
- **Recommandation** : confirmer H-01 à H-08 et H-10 (cette dernière documentée comme limite connue dans le mémoire), et réintégrer H-09 : le mot de passe protège la révocation et la suppression (**points N-4.1** et **N-4.3**), et sans changement de mot de passe un titulaire qui le croit volé n'a d'autre recours que la suppression de son compte.
