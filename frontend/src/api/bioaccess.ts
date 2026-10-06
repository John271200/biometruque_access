/*
 * Fonctions d'appel de l'API, une par route du contrat (section 3).
 * Les jetons sont passés explicitement : le jeton « compte » vient du store compte,
 * le jeton « acces » du store acces (mémoire uniquement).
 */
import { requete } from './client'
import type {
  Dossier,
  Identifiant,
  ListeDossiers,
  ListeTentatives,
  NouveauCompte,
  ReponseSession,
  RetourImage,
  SessionInfo,
  TexteConsentement,
  Utilisateur,
  VersionConsentement,
} from './types'

const compte = (valeur: string) => ({ type: 'compte', valeur }) as const
const acces = (valeur: string) => ({ type: 'acces', valeur }) as const
const segment = (valeur: Identifiant) => encodeURIComponent(String(valeur))

export const api = {
  // --- Compte et session « compte » ---
  creerCompte: (donnees: NouveauCompte) =>
    requete<Utilisateur>('/comptes', { methode: 'POST', json: donnees }),

  ouvrirSession: (email: string, motDePasse: string) =>
    requete<ReponseSession>('/session', { methode: 'POST', json: { email, mot_de_passe: motDePasse } }),

  fermerSession: (jeton: string) =>
    requete<void>('/session', { methode: 'DELETE', jeton: compte(jeton) }),

  moi: (jeton: string) => requete<Utilisateur>('/moi', { jeton: compte(jeton) }),

  tentatives: (jeton: string) => requete<ListeTentatives>('/moi/tentatives', { jeton: compte(jeton) }),

  revoquer: (jeton: string, motDePasse: string) =>
    requete<Utilisateur>('/moi/revocation', {
      methode: 'POST',
      jeton: compte(jeton),
      json: { mot_de_passe: motDePasse },
    }),

  supprimerCompte: (jeton: string, motDePasse: string) =>
    requete<void>('/moi', {
      methode: 'DELETE',
      jeton: compte(jeton),
      json: { mot_de_passe: motDePasse, confirmation: 'SUPPRIMER' },
    }),

  // --- Consentement ---
  texteConsentement: () => requete<TexteConsentement>('/consentement/texte'),

  enregistrerConsentement: (jeton: string, accepte: boolean, version: VersionConsentement) =>
    requete<Utilisateur>('/consentement', { methode: 'POST', jeton: compte(jeton), json: { accepte, version } }),

  retirerConsentement: (jeton: string) =>
    requete<Utilisateur>('/consentement', { methode: 'DELETE', jeton: compte(jeton) }),

  // --- Enrôlement (jeton « compte ») ---
  creerSessionEnrolement: (jeton: string) =>
    requete<SessionInfo>('/enrolement/sessions', { methode: 'POST', jeton: compte(jeton) }),

  envoyerImageEnrolement: (jeton: string, sessionId: string, image: Blob) =>
    requete<RetourImage>(`/enrolement/sessions/${segment(sessionId)}/images`, {
      methode: 'POST',
      jeton: compte(jeton),
      image,
    }),

  abandonnerEnrolement: (jeton: string, sessionId: string) =>
    requete<void>(`/enrolement/sessions/${segment(sessionId)}`, { methode: 'DELETE', jeton: compte(jeton) }),

  // --- Authentification biométrique (sans jeton) ---
  creerSessionAuthentification: (email: string) =>
    requete<SessionInfo>('/authentification/sessions', { methode: 'POST', json: { email } }),

  envoyerImageAuthentification: (sessionId: string, image: Blob) =>
    requete<RetourImage>(`/authentification/sessions/${segment(sessionId)}/images`, { methode: 'POST', image }),

  abandonnerAuthentification: (sessionId: string) =>
    requete<void>(`/authentification/sessions/${segment(sessionId)}`, { methode: 'DELETE' }),

  // --- Base protégée (jeton « acces » uniquement) ---
  listerDossiers: (jetonAcces: string) => requete<ListeDossiers>('/dossiers', { jeton: acces(jetonAcces) }),

  lireDossier: (jetonAcces: string, id: Identifiant) =>
    requete<Dossier>(`/dossiers/${segment(id)}`, { jeton: acces(jetonAcces) }),
}
