# 8. Points à trancher

> **C'est ici que tu décides.** Chaque point indique la question, les options et ma
> recommandation. Rien n'est appliqué tant que tu n'as pas répondu. Tu peux répondre
> point par point (« 3 : b », « 19 : a », « 24 : OK ») ; les cas d'utilisation seront mis à
> jour en conséquence avant de passer à l'étape 2.
>
> Les points marqués ★ changent fortement le modèle de données ou la sécurité : à trancher en priorité.

## A. Comptes et sessions

**1. Vérification de l'email à l'inscription**
- a) Code à 6 chiffres envoyé par email (nécessite un serveur SMTP ; en local, un outil type Mailpit).
- b) Pas de vérification en v1.
- *Recommandation : b.* L'email sert uniquement d'identifiant revendiqué ; la sécurité repose sur la biométrie. Risque accepté et documenté : quelqu'un peut s'inscrire avec l'email d'autrui (il ne peut pas pour autant s'authentifier à sa place). a) en perspective.

**2. Politique de mot de passe** — proposition : 12 caractères minimum, une majuscule, une minuscule, un chiffre, refus des mots de passe courants.
**2bis. Email déjà utilisé** — a) message explicite ; b) message neutre.
- *Recommandation : explicite à l'inscription (ergonomie), neutre à la connexion et à l'authentification.*

**3. ★ Facteurs exigés à l'authentification biométrique**
- a) Email + biométrie (lettre du brief : « l'utilisateur saisit son email »).
- b) Email + mot de passe + biométrie (deux facteurs de nature différente).
- *Recommandation : a.* Elle respecte le brief et isole la contribution de la biométrie, ce qui rend l'évaluation du mémoire lisible. b) est plus robuste mais change le discours. Dans les deux cas, la session « compte » (mot de passe) ne donne **jamais** accès à la base protégée.

**4. Jeton biométrique (JWT 10 min)**
- Renouvelable sans repasser la biométrie ? *Recommandation : non*, après 10 min on repasse la capture.
- Un seul jeton actif par utilisateur ? *Recommandation : oui*, un nouveau jeton invalide le précédent.
- Déconnexion = révocation immédiate du jeton (liste de révocation par identifiant de jeton) ? *Recommandation : oui.*

**5. Création du premier administrateur**
- a) Commande en ligne de commande lancée sur le serveur ; b) variables d'environnement lues au premier démarrage ; c) migration de base.
- *Recommandation : a* (aucun secret persistant dans l'environnement).

**5bis. ★ L'espace d'administration exige-t-il aussi la biométrie ?**
- a) Mot de passe seul ; b) l'administrateur s'enrôle comme tout le monde, et les actions sensibles (seuils, suppression) exigent un jeton biométrique valide.
- *Recommandation : b.* Sinon l'administrateur, qui peut baisser les seuils, devient le maillon faible de tout le dispositif. Le mot de passe seul ne sert qu'au tout premier démarrage.

## B. Consentement et protection des données

**6. Durée de conservation des gabarits**
- *Recommandation : 12 mois après le dernier accès réussi ; pour les volontaires de l'évaluation, destruction au plus tard 3 mois après la soutenance.*

**7. Effet du retrait du consentement**
- a) Gabarits détruits, compte conservé (`NON_ENROLE`, peut consentir à nouveau plus tard).
- b) Suppression totale du compte.
- *Recommandation : a.* Retirer son consentement et effacer son compte sont deux droits distincts ; UC-12 couvre l'effacement.

**8. Responsable de traitement et texte du consentement**
- Qui apparaît comme responsable : toi, ton encadrant, l'IFRI ? Contact à afficher ?
- Le Code du numérique béninois encadre strictement les données biométriques : **vérifie avec ton encadrant** si une formalité auprès de l'APDP est nécessaire, même pour un traitement académique avec volontaires. À citer dans le mémoire dans tous les cas.

**9. Journaux après suppression d'un compte**
- a) Suppression des lignes ; b) pseudonymisation (l'identité est remplacée par un identifiant non réversible) ; c) conservation telle quelle.
- *Recommandation : b*, durée de conservation des journaux 12 mois. On garde la traçabilité et les statistiques (EER) sans identifier la personne. Même traitement pour l'historique des consentements.

## C. Enrôlement

**10. Enrôlement atomique** — a) visage **et** oreille dans la même session, ou rien ; b) reprise possible étape par étape.
- *Recommandation : a.* C'est la seule option cohérente avec le défi de vivacité « un mouvement continu ».

