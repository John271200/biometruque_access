/* Mise en forme des dates, scores et durées pour l'affichage (fuseau et conventions du navigateur). */

const formatDateHeure = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })
const formatHeure = new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' })
const formatDate = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' })
const formatScore = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 3, maximumFractionDigits: 3 })

function lireDate(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? null : date
}

/** « 6 oct. 2026, 14:35 » en heure locale ; « — » si absent. */
export function formaterDateHeure(iso: string | null | undefined): string {
  const date = lireDate(iso)
  return date ? formatDateHeure.format(date) : '—'
}

/** « 6 octobre 2026 » ; la valeur brute est conservée si elle n'est pas une date. */
export function formaterDate(iso: string | null | undefined): string {
  const date = lireDate(iso)
  if (date) return formatDate.format(date)
  return iso ?? '—'
}

/** Heure locale d'une échéance (« 14:35 »), précédée de la date si ce n'est pas aujourd'hui. */
export function formaterEcheance(iso: string | null | undefined): string {
  const date = lireDate(iso)
  if (!date) return '—'
  const memeJour = date.toDateString() === new Date().toDateString()
  return memeJour ? formatHeure.format(date) : formatDateHeure.format(date)
}

/** Vrai si la date ISO est dans le futur. */
export function estFutur(iso: string | null | undefined): boolean {
  const date = lireDate(iso)
  return date !== null && date.getTime() > Date.now()
}

/** Score à trois décimales (« 0,734 ») ; « — » quand le serveur masque la valeur (null). */
export function formaterScore(valeur: number | null | undefined): string {
  return typeof valeur === 'number' ? formatScore.format(valeur) : '—'
}

/** Durée en « mm:ss ». */
export function formaterDuree(secondes: number): string {
  const s = Math.max(0, Math.floor(secondes))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}
