<script setup lang="ts">
// Enrôlement biométrique : ouverture d'une session, capture guidée, puis confirmation.
import { onMounted, ref } from 'vue'
import { api, ApiError, messageErreur, type RetourImage, type SessionInfo } from '../api'
import AlerteMessage from '../components/AlerteMessage.vue'
import CaptureGuidee from '../components/capture/CaptureGuidee.vue'
import IndicateurChargement from '../components/IndicateurChargement.vue'
import { useCompteStore } from '../stores/compte'

type Etat = 'ouverture' | 'capture' | 'termine' | 'erreur'

const compte = useCompteStore()

const etat = ref<Etat>('ouverture')
const sessionInfo = ref<SessionInfo | null>(null)
const cleCapture = ref(0)
const erreur = ref<{ code: string; message: string } | null>(null)

async function ouvrirSession(): Promise<void> {
  etat.value = 'ouverture'
  erreur.value = null
  try {
    sessionInfo.value = await api.creerSessionEnrolement(compte.jetonRequis())
    cleCapture.value += 1
    etat.value = 'capture'
  } catch (e) {
    erreur.value = { code: e instanceof ApiError ? e.code : 'ERREUR_INATTENDUE', message: messageErreur(e) }
    etat.value = 'erreur'
  }
}

function envoyerImage(sessionId: string, image: Blob): Promise<RetourImage> {
  return api.envoyerImageEnrolement(compte.jetonRequis(), sessionId, image)
}

async function abandonnerSession(sessionId: string): Promise<void> {
  // Le jeton peut avoir disparu (déconnexion) : rien à abandonner côté serveur dans ce cas.
  if (compte.jeton !== null) await api.abandonnerEnrolement(compte.jeton, sessionId)
}

function surTerminee(retour: RetourImage): void {
  if (retour.utilisateur) compte.definirUtilisateur(retour.utilisateur)
  etat.value = 'termine'
}

onMounted(ouvrirSession)
</script>

<template>
  <div class="conteneur page">
    <h1>Enrôlement biométrique</h1>
    <p class="page__intro">
      Nous allons enregistrer votre visage puis votre oreille. Comptez environ une minute ; restez dans un endroit
      calme et bien éclairé.
    </p>

    <IndicateurChargement v-if="etat === 'ouverture'" texte="Ouverture de la session d'enrôlement…" />

    <div v-else-if="etat === 'erreur' && erreur" class="pile">
      <AlerteMessage v-if="erreur.code === 'CONSENTEMENT_REQUIS'" type="alerte" titre="Consentement requis">
        <p>{{ erreur.message }}</p>
        <p>L'enrôlement ne peut avoir lieu qu'après votre consentement explicite.</p>
      </AlerteMessage>
      <AlerteMessage v-else-if="erreur.code === 'DEJA_ENROLE'" type="info" titre="Vous êtes déjà enrôlé">
        <p>{{ erreur.message }}</p>
        <p>Pour recommencer, révoquez d'abord votre enrôlement depuis votre espace.</p>
      </AlerteMessage>
      <AlerteMessage v-else type="erreur" titre="Enrôlement impossible">
        <p>{{ erreur.message }}</p>
      </AlerteMessage>
      <div class="actions">
        <RouterLink v-if="erreur.code === 'CONSENTEMENT_REQUIS'" to="/consentement" class="bouton">
          Donner mon consentement
        </RouterLink>
        <button v-else-if="erreur.code !== 'DEJA_ENROLE'" type="button" class="bouton" @click="ouvrirSession">
          Réessayer
        </button>
        <RouterLink to="/mon-espace" class="bouton bouton--secondaire">Retour à mon espace</RouterLink>
      </div>
    </div>

    <div v-else-if="etat === 'capture' && sessionInfo" class="pile">
      <CaptureGuidee
        :key="cleCapture"
        mode="enrolement"
        :session-info="sessionInfo"
        :envoyer-image="envoyerImage"
        :abandonner-session="abandonnerSession"
        @terminee="surTerminee"
        @recommencer="ouvrirSession"
      />
      <div class="actions">
        <RouterLink to="/mon-espace" class="bouton bouton--discret">Annuler et revenir à mon espace</RouterLink>
      </div>
    </div>

    <section v-else-if="etat === 'termine'" class="carte pile" aria-labelledby="titre-succes">
      <h2 id="titre-succes" class="succes">Enrôlement réussi</h2>
      <p>
        Vos gabarits biométriques (visage et oreille
        {{ compte.utilisateur?.enrolement.cote_oreille ?? sessionInfo?.cote_attendu ?? 'droite' }}) sont enregistrés
        sous forme protégée. Aucune image n'a été conservée.
      </p>
      <div class="actions">
        <RouterLink
          :to="{ name: 'acces', query: { email: compte.utilisateur?.email ?? '' } }"
          class="bouton"
        >
          Accéder à la base protégée
        </RouterLink>
        <RouterLink to="/mon-espace" class="bouton bouton--secondaire">Retour à mon espace</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.succes {
  color: var(--couleur-succes);
}
</style>
