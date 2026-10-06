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
