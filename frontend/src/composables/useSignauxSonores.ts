/*
 * Signaux sonores (WebAudio) : bip court à chaque image retenue, mélodie montante en fin
 * de capture réussie, tonalité descendante en cas d'échec. Le contexte audio doit être
 * activé lors d'un geste utilisateur (clic sur « Démarrer ») pour respecter les règles
 * de lecture automatique des navigateurs.
 */
import { onBeforeUnmount } from 'vue'

export function useSignauxSonores() {
  let contexte: AudioContext | null = null

  function activer(): void {
    if (typeof AudioContext === 'undefined') return
    contexte ??= new AudioContext()
    void contexte.resume()
  }

  function tonalite(frequence: number, decalage: number, duree: number, forme: OscillatorType = 'sine'): void {
    if (contexte === null) return
    const oscillateur = contexte.createOscillator()
    const gain = contexte.createGain()
    const debut = contexte.currentTime + decalage
    oscillateur.type = forme
    oscillateur.frequency.value = frequence
    // Enveloppe courte pour éviter les claquements.
    gain.gain.setValueAtTime(0.0001, debut)
    gain.gain.exponentialRampToValueAtTime(0.25, debut + 0.015)
    gain.gain.exponentialRampToValueAtTime(0.0001, debut + duree)
    oscillateur.connect(gain).connect(contexte.destination)
    oscillateur.start(debut)
    oscillateur.stop(debut + duree + 0.05)
  }

  /** Bip court (image retenue). */
  function bip(): void {
    tonalite(1046.5, 0, 0.12)
  }

  /** Arpège montant (capture terminée). */
  function succes(): void {
    tonalite(659.25, 0, 0.18)
    tonalite(783.99, 0.15, 0.18)
    tonalite(1046.5, 0.3, 0.4)
  }

  /** Deux notes descendantes (échec ou accès refusé). */
  function echec(): void {
    tonalite(392, 0, 0.3, 'triangle')
    tonalite(261.63, 0.25, 0.45, 'triangle')
  }

  onBeforeUnmount(() => {
    void contexte?.close()
    contexte = null
  })

  return { activer, bip, succes, echec }
}
