<script setup lang="ts">
// Résultat d'une authentification : verdict, raison du refus, scores (quand le serveur
// les expose) et tableau des règles R1–R4. Les actions sont fournies par le slot.
import { computed, onMounted, ref } from 'vue'
import type { Decision } from '../api'
import { formaterScore } from '../utils/format'

const props = defineProps<{ decision: Decision }>()

const titre = ref<HTMLElement | null>(null)

const scores = computed(() =>
  [
    { libelle: 'Score visage', valeur: props.decision.score_visage },
    { libelle: 'Score oreille', valeur: props.decision.score_oreille },
    { libelle: 'Score de fusion', valeur: props.decision.score_fusion },
  ].filter((score) => score.valeur !== null),
)

/** En production, valeurs et seuils sont masqués (null) : les colonnes sont alors omises. */
const afficherValeurs = computed(() => props.decision.regles.some((r) => r.valeur !== null || r.seuil !== null))

// Le focus est placé sur le verdict pour qu'il soit lu immédiatement.
onMounted(() => titre.value?.focus())
</script>

<template>
  <section class="decision carte" :class="decision.accepte ? 'decision--accorde' : 'decision--refuse'">
    <h2 ref="titre" class="decision__verdict" tabindex="-1">
      <span class="decision__icone" aria-hidden="true">{{ decision.accepte ? '✓' : '✕' }}</span>
      {{ decision.accepte ? 'Accès accordé' : 'Accès refusé' }}
    </h2>
    <p v-if="!decision.accepte && decision.raison" class="decision__raison">
      <strong>Raison :</strong> {{ decision.raison }}
    </p>

    <dl v-if="scores.length > 0" class="definitions decision__scores">
      <template v-for="score in scores" :key="score.libelle">
        <dt>{{ score.libelle }}</dt>
        <dd>{{ formaterScore(score.valeur) }}</dd>
      </template>
    </dl>

    <table class="tableau tableau--adaptatif decision__regles">
      <caption>Règles de décision (l'accès exige que les quatre soient respectées)</caption>
      <thead>
        <tr>
          <th scope="col">Règle</th>
          <th scope="col">Verdict</th>
          <th v-if="afficherValeurs" scope="col" class="nombre">Valeur</th>
          <th v-if="afficherValeurs" scope="col" class="nombre">Seuil</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="regle in decision.regles" :key="regle.code">
          <th scope="row" data-libelle="Règle">
            <span><strong>{{ regle.code }}</strong> · {{ regle.libelle }}</span>
          </th>
          <td data-libelle="Verdict">
            <span class="pastille" :class="regle.ok ? 'pastille--succes' : 'pastille--danger'">
              <span aria-hidden="true">{{ regle.ok ? '✓' : '✗' }}</span>
              {{ regle.ok ? 'Respectée' : 'Non respectée' }}
            </span>
          </td>
          <td v-if="afficherValeurs" class="nombre" data-libelle="Valeur">{{ formaterScore(regle.valeur) }}</td>
          <td v-if="afficherValeurs" class="nombre" data-libelle="Seuil">{{ formaterScore(regle.seuil) }}</td>
        </tr>
      </tbody>
    </table>

    <div class="actions decision__actions">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.decision {
  --couleur-verdict: var(--couleur-succes);
  border-top: 6px solid var(--couleur-verdict);
}

.decision--refuse {
  --couleur-verdict: var(--couleur-danger);
}

.decision__verdict {
  display: flex;
  gap: var(--espace-3);
  align-items: center;
  color: var(--couleur-verdict);
  font-size: var(--taille-xl);
}

.decision__icone {
  display: inline-grid;
  flex: none;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--rayon-rond);
  background: var(--couleur-verdict);
  color: var(--couleur-surface);
}

.decision__raison {
  padding: var(--espace-3);
  border-radius: var(--rayon-s);
  background: var(--couleur-danger-pale);
}

.decision__scores {
  font-variant-numeric: tabular-nums;
}

.decision__regles {
  margin-block: var(--espace-4);
}

.decision__regles tbody th {
  font-weight: var(--graisse-normale);
}
</style>
