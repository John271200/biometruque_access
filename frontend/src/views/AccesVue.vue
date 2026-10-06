<script setup lang="ts">
// Authentification biométrique : email → session → capture guidée → décision.
// En cas de succès, le jeton « acces » est gardé en mémoire et la base s'ouvre après 2 s.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError, messageErreur, type RetourImage, type SessionInfo } from '../api'
import AlerteMessage from '../components/AlerteMessage.vue'
import ChampTexte from '../components/ChampTexte.vue'
import PanneauDecision from '../components/PanneauDecision.vue'
import CaptureGuidee from '../components/capture/CaptureGuidee.vue'
import { useAccesStore } from '../stores/acces'
import { useCompteStore } from '../stores/compte'
import { formaterEcheance } from '../utils/format'
import { parametre } from '../utils/navigation'

type Etape = 'saisie' | 'capture' | 'decision'

/** Validité du jeton d'accès selon le contrat, si le serveur ne la précise pas. */
const VALIDITE_ACCES_PAR_DEFAUT_S = 600
const DELAI_REDIRECTION_MS = 2000

const route = useRoute()
const router = useRouter()
const acces = useAccesStore()
const compte = useCompteStore()

const etape = ref<Etape>('saisie')
const email = ref(parametre(route.query.email) ?? compte.utilisateur?.email ?? acces.email)
const erreurEmail = ref<string | null>(null)
const erreur = ref<{ titre: string; message: string; code: string; verrouilleJusqua: string | null } | null>(null)
const ouvertureEnCours = ref(false)
const sessionInfo = ref<SessionInfo | null>(null)
const cleCapture = ref(0)
const resultat = ref<RetourImage | null>(null)
let minuteurRedirection: number | undefined

const accesRequis = computed(() => parametre(route.query.motif) === 'acces-requis')
const decision = computed(() => resultat.value?.decision ?? null)
const accesAccorde = computed(() => decision.value?.accepte === true && Boolean(resultat.value?.jeton_acces))

function lireErreur(e: unknown): NonNullable<typeof erreur.value> {
  if (!(e instanceof ApiError)) {
    return { titre: 'Authentification impossible', message: messageErreur(e), code: 'ERREUR_INATTENDUE', verrouilleJusqua: null }
  }
  if (e.code === 'COMPTE_VERROUILLE') {
    const fin = e.details.verrouille_jusqua
    return {
      titre: 'Compte temporairement verrouillé',
      message: e.message,
      code: e.code,
      verrouilleJusqua: typeof fin === 'string' ? fin : null,
    }
  }
  if (e.code === 'COMPTE_NON_ENROLE') {
    return { titre: 'Aucun enrôlement pour ce compte', message: e.message, code: e.code, verrouilleJusqua: null }
  }
  return { titre: 'Authentification impossible', message: e.message, code: e.code, verrouilleJusqua: null }
}

async function ouvrirSession(): Promise<void> {
  erreur.value = null
  erreurEmail.value = null
  const adresse = email.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adresse)) {
    erreurEmail.value = "Saisissez l'adresse email de votre compte."
    etape.value = 'saisie'
    await nextTick()
    document.getElementById('acces-email')?.focus()
    return
  }
  ouvertureEnCours.value = true
  try {
    sessionInfo.value = await api.creerSessionAuthentification(adresse)
    resultat.value = null
    cleCapture.value += 1
    etape.value = 'capture'
  } catch (e) {
    erreur.value = lireErreur(e)
    const messageChamp = e instanceof ApiError ? e.champs.email : undefined
    if (messageChamp) erreurEmail.value = messageChamp
    etape.value = 'saisie'
  } finally {
    ouvertureEnCours.value = false
  }
}

function envoyerImage(sessionId: string, image: Blob): Promise<RetourImage> {
  return api.envoyerImageAuthentification(sessionId, image)
}

async function abandonnerSession(sessionId: string): Promise<void> {
  await api.abandonnerAuthentification(sessionId)
}

function ouvrirBase(): void {
  window.clearTimeout(minuteurRedirection)
  void router.push({ name: 'base' })
}