**11. Agrégation des 5 captures**
- a) Moyenne des 5 vecteurs puis **un** BioHash par modalité ; b) 5 BioHash conservés, score = meilleur ou moyenne des 5 comparaisons.
- *Recommandation : a* (simple, rapide, standard pour ArcFace). b) pourrait réduire le FRR de l'oreille : à comparer dans UC-21.

**12. Oreille droite seulement** — *Recommandation : oui en v1* (brief) ; oreille gauche en perspective.

**13. Valeurs chiffrées de qualité et de pose** — les propositions de RM-03.1, RM-03.3, RM-04.1 et RM-04.2 (détection ≥ 0,6, visage ≥ 120 px, Laplacien ≥ 100, luminance 60–200, profil 60°–100°, vignette ≥ 64 × 96 px, 500 ms entre captures).
- *Recommandation : les prendre comme valeurs de départ, puis les calibrer sur tes propres captures (webcam, éclairage de la salle) avant l'enrôlement des volontaires.*
**13bis. Cadence d'envoi des images** — proposition 3 images/s pour le retour qualité. Le mode de transport (envoi par lots ou flux continu) sera tranché à l'étape 3.

**14. Délais et essais d'enrôlement** — proposition : 60 s maximum par étape ; après 3 enrôlements avortés, pause de 10 minutes.

**15. ★ Ergonomie du profil : l'utilisateur ne voit plus l'écran**
- Quand on tourne la tête de 60° à 90° pour montrer l'oreille, **on ne voit plus l'écran**, ni sur PC ni sur mobile : le cadre-guide et les messages deviennent invisibles au moment critique.
- a) Retour sonore (bip qui s'accélère quand l'oreille est bien placée, consignes vocales en français) ; b) capture automatique dès que les critères sont remplis, sans action de l'utilisateur ; c) une tierce personne tient la caméra.
- *Recommandation : a + b.* Et sur mobile : autoriser l'authentification, mais recommander le PC pour l'enrôlement ?

## D. Vivacité

**16. ★ Mouvement demandé à l'authentification**
- a) Identique à l'enrôlement (face → profil gauche).
- b) Ajouter un élément aléatoire (ex. consigne finale tirée au hasard : « revenez de face » / « levez le menton »).
- *Recommandation : a en v1*, en documentant la limite : une **vidéo rejouée** de la victime qui tourne la tête passerait un défi fixe. Ajouter « rejeu vidéo » au laboratoire (point 32) pour le mesurer honnêtement ; b) en perspective.

**17. Critères chiffrés de vivacité** — proposition RM-04.5 : au moins 8 images intermédiaires, lacet globalement monotone (au plus 2 inversions), amplitude ≥ 50°, mouvement entre 1,5 s et 15 s.

**18. Un échec de vivacité compte-t-il pour le verrouillage ?** — *Recommandation : oui*, même si les scores biométriques sont bons ; sinon un attaquant peut essayer des photos à l'infini.

## E. Gabarits et protection

**19. ★ Où vit le jeton personnel du BioHashing ?**
- a) En base, chiffré avec la clé maîtresse : transparent pour l'utilisateur. Mais si la base **et** la clé fuient, l'attaquant a le jeton et le gabarit, et la protection se réduit au chiffrement.
- b) Dérivé du mot de passe (Argon2) : impose le mot de passe à l'authentification (point 3 b), et tout changement de mot de passe impose un ré-enrôlement.
- c) Remis à l'utilisateur (fichier ou QR code) : vrai facteur de possession, mais ergonomie lourde.
- *Recommandation : a si point 3 = a ; b si point 3 = b.* Dans tous les cas, le mémoire doit évaluer le scénario « jeton volé » (voir section 6).

**20. Score par modalité** — score = 1 − (distance de Hamming / 256). *Recommandation : oui.*

**21. ★ Conservation d'images pour la recherche**
- Le protocole d'évaluation (UC-21) doit pouvoir rejouer les deux extracteurs d'oreille sur les mêmes captures. Or le brief interdit toute image conservée : **les deux exigences se contredisent.**
- a) Aucune image, jamais : l'évaluation se limite aux scores calculés au moment de la capture (pas de rejeu, pas de nouvel extracteur testable après coup).
- b) Consentement « recherche » séparé et facultatif, réservé aux 10–15 volontaires : images chiffrées, pseudonymisées, stockées à part, jamais utilisées pour l'authentification, destruction datée.
- *Recommandation : b.*

**22. Coexistence des deux extracteurs d'oreille** — a) un seul, choisi avant l'enrôlement des volontaires ; b) deux gabarits d'oreille par utilisateur tant que l'évaluation n'est pas terminée.
- *Recommandation : b, puis a une fois l'extracteur choisi.*

## F. Décision et fusion

