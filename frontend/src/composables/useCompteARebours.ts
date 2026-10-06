/* Compte à rebours en secondes jusqu'à une échéance (horodatage en millisecondes). */
import { computed, onBeforeUnmount, ref } from 'vue'

export function useCompteARebours(echeance: () => number) {
  const maintenant = ref(Date.now())
  const minuteur = window.setInterval(() => {
    maintenant.value = Date.now()
  }, 1000)
  onBeforeUnmount(() => window.clearInterval(minuteur))

  const secondesRestantes = computed(() => Math.max(0, Math.ceil((echeance() - maintenant.value) / 1000)))
  return { secondesRestantes }
}
