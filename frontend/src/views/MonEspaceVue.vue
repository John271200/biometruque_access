<script setup lang="ts">
// Espace personnel : état du consentement, de l'enrôlement et du verrouillage, actions
// associées (révocation, retrait, suppression) et historique des tentatives.
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  api,
  ApiError,
  messageErreur,
  type EtatConsentement,
  type EtatEnrolement,
  type Tentative,
} from '../api'
import AlerteMessage from '../components/AlerteMessage.vue'
import ChampTexte from '../components/ChampTexte.vue'
import FenetreModale from '../components/FenetreModale.vue'
import IndicateurChargement from '../components/IndicateurChargement.vue'
import { useAccesStore } from '../stores/acces'
import { useCompteStore } from '../stores/compte'
import { useFlashStore } from '../stores/flash'
import { estFutur, formaterDateHeure, formaterEcheance, formaterScore } from '../utils/format'

const router = useRouter()
const compte = useCompteStore()
const acces = useAccesStore()
const flash = useFlashStore()

const SEUIL_VERROUILLAGE = 5

interface Libelle {
  texte: string
  classe: string
}

const ETATS_CONSENTEMENT: Record<EtatConsentement, Libelle> = {
  ABSENT: { texte: 'Non donné', classe: 'pastille--alerte' },
  ACCORDE: { texte: 'Accordé', classe: 'pastille--succes' },
  RETIRE: { texte: 'Retiré', classe: 'pastille--danger' },
}

const ETATS_ENROLEMENT: Record<EtatEnrolement, Libelle> = {
  NON_ENROLE: { texte: 'Non enrôlé', classe: 'pastille--alerte' },
  ENROLE: { texte: 'Enrôlé', classe: 'pastille--succes' },
  REVOQUE: { texte: 'Révoqué', classe: 'pastille--danger' },
}

const ACCORDEE: Libelle = { texte: 'Accordée', classe: 'pastille--succes' }
const REFUSEE: Libelle = { texte: 'Refusée', classe: 'pastille--danger' }

// ---- Chargement ----

const chargement = ref(true)
const erreurChargement = ref<string | null>(null)
const tentatives = ref<Tentative[]>([])
const erreurTentatives = ref<string | null>(null)
const messageAction = ref<string | null>(null)

async function charger(): Promise<void> {
  const jeton = compte.jeton
  if (jeton === null) return
  chargement.value = true
  erreurChargement.value = null
  erreurTentatives.value = null
  const [moi, historique] = await Promise.allSettled([compte.charger(), api.tentatives(jeton)])
  if (moi.status === 'rejected') erreurChargement.value = messageErreur(moi.reason)
  if (historique.status === 'fulfilled') tentatives.value = historique.value.tentatives
  else erreurTentatives.value = messageErreur(historique.reason)
  chargement.value = false
}

onMounted(charger)

// ---- États dérivés ----

const utilisateur = computed(() => compte.utilisateur)
const consentementAccorde = computed(() => utilisateur.value?.consentement.etat === 'ACCORDE')
const enrole = computed(() => utilisateur.value?.enrolement.etat === 'ENROLE')
const verrouille = computed(() => estFutur(utilisateur.value?.verrouille_jusqua))
const lienAcces = computed(() => ({ name: 'acces', query: { email: utilisateur.value?.email ?? '' } }))

const afficherScores = computed(() =>
  tentatives.value.some((t) => t.score_visage !== null || t.score_oreille !== null || t.score_fusion !== null),
)

/** Le format de « decision » n'est pas fixé par le contrat : booléen ou libellé. */
function lireDecision(decision: boolean | string): Libelle {
  if (typeof decision === 'boolean') return decision ? ACCORDEE : REFUSEE
  const normalise = decision.normalize('NFD').replace(/\p{M}/gu, '').toUpperCase()
  if (/ACCEPT|ACCORD|SUCCES|AUTORIS/.test(normalise)) return ACCORDEE
  if (/REFUS|REJET|ECHEC/.test(normalise)) return REFUSEE
  return { texte: decision, classe: '' }
}

// ---- Fenêtres de confirmation ----

type Modale = 'retrait' | 'revocation' | 'suppression'

const modale = ref<Modale | null>(null)
const motDePasse = ref('')
const saisieConfirmation = ref('')
const erreursModale = ref<{ motDePasse?: string; confirmation?: string; generale?: string }>({})
const actionEnCours = ref(false)

function ouvrir(nom: Modale): void {
  motDePasse.value = ''
  saisieConfirmation.value = ''
  erreursModale.value = {}
  messageAction.value = null
  modale.value = nom
}

function fermer(): void {
  modale.value = null
}

