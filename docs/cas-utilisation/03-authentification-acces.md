# 3. Authentification et accès à la base protégée (UC-07 à UC-10)

> Statut : **BROUILLON v1 — en attente de validation**.

---

## UC-07 — Se connecter à son espace compte (email + mot de passe)

> **En tant que** titulaire de compte, **je veux** me connecter avec mon email et mon mot de passe, **afin de** gérer mon consentement, mon enrôlement et mes données, sachant que cette connexion ne m'ouvre pas la base protégée.

- **Acteur principal** : Titulaire de compte (y compris utilisateur enrôlé et administrateur)
- **Préconditions** : aucune. Service joignable en HTTPS (ou sur `localhost`).
- **Déclencheur** : soumission du formulaire de connexion, ou redirection depuis une page qui exige une session « compte » (E-06.1, E-07.5).

**Scénario nominal**
1. L'utilisateur saisit son email et son mot de passe.
2. Le système normalise l'email (RM-01.2).
3. Le système vérifie que la connexion « compte » n'est pas suspendue pour cet email (RM-07.4).
4. Le système vérifie le mot de passe contre le hachage Argon2id (RM-01.5), en un temps comparable que le compte existe ou non (RM-07.3).
5. Le système vérifie l'état du compte : non `SUPPRIME` ; email vérifié si le **point 1** est retenu.
6. Le système ouvre une session « compte » (RM-07.5), remet à zéro le compteur d'échecs de mot de passe et journalise la connexion (RM-07.7).
7. Le système oriente l'utilisateur selon son état :
   - consentement `ABSENT`, ou texte de consentement mis à jour (A-02.3) → UC-02 ;
   - consentement `ACCORDE` et enrôlement `NON_ENROLE` ou `REVOQUE` → invitation à s'enrôler (UC-03) ;
   - enrôlement `ENROLE` → page « Mes données » (UC-06), avec le bouton « Accéder à la base protégée » qui lance UC-08 ;
   - rôle `admin` → espace d'administration (UC-13 à UC-18).

**Scénarios alternatifs et d'erreur**
- **E-07.1 Email inconnu ou mot de passe faux** → refus avec un message unique pour les deux cas : « Email ou mot de passe incorrect. » ; échec compté (RM-07.4) ; journalisé sans le mot de passe saisi.
- **E-07.2 Compte supprimé** → traité exactement comme E-07.1.
- **E-07.3 Email non vérifié** (si **point 1** = oui), mot de passe correct → aucun accès aux fonctions du compte ; redirection vers la saisie du code (A-01.1) : « Votre adresse n'est pas encore vérifiée. Saisissez le code reçu par email ou demandez-en un nouveau. » Ce message n'apparaît qu'après un mot de passe correct et ne renseigne donc pas un tiers.
- **E-07.4 Trop d'échecs de mot de passe** → connexion « compte » suspendue pour cet email (RM-07.4) : « Trop de tentatives de connexion. Réessayez après 14 h 32. » Même message que l'email existe ou non.
- **E-07.5 Session expirée** → « Votre session a expiré. Reconnectez-vous. » ; après reconnexion, retour à la page demandée.
- **E-07.6 Session « compte » présentée à la base protégée** → refus et redirection vers UC-08 (E-10.4).
- **A-07.1 Déconnexion** → « Se déconnecter » invalide la session côté serveur (pas seulement dans le navigateur), journalise l'événement et ramène à l'accueil. Effet sur un jeton d'accès biométrique encore valide : **point 4**.
- **A-07.2 Compte supprimé pendant une session ouverte** (UC-12, UC-14) → la session est refusée dès la requête suivante (RM-07.6).
- **A-07.3 Authentification biométrique verrouillée** (UC-09) → la connexion « compte » reste possible (proposition, **point N-3.2**) ; un bandeau signale le verrouillage et son heure de fin (**point N-3.11**).
- **A-07.4 Mot de passe oublié** → aucun cas d'utilisation de la numérotation actuelle ne le couvre (**point N-3.13**).

**Règles métier**
- RM-07.1 — La session « compte » ne donne **jamais** accès à la base protégée, quel que soit le rôle, `admin` compris. Seul le jeton d'accès biométrique délivré par UC-08 y donne accès (UC-10).
- RM-07.2 — Les messages d'échec ne permettent pas de distinguer un email inconnu, un compte supprimé et un mot de passe faux. Cohérence avec le message explicite proposé à l'inscription (**point 2bis**) : **point N-3.3**.
- RM-07.3 — Temps de réponse indépendant de l'existence du compte (calcul Argon2id factice si l'email est inconnu) : **point N-3.3** — proposition : oui.
- RM-07.4 — Limitation des tentatives de mot de passe : **point N-3.2** — proposition : 5 échecs en 15 minutes pour un même email saisi, existant ou non, suspendent la connexion « compte » pendant 15 minutes ; compteur **distinct** du verrouillage biométrique (UC-09).
- RM-07.5 — Durée de la session « compte » : **point N-3.1** — proposition : fin après 30 minutes d'inactivité et au plus tard 8 heures après l'ouverture ; identifiant de session transmis uniquement en HTTPS et inaccessible au JavaScript de la page.
- RM-07.6 — La session est invalidée à la déconnexion et à la suppression du compte ; à un changement de mot de passe si le **point N-3.13** l'introduit.
- RM-07.7 — Chaque connexion, réussie ou échouée, est journalisée (email normalisé, horodatage, adresse IP, résultat). Le mot de passe saisi n'est jamais journalisé (RM-01.5).
- RM-07.8 — L'administrateur se connecte par ce même cas d'utilisation ; un facteur supplémentaire pour ce rôle relève du **point N-3.12**.

**Postcondition** : session « compte » ouverte, limitée à la gestion du compte (UC-02 à UC-06, UC-11, UC-12) ou à l'administration selon le rôle ; aucun accès à la base protégée.

---

## UC-08 — S'authentifier biométriquement (visage + oreille)

