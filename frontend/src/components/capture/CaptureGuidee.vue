<script setup lang="ts">
/*
 * Capture biométrique guidée, commune à l'enrôlement et à l'authentification.
 *
 * Boucle strictement séquentielle : capture d'une image 640×480 non miroir → envoi →
 * attente de la réponse → mise à jour de l'interface → image suivante au moins 250 ms
 * après la précédente. Jamais deux requêtes en vol. Arrêt sur etape « terminee » ou « echec ».
 *
 * L'utilisateur ne voit plus l'écran quand il tourne la tête de profil : les consignes sont
 * donc aussi lues à voix haute et chaque image retenue est signalée par un bip.
 */
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { ApiError, messageErreur, type ModeCapture, type RetourImage, type SessionInfo } from '../../api'
import { MESSAGES_CAMERA, useCamera } from '../../composables/useCamera'
import { useGuidageVocal } from '../../composables/useGuidageVocal'
import { useSignauxSonores } from '../../composables/useSignauxSonores'
import AlerteMessage from '../AlerteMessage.vue'
import EtapesCapture from './EtapesCapture.vue'
import JaugeLacet from './JaugeLacet.vue'
import { creerCaptureur, dessinerSurimpression } from './image'
import type { AbandonSession, EchecCapture, EnvoiImage } from './types'

const props = defineProps<{
  mode: ModeCapture
  sessionInfo: SessionInfo
  envoyerImage: EnvoiImage
  /** Appelée au démontage si la capture est restée inachevée. */
  abandonnerSession?: AbandonSession
}>()

const emit = defineEmits<{
  /** Dernier RetourImage complet (avec `utilisateur`, ou `decision` et éventuellement `jeton_acces`). */
  terminee: [retour: RetourImage]
  echec: [erreur: EchecCapture]
  recommencer: []
}>()

const INTERVALLE_MIN_MS = 250
const ECHECS_TRANSITOIRES_MAX = 3
const LACET_CIBLE = 45
const CONSIGNE_INITIALE = "Regardez la caméra de face et placez votre visage dans l'ovale."

type Phase = 'preparation' | 'demarrage' | 'capture' | 'terminee' | 'echec'

const video = ref<HTMLVideoElement | null>(null)
const surimpression = ref<HTMLCanvasElement | null>(null)
const phase = ref<Phase>('preparation')
const retour = ref<RetourImage | null>(null)
const echec = ref<EchecCapture | null>(null)
const reseauInstable = ref(false)
const idTitre = useId()
const idInterrupteur = useId()

const {
  erreur: erreurCamera,
  active: cameraActive,
  demarrer: demarrerCamera,
  arreter: arreterCamera,
} = useCamera(video)
const { disponible: vocalDisponible, actif: vocalActif, annoncer } = useGuidageVocal()
const sons = useSignauxSonores()
const capturer = creerCaptureur()

let boucleActive = false
let demonte = false
let observateur: ResizeObserver | null = null

// ---- Données dérivées pour l'affichage ----

const coteOreille = computed(() => props.sessionInfo.cote_attendu ?? 'droite')
const sensRotation = computed(() => (coteOreille.value === 'droite' ? 'gauche' : 'droite'))
const etape = computed(() => retour.value?.etape ?? 'visage')
const criteres = computed(() => retour.value?.criteres ?? [])

const progression = computed(() => ({
  capturesVisage: retour.value?.captures_visage ?? 0,
  capturesVisageRequises: retour.value?.captures_visage_requises ?? props.sessionInfo.captures_visage_requises,
  capturesOreille: retour.value?.captures_oreille ?? 0,
  capturesOreilleRequises: retour.value?.captures_oreille_requises ?? props.sessionInfo.captures_oreille_requises,
}))

/** Le contrat annonce du JPEG base64 : on accepte aussi une data URL déjà formée. */
const apercuOreille = computed(() => {
  const brut = retour.value?.apercu_oreille
  if (!brut) return null
  return brut.startsWith('data:') ? brut : `data:image/jpeg;base64,${brut}`
})

