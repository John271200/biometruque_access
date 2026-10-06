<script setup lang="ts">
// Gabarit général : lien d'évitement, en-tête, message ponctuel, contenu et pied de page.
import { nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import AlerteMessage from './components/AlerteMessage.vue'
import EnTete from './components/EnTete.vue'
import { useFlashStore } from './stores/flash'

const flash = useFlashStore()
const router = useRouter()
const contenu = ref<HTMLElement | null>(null)

// Après chaque changement de page (hors premier affichage), le focus est placé sur le
// contenu principal pour que les lecteurs d'écran annoncent la nouvelle page.
let premiereNavigation = true
router.afterEach((vers, depuis) => {
  if (premiereNavigation) {
    premiereNavigation = false
    return
  }
  if (vers.path === depuis.path) return
  void nextTick(() => contenu.value?.focus({ preventScroll: true }))
})
</script>

<template>
  <a href="#contenu" class="evitement">Aller au contenu</a>
  <EnTete />
  <div v-if="flash.message" class="conteneur flash">
    <AlerteMessage :type="flash.message.type" fermable @fermer="flash.fermer()">
      <p>{{ flash.message.texte }}</p>
    </AlerteMessage>
  </div>
  <main id="contenu" ref="contenu" class="principal" tabindex="-1">
    <RouterView />
  </main>
  <footer class="pied">
    <div class="conteneur">
      <p>
        BioAccess — prototype de recherche (mémoire de Master Génie Logiciel, IFRI, Bénin). Les dossiers
        patients sont fictifs.
      </p>
    </div>
  </footer>
</template>

<style scoped>
.evitement {
  position: absolute;
  top: var(--espace-2);
  left: var(--espace-2);
  z-index: 10;
  padding: var(--espace-2) var(--espace-4);
  border-radius: var(--rayon-s);
  background: var(--couleur-primaire);
  color: var(--couleur-sur-primaire);
  font-weight: var(--graisse-moyenne);
  transform: translateY(-200%);
}

.evitement:focus {
  transform: none;
}

.flash {
  padding-top: var(--espace-4);
}

.principal {
  display: block;
  min-height: 60vh;
}

.principal:focus {
  outline: none;
}

.pied {
  border-top: 1px solid var(--couleur-bordure);
  background: var(--couleur-surface);
  color: var(--couleur-texte-doux);
  font-size: var(--taille-s);
}

.pied p {
  margin: 0;
  padding-block: var(--espace-4);
}
</style>