**23. Source des paramètres de normalisation z-score**
- a) Calibration figée sur un jeu de référence (versionnée, reproductible) ; b) recalcul glissant sur les tentatives réelles.
- *Recommandation : a.* b) est manipulable : un attaquant peut fausser les statistiques par des tentatives répétées, et les résultats ne sont pas reproductibles.

**24. Poids et planchers initiaux** — proposition : poids 0,6 visage / 0,4 oreille ; planchers fixés pour un FRR ≤ 5 % par modalité sur les données de calibration. Provisoires, recalculés après UC-21.

**25. Ordre des règles** — R1 vivacité → R2 plancher visage → R3 plancher oreille → R4 seuil de fusion.
- *Recommandation : toutes les règles sont évaluées (pour le journal et le rapport), la raison affichée est la première en échec.*

**26. Verrouillage**
- Clé : a) compte revendiqué ; b) compte + adresse IP.
- *Recommandation : 5 échecs consécutifs sur le compte, verrouillage de 15 minutes, compteur remis à zéro après un succès, déverrouillage manuel par l'administrateur. Plus une limite par IP contre le balayage de nombreux comptes.* Risque à documenter : quelqu'un peut verrouiller volontairement le compte d'autrui (déni de service ciblé).

**27. ★ Détail de la réponse en cas d'échec**
- a) Détail complet (scores chiffrés) partout ; b) détail complet uniquement en laboratoire et dans le journal admin, message générique en production ; c) en production, verdict de chaque règle (passée / échouée) et raison, **sans valeurs numériques**.
- *Recommandation : c.* Elle respecte le brief (« décision de chaque règle, raison du refus ») sans offrir à un attaquant un oracle de score qu'il pourrait optimiser par essais successifs. Les scores complets restent visibles en labo et pour l'administrateur.

## G. Base protégée et administration

**28. Ressource sensible fictive** — proposition : environ 50 dossiers patients **fictifs** générés par script (identifiant, nom fictif, âge, groupe sanguin, antécédents, traitement, médecin référent), affichés avec la mention « données fictives ».

**29. Granularité d'accès** — a) tout utilisateur authentifié voit tous les dossiers, en lecture seule ; b) contrôle d'accès par dossier ou par rôle.
- *Recommandation : a.* L'objet du mémoire est l'authentification, pas le contrôle d'accès fin.

**30. Réglage des seuils** — effet immédiat sur les tentatives suivantes, chaque réglage versionné (auteur, date), bornes de validation, retour à une version antérieure possible. *Recommandation : oui à tout.*

## H. Laboratoire et évaluation

**31. Rôle évaluateur** — a) distinct ; b) fusionné avec administrateur.
- *Recommandation : distinct mais cumulable sur un même compte* (séparation des privilèges, argument utile pour la partie sécurité du mémoire).

**32. Liste fermée des types de tentative** — légitime, imposteur réel, photo imprimée, photo sur écran de téléphone, oreille cachée par les cheveux, visage masqué ; *recommandation : ajouter « rejeu vidéo »* (voir point 16).

**33. Tentatives du laboratoire** — a) même journal avec un drapeau « laboratoire », exclues par défaut des statistiques de production ; b) stockage séparé. *Recommandation : a.*

**34. Contenu du rapport PDF** — proposition : contexte et date, version des paramètres de décision, effectifs, taux d'acceptation par type de tentative, taux de rejet par règle, graphiques, limites de l'expérience.

## I. Projet

**35. Dépôt de code** — ✅ **Tranché** : `John271200/biometruque_access`.