const messageFinal = computed(() => {
  const decision = retour.value?.decision
  if (decision) return decision.accepte ? 'Accès accordé.' : 'Accès refusé.'
  return retour.value?.message || 'Capture terminée.'
})

const messagePrincipal = computed(() => {
  switch (phase.value) {
    case 'preparation':
      return erreurCamera.value ? 'Caméra indisponible.' : 'Lisez les conseils, puis démarrez la capture.'
    case 'demarrage':
      return 'Activation de la caméra…'
    case 'capture':
      return retour.value?.message || CONSIGNE_INITIALE
    case 'terminee':
      return messageFinal.value
    case 'echec':
      return echec.value?.titre ?? 'Capture interrompue.'
  }
})

const mentionConfidentialite = computed(() =>
  props.mode === 'enrolement'
    ? 'Les images sont analysées puis effacées : seul un gabarit protégé (BioHashing et chiffrement AES-256) est conservé.'
    : "Les images sont analysées puis effacées : aucune image n'est conservée.",
)

// ---- Surimpression (cadres et guide ovale) ----

function redessiner(): void {
  const canvas = surimpression.value
  if (!canvas) return
  const enCapture = phase.value === 'capture'
  const actuel = enCapture ? retour.value : null
  dessinerSurimpression(canvas, {
    guideOvale: enCapture && etape.value === 'visage',
    cadreVisage: actuel?.cadre_visage ?? null,
    cadreOreille: actuel?.cadre_oreille ?? null,
    visageConforme: actuel !== null && (actuel.image_retenue || actuel.criteres.every((c) => c.ok)),
  })
}

watch([retour, phase], redessiner, { flush: 'post' })

onMounted(() => {
  if (surimpression.value && typeof ResizeObserver !== 'undefined') {
    observateur = new ResizeObserver(redessiner)
    observateur.observe(surimpression.value)
  }
})

// ---- Boucle d'envoi ----

const pause = (ms: number) => new Promise<void>((resoudre) => window.setTimeout(resoudre, ms))

/** Erreurs passagères : on retente quelques fois avant d'abandonner. */
function estTransitoire(erreur: unknown): boolean {
  if (!(erreur instanceof ApiError)) return false
  return (
    erreur.statut === 0 ||
    erreur.code === 'IMAGE_EN_COURS' ||
    erreur.statut === 429 ||
    (erreur.statut >= 502 && erreur.statut <= 504)
  )
}

function versEchec(erreur: unknown): EchecCapture {
  if (erreur instanceof ApiError && erreur.code === 'SESSION_INTROUVABLE') {
    return {
      code: erreur.code,
      titre: 'Session expirée',
      message:
        'La session de capture a expiré (plus de deux minutes sans image reçue). Cliquez sur «\u00a0Recommencer\u00a0» pour en ouvrir une nouvelle.',
    }
  }
  return {
    code: erreur instanceof ApiError ? erreur.code : 'ERREUR_INATTENDUE',
    titre: 'Capture interrompue',
    message: messageErreur(erreur),
  }
}

function terminer(reponse: RetourImage): void {
  boucleActive = false
  phase.value = 'terminee'
  arreterCamera()
  if (reponse.decision && !reponse.decision.accepte) sons.echec()
  else sons.succes()
  annoncer(messageFinal.value, true)
  emit('terminee', reponse)
}

function echouer(erreur: EchecCapture): void {
  boucleActive = false
  echec.value = erreur
  phase.value = 'echec'
  arreterCamera()
  sons.echec()
  annoncer(`${erreur.titre}. ${erreur.message}`, true)
  emit('echec', erreur)
}

