import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_ORIGIN || 'https://10.1.5.58:8000'

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0', // Allow access from any IP
      port: 3000,
      proxy: {
        '/auth': {
          target,
          changeOrigin: true,
          secure: false, // Allow self-signed certificates for development
        },
        '/api': {
          target,
          changeOrigin: true,
          secure: false,
        },
        '/discovery': {
          target,
          changeOrigin: true,
          secure: false,
        },
        '/iam': {
          target,
          changeOrigin: true,
          secure: false,
        },
        '/.well-known': {
          target,
          changeOrigin: true,
          secure: false,
        }
      }
    }
  }
})