/** Erreur d'une action protégée par mot de passe : rattachée au champ si possible. */
function signalerErreurAction(erreur: unknown): void {
  const messageChamp = erreur instanceof ApiError ? erreur.champs.mot_de_passe : undefined
  erreursModale.value = messageChamp ? { motDePasse: messageChamp } : { generale: messageErreur(erreur) }
}

async function retirerConsentement(): Promise<void> {
  actionEnCours.value = true
  erreursModale.value = {}
  try {
    compte.definirUtilisateur(await api.retirerConsentement(compte.jetonRequis()))
    acces.effacer()
    fermer()
    messageAction.value = 'Consentement retiré : vos gabarits biométriques ont été détruits.'
    await charger()
  } catch (erreur) {
    erreursModale.value = { generale: messageErreur(erreur) }
  } finally {
    actionEnCours.value = false
  }
}

async function revoquer(): Promise<void> {
  if (motDePasse.value === '') {
    erreursModale.value = { motDePasse: 'Saisissez votre mot de passe pour confirmer.' }
    return
  }
  actionEnCours.value = true
  erreursModale.value = {}
  try {
    compte.definirUtilisateur(await api.revoquer(compte.jetonRequis(), motDePasse.value))
    acces.effacer()
    fermer()
    flash.publier(
      'Enrôlement révoqué : vos gabarits et votre jeton BioHashing ont été détruits. Vous pouvez vous ré-enrôler.',
      'succes',
    )
    await router.push({ name: 'enrolement' })
  } catch (erreur) {
    signalerErreurAction(erreur)
  } finally {
    actionEnCours.value = false
  }
}

async function supprimerCompte(): Promise<void> {
  const erreurs: { motDePasse?: string; confirmation?: string } = {}
  if (motDePasse.value === '') erreurs.motDePasse = 'Saisissez votre mot de passe pour confirmer.'
  if (saisieConfirmation.value.trim() !== 'SUPPRIMER') {
    erreurs.confirmation = 'Saisissez exactement SUPPRIMER, en majuscules.'
  }
  erreursModale.value = erreurs
  if (erreurs.motDePasse || erreurs.confirmation) return
  actionEnCours.value = true
  try {
    await api.supprimerCompte(compte.jetonRequis(), motDePasse.value)
    compte.oublier()
    acces.effacer()
    fermer()
    flash.publier('Votre compte et toutes les données associées ont été supprimés.', 'succes')
    await router.push({ name: 'accueil' })
  } catch (erreur) {
    signalerErreurAction(erreur)
  } finally {
    actionEnCours.value = false
  }
}
</script>