> **En tant qu'**utilisateur enrôlé, **je veux** prouver mon identité en présentant mon visage puis mon oreille droite dans un mouvement de tête continu, **afin d'**obtenir un jeton d'accès temporaire à la base protégée, qu'une simple photo de mon visage ne permettrait pas d'obtenir.

- **Acteur principal** : Utilisateur enrôlé
- **Préconditions** : contexte sécurisé (HTTPS ou `localhost`) ; webcam disponible. Aucune session « compte » n'est requise. L'existence du compte, son enrôlement, son consentement et l'absence de verrouillage ne sont pas des préconditions : ils sont vérifiés au pas 2 (RM-08.1).
- **Déclencheur** : clic sur « Accéder à la base protégée », ou redirection depuis UC-10 (jeton absent, expiré ou invalide).

**Scénario nominal**
1. L'utilisateur saisit son email (et son mot de passe si le **point 3** l'exige, A-08.1).
2. Le système normalise l'email (RM-01.2) et applique les vérifications préalables de RM-08.1 ; si l'une échoue, aucune capture n'est ouverte (E-08.1 à E-08.6).
3. Le système ouvre une session d'authentification (RM-08.2) : identifiant de tentative, compte visé, horodatage, adresse IP.
4. Le navigateur ouvre le flux vidéo (E-08.7), affiche le cadre-guide ovale et envoie des images à la cadence du **point 13bis**.
5. Étape visage : le serveur applique à chaque image les critères RM-03.1, renvoie le même retour qualité qu'en UC-03, retient le nombre de captures fixé par RM-08.3, espacées selon RM-03.3, et calcule le plongement ArcFace de chaque capture retenue.
6. Sans couper le flux, le système affiche la consigne de rotation (RM-08.4), le cadre-guide de l'oreille et l'indicateur d'angle.
7. Étape oreille : le serveur applique RM-04.1, RM-04.2 et RM-04.4, recadre et retient les vignettes conformes jusqu'au nombre fixé par RM-08.3.
8. Pendant toute la séquence, le serveur relève les indicateurs de vivacité (lacet image par image, continuité du suivi, horodatages) ; le retour affiché porte sur la qualité et l'angle (RM-08.13).
9. À la dernière capture retenue, le système évalue la vivacité sur la séquence complète (R1, RM-08.10).
10. Le système agrège les plongements visage, calcule et agrège les descripteurs d'oreille (RM-08.5).
11. Le système obtient le jeton personnel de l'utilisateur (**point 19**), en dérive la base orthonormée et calcule un BioHash de 256 bits par modalité (RM-05.3).
12. Le système vérifie l'intégrité des deux gabarits stockés et les déchiffre en mémoire (RM-08.6).
13. Le système calcule le score brut de chaque modalité (RM-08.7), son score normalisé (RM-08.8) et le score fusionné (RM-08.9).
14. Le système évalue les règles R1 à R4 avec les paramètres de décision en vigueur (RM-08.12), en déduit la décision et la raison prioritaire de refus (RM-08.10, RM-08.11).
15. Le système efface de la mémoire toutes les données biométriques de la tentative (RM-08.16).
16. Le système vérifie que l'authentification n'a pas été verrouillée entre-temps (RM-09.7), délivre le jeton d'accès biométrique (RM-08.14) et remet à zéro le compteur d'échecs (UC-09).
17. Le système journalise la tentative (RM-08.15).
18. Le système affiche le résultat (RM-08.13) et redirige vers la base protégée (UC-10).

