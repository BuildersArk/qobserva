import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Split large libraries into their own cached chunks (keeps each under 500 kB).
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          vendor: ['@tanstack/react-query', 'axios', 'date-fns', 'lucide-react', 'clsx'],
        },
      },
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0', // Allow external connections (needed for Docker)
    proxy: {
      '/api': {
        // In Docker, proxy to collector service; locally use localhost
        // VITE_API_URL is set in docker-compose.yml for Docker environment
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/v1'),
        // When the collector requires a token (QOBSERVA_LOCAL_TOKEN), the proxy adds it.
        headers: process.env.QOBSERVA_LOCAL_TOKEN
          ? { Authorization: `Bearer ${process.env.QOBSERVA_LOCAL_TOKEN}` }
          : undefined,
      }
    }
  }
})
