<script setup lang="ts">
// Création de compte, puis connexion automatique et redirection vers le consentement.
import { computed, nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError, messageErreur } from '../api'
import AlerteMessage from '../components/AlerteMessage.vue'
import ChampTexte from '../components/ChampTexte.vue'
import { useCompteStore } from '../stores/compte'
import { useFlashStore } from '../stores/flash'

type Champ = 'nom' | 'email' | 'mot_de_passe' | 'confirmation'
const CHAMPS: Champ[] = ['nom', 'email', 'mot_de_passe', 'confirmation']

const router = useRouter()
const compte = useCompteStore()
const flash = useFlashStore()

const formulaire = reactive<Record<Champ, string>>({ nom: '', email: '', mot_de_passe: '', confirmation: '' })
const erreurs = ref<Partial<Record<Champ, string>>>({})
const erreurGenerale = ref<string | null>(null)
const emailDejaUtilise = ref(false)
const envoiEnCours = ref(false)

// Politique de mot de passe du contrat : 12 caractères, une majuscule, une minuscule, un chiffre.
const regles = computed(() => {
  const mdp = formulaire.mot_de_passe
  return [
    { libelle: 'Au moins 12 caractères', ok: mdp.length >= 12 },
    { libelle: 'Une lettre majuscule', ok: /\p{Lu}/u.test(mdp) },
    { libelle: 'Une lettre minuscule', ok: /\p{Ll}/u.test(mdp) },
    { libelle: 'Un chiffre', ok: /\d/.test(mdp) },
  ]
})

function valider(): Partial<Record<Champ, string>> {
  const resultat: Partial<Record<Champ, string>> = {}
  if (formulaire.nom.trim() === '') resultat.nom = 'Indiquez votre nom.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formulaire.email.trim())) {
    resultat.email = 'Saisissez une adresse email valide (exemple : nom@domaine.bj).'
  }
  if (!regles.value.every((regle) => regle.ok)) {
    resultat.mot_de_passe = 'Le mot de passe ne respecte pas encore toutes les règles indiquées.'
  }
  if (formulaire.confirmation === '' || formulaire.confirmation !== formulaire.mot_de_passe) {
    resultat.confirmation = 'Les deux mots de passe ne correspondent pas.'
  }
  return resultat
}

async function signalerErreurs(nouvelles: Partial<Record<Champ, string>>): Promise<void> {
  erreurs.value = nouvelles
  await nextTick()
  const premier = CHAMPS.find((champ) => nouvelles[champ])
  if (premier) document.getElementById(`inscription-${premier}`)?.focus()
}

function erreursServeur(erreur: ApiError): Partial<Record<Champ, string>> {
  if (erreur.code === 'EMAIL_DEJA_UTILISE') return { email: erreur.message }
  const resultat: Partial<Record<Champ, string>> = {}
  for (const champ of CHAMPS) {
    const message = erreur.champs[champ]
    if (message) resultat[champ] = message
  }
  return resultat
}

async function soumettre(): Promise<void> {
  erreurGenerale.value = null
  emailDejaUtilise.value = false
  const locales = valider()
  if (Object.keys(locales).length > 0) {
    await signalerErreurs(locales)
    return
  }
  erreurs.value = {}
  envoiEnCours.value = true
  const email = formulaire.email.trim()
  try {
    await api.creerCompte({ nom: formulaire.nom.trim(), email, mot_de_passe: formulaire.mot_de_passe })
  } catch (erreur) {
    envoiEnCours.value = false
    emailDejaUtilise.value = erreur instanceof ApiError && erreur.code === 'EMAIL_DEJA_UTILISE'
    const parChamp = erreur instanceof ApiError ? erreursServeur(erreur) : {}
    if (Object.keys(parChamp).length > 0) await signalerErreurs(parChamp)
    else erreurGenerale.value = messageErreur(erreur)
    return
  }
  try {
    await compte.connecter(email, formulaire.mot_de_passe)
    flash.publier('Votre compte est créé. Étape suivante : votre consentement.', 'succes')
    await router.push({ name: 'consentement' })
  } catch {
    flash.publier('Votre compte est créé. Connectez-vous pour continuer.', 'succes')
    await router.push({ name: 'connexion' })
  } finally {
    envoiEnCours.value = false
  }
}
</script>

<template>
  <div class="conteneur page page--etroite">
    <h1>Créer un compte</h1>
    <p class="page__intro">
      Votre compte vous permet de donner votre consentement, de vous enrôler et de gérer vos données.
      Tous les champs sont obligatoires.
    </p>

    <form class="carte formulaire" novalidate @submit.prevent="soumettre">
      <AlerteMessage v-if="erreurGenerale" type="erreur" titre="Inscription impossible">
        <p>{{ erreurGenerale }}</p>
      </AlerteMessage>

      <ChampTexte
        id="inscription-nom"
        v-model="formulaire.nom"
        libelle="Nom complet"
        autocomplete="name"
        :erreur="erreurs.nom"
      />
      <ChampTexte
        id="inscription-email"
        v-model="formulaire.email"
        libelle="Adresse email"
        type="email"
        autocomplete="email"
        inputmode="email"
        spellcheck="false"
        :erreur="erreurs.email"
      >
        <p v-if="emailDejaUtilise && erreurs.email" class="champ__aide">
          Déjà inscrit ? <RouterLink to="/connexion">Se connecter</RouterLink>
        </p>
      </ChampTexte>
      <ChampTexte
        id="inscription-mot_de_passe"
        v-model="formulaire.mot_de_passe"
        libelle="Mot de passe"
        type="password"
        autocomplete="new-password"
        decrit-par="politique-mdp"
        :erreur="erreurs.mot_de_passe"
      >
        <ul id="politique-mdp" class="politique" aria-label="Règles du mot de passe">
          <li v-for="regle in regles" :key="regle.libelle" :class="{ 'politique--ok': regle.ok }">
            <span aria-hidden="true">{{ regle.ok ? '✓' : '○' }}</span>
            {{ regle.libelle }}
            <span class="visuellement-masque">{{ regle.ok ? '(respectée)' : '(non respectée)' }}</span>
          </li>
        </ul>
      </ChampTexte>
      <ChampTexte
        id="inscription-confirmation"
        v-model="formulaire.confirmation"
        libelle="Confirmation du mot de passe"
        type="password"
        autocomplete="new-password"
        :erreur="erreurs.confirmation"
      />

      <div class="actions">
        <button type="submit" class="bouton" :disabled="envoiEnCours">
          {{ envoiEnCours ? 'Création en cours…' : 'Créer mon compte' }}
        </button>
      </div>
      <p class="texte-petit texte-doux">
        Déjà un compte ? <RouterLink to="/connexion">Se connecter</RouterLink>
      </p>
    </form>
  </div>
</template>

<style scoped>
.politique {
  margin: var(--espace-2) 0 0;
  padding: 0;
  list-style: none;
  color: var(--couleur-texte-doux);
  font-size: var(--taille-s);
}

.politique li {
  display: flex;
  gap: var(--espace-2);
}

.politique--ok {
  color: var(--couleur-succes);
}
</style>
