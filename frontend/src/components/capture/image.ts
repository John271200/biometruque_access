/*
 * Préparation des images envoyées au serveur et dessin de la surimpression.
 *
 * Repères : le serveur reçoit l'image NON miroir (ce que voit la caméra) et renvoie des
 * cadres normalisés dans ce repère. L'affichage, lui, est en miroir (CSS scaleX(-1)) sur la
 * vidéo ET sur le canvas de surimpression : les cadres se dessinent donc tels quels, et le
 * miroir CSS les aligne sur la vidéo. Aucun texte n'est dessiné sur ce canvas (il serait inversé).
 */
import type { Cadre } from '../../api'

const LARGEUR_ENVOI = 640
const HAUTEUR_ENVOI = 480
const QUALITE_JPEG = 0.85

const COULEURS = {
  conforme: '#3ddc84',
  aCorriger: '#ffb020',
  oreille: '#38bdf8',
  liseré: 'rgb(0 0 0 / 55%)',
  voile: 'rgb(15 21 32 / 45%)',
  guide: 'rgb(255 255 255 / 92%)',
}

interface Zone {
  x: number
  y: number
  largeur: number
  hauteur: number
}

/**
 * Zone source centrée au format 4:3 : c'est exactement la partie visible à l'écran,
 * la vidéo étant affichée dans un cadre 4:3 avec `object-fit: cover`.
 */
function recadrage4x3(largeur: number, hauteur: number): Zone {
  const ratio = LARGEUR_ENVOI / HAUTEUR_ENVOI
  if (largeur / hauteur > ratio) {
    const largeurUtile = hauteur * ratio
    return { x: (largeur - largeurUtile) / 2, y: 0, largeur: largeurUtile, hauteur }
  }
  const hauteurUtile = largeur / ratio
  return { x: 0, y: (hauteur - hauteurUtile) / 2, largeur, hauteur: hauteurUtile }
}

/** Crée une fonction qui capture l'image courante de la vidéo en JPEG 640×480 non miroir. */
export function creerCaptureur(): (video: HTMLVideoElement) => Promise<Blob | null> {
  const canvas = document.createElement('canvas')
  canvas.width = LARGEUR_ENVOI
  canvas.height = HAUTEUR_ENVOI
  const contexte = canvas.getContext('2d')

  return (video) => {
    if (!contexte || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || video.videoWidth === 0) {
      return Promise.resolve(null)
    }
    const zone = recadrage4x3(video.videoWidth, video.videoHeight)
    contexte.drawImage(video, zone.x, zone.y, zone.largeur, zone.hauteur, 0, 0, LARGEUR_ENVOI, HAUTEUR_ENVOI)
    return new Promise((resoudre) => canvas.toBlob(resoudre, 'image/jpeg', QUALITE_JPEG))
  }
}

export interface OptionsSurimpression {
  guideOvale: boolean
  cadreVisage: Cadre | null
  cadreOreille: Cadre | null
  visageConforme: boolean
}

function dessinerOvale(contexte: CanvasRenderingContext2D, largeur: number, hauteur: number): void {
  const cx = largeur / 2
  const cy = hauteur * 0.48
  const rx = largeur * 0.19
  const ry = hauteur * 0.36
  contexte.save()
  // Voile autour de l'ovale pour indiquer où placer le visage.
  contexte.beginPath()
  contexte.rect(0, 0, largeur, hauteur)
  contexte.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2)
  contexte.fillStyle = COULEURS.voile
  contexte.fill('evenodd')
  contexte.beginPath()
  contexte.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2)
  contexte.setLineDash([10, 8])
  contexte.lineWidth = 3
  contexte.strokeStyle = COULEURS.guide
  contexte.stroke()
  contexte.restore()
}

function dessinerCadre(
  contexte: CanvasRenderingContext2D,
  [x1, y1, x2, y2]: Cadre,
  largeur: number,
  hauteur: number,
  couleur: string,
): void {
  const x = x1 * largeur
  const y = y1 * hauteur
  const l = (x2 - x1) * largeur
  const h = (y2 - y1) * hauteur
  contexte.save()
  // Liseré sombre sous le trait coloré : lisible quel que soit l'arrière-plan.
  contexte.lineWidth = 6
  contexte.strokeStyle = COULEURS.liseré
  contexte.strokeRect(x, y, l, h)
  contexte.lineWidth = 3
  contexte.strokeStyle = couleur
  contexte.strokeRect(x, y, l, h)
  contexte.restore()
}

/** Redessine la surimpression à la taille affichée du canvas (net sur écrans haute densité). */
export function dessinerSurimpression(canvas: HTMLCanvasElement, options: OptionsSurimpression): void {
  const largeur = canvas.clientWidth
  const hauteur = canvas.clientHeight
  const contexte = canvas.getContext('2d')
  if (!contexte || largeur === 0 || hauteur === 0) return
  const densite = window.devicePixelRatio || 1
  const largeurPixels = Math.round(largeur * densite)
  const hauteurPixels = Math.round(hauteur * densite)
  if (canvas.width !== largeurPixels || canvas.height !== hauteurPixels) {
    canvas.width = largeurPixels
    canvas.height = hauteurPixels
  }
  contexte.setTransform(densite, 0, 0, densite, 0, 0)
  contexte.clearRect(0, 0, largeur, hauteur)
  if (options.guideOvale) dessinerOvale(contexte, largeur, hauteur)
  if (options.cadreVisage) {
    const couleur = options.visageConforme ? COULEURS.conforme : COULEURS.aCorriger
    dessinerCadre(contexte, options.cadreVisage, largeur, hauteur, couleur)
  }
  if (options.cadreOreille) dessinerCadre(contexte, options.cadreOreille, largeur, hauteur, COULEURS.oreille)
}
