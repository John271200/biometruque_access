<script setup lang="ts">
// Base protégée : liste et détail des dossiers patients fictifs, accessibles uniquement
// avec le jeton « acces » (10 min) gardé en mémoire. Compte à rebours de validité affiché.
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError, messageErreur, type Dossier, type DossierResume, type TexteOuListe } from '../api'
import AlerteMessage from '../components/AlerteMessage.vue'
import IndicateurChargement from '../components/IndicateurChargement.vue'
import { useCompteARebours } from '../composables/useCompteARebours'
import { useAccesStore } from '../stores/acces'
import { formaterDate, formaterDuree } from '../utils/format'

const router = useRouter()
const acces = useAccesStore()
const { secondesRestantes } = useCompteARebours(() => acces.expireA)

const chargement = ref(true)
const erreur = ref<string | null>(null)
/** Accès refusé ou expiré : seule une nouvelle authentification biométrique peut le rétablir. */
const accesPerdu = ref<string | null>(null)
const dossiers = ref<DossierResume[]>([])
const selection = ref<Dossier | null>(null)
const chargementDetail = ref<DossierResume['id'] | null>(null)
const erreurDetail = ref<string | null>(null)
const titreDetail = ref<HTMLElement | null>(null)

const bientotExpire = computed(() => accesPerdu.value === null && secondesRestantes.value > 0 && secondesRestantes.value <= 60)

function perdreAcces(message: string): void {
  acces.effacer()
  selection.value = null
  accesPerdu.value = message
}

/** 401/403 → message clair et ré-authentification ; autres erreurs → message simple. */
function traiterErreur(e: unknown, cible: typeof erreur): void {
  if (e instanceof ApiError && (e.statut === 401 || e.statut === 403)) perdreAcces(e.message)
  else cible.value = messageErreur(e)
}

async function charger(): Promise<void> {
  const jeton = acces.jeton
  if (jeton === null) {
    perdreAcces("Aucune autorisation d'accès en cours.")
    chargement.value = false
    return
  }
  chargement.value = true
  erreur.value = null
  try {
    const reponse = await api.listerDossiers(jeton)
    dossiers.value = reponse.dossiers
    acces.synchroniser(reponse.expire_dans)
  } catch (e) {
    traiterErreur(e, erreur)
  } finally {
    chargement.value = false
  }
}

async function consulter(id: DossierResume['id']): Promise<void> {
  const jeton = acces.jeton
  if (jeton === null) return
  chargementDetail.value = id
  erreurDetail.value = null
  try {
    selection.value = await api.lireDossier(jeton, id)
    await nextTick()
    titreDetail.value?.focus()
  } catch (e) {
    traiterErreur(e, erreurDetail)
  } finally {
    chargementDetail.value = null
  }
}

function revenirALaListe(): void {
  selection.value = null
}

function reAuthentifier(): void {
  void router.push({ name: 'acces', query: acces.email ? { email: acces.email } : {} })
}

/** Les champs médicaux peuvent être un texte ou une liste. */
function enListe(valeur: TexteOuListe): string[] {
  if (valeur === null) return []
  return (Array.isArray(valeur) ? valeur : [valeur]).filter((element) => element.trim() !== '')
}

watch(secondesRestantes, (secondes) => {
  if (secondes === 0 && accesPerdu.value === null) {
    perdreAcces("Votre autorisation d'accès a expiré (validité : 10 minutes).")
  }
})

onMounted(charger)
</script>

