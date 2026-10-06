<script setup lang="ts">
// Champ de formulaire libellé : aide, message d'erreur relié par aria-describedby.
// Les attributs non déclarés (inputmode, spellcheck…) sont transmis à l'<input>.
import { computed } from 'vue'

defineOptions({ inheritAttrs: false })

const modele = defineModel<string>({ required: true })

const props = withDefaults(
  defineProps<{
    id: string
    libelle: string
    type?: 'text' | 'email' | 'password'
    autocomplete?: string
    aide?: string
    erreur?: string | null
    /** Identifiant d'un élément descriptif supplémentaire placé dans le slot. */
    decritPar?: string
  }>(),
  { type: 'text', autocomplete: 'off', aide: '', erreur: null, decritPar: '' },
)

const idAide = computed(() => `${props.id}-aide`)
const idErreur = computed(() => `${props.id}-erreur`)
const descriptions = computed(() => {
  const ids = [props.aide ? idAide.value : '', props.decritPar, props.erreur ? idErreur.value : '']
  return ids.filter((id) => id !== '').join(' ') || undefined
})
</script>

<template>
  <div class="champ">
    <label :for="id" class="champ__libelle">{{ libelle }}</label>
    <p v-if="aide" :id="idAide" class="champ__aide">{{ aide }}</p>
    <input
      :id="id"
      v-model="modele"
      v-bind="$attrs"
      class="champ__saisie"
      :type="type"
      :autocomplete="autocomplete"
      :aria-invalid="erreur ? 'true' : undefined"
      :aria-describedby="descriptions"
    />
    <slot />
    <p v-if="erreur" :id="idErreur" class="champ__erreur">{{ erreur }}</p>
  </div>
</template>
