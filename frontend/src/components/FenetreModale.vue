<script setup lang="ts">
// Fenêtre modale basée sur <dialog> : piège du focus, touche Échap et fond assombri natifs.
import { onMounted, ref, useId, watch } from 'vue'

const props = defineProps<{ ouverte: boolean; titre: string }>()
const emit = defineEmits<{ fermer: [] }>()

const dialogue = ref<HTMLDialogElement | null>(null)
const idTitre = useId()

function synchroniser(ouverte: boolean): void {
  const element = dialogue.value
  if (!element) return
  if (ouverte && !element.open) element.showModal()
  else if (!ouverte && element.open) element.close()
}

watch(() => props.ouverte, synchroniser, { flush: 'post' })
onMounted(() => synchroniser(props.ouverte))
</script>

<template>
  <dialog ref="dialogue" class="modale" :aria-labelledby="idTitre" @close="emit('fermer')">
    <!-- Le contenu n'existe que modale ouverte : chaque ouverture repart d'un formulaire vierge. -->
    <template v-if="ouverte">
      <h2 :id="idTitre" class="modale__titre">{{ titre }}</h2>
      <slot />
    </template>
  </dialog>
</template>

<style scoped>
.modale {
  width: min(32rem, calc(100vw - 2 * var(--espace-4)));
  max-height: calc(100dvh - 2 * var(--espace-4));
  padding: var(--espace-5);
  border: 0;
  border-radius: var(--rayon-l);
  background: var(--couleur-surface);
  color: var(--couleur-texte);
  box-shadow: var(--ombre-forte);
}

.modale::backdrop {
  background: rgb(15 21 32 / 55%);
}

.modale__titre {
  margin-bottom: var(--espace-4);
}
</style>
