import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0', // Allow external connections (needed for Docker)
    proxy: {
      '/api': {
        // In Docker, proxy to collector service; locally use localhost
        // VITE_API_URL is set in docker-compose.yml for Docker environment
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/v1')
      }
    }
  }
})
