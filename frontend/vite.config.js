import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

const frontendDirectory = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  base: '/static/frontend/',
  plugins: [svelte()],
  resolve: {
    conditions: ['browser'],
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.js'],
  },
  build: {
    outDir: resolve(frontendDirectory, '../app/static/frontend'),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(frontendDirectory, 'src/main.js'),
      output: {
        entryFileNames: 'app.js',
        assetFileNames: 'app.[ext]',
      },
    },
  },
});
