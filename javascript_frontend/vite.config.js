import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * The API base URL is read from VITE_API_URL (see .env.example).
 *
 * Two supported ways to reach the backend:
 *
 * 1. Dev proxy (no backend change needed, works out of the box)
 *    Leave VITE_API_URL empty, so the browser calls "/api/..." on the
 *    Vite dev server, and Vite forwards those requests to the backend.
 *    Same origin from the browser's point of view, so no CORS applies.
 *
 * 2. Direct (needs CORS on the backend)
 *    Set VITE_API_URL=http://localhost:8000. The browser then calls the
 *    backend cross-origin (localhost:5173 -> localhost:8000), which the
 *    browser blocks unless the API enables CORS.
 *
 * The proxy target still uses VITE_API_URL (or the local default) so a
 * single variable controls both modes.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_URL || 'http://localhost:8000'

  return {
    plugins: [react()],

    server: {
      port: 5173,
      // Only used when the app calls "/api/..." on this origin, i.e.
      // when VITE_API_URL is empty.
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
        },
      },
    },

    preview: {
      port: 4173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
        },
      },
    },

    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})