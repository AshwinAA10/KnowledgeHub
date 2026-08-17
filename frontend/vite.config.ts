import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  test: {
    // Use jsdom to simulate the browser DOM
    environment: 'jsdom',
    // Import jest-dom matchers globally in every test file
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
})
