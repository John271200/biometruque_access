/*
 * Accès à la webcam : ouverture du flux, diagnostic des erreurs (permission,
 * absence de caméra, contexte non sécurisé) et arrêt des pistes au démontage.
 */
import { onBeforeUnmount, ref, type Ref } from 'vue'

export type ErreurCamera =
  | 'contexte_non_securise'
  | 'non_supporte'
  | 'permission_refusee'
  | 'aucune_camera'
  | 'camera_occupee'
  | 'inconnue'

export const MESSAGES_CAMERA: Record<ErreurCamera, string> = {
  contexte_non_securise:
    "Le navigateur n'autorise la caméra que sur une page sécurisée. Ouvrez BioAccess en HTTPS, ou en local via http://localhost.",
  non_supporte:
    "Ce navigateur ne permet pas d'accéder à la caméra. Utilisez une version récente de Chrome, Edge, Firefox ou Safari.",
  permission_refusee:
    "L'accès à la caméra a été refusé. Autorisez la caméra pour ce site (icône à gauche de la barre d'adresse), puis cliquez sur «\u00a0Réessayer\u00a0».",
  aucune_camera: 'Aucune caméra n’a été détectée. Branchez une webcam, puis cliquez sur «\u00a0Réessayer\u00a0».',
  camera_occupee:
    'La caméra est déjà utilisée par une autre application (visioconférence…). Fermez-la, puis cliquez sur «\u00a0Réessayer\u00a0».',
  inconnue: 'Impossible de démarrer la caméra. Réessayez ou changez de navigateur.',
}

const CONTRAINTES: MediaStreamConstraints = {
  video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
  audio: false,
}

function classerErreur(erreur: unknown): ErreurCamera {
  const nom = erreur instanceof Error || erreur instanceof DOMException ? erreur.name : ''
  switch (nom) {
    case 'NotAllowedError':
    case 'SecurityError':
      return 'permission_refusee'
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'aucune_camera'
    case 'NotReadableError':
    case 'AbortError':
      return 'camera_occupee'
    default:
      return 'inconnue'
  }
}

/** Attend que la vidéo connaisse ses dimensions réelles. */
function attendreDimensions(video: HTMLVideoElement): Promise<void> {
  if (video.videoWidth > 0) return Promise.resolve()
  return new Promise((resoudre) => video.addEventListener('loadedmetadata', () => resoudre(), { once: true }))
}

export function useCamera(video: Ref<HTMLVideoElement | null>) {
  const erreur = ref<ErreurCamera | null>(null)
  const active = ref(false)
  let flux: MediaStream | null = null

  function arreter(): void {
    flux?.getTracks().forEach((piste) => piste.stop())
    flux = null
    if (video.value) video.value.srcObject = null
    active.value = false
  }

  async function demarrer(): Promise<boolean> {
    erreur.value = null
    if (!window.isSecureContext) {
      erreur.value = 'contexte_non_securise'
      return false
    }
    if (typeof navigator.mediaDevices?.getUserMedia !== 'function') {
      erreur.value = 'non_supporte'
      return false
    }
    try {
      flux = await navigator.mediaDevices.getUserMedia(CONTRAINTES)
      const element = video.value
      if (!element) throw new Error('Élément vidéo absent')
      element.srcObject = flux
      await element.play()
      await attendreDimensions(element)
      active.value = true
      return true
    } catch (e) {
      arreter()
      erreur.value = classerErreur(e)
      return false
    }
  }

  onBeforeUnmount(arreter)

  return { erreur, active, demarrer, arreter }
}
