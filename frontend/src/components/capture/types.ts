/* Types propres au composant de capture guidée. */
import type { RetourImage } from '../../api'

/** Envoie une image JPEG à la session indiquée et renvoie l'analyse du serveur. */
export type EnvoiImage = (sessionId: string, image: Blob) => Promise<RetourImage>

/** Abandonne une session de capture inachevée (appel DELETE, au mieux). */
export type AbandonSession = (sessionId: string) => Promise<void>

/** Échec définitif d'une capture, émis par l'événement « echec ». */
export interface EchecCapture {
  code: string
  titre: string
  message: string
}