**36. Réutilisation de la démo ORL + IIT Delhi**
- a) S'en servir pour calibrer les seuils et le z-score de départ, et comme point de comparaison dans UC-21 ; b) repartir de zéro.
- *Recommandation : a*, sans reprendre son code tel quel avant relecture. **Où se trouve le code de la démo ?** (Remarque : les images ORL sont en niveaux de gris 92 × 112 px ; les scores ArcFace obtenus dessus ne seront pas représentatifs d'une webcam.)

## J. Points soulevés pendant la rédaction détaillée

Chaque point est développé (question, options, recommandation) à la fin de la section
indiquée. Les doublons entre sections sont regroupés : **une seule réponse suffit** pour
chaque ligne.

### ★ À trancher en priorité

| Point(s) | Sujet | Où |
|---|---|---|
| **N-3.14 = N-4.1** | **Révocation + ré-enrôlement avec le seul mot de passe** : un voleur de mot de passe peut enrôler *son* visage et prendre le compte. Quelle preuve exiger avant de révoquer ? | [03](03-authentification-acces.md), [04](04-maitrise-des-donnees.md) |
| **N-5.13** | Source de la vérité terrain pour le tableau de bord (FAR/FRR/EER impossibles sans étiquettes) | [05](05-administration.md) |
| **N-6.10** | Scénarios de protection à rapporter (sans BioHashing / jeton secret / jeton volé) — sinon EER artificiellement proche de 0 | [06](06-laboratoire-evaluation.md) |
| **N-6.4** | Consentement des participants au laboratoire (cible, imposteur, personne dont la photo sert d'attaque) | [06](06-laboratoire-evaluation.md) |
| **N-3.7 = N-5.11** | Les planchers R2/R3 portent-ils sur le score brut ou le score normalisé ? | [03](03-authentification-acces.md), [05](05-administration.md) |
| **N-7.8** | Licence des modèles InsightFace (usage de recherche non commercial) | [07](07-regles-transversales.md) |

### Authentification et accès — [section 3](03-authentification-acces.md)
| Point | Sujet |
|---|---|
| N-3.1 | Forme et durée de la session « compte » |
| N-3.2 | Compteur des échecs de mot de passe et portée du verrouillage |
| N-3.3 | Cohérence de la politique d'énumération des comptes (avec 2bis) |
| N-3.4 | Effet des refus de qualité, délais et abandons sur le verrouillage |
| N-3.5 = N-7.7 | Définition mesurable de « < 2 s sur CPU » |
| N-3.6 | Nombre de captures à l'authentification (le MVP utilise 3 + 3) |
| N-3.8 | Conséquences d'un échec d'intégrité d'un gabarit |
| N-3.9 | Sessions d'authentification simultanées sur un même compte |
| N-3.10 = N-6.2 | Effet des tentatives du laboratoire sur le compte ciblé |
| N-3.11 | Information du titulaire après un verrouillage |
| N-3.12 ≈ 5bis | Authentification renforcée de l'administrateur |
| N-3.13 ≈ N-7.9 | Mot de passe oublié / changement de mot de passe (hors périmètre ?) |

### Maîtrise des données — [section 4](04-maitrise-des-donnees.md)
| Point | Sujet |
|---|---|
| N-4.2 | Motif de révocation et suites données |
| N-4.3 | Forme de la confirmation de suppression |
| N-4.4 | Effet immédiat ou délai de grâce |
| N-4.5 | Sort de l'historique des consentements après suppression |
| N-4.6 | Notification par email des opérations sensibles |
| N-4.7 | Conservation d'un compte sans gabarit actif |

### Administration — [section 5](05-administration.md)
| Point | Sujet |
|---|---|
| N-5.1 | Fuseau d'affichage des horodatages |
| N-5.2 | Confirmation forte des actes sensibles |
| N-5.3 | Motif obligatoire des actes administratifs |
| N-5.4 | Réglages d'ergonomie des listes |
| N-5.5 | Gestion des rôles depuis l'interface |
| N-5.6 | Actions sur un autre administrateur ou sur soi-même |
| N-5.7 | Information de l'utilisateur visé |
| N-5.8 | Organisation des journaux consultables |
| N-5.9 | Export des journaux et traçabilité des consultations |
| N-5.10 = N-7.4 | Intégrité du journal (ajout seul, chaînage) |
| N-5.12 | Dérivation du seuil de fusion à partir du FAR cible |
| N-5.14 | Effectifs minimaux et incertitude affichée |
| N-5.15 | Un jeu de paramètres de décision par extracteur d'oreille |
| N-5.16 | Bascule d'extracteur quand des utilisateurs sont déjà enrôlés |

### Laboratoire et évaluation — [section 6](06-laboratoire-evaluation.md)
| Point | Sujet |
|---|---|
| N-6.1 | Forme du mode laboratoire (campagnes) |
| N-6.3 | Fiabilité et correction de l'étiquetage |
| N-6.5 | Tentatives interrompues et échecs d'acquisition |
| N-6.6 | Format de l'export CSV |
| N-6.7 | Pseudonymisation des personnes |
| N-6.8 | Exécution du protocole et sorties |
| N-6.9 | Protocole de collecte et constitution des comparaisons |
| N-6.11 | Séparation calibration / test |
| N-6.12 | Statistiques sur petits effectifs |
| N-6.13 | Courbe DET de « fusion + garde-fou » |
| N-6.14 | Critère de choix de l'extracteur d'oreille |

### Transversal — [section 7](07-regles-transversales.md)
| Point | Sujet |
|---|---|
| N-7.1 | Réglages transverses à valider en bloc |
| N-7.2 | Cible de déploiement, certificat TLS, coffre de secrets |
| N-7.3 | Rotation de la clé maîtresse |
| N-7.5 | Droit de rectification |
| N-7.6 | Sauvegardes et délai réel d'effacement |
| N-7.9 | Confirmation du hors-périmètre v1 |
