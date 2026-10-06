import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// En développement, Vite (port 5173) relaie /api vers le backend FastAPI (port 8000).
// En production, FastAPI sert le contenu de frontend/dist sur le même domaine :
// le frontend n'utilise donc que des URL relatives /api/...
const relaisApi = {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: relaisApi,
  },
  preview: {
    port: 4173,
    proxy: relaisApi,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2022',
  },
})
