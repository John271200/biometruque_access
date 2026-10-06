# Consignes pour les assistants IA — BioAccess

- Méthode imposée, en étapes verrouillées : voir `SUIVI.md`. Ne jamais commencer une étape
  tant que la précédente n'est pas cochée (validée explicitement par l'auteur).
- Ne jamais décider seul d'une règle métier, du modèle de données ou de l'architecture :
  proposer, marquer « proposition », renvoyer à `docs/cas-utilisation/08-points-a-trancher.md`, demander.
- Langue : français (documentation, interface, commentaires de code).
- Contraintes fixes : CPU uniquement ; aucune image brute ni vecteur biométrique en clair
  conservé après l'enrôlement ; HTTPS hors localhost ; authentification < 2 s sur CPU.
