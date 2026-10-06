<script setup lang="ts">
// Jauge de rotation de la tête (lacet, en degrés) avec repère de l'angle visé.
import { computed, useId } from 'vue'

const props = withDefaults(defineProps<{ lacet: number | null; cible?: number; maximum?: number }>(), {
  cible: 45,
  maximum: 90,
})

const idLibelle = useId()
const valeur = computed(() => (props.lacet === null ? 0 : Math.min(Math.abs(props.lacet), props.maximum)))
const atteinte = computed(() => props.lacet !== null && Math.abs(props.lacet) >= props.cible)
const texte = computed(() =>
  props.lacet === null
    ? 'non mesurée'
    : `${Math.round(Math.abs(props.lacet))}° (objectif : ${props.cible}° ou plus)`,
)
</script>

<template>
  <div class="jauge">
    <p class="jauge__entete">
      <span :id="idLibelle">Rotation de la tête</span>
      <span class="jauge__valeur">{{ texte }}</span>
    </p>
    <div
      class="jauge__piste"
      role="meter"
      :aria-labelledby="idLibelle"
      aria-valuemin="0"
      :aria-valuemax="maximum"
      :aria-valuenow="Math.round(valeur)"
      :aria-valuetext="texte"
    >
      <div
        class="jauge__remplissage"
        :class="{ 'jauge__remplissage--atteinte': atteinte }"
        :style="{ width: `${(valeur / maximum) * 100}%` }"
      ></div>
      <div class="jauge__cible" :style="{ left: `${(cible / maximum) * 100}%` }" aria-hidden="true"></div>
    </div>
  </div>
</template>

<style scoped>
.jauge__entete {
  display: flex;
  flex-wrap: wrap;
  gap: var(--espace-1) var(--espace-3);
  justify-content: space-between;
  margin-bottom: var(--espace-2);
  font-size: var(--taille-s);
  font-weight: var(--graisse-moyenne);
}

.jauge__valeur {
  color: var(--couleur-texte-doux);
  font-variant-numeric: tabular-nums;
}

.jauge__piste {
  position: relative;
  height: 0.875rem;
  border: 1px solid var(--couleur-bordure-forte);
  border-radius: var(--rayon-rond);
  background: var(--couleur-surface-alt);
  overflow: hidden;
}

.jauge__remplissage {
  height: 100%;
  background: var(--couleur-primaire);
  transition: width var(--duree) ease-out;
}

.jauge__remplissage--atteinte {
  background: var(--couleur-succes);
}

.jauge__cible {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 3px;
  margin-left: -1px;
  background: var(--couleur-texte);
}
</style>