<template>
  <div class="conteneur page">
    <h1>Base protégée</h1>

    <div class="bandeau" role="note">
      <p class="bandeau__fictif">
        <span aria-hidden="true">⚠</span> Données fictives de démonstration : aucun patient réel.
      </p>
      <p v-if="accesPerdu === null" class="bandeau__minuteur">
        Accès valide encore <span role="timer" class="bandeau__duree">{{ formaterDuree(secondesRestantes) }}</span>
      </p>
    </div>
    <p class="visuellement-masque" aria-live="polite">
      {{ bientotExpire ? "Il reste moins d'une minute avant l'expiration de votre accès." : '' }}
    </p>

    <div v-if="accesPerdu" class="pile">
      <AlerteMessage type="alerte" titre="Accès à la base non autorisé">
        <p>{{ accesPerdu }}</p>
        <p>Pour consulter les dossiers, authentifiez-vous de nouveau par votre visage et votre oreille.</p>
      </AlerteMessage>
      <button type="button" class="bouton" @click="reAuthentifier">Se ré-authentifier</button>
    </div>

    <IndicateurChargement v-else-if="chargement" texte="Chargement des dossiers…" />

    <div v-else-if="erreur" class="pile">
      <AlerteMessage type="erreur" titre="Dossiers indisponibles">
        <p>{{ erreur }}</p>
      </AlerteMessage>
      <button type="button" class="bouton" @click="charger">Réessayer</button>
    </div>

    <article v-else-if="selection" class="carte dossier" aria-labelledby="titre-dossier">
      <button type="button" class="bouton bouton--discret dossier__retour" @click="revenirALaListe">
        <span aria-hidden="true">←</span> Retour à la liste
      </button>
      <h2 id="titre-dossier" ref="titreDetail" tabindex="-1">{{ selection.nom }}</h2>
      <dl class="definitions">
        <dt>Âge</dt>
        <dd>{{ selection.age }} ans</dd>
        <dt>Groupe sanguin</dt>
        <dd>{{ selection.groupe_sanguin }}</dd>
        <dt>Médecin traitant</dt>
        <dd>{{ selection.medecin }}</dd>
        <dt>Dernière consultation</dt>
        <dd>{{ formaterDate(selection.derniere_consultation) }}</dd>
      </dl>
      <div class="dossier__sections">
        <section
          v-for="rubrique in [
            { titre: 'Antécédents', valeur: selection.antecedents },
            { titre: 'Traitement en cours', valeur: selection.traitement },
            { titre: 'Allergies', valeur: selection.allergies },
          ]"
          :key="rubrique.titre"
          class="dossier__rubrique"
        >
          <h3>{{ rubrique.titre }}</h3>
          <ul v-if="enListe(rubrique.valeur).length > 1">
            <li v-for="element in enListe(rubrique.valeur)" :key="element">{{ element }}</li>
          </ul>
          <p v-else>{{ enListe(rubrique.valeur)[0] ?? 'Aucun élément renseigné.' }}</p>
        </section>
      </div>
    </article>

    <section v-else aria-labelledby="titre-liste">
      <h2 id="titre-liste">Dossiers patients</h2>
      <AlerteMessage v-if="erreurDetail" type="erreur" titre="Dossier indisponible">
        <p>{{ erreurDetail }}</p>
      </AlerteMessage>
      <p v-if="dossiers.length === 0" class="texte-doux">Aucun dossier n'est disponible dans la base.</p>
      <table v-else class="tableau tableau--adaptatif liste">
        <caption class="visuellement-masque">
          Liste des dossiers patients fictifs
        </caption>
        <thead>
          <tr>
            <th scope="col">Patient</th>
            <th scope="col" class="nombre">Âge</th>
            <th scope="col">Groupe sanguin</th>
            <th scope="col">Médecin traitant</th>
            <th scope="col"><span class="visuellement-masque">Action</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="dossier in dossiers" :key="dossier.id">
            <td data-libelle="Patient" class="liste__nom">{{ dossier.nom }}</td>
            <td data-libelle="Âge" class="nombre">{{ dossier.age }} ans</td>
            <td data-libelle="Groupe sanguin">{{ dossier.groupe_sanguin }}</td>
            <td data-libelle="Médecin">{{ dossier.medecin }}</td>
            <td class="liste__action">
              <button
                type="button"
                class="bouton bouton--secondaire"
                :disabled="chargementDetail !== null"
                @click="consulter(dossier.id)"
              >
                {{ chargementDetail === dossier.id ? 'Ouverture…' : 'Consulter' }}
                <span class="visuellement-masque">le dossier de {{ dossier.nom }}</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.bandeau {
  display: flex;
  flex-wrap: wrap;
  gap: var(--espace-2) var(--espace-4);
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--espace-5);
  padding: var(--espace-3) var(--espace-4);
  border: 1px solid var(--couleur-alerte);
  border-radius: var(--rayon-s);
  background: var(--couleur-alerte-pale);
}

.bandeau p {
  margin: 0;
}

.bandeau__fictif {
  color: var(--couleur-alerte);
  font-weight: var(--graisse-forte);
}

.bandeau__duree {
  font-family: var(--police-mono);
  font-weight: var(--graisse-forte);
}

.liste__nom {
  font-weight: var(--graisse-moyenne);
}

.liste__action {
  text-align: right;
}

.tableau td.liste__action::before {
  content: none;
}

@media (max-width: 40rem) {
  .tableau--adaptatif td.liste__action {
    display: block;
  }

  .liste__action .bouton {
    width: 100%;
  }
}

.dossier__retour {
  margin: calc(-1 * var(--espace-2)) 0 var(--espace-3) calc(-1 * var(--espace-3));
}

.dossier h2:focus {
  outline: none;
}

.dossier__sections {
  display: grid;
  gap: var(--espace-4);
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));
  margin-top: var(--espace-5);
}

.dossier__rubrique {
  padding: var(--espace-4);
  border-radius: var(--rayon-m);
  background: var(--couleur-surface-alt);
}

.dossier__rubrique > :last-child {
  margin-bottom: 0;
}
</style>