<template>
  <div class="conteneur page">
    <h1>Mon espace</h1>

    <IndicateurChargement v-if="chargement && !utilisateur" texte="Chargement de votre espace…" />

    <div v-else-if="erreurChargement && !utilisateur" class="pile">
      <AlerteMessage type="erreur" titre="Espace indisponible">
        <p>{{ erreurChargement }}</p>
      </AlerteMessage>
      <button type="button" class="bouton" @click="charger">Réessayer</button>
    </div>

    <div v-else-if="utilisateur" class="pile">
      <p class="page__intro">Bonjour {{ utilisateur.nom }} ({{ utilisateur.email }}).</p>

      <AlerteMessage v-if="messageAction" type="succes" fermable @fermer="messageAction = null">
        <p>{{ messageAction }}</p>
      </AlerteMessage>
      <AlerteMessage v-if="erreurChargement" type="alerte" titre="Informations peut-être obsolètes">
        <p>{{ erreurChargement }}</p>
      </AlerteMessage>

      <div class="grille-cartes">
        <section class="carte etat" aria-labelledby="titre-consentement">
          <h2 id="titre-consentement">Consentement</h2>
          <p>
            <span class="pastille" :class="ETATS_CONSENTEMENT[utilisateur.consentement.etat].classe">
              {{ ETATS_CONSENTEMENT[utilisateur.consentement.etat].texte }}
            </span>
          </p>
          <dl v-if="utilisateur.consentement.date" class="definitions texte-petit">
            <dt>Date</dt>
            <dd>{{ formaterDateHeure(utilisateur.consentement.date) }}</dd>
            <dt>Version</dt>
            <dd>{{ utilisateur.consentement.version ?? '—' }}</dd>
          </dl>
          <div class="actions">
            <RouterLink v-if="!consentementAccorde" to="/consentement" class="bouton">
              Donner mon consentement
            </RouterLink>
            <button v-else type="button" class="bouton bouton--danger-contour" @click="ouvrir('retrait')">
              Retirer mon consentement
            </button>
          </div>
        </section>

        <section class="carte etat" aria-labelledby="titre-enrolement">
          <h2 id="titre-enrolement">Enrôlement biométrique</h2>
          <p>
            <span class="pastille" :class="ETATS_ENROLEMENT[utilisateur.enrolement.etat].classe">
              {{ ETATS_ENROLEMENT[utilisateur.enrolement.etat].texte }}
            </span>
          </p>
          <dl v-if="utilisateur.enrolement.date" class="definitions texte-petit">
            <dt>Date</dt>
            <dd>{{ formaterDateHeure(utilisateur.enrolement.date) }}</dd>
            <dt>Oreille</dt>
            <dd>{{ utilisateur.enrolement.cote_oreille ?? '—' }}</dd>
            <dt>Extracteur</dt>
            <dd>{{ utilisateur.enrolement.extracteur_oreille ?? '—' }}</dd>
          </dl>
          <p v-if="!consentementAccorde && !enrole" class="texte-petit texte-doux">
            L'enrôlement nécessite votre consentement préalable.
          </p>
          <div class="actions">
            <RouterLink v-if="consentementAccorde && !enrole" to="/enrolement" class="bouton">M'enrôler</RouterLink>
            <template v-if="enrole">
              <RouterLink :to="lienAcces" class="bouton">Accéder à la base</RouterLink>
              <button type="button" class="bouton bouton--secondaire" @click="ouvrir('revocation')">
                Révoquer et me ré-enrôler
              </button>
            </template>
          </div>
        </section>

        <section class="carte etat" aria-labelledby="titre-verrouillage">
          <h2 id="titre-verrouillage">Verrouillage</h2>
          <p>
            <span class="pastille" :class="verrouille ? 'pastille--danger' : 'pastille--succes'">
              {{ verrouille ? 'Verrouillé' : 'Non verrouillé' }}
            </span>
          </p>
          <p v-if="verrouille" class="texte-petit">
            Trop d'échecs consécutifs : l'authentification biométrique est bloquée jusqu'à
            <strong>{{ formaterEcheance(utilisateur.verrouille_jusqua) }}</strong> (heure locale).
          </p>
          <p class="texte-petit texte-doux">
            Échecs consécutifs : {{ utilisateur.echecs_consecutifs }} / {{ SEUIL_VERROUILLAGE }}. Au-delà, le compte
            est verrouillé 15 minutes ; une authentification réussie remet le compteur à zéro.
          </p>
        </section>
      </div>

      <section class="carte" aria-labelledby="titre-tentatives">
        <h2 id="titre-tentatives">Dernières tentatives d'authentification</h2>
        <AlerteMessage v-if="erreurTentatives" type="erreur" titre="Historique indisponible">
          <p>{{ erreurTentatives }}</p>
        </AlerteMessage>
        <IndicateurChargement v-else-if="chargement" texte="Chargement de l'historique…" />
        <p v-else-if="tentatives.length === 0" class="texte-doux">Aucune tentative enregistrée pour le moment.</p>
        <table v-else class="tableau tableau--adaptatif">
          <caption class="visuellement-masque">
            Vos 20 dernières tentatives, de la plus récente à la plus ancienne
          </caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Décision</th>
              <th scope="col">Raison</th>
              <template v-if="afficherScores">
                <th scope="col" class="nombre">Visage</th>
                <th scope="col" class="nombre">Oreille</th>
                <th scope="col" class="nombre">Fusion</th>
              </template>
              <th scope="col">Règles</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(tentative, index) in tentatives" :key="`${tentative.horodatage}-${index}`">
              <td data-libelle="Date">{{ formaterDateHeure(tentative.horodatage) }}</td>
              <td data-libelle="Décision">
                <span class="pastille" :class="lireDecision(tentative.decision).classe">
                  {{ lireDecision(tentative.decision).texte }}
                </span>
              </td>
              <td data-libelle="Raison">{{ tentative.raison ?? '—' }}</td>
              <template v-if="afficherScores">
                <td class="nombre" data-libelle="Visage">{{ formaterScore(tentative.score_visage) }}</td>
                <td class="nombre" data-libelle="Oreille">{{ formaterScore(tentative.score_oreille) }}</td>
                <td class="nombre" data-libelle="Fusion">{{ formaterScore(tentative.score_fusion) }}</td>
              </template>
              <td data-libelle="Règles">
                <ul v-if="tentative.regles && tentative.regles.length > 0" class="regles">
                  <li
                    v-for="regle in tentative.regles"
                    :key="regle.code"
                    class="regles__item"
                    :class="regle.ok ? 'regles__item--ok' : 'regles__item--ko'"
                    :title="regle.libelle"
                  >
                    {{ regle.code }}
                    <span aria-hidden="true">{{ regle.ok ? '✓' : '✗' }}</span>
                    <span class="visuellement-masque">
                      {{ regle.libelle }} : {{ regle.ok ? 'respectée' : 'non respectée' }}
                    </span>
                  </li>
                </ul>
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="carte zone-sensible" aria-labelledby="titre-suppression">
        <h2 id="titre-suppression">Supprimer mon compte</h2>
        <p class="texte-doux">
          Supprime définitivement votre compte, vos gabarits biométriques et votre jeton BioHashing. Cette action est
          irréversible.
        </p>
        <button type="button" class="bouton bouton--danger" @click="ouvrir('suppression')">Supprimer mon compte</button>
      </section>
    </div>

    <FenetreModale :ouverte="modale === 'retrait'" titre="Retirer mon consentement" @fermer="fermer">
      <form class="formulaire" novalidate @submit.prevent="retirerConsentement">
        <p>
          Vos gabarits biométriques seront <strong>détruits</strong>. Pour accéder de nouveau à la base protégée, il
          faudra redonner votre consentement puis vous ré-enrôler.
        </p>
        <AlerteMessage v-if="erreursModale.generale" type="erreur">
          <p>{{ erreursModale.generale }}</p>
        </AlerteMessage>
        <div class="actions">
          <button type="submit" class="bouton bouton--danger" :disabled="actionEnCours">
            {{ actionEnCours ? 'Retrait…' : 'Retirer mon consentement' }}
          </button>
          <button type="button" class="bouton bouton--secondaire" @click="fermer">Annuler</button>
        </div>
      </form>
    </FenetreModale>

    <FenetreModale :ouverte="modale === 'revocation'" titre="Révoquer mon enrôlement" @fermer="fermer">
      <form class="formulaire" novalidate @submit.prevent="revoquer">
        <p>
          Vos gabarits et votre jeton BioHashing seront détruits, puis vous serez dirigé vers un nouvel enrôlement.
          Confirmez avec votre mot de passe.
        </p>
        <AlerteMessage v-if="erreursModale.generale" type="erreur">
          <p>{{ erreursModale.generale }}</p>
        </AlerteMessage>
        <ChampTexte
          id="revocation-mdp"
          v-model="motDePasse"
          libelle="Mot de passe"
          type="password"
          autocomplete="current-password"
          :erreur="erreursModale.motDePasse"
        />
        <div class="actions">
          <button type="submit" class="bouton bouton--danger" :disabled="actionEnCours">
            {{ actionEnCours ? 'Révocation…' : 'Révoquer et me ré-enrôler' }}
          </button>
          <button type="button" class="bouton bouton--secondaire" @click="fermer">Annuler</button>
        </div>
      </form>
    </FenetreModale>

    <FenetreModale :ouverte="modale === 'suppression'" titre="Supprimer définitivement mon compte" @fermer="fermer">
      <form class="formulaire" novalidate @submit.prevent="supprimerCompte">
        <p>
          Toutes vos données seront effacées : compte, consentement, gabarits biométriques et jeton BioHashing.
          <strong>Cette action est irréversible.</strong>
        </p>
        <AlerteMessage v-if="erreursModale.generale" type="erreur">
          <p>{{ erreursModale.generale }}</p>
        </AlerteMessage>
        <ChampTexte
          id="suppression-mdp"
          v-model="motDePasse"
          libelle="Mot de passe"
          type="password"
          autocomplete="current-password"
          :erreur="erreursModale.motDePasse"
        />
        <ChampTexte
          id="suppression-confirmation"
          v-model="saisieConfirmation"
          libelle="Saisissez SUPPRIMER pour confirmer"
          autocapitalize="characters"
          spellcheck="false"
          :erreur="erreursModale.confirmation"
        />
        <div class="actions">
          <button type="submit" class="bouton bouton--danger" :disabled="actionEnCours">
            {{ actionEnCours ? 'Suppression…' : 'Supprimer mon compte' }}
          </button>
          <button type="button" class="bouton bouton--secondaire" @click="fermer">Annuler</button>
        </div>
      </form>
    </FenetreModale>
  </div>
</template>

<style scoped>
.etat {
  display: flex;
  flex-direction: column;
}

.etat .actions {
  margin-top: auto;
}

.regles {
  display: flex;
  flex-wrap: wrap;
  gap: var(--espace-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.regles__item {
  padding: 0 var(--espace-2);
  border-radius: var(--rayon-s);
  font-size: var(--taille-xs);
  font-weight: var(--graisse-moyenne);
  white-space: nowrap;
}

.regles__item--ok {
  background: var(--couleur-succes-pale);
  color: var(--couleur-succes);
}

.regles__item--ko {
  background: var(--couleur-danger-pale);
  color: var(--couleur-danger);
}

.zone-sensible {
  border-color: var(--couleur-danger);
}
</style>
