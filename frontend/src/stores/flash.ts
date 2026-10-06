/*
 * Message ponctuel affiché après une navigation (ex. « Compte supprimé »).
 * Il reste visible sur la page d'arrivée puis disparaît à la navigation suivante.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type TypeMessage = 'info' | 'succes' | 'alerte' | 'erreur'

interface MessageFlash {
  texte: string
  type: TypeMessage
  affiche: boolean
}

export const useFlashStore = defineStore('flash', () => {
  const message = ref<MessageFlash | null>(null)

  function publier(texte: string, type: TypeMessage = 'info'): void {
    message.value = { texte, type, affiche: false }
  }

  /** Appelé après chaque navigation : marque le message comme vu, ou le retire s'il l'était déjà. */
  function apresNavigation(): void {
    if (message.value === null) return
    if (message.value.affiche) message.value = null
    else message.value.affiche = true
  }

  function fermer(): void {
    message.value = null
  }

  return { message, publier, apresNavigation, fermer }
})
