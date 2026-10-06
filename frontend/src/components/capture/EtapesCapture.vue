<script setup lang="ts">
// Indicateur d'étapes « Visage n/N → Rotation → Oreille n/N ».
import { computed } from 'vue'
import type { EtapeCapture } from '../../api'

const props = defineProps<{
  etape: EtapeCapture
  capturesVisage: number
  capturesVisageRequises: number
  capturesOreille: number
  capturesOreilleRequises: number
}>()

type Statut = 'fait' | 'en-cours' | 'a-venir'

/** Rang de l'étape courante (0 visage, 1 rotation, 2 oreille, 3 terminé). */
const rang = computed(() => {
  switch (props.etape) {
    case 'visage':
      return 0
    case 'rotation':
      return 1
    case 'oreille':
      return 2
    case 'terminee':
      return 3
    case 'echec':
      // En cas d'échec, on situe l'étape d'après les captures déjà obtenues.
      if (props.capturesOreille > 0) return 2
      return props.capturesVisage >= props.capturesVisageRequises ? 1 : 0
  }
})

const LIBELLES_STATUT: Record<Statut, string> = { fait: 'terminée', 'en-cours': 'en cours', 'a-venir': 'à venir' }

const etapes = computed(() =>
  [
    `Visage ${props.capturesVisage}/${props.capturesVisageRequises}`,
    'Rotation',
    `Oreille ${props.capturesOreille}/${props.capturesOreilleRequises}`,
  ].map((libelle, index) => {
    const statut: Statut = index < rang.value ? 'fait' : index === rang.value ? 'en-cours' : 'a-venir'
    return { libelle, statut }
  }),
)
</script>

<template>
  <ol class="etapes" aria-label="Progression de la capture">
    <li v-for="etapeAffichee in etapes" :key="etapeAffichee.libelle" class="etapes__item">
      <span
        class="etapes__pastille"
        :class="`etapes__pastille--${etapeAffichee.statut}`"
        :aria-current="etapeAffichee.statut === 'en-cours' ? 'step' : undefined"
      >
        <span class="etapes__puce" aria-hidden="true">{{ etapeAffichee.statut === 'fait' ? '✓' : '' }}</span>
        {{ etapeAffichee.libelle }}
        <span class="visuellement-masque">({{ LIBELLES_STATUT[etapeAffichee.statut] }})</span>
      </span>
    </li>
  </ol>
</template>

<style scoped>
.etapes {
  display: flex;
  flex-wrap: wrap;
  gap: var(--espace-2);
  align-items: center;
  margin: 0;
  padding: 0;
  list-style: none;
}

.etapes__item {
  display: inline-flex;
  gap: var(--espace-2);
  align-items: center;
}

/* Flèche décorative entre les étapes (ignorée par les lecteurs d'écran). */
.etapes__item + .etapes__item::before {
  content: "→";
  content: "→" / "";
  color: var(--couleur-texte-doux);
}

.etapes__pastille {
  display: inline-flex;
  gap: var(--espace-2);
  align-items: center;
  padding: var(--espace-1) var(--espace-3);
  border: 1px solid var(--couleur-bordure);
  border-radius: var(--rayon-rond);
  background: var(--couleur-surface);
  color: var(--couleur-texte-doux);
  font-size: var(--taille-s);
  font-weight: var(--graisse-moyenne);
  font-variant-numeric: tabular-nums;
}

.etapes__puce {
  display: inline-grid;
  place-items: center;
  width: 1.125rem;
  height: 1.125rem;
  border: 2px solid currentColor;
  border-radius: var(--rayon-rond);
  font-size: 0.7rem;
}

.etapes__pastille--en-cours {
  border-color: var(--couleur-primaire);
  background: var(--couleur-primaire-pale);
  color: var(--couleur-primaire);
}

.etapes__pastille--en-cours .etapes__puce {
  background: var(--couleur-primaire);
}

.etapes__pastille--fait {
  border-color: var(--couleur-succes);
  background: var(--couleur-succes-pale);
  color: var(--couleur-succes);
}

.etapes__pastille--fait .etapes__puce {
  border-color: var(--couleur-succes);
  background: var(--couleur-succes);
  color: var(--couleur-surface);
}
</style>
