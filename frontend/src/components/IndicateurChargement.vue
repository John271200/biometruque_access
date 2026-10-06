<script setup lang="ts">
// Indicateur de chargement accessible (texte lu par les lecteurs d'écran).
withDefaults(defineProps<{ texte?: string }>(), { texte: 'Chargement…' })
</script>

<template>
  <p class="chargement" role="status">
    <span class="chargement__roue" aria-hidden="true"></span>
    {{ texte }}
  </p>
</template>

<style scoped>
.chargement {
  display: flex;
  gap: var(--espace-3);
  align-items: center;
  color: var(--couleur-texte-doux);
}

.chargement__roue {
  width: 1.25rem;
  height: 1.25rem;
  border: 3px solid var(--couleur-bordure);
  border-top-color: var(--couleur-primaire);
  border-radius: var(--rayon-rond);
  animation: rotation 0.8s linear infinite;
}

@keyframes rotation {
  to {
    transform: rotate(360deg);
  }
}
</style>
