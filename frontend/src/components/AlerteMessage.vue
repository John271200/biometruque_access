<script setup lang="ts">
// Encart de message (information, succès, alerte, erreur). Les erreurs sont annoncées
// immédiatement aux lecteurs d'écran (role="alert"), les autres poliment (role="status").
import { computed } from 'vue'
import type { TypeMessage } from '../stores/flash'

const props = defineProps<{
  type: TypeMessage
  titre?: string
  fermable?: boolean
}>()

const emit = defineEmits<{ fermer: [] }>()

const ICONES: Record<TypeMessage, string> = { info: 'i', succes: '✓', alerte: '!', erreur: '✕' }
const role = computed(() => (props.type === 'erreur' ? 'alert' : 'status'))
</script>

<template>
  <div class="alerte" :class="`alerte--${type}`" :role="role">
    <span class="alerte__icone" aria-hidden="true">{{ ICONES[type] }}</span>
    <div class="alerte__corps">
      <p v-if="titre" class="alerte__titre">{{ titre }}</p>
      <slot />
    </div>
    <button v-if="fermable" type="button" class="alerte__fermer" @click="emit('fermer')">
      <span aria-hidden="true">×</span>
      <span class="visuellement-masque">Fermer le message</span>
    </button>
  </div>
</template>

<style scoped>
.alerte {
  --couleur-alerte-accent: var(--couleur-info);
  --couleur-alerte-fond: var(--couleur-info-pale);
  display: flex;
  gap: var(--espace-3);
  align-items: flex-start;
  padding: var(--espace-3) var(--espace-4);
  border: 1px solid var(--couleur-alerte-accent);
  border-left-width: 5px;
  border-radius: var(--rayon-s);
  background: var(--couleur-alerte-fond);
}

.alerte--succes {
  --couleur-alerte-accent: var(--couleur-succes);
  --couleur-alerte-fond: var(--couleur-succes-pale);
}

.alerte--alerte {
  --couleur-alerte-accent: var(--couleur-alerte);
  --couleur-alerte-fond: var(--couleur-alerte-pale);
}

.alerte--erreur {
  --couleur-alerte-accent: var(--couleur-danger);
  --couleur-alerte-fond: var(--couleur-danger-pale);
}

.alerte__icone {
  display: inline-grid;
  flex: none;
  place-items: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: var(--rayon-rond);
  background: var(--couleur-alerte-accent);
  color: var(--couleur-surface);
  font-size: var(--taille-s);
  font-weight: var(--graisse-forte);
}

.alerte__corps {
  flex: 1;
  min-width: 0;
  color: var(--couleur-texte);
}

.alerte__corps :deep(p:last-child),
.alerte__corps :deep(ul:last-child) {
  margin-bottom: 0;
}

.alerte__titre {
  margin-bottom: var(--espace-1);
  color: var(--couleur-alerte-accent);
  font-weight: var(--graisse-forte);
}

.alerte__fermer {
  flex: none;
  width: var(--cible-tactile);
  height: var(--cible-tactile);
  margin: calc(-1 * var(--espace-2)) calc(-1 * var(--espace-2)) 0 0;
  border: 0;
  border-radius: var(--rayon-s);
  background: transparent;
  color: var(--couleur-texte);
  font-size: var(--taille-l);
  cursor: pointer;
}

.alerte__fermer:hover {
  background: rgb(0 0 0 / 6%);
}
</style>
