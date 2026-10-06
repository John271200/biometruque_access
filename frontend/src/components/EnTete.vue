<script setup lang="ts">
// En-tête : marque, navigation principale et déconnexion.
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAccesStore } from '../stores/acces'
import { useCompteStore } from '../stores/compte'
import { useFlashStore } from '../stores/flash'

const compte = useCompteStore()
const acces = useAccesStore()
const flash = useFlashStore()
const router = useRouter()
const deconnexionEnCours = ref(false)

async function deconnecter(): Promise<void> {
  deconnexionEnCours.value = true
  await compte.deconnecter()
  acces.effacer()
  deconnexionEnCours.value = false
  flash.publier('Vous êtes déconnecté.', 'info')
  await router.push({ name: 'accueil' })
}
</script>

<template>
  <header class="entete">
    <div class="conteneur entete__barre">
      <RouterLink to="/" class="entete__marque">
        <svg class="entete__logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
          <rect width="32" height="32" rx="7" fill="currentColor" />
          <path
            d="M11 9.5a7 7 0 0 1 10 0M8.5 13a10 10 0 0 1 15 0M12.5 23c-1-2-1.5-4-1.5-6a5 5 0 0 1 10 0c0 1.2-.2 2.4-.6 3.5M16 17c0 2.5.7 4.8 2 6.8"
            fill="none"
            stroke="#fff"
            stroke-width="2"
            stroke-linecap="round"
          />
        </svg>
        BioAccess
      </RouterLink>
      <nav aria-label="Navigation principale">
        <ul class="entete__liens">
          <li><RouterLink to="/acces" class="entete__lien">Accès biométrique</RouterLink></li>
          <template v-if="compte.connecte">
            <li><RouterLink to="/mon-espace" class="entete__lien">Mon espace</RouterLink></li>
            <li>
              <button
                type="button"
                class="entete__lien entete__bouton"
                :disabled="deconnexionEnCours"
                @click="deconnecter"
              >
                Se déconnecter
              </button>
            </li>
          </template>
          <template v-else>
            <li><RouterLink to="/connexion" class="entete__lien">Se connecter</RouterLink></li>
            <li><RouterLink to="/inscription" class="entete__lien">Créer un compte</RouterLink></li>
          </template>
        </ul>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.entete {
  background: var(--couleur-surface);
  border-bottom: 1px solid var(--couleur-bordure);
}

.entete__barre {
  display: flex;
  flex-wrap: wrap;
  gap: var(--espace-2) var(--espace-4);
  align-items: center;
  justify-content: space-between;
  padding-block: var(--espace-2);
}

.entete__marque {
  display: inline-flex;
  gap: var(--espace-2);
  align-items: center;
  min-height: var(--cible-tactile);
  color: var(--couleur-primaire);
  font-size: var(--taille-l);
  font-weight: var(--graisse-forte);
  text-decoration: none;
}

.entete__logo {
  width: 2rem;
  height: 2rem;
}

.entete__liens {
  display: flex;
  flex-wrap: wrap;
  gap: var(--espace-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.entete__lien {
  display: inline-flex;
  align-items: center;
  min-height: var(--cible-tactile);
  padding: 0 var(--espace-3);
  border-radius: var(--rayon-s);
  color: var(--couleur-texte);
  font-size: var(--taille-s);
  font-weight: var(--graisse-moyenne);
  text-decoration: none;
}

.entete__lien:hover {
  background: var(--couleur-primaire-pale);
  color: var(--couleur-primaire-survol);
}

.entete__lien.router-link-active {
  color: var(--couleur-primaire);
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 0.4em;
}

.entete__bouton {
  border: 0;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}

@media (max-width: 30rem) {
  .entete__liens {
    width: 100%;
    margin-left: calc(-1 * var(--espace-3));
  }
}
</style>
