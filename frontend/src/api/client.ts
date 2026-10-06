/*
 * Client HTTP de l'API BioAccess : appels relatifs à /api, en-tête Authorization,
 * et conversion uniforme des erreurs {"detail": {"code", "message", "champs"?}} en ApiError.
 */

const PREFIXE_API = '/api'

export type TypeJeton = 'compte' | 'acces'

export class ApiError extends Error {
  /** Code HTTP (0 si le serveur n'a pas pu être joint). */
  readonly statut: number
  /** Code machine du contrat (ex. « COMPTE_VERROUILLE »). */
  readonly code: string
  /** Messages d'erreur par champ de formulaire (erreurs 422 notamment). */
  readonly champs: Record<string, string>
  /** Contenu brut de l'erreur, pour les données complémentaires (ex. verrouille_jusqua). */
  readonly details: Record<string, unknown>

  constructor(
    statut: number,
    code: string,
    message: string,
    champs: Record<string, string> = {},
    details: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.statut = statut
    this.code = code
    this.champs = champs
    this.details = details
  }
}

interface OptionsRequete {
  methode?: 'GET' | 'POST' | 'DELETE'
  jeton?: { type: TypeJeton; valeur: string }
  json?: unknown
  image?: Blob
}

const MESSAGES_PAR_STATUT: Record<number, string> = {
  0: 'Impossible de joindre le serveur BioAccess. Vérifiez votre connexion puis réessayez.',
  400: 'La requête est invalide.',
  401: 'Authentification requise ou expirée.',
  403: 'Accès refusé.',
  404: 'Ressource introuvable.',
  409: "L'opération est en conflit avec l'état actuel.",
  413: 'Le fichier envoyé est trop volumineux.',
  422: 'Certaines informations sont invalides.',
  423: 'Le compte est temporairement verrouillé.',
  429: 'Trop de requêtes : patientez quelques instants.',
}

const MESSAGE_SERVEUR = 'Le serveur a rencontré une erreur. Réessayez dans un instant.'

let surSessionCompteExpiree: (() => void) | null = null

/** Enregistre l'action à mener quand le jeton « compte » est refusé (expiré ou invalide). */
export function definirGestionnaireSessionExpiree(gestionnaire: () => void): void {
  surSessionCompteExpiree = gestionnaire
}

function estObjet(valeur: unknown): valeur is Record<string, unknown> {
  return typeof valeur === 'object' && valeur !== null && !Array.isArray(valeur)
}

function messageParDefaut(statut: number): string {
  return MESSAGES_PAR_STATUT[statut] ?? MESSAGE_SERVEUR
}

/** Ramène les clés de champs à leur dernier segment (« body.email » → « email »). */
function normaliserChamps(valeur: unknown): Record<string, string> {
  if (!estObjet(valeur)) return {}
  const champs: Record<string, string> = {}
  for (const [cle, message] of Object.entries(valeur)) {
    const nom = cle.split('.').pop() ?? cle
    champs[nom] = Array.isArray(message) ? message.join(' ') : String(message)
  }
  return champs
}

function construireErreur(statut: number, corps: unknown): ApiError {
  const detail = estObjet(corps) ? corps.detail : undefined
  if (!estObjet(detail)) {
    // Erreur hors contrat (ex. « Not Found » de FastAPI) : message français générique.
    return new ApiError(statut, `HTTP_${statut}`, messageParDefaut(statut))
  }
  const supplements = estObjet(corps) ? corps : {}
  return new ApiError(
    statut,
    typeof detail.code === 'string' ? detail.code : `HTTP_${statut}`,
    typeof detail.message === 'string' && detail.message !== '' ? detail.message : messageParDefaut(statut),
    normaliserChamps(detail.champs),
    { ...supplements, ...detail },
  )
}

async function lireCorps(reponse: Response): Promise<unknown> {
  if (reponse.status === 204) return undefined
  const type = reponse.headers.get('content-type') ?? ''
  if (!type.includes('json')) return undefined
  try {
    return await reponse.json()
  } catch {
    return undefined
  }
}

/** Effectue un appel à l'API et renvoie le corps JSON typé, ou lève une ApiError. */
export async function requete<T>(chemin: string, options: OptionsRequete = {}): Promise<T> {
  const entetes: Record<string, string> = { Accept: 'application/json' }
  let corps: BodyInit | undefined
  if (options.image) {
    entetes['Content-Type'] = 'image/jpeg'
    corps = options.image
  } else if (options.json !== undefined) {
    entetes['Content-Type'] = 'application/json'
    corps = JSON.stringify(options.json)
  }
  if (options.jeton) {
    entetes.Authorization = `Bearer ${options.jeton.valeur}`
  }

  let reponse: Response
  try {
    reponse = await fetch(PREFIXE_API + chemin, {
      method: options.methode ?? 'GET',
      headers: entetes,
      body: corps,
      credentials: 'same-origin',
    })
  } catch {
    throw new ApiError(0, 'RESEAU_INDISPONIBLE', messageParDefaut(0))
  }

  const contenu = await lireCorps(reponse)
  if (!reponse.ok) {
    const erreur = construireErreur(reponse.status, contenu)
    // Seuls les refus de jeton (JETON_EXPIRE, JETON_INVALIDE…) ferment la session :
    // un mot de passe erroné lors d'une révocation ne doit pas déconnecter l'utilisateur.
    if (erreur.statut === 401 && options.jeton?.type === 'compte' && erreur.code.startsWith('JETON_')) {
      surSessionCompteExpiree?.()
    }
    throw erreur
  }
  if (reponse.status !== 204 && contenu === undefined) {
    throw new ApiError(reponse.status, 'REPONSE_INVALIDE', 'Réponse inattendue du serveur.')
  }
  return contenu as T
}

/** Message à afficher pour une erreur quelconque (les erreurs internes ne sont pas exposées). */
export function messageErreur(erreur: unknown): string {
  if (erreur instanceof ApiError) return erreur.message
  return 'Une erreur inattendue est survenue. Réessayez.'
}
