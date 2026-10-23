import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// Backend (uvicorn) für `npm run dev`; die Seite ruft alle Endpunkte relativ auf.
const API = process.env.FAVICON_API ?? 'http://127.0.0.1:8000'
const API_PATHS = ['/convert', '/package', '/snippet', '/fonts', '/health', '/static']

export default defineConfig({
  plugins: [vue()],
  // Relative Asset-URLs: läuft unter / (lokal) und unter /favicon-tool/ (NGINX) ohne Anpassung
  base: './',
  publicDir: false,
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
  },
  server: {
    proxy: Object.fromEntries(API_PATHS.map((path) => [path, API])),
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.spec.ts'],
  },
})
