/* Aides de navigation partagées par les vues. */
import type { LocationQueryValue } from 'vue-router'

/** Première valeur textuelle d'un paramètre de requête (?cle=valeur). */
export function parametre(valeur: LocationQueryValue | LocationQueryValue[] | undefined): string | null {
  const premiere = Array.isArray(valeur) ? valeur[0] : valeur
  return typeof premiere === 'string' && premiere !== '' ? premiere : null
}

/** Chemin interne sûr (évite les redirections ouvertes vers un autre domaine). */
export function cheminInterne(valeur: string | null, parDefaut: string): string {
  return valeur !== null && valeur.startsWith('/') && !valeur.startsWith('//') ? valeur : parDefaut
}
