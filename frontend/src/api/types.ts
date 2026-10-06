/*
 * Types TypeScript reflétant le contrat d'API du MVP
 * (docs/mvp/CONTRAT-MVP.md, sections 2 et 3). Toute évolution du contrat doit être
 * répercutée ici en premier : le compilateur signale ensuite les écrans concernés.
 */

export type EtatConsentement = 'ABSENT' | 'ACCORDE' | 'RETIRE'
export type EtatEnrolement = 'NON_ENROLE' | 'ENROLE' | 'REVOQUE'
export type CoteOreille = 'droite' | 'gauche'
export type ModeCapture = 'enrolement' | 'authentification'
export type EtapeCapture = 'visage' | 'rotation' | 'oreille' | 'terminee' | 'echec'

/** Le contrat ne fixe pas le type des identifiants (entier ou UUID) : les deux sont acceptés. */
export type Identifiant = string | number

/** Version du texte de consentement, renvoyée telle quelle lors du POST /consentement. */
export type VersionConsentement = string | number

/** Cadre [x1, y1, x2, y2] normalisé entre 0 et 1, exprimé dans l'image NON miroir. */
export type Cadre = [number, number, number, number]

export interface Utilisateur {
  id: Identifiant
  nom: string
  email: string
  role: string
  consentement: {
    etat: EtatConsentement
    version: VersionConsentement | null
    date: string | null
  }
  enrolement: {
    etat: EtatEnrolement
    date: string | null
    extracteur_oreille: string | null
    cote_oreille: CoteOreille | null
  }
  /** Date ISO 8601 UTC de fin de verrouillage, ou null si le compte n'est pas verrouillé. */
  verrouille_jusqua: string | null
  echecs_consecutifs: number
}

export interface NouveauCompte {
  nom: string
  email: string
  mot_de_passe: string
}

export interface ReponseSession {
  jeton_compte: string
  /** Durée de validité du jeton, en secondes. */
  expire_dans: number
  utilisateur: Utilisateur
}

export interface TexteConsentement {
  version: VersionConsentement
  titre: string
  paragraphes: string[]
  responsable: string
}

export interface SessionInfo {
  session_id: string
  etape: 'visage'
  captures_visage_requises: number
  captures_oreille_requises: number
  cote_attendu: CoteOreille | null
  /** Durée de vie de la session sans image reçue, en secondes. */
  expire_dans: number
}

export interface Critere {
  code: string
  ok: boolean
  message: string
}

export interface RegleDecision {
  code: string
  libelle: string
  ok: boolean
  valeur: number | null
  seuil: number | null
}

/** Décision de fusion. En production, les champs numériques valent null (point 27 c). */
export interface Decision {
  accepte: boolean
  score_visage: number | null
  score_oreille: number | null
  z_visage: number | null
  z_oreille: number | null
  score_fusion: number | null
  regles: RegleDecision[]
  raison: string | null
}

export interface RetourImage {
  etape: EtapeCapture
  captures_visage: number
  captures_visage_requises: number
  captures_oreille: number
  captures_oreille_requises: number
  image_retenue: boolean
  message: string
  criteres: Critere[]
  lacet: number | null
  cadre_visage: Cadre | null
  cadre_oreille: Cadre | null
  apercu_oreille: string | null
  raison_echec: string | null
  /** Enrôlement uniquement, quand etape = "terminee". */
  utilisateur?: Utilisateur | null
  /** Authentification uniquement, quand etape = "terminee". */
  decision?: Decision | null
  /** Authentification acceptée uniquement. */
  jeton_acces?: string | null
  expire_dans?: number | null
}

export interface DossierResume {
  id: Identifiant
  nom: string
  age: number
  groupe_sanguin: string
  medecin: string
}

/** Le contrat ne précise pas si ces champs sont des textes ou des listes : les deux sont gérés. */
export type TexteOuListe = string | string[] | null

export interface Dossier extends DossierResume {
  antecedents: TexteOuListe
  traitement: TexteOuListe
  allergies: TexteOuListe
  derniere_consultation: string | null
}

export interface ListeDossiers {
  dossiers: DossierResume[]
  /** Validité restante du jeton d'accès, en secondes. */
  expire_dans: number
}

export interface Tentative {
  horodatage: string
  /** Le contrat ne fixe pas le format : booléen ou libellé (« ACCEPTEE », « REFUSEE »…). */
  decision: boolean | string
  raison: string | null
  score_visage: number | null
  score_oreille: number | null
  score_fusion: number | null
  regles: RegleDecision[] | null
}

export interface ListeTentatives {
  tentatives: Tentative[]
}