function traiterRetour(reponse: RetourImage): void {
  retour.value = reponse
  if (reponse.etape === 'terminee') {
    terminer(reponse)
  } else if (reponse.etape === 'echec') {
    echouer({
      code: 'ECHEC_CAPTURE',
      titre: 'Capture interrompue',
      message: reponse.raison_echec || reponse.message || 'La capture a échoué. Recommencez.',
    })
  } else {
    if (reponse.image_retenue) sons.bip()
    annoncer(reponse.message)
  }
}

async function boucle(): Promise<void> {
  boucleActive = true
  let echecsTransitoires = 0
  let debutPrecedent = Number.NEGATIVE_INFINITY
  while (boucleActive) {
    const attente = INTERVALLE_MIN_MS - (performance.now() - debutPrecedent)
    if (attente > 0) await pause(attente)
    const element = video.value
    if (!boucleActive || !element) break
    debutPrecedent = performance.now()
    const image = await capturer(element)
    if (!image) continue
    try {
      const reponse = await props.envoyerImage(props.sessionInfo.session_id, image)
      if (!boucleActive) break
      echecsTransitoires = 0
      reseauInstable.value = false
      traiterRetour(reponse)
    } catch (erreur) {
      if (!boucleActive) break
      if (estTransitoire(erreur) && echecsTransitoires < ECHECS_TRANSITOIRES_MAX) {
        echecsTransitoires += 1
        reseauInstable.value = true
        continue
      }
      echouer(versEchec(erreur))
    }
  }
}

async function demarrer(): Promise<void> {
  // Le clic débloque l'audio (WebAudio et synthèse vocale) selon les règles des navigateurs.
  sons.activer()
  phase.value = 'demarrage'
  const ok = await demarrerCamera()
  if (demonte) return
  if (!ok) {
    phase.value = 'preparation'
    return
  }
  phase.value = 'capture'
  annoncer(CONSIGNE_INITIALE, true)
  void boucle()
}

onBeforeUnmount(() => {
  demonte = true
  boucleActive = false
  observateur?.disconnect()
  const inachevee = phase.value !== 'terminee' && phase.value !== 'echec'
  if (inachevee && props.abandonnerSession) {
    props.abandonnerSession(props.sessionInfo.session_id).catch(() => undefined)
  }
})
</script>

