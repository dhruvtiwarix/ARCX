import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Exposes the server to the local network
    port: 3000,
    proxy: {
      // Proxy all /api calls to Django during development
      // This avoids CORS issues in dev. In production, nginx handles this.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})