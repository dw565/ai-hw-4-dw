import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Backend runs on 8000 (uvicorn main:app --reload --port 8000); override with BACKEND_PORT.
const backend = `http://127.0.0.1:${process.env.BACKEND_PORT ?? '8000'}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
      '/images': backend,
    },
  },
})