**Scénarios alternatifs et d'erreur**
- **E-08.1 Email inconnu ou compte supprimé** → aucune capture ; message ne révélant pas l'existence du compte (**point N-3.3**) : « Aucune authentification biométrique n'est possible pour cette adresse. Vérifiez votre saisie, ou connectez-vous à votre espace compte pour finaliser votre enrôlement. » Journalisé (motif « vérification préalable », traitement de l'email saisi : **point 9**) ; non compté pour le verrouillage.
- **E-08.2 Compte non utilisable pour la biométrie** (email non vérifié, consentement `ABSENT` ou `RETIRE`, texte de consentement mis à jour, enrôlement `NON_ENROLE` ou `REVOQUE`) → aucune capture ; même message que E-08.1 (proposition, **point N-3.3**) ; le titulaire légitime trouve la cause exacte dans son espace compte (UC-06). Variante si les messages explicites sont retenus : « Votre compte n'a pas d'enrôlement biométrique actif. Connectez-vous à votre espace compte pour vous enrôler. »
- **E-08.3 Authentification verrouillée** (UC-09) → aucune capture : « Authentification biométrique verrouillée après 5 échecs. Réessayez après 14 h 47. » Ce message révèle l'existence d'un compte enrôlé (**point N-3.3**).
- **E-08.4 Mot de passe incorrect** (si **point 3** = email + mot de passe + biométrie) → « Email ou mot de passe incorrect. » ; compté dans la limitation des tentatives de mot de passe (RM-07.4), pas dans le verrouillage biométrique.
- **E-08.5 Gabarit d'oreille inexploitable** (extracteur ayant produit le gabarit retiré ou indisponible, UC-18, **point 22**) → aucune capture : « Votre enrôlement doit être renouvelé. Connectez-vous à votre espace compte. » (même réserve que E-08.2) ; non compté.
- **E-08.6 Service indisponible** (clé maîtresse absente ou invalide, modèle non chargé) → aucune capture, alerte administrateur : « Authentification biométrique momentanément indisponible. Réessayez plus tard. » Jamais de mode dégradé donnant accès sans biométrie.
- **E-08.7 Webcam refusée ou contexte non sécurisé** → comme E-03.8 ; session fermée sans décision, non comptée.
- **E-08.8 Image non conforme** (visage absent ou multiple, flou, éclairage, cadrage, pose ; oreille hors cadre, masquée, angle insuffisant ou excessif) → image non retenue, avec les messages de E-03.1 à E-03.6 et E-04.1 à E-04.5. Ce n'est pas un échec d'authentification (**point N-3.4**).
- **E-08.9 Délai dépassé** (**point 14** — proposition : 90 secondes pour la session complète) → session fermée sans décision : « Temps écoulé. Recommencez l'authentification. » ; journalisé comme abandon ; non compté (**point N-3.4**).
- **E-08.10 Interruption du flux vidéo** (perte réseau, onglet masqué, caméra débranchée, page rechargée) → la continuité est rompue (RM-04.6), session fermée sans décision : « La vidéo a été interrompue. Recommencez depuis le début. » ; non compté (**point N-3.4**).
- **E-08.11 Abandon volontaire** (bouton « Annuler ») → même traitement que E-08.9.
- **E-08.12 Verrouillage survenu pendant la capture** (5e échec atteint par une autre session sur le même compte) → aucun jeton ne peut être délivré (RM-09.7) ; session fermée avec le message de E-08.3 (**point 26**, **point N-3.9**).
- **E-08.13 Vivacité en échec** (R1 : rotation absente, discontinue, trop rapide ou trop lente, saut d'angle, rupture de suivi, captures visage incohérentes) → accès refusé : « Mouvement de tête non reconnu. Recommencez en tournant lentement la tête vers la gauche, sans à-coups ni pause. » ; compté comme échec si le **point 18** le confirme (proposition : oui, même avec de bons scores).
- **E-08.14 Identité non confirmée** (au moins une des règles R2, R3, R4 en échec) → accès refusé : « Identité non confirmée. Il vous reste 2 essais avant un verrouillage temporaire. » (affichage des essais restants : **point 27**) ; compté comme échec (UC-09). Le détail des règles n'est affiché que selon RM-08.13.
- **E-08.15 Gabarit indéchiffrable** (vérification d'intégrité GCM en échec : gabarit altéré ou substitué, clé maîtresse différente) → aucune comparaison, aucun accès ; alerte administrateur ; événement de sécurité journalisé : « Authentification impossible pour ce compte. L'administrateur a été prévenu. » ; non compté comme échec de l'utilisateur ; suite à donner : **point N-3.8**.
- **E-08.16 Erreur technique d'extraction** (modèle en erreur, image corrompue) → aucune décision : « Traitement impossible, veuillez recommencer. » ; erreur journalisée sans donnée biométrique ; non comptée.
- **A-08.1 Mot de passe exigé** (**point 3**) → un champ mot de passe s'ajoute au pas 1, vérifié avant toute autre condition propre au compte (RM-08.1). Si une session « compte » est active, l'email est prérempli ; dispense de ressaisie du mot de passe dans ce cas : **point 3** — proposition : oui, la session prouvant déjà la connaissance du mot de passe.
- **A-08.2 Défi aléatoire** (si **point 16** = défi) → le serveur tire la consigne au pas 6 ; le client ne la connaît qu'à ce moment. Un défi gauche/droite n'est compatible avec le **point 12** (oreille droite seule) que si l'oreille gauche est aussi enrôlée, ou si le tirage porte sur autre chose que le côté (par exemple une pause imposée à un angle tiré au sort).
- **A-08.3 Tentative du laboratoire d'attaques** (UC-19) → même chaîne de traitement et mêmes paramètres de décision ; tentative étiquetée (type d'attaque : **point 32**) ; place dans le journal et le tableau de bord : **point 33** ; effet sur le verrouillage : **point N-3.10**.
- **A-08.4 Jeton d'accès biométrique déjà valide pour ce compte** → un nouveau jeton est délivré ; sort de l'ancien : **point 4** — proposition : invalidé, un seul jeton actif par compte.
- **A-08.5 Authentification sur mobile** (**point 15**) → même déroulé avec la caméra frontale ; mêmes critères de qualité (RM-03.1, RM-04.2).

**Règles métier**
- RM-08.1 — Vérifications préalables, dans cet ordre, toutes bloquantes ; aucune image n'est acceptée tant qu'elles ne sont pas toutes satisfaites :
  1. service opérationnel : clé maîtresse et modèles chargés (E-08.6) ;
  2. mot de passe correct, si le **point 3** l'exige (E-08.4) ;
  3. compte existant et non `SUPPRIME` (E-08.1) ;
  4. authentification non verrouillée (UC-09, E-08.3) ;
  5. email vérifié si le **point 1** est retenu, consentement `ACCORDE` dans la version en vigueur, enrôlement `ENROLE` (E-08.2) ;
  6. gabarit visage et gabarit oreille « actif pour la décision » présents, extracteur correspondant disponible (E-08.5).
- RM-08.2 — Session d'authentification : à usage unique, liée à un seul compte et à une seule tentative ; toute image reçue hors d'une session ouverte, ou après sa fermeture, est rejetée. Délai maximal : **point 14**. Sessions simultanées sur un même compte : **point N-3.9**. Aucune image n'est écrite sur disque (même règle que RM-03.5) ; conservation éventuelle d'images des tentatives du laboratoire : **point 21**.
- RM-08.3 — Capture : critères de qualité, écart minimal entre captures et contrôle côté serveur identiques à l'enrôlement — RM-03.1, RM-03.3, RM-03.7 pour le visage ; RM-04.1, RM-04.2, RM-04.4, RM-04.6, RM-04.7 pour l'oreille. Nombre de captures retenues par modalité : **point N-3.6** — proposition : 3 pour le visage, 3 pour l'oreille.
- RM-08.4 — Mouvement attendu : **point 16** — proposition : en v1, rotation vers la gauche identique à l'enrôlement (seule option compatible sans autre changement avec le **point 12**). Limite à documenter : un mouvement prévisible protège contre la photo imprimée et l'image fixe, pas contre une vidéo de la rotation rejouée sur un écran ou injectée par une caméra virtuelle ; seul un défi imprévisible (A-08.2) réduit ce risque.
- RM-08.5 — Extraction : plongement ArcFace 512-D pour le visage ; pour l'oreille, l'extracteur qui a produit le gabarit « actif pour la décision » de l'utilisateur (UC-05 pas 6, A-05.2), même s'il diffère de l'extracteur actif par défaut (UC-18, **point 22**), car des descripteurs issus d'extracteurs différents ne sont pas comparables. Agrégation identique à l'enrôlement (**point 11**) : un seul BioHash par modalité.
- RM-08.6 — Les gabarits stockés ne sont déchiffrés qu'en mémoire et pour la seule durée de la comparaison, après vérification de l'étiquette d'authentification GCM et des données additionnelles authentifiées (identifiant utilisateur, modalité, RM-05.4). Aucune comparaison n'est faite sur un gabarit dont l'intégrité n'est pas établie (E-08.15).
- RM-08.7 — Score brut par modalité m (visage v, oreille o) : `s_m = 1 − d_H(b_m, b*_m) / 256`, où `b_m` est le BioHash calculé, `b*_m` le BioHash stocké et `d_H` la distance de Hamming (**point 20**). `s_m` est compris entre 0 et 1 ; 1 signifie des BioHash identiques.
- RM-08.8 — Normalisation z-score : `z_m = (s_m − μ_m) / σ_m`, avec des paramètres propres à chaque modalité et, pour l'oreille, à chaque extracteur. Source et mise à jour de `μ_m` et `σ_m` : **point 23** — proposition : estimés sur un jeu de développement distinct des volontaires évalués, figés et versionnés avec les paramètres de décision.
- RM-08.9 — Fusion par somme pondérée : `S = w_v · z_v + w_o · z_o`. Poids : **point 24** — proposition : `w_v + w_o = 1`, valeurs initiales 0,5 et 0,5 jusqu'aux premières mesures.
- RM-08.10 — Règles de décision. L'accès est accordé **si et seulement si les quatre règles passent** ; aucune ne compense une autre :
  1. **R1 — Vivacité** : séquence frontal → profil continue et conforme à RM-04.5 (valeurs : **point 17**), sans interruption du flux (RM-04.6), sans rupture de suivi (RM-04.4), avec des captures visage cohérentes entre elles (RM-03.4) ;
  2. **R2 — Plancher visage** : score visage ≥ plancher `P_v` ;
  3. **R3 — Plancher oreille** : score oreille ≥ plancher `P_o` ;
  4. **R4 — Seuil de fusion** : `S ≥ T`, où `T` découle du FAR cible réglé par l'administrateur (UC-16).

  R2 et R3 garantissent qu'une modalité excellente, par exemple une photo du visage de la victime, ne compense pas l'autre. Valeurs initiales de `P_v`, `P_o` et `T` : **point 24** ; espace (score brut ou normalisé) dans lequel s'expriment les planchers : **point N-3.7**.
- RM-08.11 — Ordre d'évaluation et raison prioritaire : **point 25** — proposition : les quatre règles sont toujours évaluées et journalisées, sans arrêt à la première en échec, pour que le journal et le laboratoire disposent de tous les verdicts ; la raison de refus retenue est la première règle en échec dans l'ordre R1, R2, R3, R4 (une vivacité en échec rend les scores non significatifs, et un plancher explique un refus plus précisément que le seuil global).
- RM-08.12 — Paramètres de décision (poids, planchers, seuil, paramètres z-score) : lus au moment de la décision ; leur version est consignée avec la tentative. Effet d'une modification survenue pendant une session : **point 30**.
- RM-08.13 — Contenu et exposition du résultat. Le résultat de chaque tentative comprend : décision ; raison prioritaire de refus ; verdict de chaque règle ; scores bruts `s_v` et `s_o` ; scores normalisés `z_v` et `z_o` ; score fusionné `S` ; planchers et seuil appliqués ; indicateurs de vivacité (amplitude, nombre d'images intermédiaires, inversions, durée du mouvement). Il est toujours journalisé intégralement. Ce qui en est affiché : **point 27** — proposition :
  - utilisateur, par défaut : décision et message générique ; R1 est nommée (« Mouvement de tête non reconnu »), R2 à R4 sont regroupées sous « Identité non confirmée » ; nombre d'essais restants avant verrouillage ;
  - mode démonstration, activable par l'administrateur pour la soutenance : résultat complet affiché à l'utilisateur ;
  - administrateur et évaluateur : résultat complet via le journal (UC-15) et le laboratoire (UC-19) ;
  - pendant la capture, le retour en temps réel porte sur la qualité et l'angle uniquement, jamais sur la vivacité ni sur les scores.
- RM-08.14 — Jeton d'accès biométrique : JWT signé par le serveur, valable 10 minutes à compter de son émission, réservé à la base protégée, lié au compte, à l'identifiant de la tentative qui l'a délivré et à l'enrôlement en vigueur à l'émission (contrôles d'UC-10). À ne pas confondre avec le jeton personnel de BioHashing (RM-05.2). Renouvellement, unicité du jeton actif, invalidation : **point 4**.
- RM-08.15 — Journalisation de **chaque** tentative — accordée, refusée, abandonnée ou en erreur — dans le journal d'audit en ajout seul : identifiant de tentative ; compte (ou email saisi pour un compte inconnu, selon le **point 9**) ; horodatages de début et de fin ; adresse IP ; contexte (standard ou laboratoire, avec son étiquette) ; extracteur d'oreille ; version des paramètres de décision ; résultat complet (RM-08.13) ; nombre d'images refusées pour qualité ; durée de traitement (RM-08.17) ; identifiant du jeton émis le cas échéant. Ne sont **jamais** journalisés : image, plongement, descripteur, BioHash, jeton personnel, JWT complet, mot de passe.
- RM-08.16 — Dès la décision rendue, ou à la fermeture de la session sans décision (délai, interruption, abandon, erreur), le système efface de la mémoire images, plongements, descripteurs, BioHash calculés, gabarits déchiffrés, base de projection et jeton personnel en clair. Cet effacement est applicatif (écrasement puis libération des tampons) : l'absence de garantie d'effacement physique dans un environnement à ramasse-miettes est une limite à mentionner dans le rapport.
- RM-08.17 — Performance : décision en moins de 2 secondes sur CPU, sans GPU. Définition mesurable : **point N-3.5** — proposition : durée côté serveur entre la réception de la dernière image retenue et l'envoi du résultat (pas 9 à 18), au 95e centile, sur la machine de référence, modèles préchargés ; le temps de capture et la latence réseau sont exclus.
- RM-08.18 — Les rôles `admin` et `evaluateur` ne dispensent jamais de cette authentification pour accéder à la base protégée.

**Postcondition** : en cas de succès, jeton d'accès biométrique de 10 minutes délivré et compteur d'échecs remis à zéro ; en cas de refus, aucun jeton et compteur mis à jour selon UC-09. Dans tous les cas, la tentative est journalisée et aucune donnée biométrique de la tentative ne subsiste en mémoire ni sur disque.

---

## UC-09 — Être verrouillé temporairement après 5 échecs

> **En tant qu'**utilisateur enrôlé, **je veux** que l'authentification biométrique de mon compte soit suspendue temporairement après 5 échecs, **afin qu'**un imposteur ne puisse pas multiplier les essais (photo, écran, masque) jusqu'à franchir les seuils.

- **Acteur principal** : Utilisateur enrôlé (le verrouillage est déclenché par le système ; l'auteur des échecs peut être un tiers)
- **Préconditions** : enrôlement `ENROLE`.
- **Déclencheur** : un refus comptabilisable (RM-09.1) porte le nombre d'échecs à 5.

**Scénario nominal**
1. À chaque refus comptabilisable rendu par UC-08 (RM-09.1), le système enregistre un échec horodaté pour la clé de verrouillage (RM-09.3).
2. Tant que le seuil n'est pas atteint, la réponse indique le nombre d'essais restants (**point 27** — proposition : oui).
3. Au 5e échec dans la fenêtre de comptage (RM-09.2), l'authentification biométrique du compte est verrouillée (état `VERROUILLE_TEMPORAIREMENT`, dont la portée relève du **point N-3.2**) avec une heure de fin (RM-09.4).
4. Le système journalise le verrouillage : compte, heures de début et de fin, identifiants des tentatives en cause, adresses IP d'origine (RM-09.8).
5. Le système affiche : « Authentification biométrique verrouillée après 5 échecs. Réessayez après 14 h 47. » (heure locale de l'utilisateur).
6. Jusqu'à l'heure de fin, toute demande d'authentification biométrique est refusée avant capture avec le même message (E-08.3).
7. À l'heure de fin, le verrou est levé automatiquement, le compteur est remis à zéro et la levée est journalisée.

**Scénarios alternatifs et d'erreur**
- **A-09.1 Succès avant le 5e échec** → compteur remis à zéro (RM-09.5).
- **A-09.2 Déverrouillage par un administrateur** → levée anticipée depuis la gestion des utilisateurs (UC-13, UC-14), journalisée avec l'administrateur et l'heure, compteur remis à zéro (**point 26** — proposition : motif obligatoire).
- **A-09.3 Verrouillage pendant une authentification en cours** (5e échec atteint par une autre session) → la session en cours ne peut aboutir à un jeton (RM-09.7) ; **point 26** — proposition : fermeture immédiate de la session avec le message de verrouillage, et au plus tard au moment de la décision ; voir aussi **point N-3.9**.
- **A-09.4 Jeton d'accès biométrique délivré avant le verrouillage** → **point 26** — proposition : il reste valide jusqu'à son expiration, car il provient d'une authentification réussie antérieure aux échecs.
- **A-09.5 Nouvel échec après la levée** → le comptage repart de zéro ; allongement progressif des verrouillages successifs : **point 26** — proposition : non en v1.
- **A-09.6 Information du titulaire** → **point N-3.11** — proposition : bandeau à la prochaine connexion « compte » (« 5 tentatives d'authentification échouées le 06/10 entre 14 h 20 et 14 h 32 ») et mention dans « Mes données » (UC-06).
- **A-09.7 Verrouillage provoqué par un tiers** (déni de service : quiconque connaît l'email peut épuiser les 5 essais) → risque inhérent à une clé par compte, à arbitrer au **point 26** ; atténué par la durée courte, le déverrouillage administrateur et le maintien de la connexion « compte » (**point N-3.2**).
- **A-09.8 Tentatives du laboratoire d'attaques** → **point N-3.10**.

**Règles métier**
- RM-09.1 — Ce qui compte comme échec :
  1. compte toujours : un refus dont au moins une des règles R2, R3, R4 est en échec, quelle que soit la raison prioritaire affichée (E-08.14) ;
  2. refus par R1 seule (vivacité en échec, scores suffisants) : **point 18** — proposition : compte, sinon un attaquant peut ajuster indéfiniment un artefact de présentation ;
  3. ne comptent pas : refus avant capture (E-08.1 à E-08.7), images refusées pour qualité, délai dépassé, interruption, abandon (**point N-3.4**), échec d'intégrité GCM ou erreur technique (**point N-3.8**) ;
  4. mot de passe faux au pas 1 d'UC-08 : compté dans la limitation de mot de passe (RM-07.4), pas ici (**point N-3.2**) ;
  5. tentatives du laboratoire : **point N-3.10**.
- RM-09.2 — Seuil : 5 échecs. Mode de comptage : **point 26** — proposition : 5 échecs sans succès intermédiaire dans une fenêtre glissante de 30 minutes ; un échec plus ancien sort du décompte.
- RM-09.3 — Clé de verrouillage : **point 26** — proposition : le compte (email normalisé) ; en complément, limitation par adresse IP tous comptes confondus (20 échecs par heure bloquent l'adresse 1 heure) contre le balayage de plusieurs comptes.
- RM-09.4 — Durée : **point 26** — proposition : 15 minutes. L'heure de fin est fixée au moment du verrouillage et affichée à l'utilisateur.
- RM-09.5 — Remise à zéro du compteur : authentification réussie ; levée du verrou, automatique ou par un administrateur. Effet d'une révocation suivie d'un ré-enrôlement (UC-11) : **point N-3.14**.
- RM-09.6 — Portée : le verrou bloque l'authentification biométrique (UC-08). Effet sur la connexion « compte » (UC-07) et sur la révocation / ré-enrôlement (UC-11) : **point N-3.2** et **point N-3.14** — proposition : UC-07 reste possible, UC-11 est bloqué jusqu'à la levée.
- RM-09.7 — Aucun jeton d'accès biométrique n'est délivré pour un compte verrouillé, y compris à l'issue d'une session d'authentification ouverte avant le verrouillage : l'état de verrouillage est vérifié à l'ouverture de la session **et** au moment de la décision.
- RM-09.8 — Journalisation : pose du verrou, levée automatique, levée par un administrateur (qui, quand, motif). Chaque échec est par ailleurs journalisé par UC-08 (RM-08.15).
- RM-09.9 — Le message de verrouillage indique l'heure de fin ; il n'indique ni les scores ni les règles en échec des tentatives en cause.

**Postcondition** : authentification biométrique du compte suspendue jusqu'à l'heure de fin, événement journalisé ; levée automatique à l'heure de fin ou anticipée par un administrateur.

---

## UC-10 — Consulter la base protégée avec le jeton biométrique

> **En tant qu'**utilisateur enrôlé authentifié biométriquement, **je veux** consulter les dossiers de la base protégée pendant la validité de mon jeton, **afin d'**accéder à des données sensibles seulement après avoir prouvé mon identité par le visage et l'oreille.

- **Acteur principal** : Utilisateur enrôlé titulaire d'un jeton d'accès biométrique (UC-08)
- **Préconditions** : jeton d'accès biométrique délivré par UC-08 depuis moins de 10 minutes.
- **Déclencheur** : redirection automatique après UC-08, ou toute navigation dans la base protégée.

**Scénario nominal**
1. Le navigateur présente le jeton d'accès biométrique avec **chaque** requête vers la base protégée.
2. Le système contrôle le jeton (RM-10.2).
3. Le système affiche la liste des dossiers fictifs (RM-10.3) en lecture seule (RM-10.4), avec la mention « Données fictives de démonstration » et le temps de validité restant (« Accès valable encore 7 min 32 s »).
4. L'utilisateur ouvre un dossier ; le système contrôle à nouveau le jeton, puis affiche le dossier.
5. Le système journalise chaque accès (RM-10.5).
6. L'utilisateur quitte la base (A-10.2) ou le jeton expire (E-10.2).

**Scénarios alternatifs et d'erreur**
- **E-10.1 Jeton absent** → redirection vers UC-08 : « Authentifiez-vous par le visage et l'oreille pour accéder à la base protégée. »
- **E-10.2 Jeton expiré** → refus et redirection vers UC-08 : « Votre accès biométrique a expiré (validité : 10 minutes). Authentifiez-vous de nouveau pour continuer. » Après une nouvelle authentification réussie, retour à la page demandée. Page déjà affichée au moment de l'expiration : **point 4** — proposition : son contenu est masqué à l'expiration et n'est pas conservé dans le cache du navigateur.
- **E-10.3 Jeton altéré ou signature invalide** → refus sans détail sur la cause : « Accès refusé. Authentifiez-vous de nouveau. » ; journalisé comme événement de sécurité.
- **E-10.4 Session « compte » présentée à la place du jeton biométrique** → refus : « Votre session compte ne donne pas accès à la base protégée. Une authentification par le visage et l'oreille est nécessaire. » ; redirection vers UC-08 ; journalisé.
- **E-10.5 Situation du compte changée depuis l'émission** (compte supprimé, consentement retiré, gabarits révoqués ou ré-enrôlés : UC-02 A-02.2, UC-11, UC-12, UC-14) → refus immédiat même si le jeton n'a pas expiré : « Votre accès n'est plus valide : votre compte ou votre enrôlement a changé. » ; journalisé.
- **E-10.6 Jeton invalidé** (remplacé par un jeton plus récent, ou fermé par « Quitter la base protégée », selon le **point 4**) → traité comme E-10.2.
- **E-10.7 Dossier inexistant** → « Dossier introuvable. » ; tentative journalisée.
- **E-10.8 Demande de création, modification ou suppression** → refusée (RM-10.4) ; journalisée.
- **A-10.1 Renouvellement** → **point 4** — proposition : aucun renouvellement sans nouvelle authentification biométrique ; durée fixe de 10 minutes, non prolongée par l'activité ; avertissement « Votre accès expire dans 1 minute ».
- **A-10.2 Sortie volontaire** → « Quitter la base protégée » invalide le jeton côté serveur (proposition, **point 4**) et journalise la sortie.
- **A-10.3 Administrateur ou évaluateur** (rôle : **point 31**) → aucun privilège particulier : même jeton biométrique exigé (RM-08.18), même journalisation.

**Règles métier**
- RM-10.1 — La base protégée n'est accessible qu'avec un jeton d'accès biométrique valide délivré par UC-08. Ni la session « compte », ni les rôles `admin` ou `evaluateur` n'y donnent accès.
- RM-10.2 — Contrôles à **chaque** requête, tous bloquants :
  1. jeton présent ;
  2. signature valide ;
  3. jeton de type « accès biométrique », réservé à la base protégée (un titre de session « compte » est refusé, E-10.4) ;
  4. jeton non expiré (10 minutes après l'émission) ;
  5. compte existant et non `SUPPRIME` ;
  6. consentement `ACCORDE` et enrôlement `ENROLE` ;
  7. enrôlement identique à celui en vigueur à l'émission (aucune révocation ni ré-enrôlement depuis) ;
  8. jeton non invalidé (**point 4**).

  Les contrôles 5 à 8 imposent une vérification côté serveur à chaque requête : la signature et la date d'expiration ne suffisent pas.
- RM-10.3 — Ressource : données entièrement fictives, générées, sans aucune donnée personnelle réelle. Nature et champs : **point 28** — proposition : une cinquantaine de dossiers patients de démonstration (identifiant, nom et prénom fictifs, date de naissance, sexe, groupe sanguin, allergies, antécédents, traitement en cours, date de dernière consultation, médecin référent fictif), avec la mention « Données fictives » sur chaque page.
- RM-10.4 — Accès en lecture seule, sauf décision contraire au **point 29**. Granularité : **point 29** — proposition : tout utilisateur authentifié consulte l'ensemble des dossiers, sans cloisonnement par utilisateur ; ni export ni impression proposés en v1.
- RM-10.5 — Journalisation de **chaque** accès, accordé ou refusé : compte, horodatage, adresse IP, ressource demandée (liste ou identifiant du dossier), résultat et motif de refus, identifiant du jeton, identifiant de la tentative d'authentification qui l'a délivré. Ce dernier lien donne accès, dans le journal, aux scores et à la décision de cette tentative (RM-08.15). Le jeton complet n'est jamais journalisé.
- RM-10.6 — Durée du jeton : 10 minutes à compter de l'émission (RM-08.14). Renouvellement sans biométrie, unicité du jeton actif, invalidation à la sortie : **point 4**.

**Postcondition** : chaque consultation et chaque refus sont journalisés et rattachés à la tentative d'authentification qui a délivré le jeton ; après expiration ou invalidation, aucune donnée de la base n'est servie sans nouvelle authentification biométrique.

---

## Nouveaux points à trancher (section 3)

Points non couverts par la liste 1 à 36, référencés ci-dessus ; à reporter dans `08-points-a-trancher.md` lors de la validation.

### N-3.1 — Forme et durée de la session « compte » (UC-07)
- **Question** : quelle durée d'inactivité, quelle durée maximale, et plusieurs sessions simultanées sont-elles permises ?
- **Options** : (a) 30 minutes d'inactivité, 8 heures au maximum, sessions multiples ; (b) 15 minutes d'inactivité, 1 heure au maximum, une seule session ; (c) session jusqu'à la fermeture du navigateur.
- **Recommandation** : (a). La session « compte » n'ouvre pas la base protégée, une durée confortable est donc acceptable ; la protection des actions destructrices (UC-11, UC-12) se traite dans ces cas d'utilisation.

### N-3.2 — Limitation des tentatives de mot de passe et portée du verrouillage (UC-07, UC-08, UC-09)
- **Question** : les échecs de mot de passe et les échecs biométriques partagent-ils un compteur ? Le verrouillage biométrique bloque-t-il aussi la connexion « compte », alors que l'état `VERROUILLE_TEMPORAIREMENT` est rangé sur l'axe « Compte » (section 1.3) ?
- **Options** : (a) compteur commun, verrou global du compte ; (b) deux compteurs distincts, chaque verrou ne bloquant que son facteur ; (c) aucune limitation du mot de passe.
- **Recommandation** : (b), la limitation du mot de passe s'appliquant à l'email saisi qu'il existe ou non. Un verrou global laisserait un tiers bloquer tout le compte, y compris « Mes données » où le titulaire constaterait l'attaque ; l'état de verrouillage serait alors à déplacer sur un axe propre à l'authentification biométrique à l'étape 2.

### N-3.3 — Cohérence de la politique d'énumération des comptes (UC-01, UC-07, UC-08)
- **Question** : faut-il masquer l'existence d'un compte à l'authentification biométrique alors que le point 2bis propose de la révéler à l'inscription ?
- **Options** : (a) accepter l'énumération partout : messages explicites en UC-08 (inconnu, non enrôlé), risque documenté ; (b) la masquer partout : message neutre à l'inscription (« Si cette adresse est disponible, un code vous a été envoyé », ce qui suppose le point 1 = oui), messages neutres et temps de réponse comparables en UC-07 et UC-08 ; (c) exiger le mot de passe en UC-08 (point 3) : le message neutre « Email ou mot de passe incorrect » fait barrière et les messages suivants peuvent être explicites.
- **Recommandation** : trancher avec les points 2bis et 3 ensemble, car masquer l'existence en UC-08 ne protège rien si UC-01 la révèle ; (c) est la plus cohérente, le mot de passe réservant au seul titulaire les messages explicites (« non enrôlé », « verrouillé jusqu'à … »). Avec l'email seul, le message de verrouillage d'UC-09 révèle de toute façon l'existence d'un compte enrôlé.

### N-3.4 — Effet des refus de qualité, délais, interruptions et abandons sur le verrouillage (UC-08, UC-09)
- **Question** : une session de capture close sans décision compte-t-elle parmi les 5 échecs ?
- **Options** : (a) non ; (b) oui ; (c) non, mais limitation séparée du nombre de sessions de capture ouvertes par compte et par adresse IP.
- **Recommandation** : (c), par exemple 20 sessions par heure. Sans comparaison, ces sessions n'apprennent rien à un attaquant sur les scores et les compter pénaliserait l'utilisateur mal éclairé, mais elles consomment du CPU et doivent être bornées.

### N-3.5 — Définition mesurable de « authentification < 2 s sur CPU » (UC-08)
- **Question** : quel intervalle, quelle statistique, quelle machine ?
- **Options** : (a) côté serveur, de la réception de la dernière image retenue à l'envoi du résultat ; (b) côté navigateur, de l'envoi de la dernière image à l'affichage du résultat, réseau compris ; (c) durée totale de la session, capture comprise.
- **Recommandation** : (a), au 95e centile sur les tentatives du protocole d'évaluation (UC-21), sur une machine de référence décrite dans le mémoire (processeur, nombre de cœurs, mémoire), modèles préchargés. (b) dépend du réseau et (c) du comportement de l'utilisateur ; la latence du retour qualité par image (proposition : < 300 ms) mérite une mesure séparée.

### N-3.6 — Nombre de captures retenues et agrégation à l'authentification (UC-08)
- **Question** : faut-il 5 captures visage et 5 captures oreille comme à l'enrôlement ?
- **Options** : (a) 5 + 5, agrégées comme à l'enrôlement ; (b) 3 + 3, agrégées ; (c) 1 + 1 (meilleure image de chaque étape) ; (d) un score par capture, puis maximum ou moyenne des scores.
- **Recommandation** : (b). L'agrégation lisse le bruit de capture comme à l'enrôlement (point 11) tout en raccourcissant la session et le calcul ; (d) multiplie les comparaisons et, avec le maximum, augmente le FAR.

### N-3.7 — Espace dans lequel s'expriment les planchers par modalité (R2, R3)
- **Question** : les planchers portent-ils sur le score brut ou sur le score normalisé ?
- **Options** : (a) score brut `s_m` ; (b) score normalisé `z_m`.
- **Recommandation** : (a). Un plancher brut est lisible (« au moins 70 % de bits concordants ») et ne bouge pas si les paramètres z-score (point 23) sont réestimés ; la normalisation ne sert qu'à rendre les deux scores additionnables pour R4.

### N-3.8 — Conséquences d'un échec d'intégrité d'un gabarit (UC-08)
- **Question** : que devient un compte dont un gabarit échoue à la vérification GCM ?
- **Options** : (a) simple refus, nouvel essai possible ; (b) authentification biométrique suspendue pour ce compte jusqu'à analyse par l'administrateur, puis ré-enrôlement (UC-11) ; (c) si plusieurs comptes sont touchés, passage du service en « authentification indisponible ».
- **Recommandation** : (b) et (c) combinées, sans incrémenter le compteur de l'utilisateur. Un échec isolé signale une altération ou une substitution de gabarit ; un échec généralisé signale un problème de clé maîtresse, pas une attaque sur un compte.

### N-3.9 — Sessions d'authentification simultanées sur un même compte (UC-08, UC-09)
- **Question** : peut-on ouvrir plusieurs sessions de capture en parallèle pour le même compte ?
- **Options** : (a) sans limite ; (b) une seule session ouverte, toute nouvelle session ferme la précédente sans décision ; (c) une seule, toute nouvelle session est refusée tant que la précédente n'est pas close.
- **Recommandation** : (b). Elle empêche de lancer des tentatives en parallèle pour dépasser 5 essais avant que le verrou ne prenne effet, sans permettre à un tiers de bloquer durablement le titulaire comme le ferait (c).

### N-3.10 — Effet des tentatives du laboratoire sur le verrouillage (UC-09, UC-19)
- **Question** : les tentatives étiquetées (photo, écran, imposteur réel…) visant le compte d'un volontaire incrémentent-elles son compteur ?
- **Options** : (a) oui, comme toute tentative ; (b) non, compteur ignoré en contexte laboratoire.
- **Recommandation** : (b), en conservant strictement la même chaîne de décision et les mêmes paramètres qu'en UC-08 : sinon une campagne d'attaques verrouillerait les volontaires, et une chaîne différente rendrait les mesures non représentatives. L'analyse des résultats doit rappeler qu'en usage réel le verrouillage borne l'attaquant à 5 essais.

### N-3.11 — Information du titulaire après un verrouillage (UC-09)
- **Question** : le titulaire est-il prévenu d'un verrouillage qu'il n'a peut-être pas provoqué ?
- **Options** : (a) aucune information ; (b) bandeau à la prochaine connexion « compte » et mention dans « Mes données » ; (c) (b) et email.
- **Recommandation** : (b) en v1, (c) si le point 1 met en place l'envoi d'emails. Un verrouillage non provoqué par le titulaire est le signe d'une attaque qu'il doit connaître.

### N-3.12 — Authentification renforcée du rôle administrateur (UC-07, UC-14, UC-16, UC-18)
- **Question** : avec son seul mot de passe, un administrateur peut abaisser planchers et seuil (UC-16), changer d'extracteur (UC-18) ou révoquer des utilisateurs (UC-14) ; la sécurité biométrique de la base se ramène alors à celle de ce mot de passe.
- **Options** : (a) mot de passe seul ; (b) ressaisie du mot de passe avant chaque action sensible ; (c) actions sensibles subordonnées à un jeton d'accès biométrique valide de l'administrateur (UC-08).
- **Recommandation** : (c), qui réutilise le mécanisme du projet et répond à l'objection prévisible du jury ; la consultation (UC-13, UC-15, UC-17) peut rester accessible avec la session « compte ». Le point 5 doit alors prévoir l'enrôlement du premier administrateur.

### N-3.13 — Mot de passe oublié et changement de mot de passe (UC-07)
- **Question** : aucun cas d'utilisation de la numérotation fixe ne couvre ces besoins ; sans eux, un titulaire qui oublie son mot de passe ne peut plus exercer ses droits (UC-06, UC-11, UC-12).
- **Options** : (a) hors périmètre v1, réinitialisation manuelle par l'administrateur ; (b) réinitialisation par code envoyé par email (suppose le point 1 = oui) ; (c) réinitialisation après authentification biométrique réussie.
- **Recommandation** : (b) si le point 1 est retenu, sinon (a), documentée comme limite ; (c) est à écarter car elle mélange les deux niveaux d'accès (section 1.4) et ferait d'une caractéristique non secrète un moyen de reprendre le compte.

### N-3.14 — Révocation et ré-enrôlement depuis une simple session « compte » (UC-07, UC-09, UC-11)
- **Question** : UC-11 n'exige qu'une session « compte ». Quiconque connaît le mot de passe peut donc révoquer les gabarits du titulaire, s'enrôler avec son propre visage et sa propre oreille, puis obtenir un jeton d'accès biométrique : la protection de la base se réduit au mot de passe. Faut-il en outre autoriser UC-11 pendant un verrouillage ?
- **Options** : (a) accepter et documenter ; (b) ré-enrôlement subordonné à une authentification biométrique réussie avec les gabarits actuels ; (c) ré-enrôlement validé par un administrateur ; (d) délai de carence avec information du titulaire.
- **Recommandation** : (b) lorsque les gabarits actuels sont encore utilisables, (c) sinon (perte, compromission, changement d'extracteur), et UC-11 bloqué pendant un verrouillage. Le petit nombre d'utilisateurs (10 à 15 volontaires) rend la validation administrateur supportable.
