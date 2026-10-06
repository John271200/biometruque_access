/*
 * Jeton « acces » (10 min) délivré après une authentification biométrique réussie.
 * Exigence de sécurité : il reste en mémoire (Pinia) et n'est JAMAIS écrit dans
 * localStorage ni sessionStorage ; un rechargement de page impose donc une nouvelle
 * authentification biométrique.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAccesStore = defineStore('acces', () => {
  const jeton = ref<string | null>(null)
  const expireA = ref(0)
  /** Email utilisé lors de l'authentification, pour pré-remplir une ré-authentification. */
  const email = ref('')

  function definir(valeur: string, expireDans: number, emailUtilise: string): void {
    jeton.value = valeur
    expireA.value = Date.now() + expireDans * 1000
    email.value = emailUtilise
  }

  /** Recale l'échéance sur la validité restante annoncée par le serveur. */
  function synchroniser(expireDans: number): void {
    if (jeton.value !== null) expireA.value = Date.now() + expireDans * 1000
  }

  function effacer(): void {
    jeton.value = null
    expireA.value = 0
  }

  function estValide(): boolean {
    return jeton.value !== null && Date.now() < expireA.value
  }

  return { jeton, expireA, email, definir, synchroniser, effacer, estValide }
})
