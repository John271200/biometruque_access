/*
 * Consignes vocales en français (speechSynthesis) : indispensables quand l'utilisateur
 * tourne la tête de profil et ne voit plus l'écran. Une consigne est prononcée quand
 * le message change, au plus une toutes les 2,5 s, sans répéter la même phrase.
 */
import { onBeforeUnmount, ref, watch } from 'vue'

const INTERVALLE_MIN_MS = 2500

export function useGuidageVocal() {
  const disponible = typeof window !== 'undefined' && 'speechSynthesis' in window
  const actif = ref(disponible)

  let voix: SpeechSynthesisVoice | null = null
  let dernierePhrase = ''
  let dernierInstant = Number.NEGATIVE_INFINITY
  let enAttente: string | null = null
  let minuteur: number | undefined

  /** Préfère une voix fr-FR locale, puis toute voix française. */
  function choisirVoix(): void {
    const francaises = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith('fr'))
    const frFr = francaises.filter((v) => v.lang.toLowerCase().replace('_', '-') === 'fr-fr')
    voix = frFr.find((v) => v.localService) ?? frFr[0] ?? francaises[0] ?? null
  }

  function prononcer(texte: string): void {
    const enonce = new SpeechSynthesisUtterance(texte)
    enonce.lang = voix?.lang ?? 'fr-FR'
    if (voix) enonce.voice = voix
    // La consigne la plus récente remplace celle en cours : elle seule est pertinente.
    if (window.speechSynthesis.speaking || window.speechSynthesis.pending) window.speechSynthesis.cancel()
    window.speechSynthesis.speak(enonce)
    dernierePhrase = texte
    dernierInstant = performance.now()
  }

  function annulerAttente(): void {
    window.clearTimeout(minuteur)
    minuteur = undefined
    enAttente = null
  }

  /**
   * Demande la lecture d'une consigne. Si la précédente date de moins de 2,5 s, la nouvelle
   * est mise en attente (seule la plus récente est conservée). `prioritaire` ignore ce délai.
   */
  function annoncer(texte: string, prioritaire = false): void {
    if (!disponible || !actif.value || texte === '') return
    if (texte === dernierePhrase && !prioritaire) {
      enAttente = null
      return
    }
    const ecoule = performance.now() - dernierInstant
    if (prioritaire || ecoule >= INTERVALLE_MIN_MS) {
      annulerAttente()
      prononcer(texte)
      return
    }
    enAttente = texte
    if (minuteur === undefined) {
      minuteur = window.setTimeout(() => {
        const texteEnAttente = enAttente
        minuteur = undefined
        enAttente = null
        if (texteEnAttente !== null && actif.value) prononcer(texteEnAttente)
      }, INTERVALLE_MIN_MS - ecoule)
    }
  }

  function taire(): void {
    if (!disponible) return
    annulerAttente()
    window.speechSynthesis.cancel()
  }

  if (disponible) {
    choisirVoix()
    window.speechSynthesis.addEventListener('voiceschanged', choisirVoix)
  }

  watch(actif, (estActif) => {
    if (!estActif) taire()
  })

  onBeforeUnmount(() => {
    taire()
    if (disponible) window.speechSynthesis.removeEventListener('voiceschanged', choisirVoix)
  })

  return { disponible, actif, annoncer }
}
