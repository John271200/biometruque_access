/*
 * Routes de l'application et garde d'accès :
 * - meta.requiert = 'compte' : jeton compte valide exigé (sinon → /connexion) ;
 * - meta.requiert = 'acces'  : jeton acces valide en mémoire exigé (sinon → /acces).
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAccesStore } from '../stores/acces'
import { useCompteStore } from '../stores/compte'
import { useFlashStore } from '../stores/flash'
import AccueilVue from '../views/AccueilVue.vue'

declare module 'vue-router' {
  interface RouteMeta {
    titre: string
    requiert?: 'compte' | 'acces'
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'accueil', component: AccueilVue, meta: { titre: 'Accueil' } },
    {
      path: '/inscription',
      name: 'inscription',
      component: () => import('../views/InscriptionVue.vue'),
      meta: { titre: 'Créer un compte' },
    },
    {
      path: '/connexion',
      name: 'connexion',
      component: () => import('../views/ConnexionVue.vue'),
      meta: { titre: 'Se connecter' },
    },
    {
      path: '/consentement',
      name: 'consentement',
      component: () => import('../views/ConsentementVue.vue'),
      meta: { titre: 'Consentement', requiert: 'compte' },
    },
    {
      path: '/mon-espace',
      name: 'mon-espace',
      component: () => import('../views/MonEspaceVue.vue'),
      meta: { titre: 'Mon espace', requiert: 'compte' },
    },
    {
      path: '/enrolement',
      name: 'enrolement',
      component: () => import('../views/EnrolementVue.vue'),
      meta: { titre: 'Enrôlement biométrique', requiert: 'compte' },
    },
    {
      path: '/acces',
      name: 'acces',
      component: () => import('../views/AccesVue.vue'),
      meta: { titre: 'Accès biométrique' },
    },
    {
      path: '/base',
      name: 'base',
      component: () => import('../views/BaseVue.vue'),
      meta: { titre: 'Base protégée', requiert: 'acces' },
    },
    {
      path: '/:cheminInconnu(.*)*',
      name: 'introuvable',
      component: () => import('../views/IntrouvableVue.vue'),
      meta: { titre: 'Page introuvable' },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((vers) => {
  if (vers.meta.requiert === 'compte' && !useCompteStore().sessionValide()) {
    return { name: 'connexion', query: { redirection: vers.fullPath } }
  }
  if (vers.meta.requiert === 'acces' && !useAccesStore().estValide()) {
    useAccesStore().effacer()
    return { name: 'acces', query: { motif: 'acces-requis' } }
  }
  return true
})

router.afterEach((vers) => {
  document.title = `${vers.meta.titre} · BioAccess`
  useFlashStore().apresNavigation()
})
