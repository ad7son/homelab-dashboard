import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(frontendDir, '..')

export default defineConfig(({ mode }) => {
  // Empty prefix so non-VITE_ vars (e.g. API_PROXY_TARGET) are loaded for the
  // Vite server only; they are not exposed to browser code via import.meta.env.
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.API_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [react()],
    resolve: {
      alias: [
        { find: '@shell', replacement: path.resolve(frontendDir, 'src') },
        {
          find: 'react-dom',
          replacement: path.resolve(frontendDir, 'node_modules/react-dom'),
        },
        {
          find: 'react-router-dom',
          replacement: path.resolve(frontendDir, 'node_modules/react-router-dom'),
        },
        { find: 'react', replacement: path.resolve(frontendDir, 'node_modules/react') },
        {
          find: 'lucide-react',
          replacement: path.resolve(frontendDir, 'node_modules/lucide-react'),
        },
        {
          find: 'recharts',
          replacement: path.resolve(frontendDir, 'node_modules/recharts'),
        },
      ],
    },
    server: {
      // projects/ lives outside frontend/, so the dev server must be allowed
      // to read the repository root. The frontend directory is inside that root.
      fs: {
        allow: [repoRoot],
      },
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
