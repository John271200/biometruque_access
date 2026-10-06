<script setup lang="ts">
// Page d'accueil : présentation, étapes du parcours et accès rapides.
import { computed } from 'vue'
import { useAccesStore } from '../stores/acces'
import { useCompteStore } from '../stores/compte'

const compte = useCompteStore()
const acces = useAccesStore()

// Avec un jeton d'accès encore valide, inutile de repasser par l'authentification.
const destinationBase = computed(() => (acces.jeton !== null && acces.estValide() ? '/base' : '/acces'))

const etapes = [
  { titre: 'Créer un compte', texte: 'Nom, email et mot de passe robuste.' },
  { titre: 'Consentir', texte: 'Lire et accepter le traitement de vos données biométriques.' },
  {
    titre: "S'enrôler",
    texte: 'Devant la webcam : 5 images du visage de face, puis 5 de l’oreille droite en tournant la tête.',
  },
  { titre: 'Accéder', texte: 'Vous ré-identifier de la même façon pour ouvrir la base protégée (10 minutes).' },
]
</script>

<template>
  <div class="conteneur page">
    <section class="accueil">
      <h1>BioAccess</h1>
      <p class="accueil__accroche">
        BioAccess protège l'accès à une base de dossiers patients par une double vérification biométrique :
        votre visage et votre oreille. Les deux scores sont fusionnés, contrôlés séparément et complétés par
        une vérification de vivacité. Vos gabarits sont protégés (BioHashing et chiffrement) ; aucune image
        n'est conservée.
      </p>
      <div class="actions">
        <template v-if="!compte.connecte">
          <RouterLink to="/inscription" class="bouton">Créer un compte</RouterLink>
          <RouterLink to="/connexion" class="bouton bouton--secondaire">Se connecter</RouterLink>
        </template>
        <RouterLink v-else to="/mon-espace" class="bouton">Mon espace</RouterLink>
        <RouterLink :to="destinationBase" class="bouton bouton--secondaire">Accéder à la base protégée</RouterLink>
      </div>
    </section>

    <section class="parcours" aria-labelledby="titre-parcours">
      <h2 id="titre-parcours">Le parcours en quatre étapes</h2>
      <ol class="parcours__liste">
        <li v-for="(etape, index) in etapes" :key="etape.titre" class="carte parcours__etape">
          <span class="parcours__numero" aria-hidden="true">{{ index + 1 }}</span>
          <h3>{{ etape.titre }}</h3>
          <p class="texte-doux">{{ etape.texte }}</p>
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.accueil {
  padding-block: var(--espace-5) var(--espace-6);
}

.accueil__accroche {
  max-width: var(--largeur-texte);
  margin-bottom: var(--espace-5);
  color: var(--couleur-texte-doux);
  font-size: var(--taille-l);
}

.parcours__liste {
  display: grid;
  gap: var(--espace-4);
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr));
  margin: 0;
  padding: 0;
  list-style: none;
}

.parcours__numero {
  display: inline-grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  margin-bottom: var(--espace-3);
  border-radius: var(--rayon-rond);
  background: var(--couleur-primaire);
  color: var(--couleur-sur-primaire);
  font-weight: var(--graisse-forte);
}
</style>
