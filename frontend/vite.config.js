import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      // 🌟 UPDATED: Catch any route starting with /api/v1 cleanly
      '^/api/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
      '^/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})