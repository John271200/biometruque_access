<script setup lang="ts">
// Connexion par email et mot de passe (jeton « compte »), puis retour à la page demandée.
import { nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { messageErreur } from '../api'
import AlerteMessage from '../components/AlerteMessage.vue'
import ChampTexte from '../components/ChampTexte.vue'
import { useCompteStore } from '../stores/compte'
import { cheminInterne, parametre } from '../utils/navigation'

const route = useRoute()
const router = useRouter()
const compte = useCompteStore()

const email = ref('')
const motDePasse = ref('')
const erreurs = ref<{ email?: string; motDePasse?: string }>({})
const erreurGenerale = ref<string | null>(null)
const envoiEnCours = ref(false)

async function soumettre(): Promise<void> {
  erreurGenerale.value = null
  const locales: { email?: string; motDePasse?: string } = {}
  if (email.value.trim() === '') locales.email = 'Indiquez votre adresse email.'
  if (motDePasse.value === '') locales.motDePasse = 'Indiquez votre mot de passe.'
  erreurs.value = locales
  if (locales.email || locales.motDePasse) {
    await nextTick()
    document.getElementById(locales.email ? 'connexion-email' : 'connexion-mdp')?.focus()
    return
  }
  envoiEnCours.value = true
  try {
    await compte.connecter(email.value.trim(), motDePasse.value)
    await router.push(cheminInterne(parametre(route.query.redirection), '/mon-espace'))
  } catch (erreur) {
    erreurGenerale.value = messageErreur(erreur)
    motDePasse.value = ''
  } finally {
    envoiEnCours.value = false
  }
}
</script>

<template>
  <div class="conteneur page page--etroite">
    <h1>Se connecter</h1>
    <p class="page__intro">Accédez à votre espace pour gérer votre consentement, votre enrôlement et vos données.</p>

    <form class="carte formulaire" novalidate @submit.prevent="soumettre">
      <AlerteMessage v-if="erreurGenerale" type="erreur" titre="Connexion impossible">
        <p>{{ erreurGenerale }}</p>
      </AlerteMessage>
      <ChampTexte
        id="connexion-email"
        v-model="email"
        libelle="Adresse email"
        type="email"
        autocomplete="username"
        inputmode="email"
        spellcheck="false"
        :erreur="erreurs.email"
      />
      <ChampTexte
        id="connexion-mdp"
        v-model="motDePasse"
        libelle="Mot de passe"
        type="password"
        autocomplete="current-password"
        :erreur="erreurs.motDePasse"
      />
      <div class="actions">
        <button type="submit" class="bouton" :disabled="envoiEnCours">
          {{ envoiEnCours ? 'Connexion…' : 'Se connecter' }}
        </button>
      </div>
      <p class="texte-petit texte-doux">
        Pas encore de compte ? <RouterLink to="/inscription">Créer un compte</RouterLink>
      </p>
    </form>
  </div>
</template>
