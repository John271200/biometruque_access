<script setup lang="ts">
// Consentement explicite au traitement biométrique : case non pré-cochée, accord ou refus.
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, messageErreur, type TexteConsentement } from '../api'
import AlerteMessage from '../components/AlerteMessage.vue'
import IndicateurChargement from '../components/IndicateurChargement.vue'
import { useCompteStore } from '../stores/compte'
import { useFlashStore } from '../stores/flash'
import { formaterDateHeure } from '../utils/format'

const router = useRouter()
const compte = useCompteStore()
const flash = useFlashStore()

const texte = ref<TexteConsentement | null>(null)
const chargement = ref(true)
const erreurChargement = ref<string | null>(null)
const coche = ref(false)
const erreurCase = ref<string | null>(null)
const erreurEnvoi = ref<string | null>(null)
const envoi = ref<'accord' | 'refus' | null>(null)
const caseConsentement = ref<HTMLInputElement | null>(null)

const consentementActuel = computed(() => compte.utilisateur?.consentement ?? null)
const dejaAccorde = computed(() => consentementActuel.value?.etat === 'ACCORDE')

async function charger(): Promise<void> {
  chargement.value = true
  erreurChargement.value = null
  try {
    const [donnees] = await Promise.all([
      api.texteConsentement(),
      compte.utilisateur ? Promise.resolve(compte.utilisateur) : compte.charger(),
    ])
    texte.value = donnees
  } catch (erreur) {
    erreurChargement.value = messageErreur(erreur)
  } finally {
    chargement.value = false
  }
}

async function repondre(accepte: boolean): Promise<void> {
  if (!texte.value) return
  erreurEnvoi.value = null
  if (accepte && !coche.value) {
    erreurCase.value = 'Cochez la case pour confirmer que vous avez lu ces informations et que vous consentez.'
    await nextTick()
    caseConsentement.value?.focus()
    return
  }
  erreurCase.value = null
  envoi.value = accepte ? 'accord' : 'refus'
  try {
    const utilisateur = await api.enregistrerConsentement(compte.jetonRequis(), accepte, texte.value.version)
    compte.definirUtilisateur(utilisateur)
    if (accepte) {
      flash.publier('Merci, votre consentement est enregistré.', 'succes')
      await router.push({ name: utilisateur.enrolement.etat === 'ENROLE' ? 'mon-espace' : 'enrolement' })
    } else {
      flash.publier(
        'Votre refus est enregistré : aucune donnée biométrique ne sera collectée, et la base protégée vous restera inaccessible.',
        'info',
      )
      await router.push({ name: 'mon-espace' })
    }
  } catch (erreur) {
    erreurEnvoi.value = messageErreur(erreur)
  } finally {
    envoi.value = null
  }
}

onMounted(charger)
</script>

<template>
  <div class="conteneur page">
    <h1>Consentement au traitement biométrique</h1>

    <IndicateurChargement v-if="chargement" texte="Chargement du texte de consentement…" />

    <div v-else-if="erreurChargement" class="pile">
      <AlerteMessage type="erreur" titre="Texte indisponible">
        <p>{{ erreurChargement }}</p>
      </AlerteMessage>
      <button type="button" class="bouton" @click="charger">Réessayer</button>
    </div>

    <div v-else-if="texte" class="pile consentement">
      <AlerteMessage v-if="dejaAccorde && consentementActuel" type="succes" titre="Consentement déjà accordé">
        <p>
          Vous avez consenti le {{ formaterDateHeure(consentementActuel.date) }} (version
          {{ consentementActuel.version ?? '—' }}).
        </p>
      </AlerteMessage>

      <article class="carte consentement__texte" aria-labelledby="titre-consentement">
        <h2 id="titre-consentement">{{ texte.titre }}</h2>
        <p v-for="(paragraphe, index) in texte.paragraphes" :key="index">{{ paragraphe }}</p>
        <p class="texte-petit texte-doux">
          Responsable du traitement : {{ texte.responsable }} · Version du texte : {{ texte.version }}
        </p>
      </article>

      <div v-if="dejaAccorde" class="actions">
        <RouterLink
          v-if="compte.utilisateur?.enrolement.etat !== 'ENROLE'"
          to="/enrolement"
          class="bouton"
        >
          Continuer vers l'enrôlement
        </RouterLink>
        <RouterLink to="/mon-espace" class="bouton bouton--secondaire">Retour à mon espace</RouterLink>
      </div>

      <form v-else class="carte formulaire" novalidate @submit.prevent="repondre(true)">
        <AlerteMessage v-if="erreurEnvoi" type="erreur" titre="Enregistrement impossible">
          <p>{{ erreurEnvoi }}</p>
        </AlerteMessage>
        <div>
          <div class="case">
            <input
              id="case-consentement"
              ref="caseConsentement"
              v-model="coche"
              type="checkbox"
              :aria-invalid="erreurCase ? 'true' : undefined"
              :aria-describedby="erreurCase ? 'case-consentement-erreur' : undefined"
            />
            <label for="case-consentement">
              J'ai lu ces informations et je consens au traitement de mes données biométriques (visage et
              oreille) pour m'authentifier sur BioAccess. Je sais que je peux retirer ce consentement à tout
              moment depuis mon espace.
            </label>
          </div>
          <p v-if="erreurCase" id="case-consentement-erreur" class="champ__erreur">{{ erreurCase }}</p>
        </div>
        <div class="actions">
          <button type="submit" class="bouton" :disabled="envoi !== null">
            {{ envoi === 'accord' ? 'Enregistrement…' : 'Je consens' }}
          </button>
          <button
            type="button"
            class="bouton bouton--secondaire"
            :disabled="envoi !== null"
            @click="repondre(false)"
          >
            {{ envoi === 'refus' ? 'Enregistrement…' : 'Je refuse' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.consentement {
  max-width: var(--largeur-texte);
}
</style>
