import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/events': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      '/timeline': {
        target: 'http://localhost:8000',
      },
    },
  },
})