function surTerminee(retour: RetourImage): void {
  resultat.value = retour
  etape.value = 'decision'
  if (retour.decision?.accepte && retour.jeton_acces) {
    acces.definir(retour.jeton_acces, retour.expire_dans ?? VALIDITE_ACCES_PAR_DEFAUT_S, email.value.trim())
    minuteurRedirection = window.setTimeout(ouvrirBase, DELAI_REDIRECTION_MS)
  }
}

function annuler(): void {
  etape.value = 'saisie'
}

// Utilisateur connecté mais profil non chargé (page rechargée) : on pré-remplit son email.
onMounted(async () => {
  if (email.value !== '' || compte.utilisateur !== null || !compte.sessionValide()) return
  try {
    const { email: adresse } = await compte.charger()
    if (email.value === '') email.value = adresse
  } catch {
    // Pré-remplissage facultatif : l'utilisateur saisit son email lui-même.
  }
})

onBeforeUnmount(() => window.clearTimeout(minuteurRedirection))
</script>

<template>
  <div class="conteneur page">
    <h1>Accès biométrique</h1>
    <p class="page__intro">
      Identifiez-vous par votre visage et votre oreille pour ouvrir la base protégée. L'autorisation obtenue est
      valable 10 minutes.
    </p>

    <div v-if="etape === 'saisie'" class="pile page--etroite acces__saisie">
      <AlerteMessage v-if="accesRequis && !erreur" type="info" titre="Authentification requise">
        <p>La base protégée exige une authentification biométrique récente. Identifiez-vous ci-dessous.</p>
      </AlerteMessage>

      <AlerteMessage v-if="erreur" :type="erreur.code === 'COMPTE_VERROUILLE' ? 'alerte' : 'erreur'" :titre="erreur.titre">
        <p>{{ erreur.message }}</p>
        <p v-if="erreur.verrouilleJusqua">
          Nouvel essai possible à partir de <strong>{{ formaterEcheance(erreur.verrouilleJusqua) }}</strong> (heure
          locale).
        </p>
        <p v-if="erreur.code === 'COMPTE_NON_ENROLE'">
          Connectez-vous à <RouterLink to="/mon-espace">votre espace</RouterLink> pour donner votre consentement et
          vous enrôler.
        </p>
      </AlerteMessage>

      <form class="carte formulaire" novalidate @submit.prevent="ouvrirSession">
        <ChampTexte
          id="acces-email"
          v-model="email"
          libelle="Adresse email de votre compte"
          type="email"
          autocomplete="email"
          inputmode="email"
          spellcheck="false"
          :erreur="erreurEmail"
        />
        <div class="actions">
          <button type="submit" class="bouton" :disabled="ouvertureEnCours">
            {{ ouvertureEnCours ? 'Préparation…' : "Commencer l'authentification" }}
          </button>
        </div>
      </form>
    </div>

    <div v-else-if="etape === 'capture' && sessionInfo" class="pile">
      <CaptureGuidee
        :key="cleCapture"
        mode="authentification"
        :session-info="sessionInfo"
        :envoyer-image="envoyerImage"
        :abandonner-session="abandonnerSession"
        @terminee="surTerminee"
        @recommencer="ouvrirSession"
      />
      <div class="actions">
        <button type="button" class="bouton bouton--discret" @click="annuler">Annuler</button>
      </div>
    </div>

    <div v-else-if="etape === 'decision'" class="pile">
      <PanneauDecision v-if="decision" :decision="decision">
        <template v-if="accesAccorde">
          <button type="button" class="bouton" @click="ouvrirBase">Ouvrir la base protégée</button>
          <p class="texte-petit texte-doux acces__redirection">Ouverture automatique dans 2 secondes…</p>
        </template>
        <template v-else>
          <button type="button" class="bouton" :disabled="ouvertureEnCours" @click="ouvrirSession">Réessayer</button>
          <RouterLink to="/" class="bouton bouton--secondaire">Retour à l'accueil</RouterLink>
        </template>
      </PanneauDecision>
      <template v-else>
        <AlerteMessage type="erreur" titre="Résultat indisponible">
          <p>Le serveur n'a pas renvoyé de décision. Recommencez l'authentification.</p>
        </AlerteMessage>
        <button type="button" class="bouton" @click="ouvrirSession">Réessayer</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.acces__saisie {
  margin-inline: 0;
  padding-inline: 0;
}

.acces__redirection {
  margin: 0;
}
</style>
