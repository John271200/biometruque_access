/*
 * Session « compte » (gestion de son espace). Le jeton compte est conservé en
 * sessionStorage : il survit à un rechargement de l'onglet mais pas à sa fermeture.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, ApiError, type Utilisateur } from '../api'

const CLE_JETON = 'bioaccess.jeton_compte'
const CLE_EXPIRATION = 'bioaccess.jeton_compte_expire_a'

function lire(cle: string): string | null {
  try {
    return sessionStorage.getItem(cle)
  } catch {
    return null
  }
}

function ecrire(cle: string, valeur: string | null): void {
  try {
    if (valeur === null) sessionStorage.removeItem(cle)
    else sessionStorage.setItem(cle, valeur)
  } catch {
    // Stockage indisponible (navigation privée stricte) : la session reste en mémoire.
  }
}

export const useCompteStore = defineStore('compte', () => {
  const jeton = ref<string | null>(lire(CLE_JETON))
  const expireA = ref<number>(Number(lire(CLE_EXPIRATION) ?? 0))
  const utilisateur = ref<Utilisateur | null>(null)

  /** Vrai dès qu'un jeton est présent (affichage) ; la validité est vérifiée par sessionValide(). */
  const connecte = computed(() => jeton.value !== null)

  function oublier(): void {
    jeton.value = null
    expireA.value = 0
    utilisateur.value = null
    ecrire(CLE_JETON, null)
    ecrire(CLE_EXPIRATION, null)
  }

  /** Vérifie la présence et l'échéance du jeton ; l'oublie s'il a expiré. */
  function sessionValide(): boolean {
    if (jeton.value === null) return false
    if (Date.now() >= expireA.value) {
      oublier()
      return false
    }
    return true
  }

  /** Renvoie le jeton courant ou lève une erreur 401 si la session a disparu. */
  function jetonRequis(): string {
    if (jeton.value === null) {
      throw new ApiError(401, 'SESSION_ABSENTE', 'Votre session a expiré. Reconnectez-vous.')
    }
    return jeton.value
  }

  async function connecter(email: string, motDePasse: string): Promise<Utilisateur> {
    const reponse = await api.ouvrirSession(email, motDePasse)
    jeton.value = reponse.jeton_compte
    expireA.value = Date.now() + reponse.expire_dans * 1000
    utilisateur.value = reponse.utilisateur
    ecrire(CLE_JETON, reponse.jeton_compte)
    ecrire(CLE_EXPIRATION, String(expireA.value))
    return reponse.utilisateur
  }

  async function deconnecter(): Promise<void> {
    const actuel = jeton.value
    oublier()
    if (actuel === null) return
    try {
      await api.fermerSession(actuel)
    } catch {
      // Le jeton est déjà oublié côté navigateur ; un échec serveur n'empêche pas la déconnexion.
    }
  }

  async function charger(): Promise<Utilisateur> {
    const donnees = await api.moi(jetonRequis())
    utilisateur.value = donnees
    return donnees
  }

  function definirUtilisateur(donnees: Utilisateur): void {
    utilisateur.value = donnees
  }

  return {
    jeton,
    utilisateur,
    connecte,
    sessionValide,
    jetonRequis,
    connecter,
    deconnecter,
    oublier,
    charger,
    definirUtilisateur,
  }
})
