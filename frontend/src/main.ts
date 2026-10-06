import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { definirGestionnaireSessionExpiree } from './api'
import App from './App.vue'
import { router } from './router'
import { useCompteStore } from './stores/compte'
import { useFlashStore } from './stores/flash'
import './styles/tokens.css'
import './styles/base.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Jeton « compte » refusé par le serveur : on oublie la session et, si la page
// courante l'exigeait, on renvoie vers la connexion en mémorisant la destination.
definirGestionnaireSessionExpiree(() => {
  const compte = useCompteStore(pinia)
  if (compte.jeton === null) return
  compte.oublier()
  useFlashStore(pinia).publier('Votre session a expiré. Reconnectez-vous pour continuer.', 'alerte')
  const courante = router.currentRoute.value
  if (courante.meta.requiert === 'compte') {
    void router.push({ name: 'connexion', query: { redirection: courante.fullPath } })
  }
})

app.mount('#app')