<template>
  <section class="capture" :aria-labelledby="idTitre">
    <h2 :id="idTitre" class="visuellement-masque">
      {{ mode === 'enrolement' ? "Capture d'enrôlement" : "Capture d'authentification" }}
    </h2>
    <div class="capture__grille">
      <div class="capture__scene">
        <p
          class="capture__message"
          :class="`capture__message--${phase}`"
          aria-live="polite"
          aria-atomic="true"
        >
          {{ messagePrincipal }}
        </p>
        <div class="capture__cadre">
          <video
            ref="video"
            class="capture__video capture__miroir"
            autoplay
            muted
            playsinline
            aria-label="Image de votre caméra, affichée en miroir"
          ></video>
          <canvas ref="surimpression" class="capture__surimpression capture__miroir" aria-hidden="true"></canvas>
          <div v-if="!cameraActive" class="capture__veille" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="48" height="48" focusable="false">
              <path
                d="M3 7.5A1.5 1.5 0 0 1 4.5 6h3l1.5-2h6l1.5 2h3A1.5 1.5 0 0 1 21 7.5v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              />
              <circle cx="12" cy="12.5" r="3.5" fill="none" stroke="currentColor" stroke-width="1.5" />
            </svg>
            <span>Caméra inactive</span>
          </div>
        </div>
        <p v-if="phase === 'capture'" class="texte-petit texte-doux capture__legende">
          Ovale : position du visage · cadre vert : visage conforme · cadre orange : à corriger · cadre bleu :
          zone de l'oreille analysée.
        </p>
        <p v-if="reseauInstable && phase === 'capture'" class="capture__reseau" role="status">
          Connexion instable : nouvel essai en cours…
        </p>
      </div>

      <div class="capture__panneau">
        <div class="interrupteur">
          <input
            :id="idInterrupteur"
            v-model="vocalActif"
            type="checkbox"
            role="switch"
            :disabled="!vocalDisponible"
          />
          <label :for="idInterrupteur">Guidage vocal</label>
          <span class="texte-petit texte-doux">
            {{ vocalDisponible ? (vocalActif ? 'activé' : 'désactivé') : 'indisponible sur ce navigateur' }}
          </span>
        </div>

        <template v-if="phase === 'preparation' || phase === 'demarrage'">
          <AlerteMessage v-if="erreurCamera" type="erreur" titre="Caméra indisponible">
            <p>{{ MESSAGES_CAMERA[erreurCamera] }}</p>
          </AlerteMessage>
          <div class="conseils">
            <h3>Comment bien se placer</h3>
            <ul>
              <li>Éclairez votre visage <strong>de face</strong> (lumière devant vous, pas dans votre dos).</li>
              <li>Un <strong>seul visage</strong> doit être visible par la caméra.</li>
              <li>Dégagez votre <strong>oreille {{ coteOreille }}</strong> : cheveux derrière l'oreille.</li>
              <li>Retirez <strong>écouteurs et bonnet</strong> (ou tout couvre-chef).</li>
              <li>Tournez la tête <strong>lentement</strong>, d'un mouvement continu.</li>
            </ul>
            <h3>Déroulement</h3>
            <ol>
              <li>Regardez la caméra de face : {{ sessionInfo.captures_visage_requises }} images du visage.</li>
              <li>
                Tournez lentement la tête vers la <strong>{{ sensRotation }}</strong> jusqu'à présenter votre
                oreille {{ coteOreille }}.
              </li>
              <li>Gardez la pose : {{ sessionInfo.captures_oreille_requises }} images de l'oreille.</li>
            </ol>
            <p>
              De profil, vous ne verrez plus l'écran : les consignes sont lues à voix haute et un
              <strong>bip</strong> signale chaque image retenue.
            </p>
            <p class="texte-petit texte-doux">{{ mentionConfidentialite }}</p>
          </div>
          <button type="button" class="bouton" :disabled="phase === 'demarrage'" @click="demarrer">
            {{ erreurCamera ? 'Réessayer' : 'Activer la caméra et démarrer' }}
          </button>
        </template>

        <template v-else-if="phase === 'capture'">
          <EtapesCapture :etape="etape" v-bind="progression" />
          <JaugeLacet :lacet="retour?.lacet ?? null" :cible="LACET_CIBLE" />
          <div v-if="criteres.length > 0">
            <h3 class="capture__sous-titre">Critères de qualité</h3>
            <ul class="criteres">
              <li
                v-for="critere in criteres"
                :key="critere.code"
                class="criteres__item"
                :class="critere.ok ? 'criteres__item--ok' : 'criteres__item--ko'"
              >
                <span class="criteres__icone" aria-hidden="true">{{ critere.ok ? '✓' : '✗' }}</span>
                <span>
                  <strong>{{ critere.ok ? 'OK' : 'À corriger' }}</strong> — {{ critere.message }}
                </span>
              </li>
            </ul>
          </div>
          <figure v-if="apercuOreille" class="apercu">
            <img :src="apercuOreille" alt="Aperçu de la zone de l'oreille analysée" />
            <figcaption class="texte-petit texte-doux">Zone de l'oreille analysée</figcaption>
          </figure>
        </template>

        <template v-else-if="phase === 'echec' && echec">
          <AlerteMessage type="erreur" :titre="echec.titre">
            <p>{{ echec.message }}</p>
          </AlerteMessage>
          <button type="button" class="bouton" @click="emit('recommencer')">Recommencer</button>
        </template>

        <AlerteMessage v-else-if="phase === 'terminee'" type="succes" titre="Capture terminée">
          <p>Toutes les images nécessaires ont été analysées.</p>
        </AlerteMessage>
      </div>
    </div>
  </section>
</template>

<style scoped>
.capture__grille {
  display: grid;
  gap: var(--espace-5);
}

@media (min-width: 60rem) {
  .capture__grille {
    grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    align-items: start;
  }
}

.capture__scene > * + *,
.capture__panneau > * + * {
  margin-top: var(--espace-4);
}

.capture__message {
  min-height: 2.6em;
  margin: 0;
  padding: var(--espace-3) var(--espace-4);
  border-left: 6px solid var(--couleur-primaire);
  border-radius: var(--rayon-s);
  background: var(--couleur-surface);
  box-shadow: var(--ombre);
  font-size: var(--taille-l);
  font-weight: var(--graisse-forte);
  line-height: 1.3;
}

@media (min-width: 48rem) {
  .capture__message {
    font-size: var(--taille-xl);
  }
}

.capture__message--terminee {
  border-left-color: var(--couleur-succes);
}

.capture__message--echec {
  border-left-color: var(--couleur-danger);
}

.capture__cadre {
  position: relative;
  aspect-ratio: 4 / 3;
  border-radius: var(--rayon-l);
  background: var(--couleur-video);
  overflow: hidden;
}

.capture__video,
.capture__surimpression {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.capture__video {
  object-fit: cover;
}

/* Affichage en miroir, plus naturel ; les images envoyées au serveur restent non miroir. */
.capture__miroir {
  transform: scaleX(-1);
}

.capture__veille {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: var(--espace-2);
  color: var(--couleur-sur-video);
}

.capture__legende {
  margin-bottom: 0;
}

.capture__reseau {
  margin: 0;
  color: var(--couleur-alerte);
  font-weight: var(--graisse-moyenne);
}

.capture__sous-titre {
  margin-bottom: var(--espace-2);
}

.conseils {
  padding: var(--espace-4);
  border: 1px solid var(--couleur-bordure);
  border-radius: var(--rayon-m);
  background: var(--couleur-surface);
}

.conseils > :last-child {
  margin-bottom: 0;
}

.criteres {
  margin: 0;
  padding: 0;
  list-style: none;
}

.criteres__item {
  display: flex;
  gap: var(--espace-2);
  align-items: flex-start;
  padding: var(--espace-2) var(--espace-3);
  border-radius: var(--rayon-s);
  font-size: var(--taille-s);
}

.criteres__item + .criteres__item {
  margin-top: var(--espace-1);
}

.criteres__item--ok {
  color: var(--couleur-texte-doux);
}

.criteres__item--ok .criteres__icone {
  color: var(--couleur-succes);
}

.criteres__item--ko {
  background: var(--couleur-alerte-pale);
  color: var(--couleur-texte);
}

.criteres__item--ko .criteres__icone {
  color: var(--couleur-alerte);
}

.criteres__icone {
  flex: none;
  font-weight: var(--graisse-forte);
}

.apercu {
  margin: 0;
}

.apercu img {
  width: 10rem;
  border: 1px solid var(--couleur-bordure);
  border-radius: var(--rayon-s);
}

.interrupteur {
  display: flex;
  flex-wrap: wrap;
  gap: var(--espace-2) var(--espace-3);
  align-items: center;
  font-weight: var(--graisse-moyenne);
}

.interrupteur input {
  position: relative;
  flex: none;
  width: 2.75rem;
  height: 1.5rem;
  margin: 0;
  border: 0;
  border-radius: var(--rayon-rond);
  background: var(--couleur-bordure-forte);
  cursor: pointer;
  appearance: none;
  transition: background-color var(--duree);
}

.interrupteur input::before {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: calc(1.5rem - 6px);
  height: calc(1.5rem - 6px);
  border-radius: var(--rayon-rond);
  background: var(--couleur-surface);
  transition: transform var(--duree);
}

.interrupteur input:checked {
  background: var(--couleur-primaire);
}

.interrupteur input:checked::before {
  transform: translateX(1.25rem);
}

.interrupteur input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
