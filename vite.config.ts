import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  // Все картинки встраиваются в сборку (для одного файла)
  build: { assetsInlineLimit: 100_000_000 },
  test: {
    include: ['src/**/*.{test,spec}.{js,ts}'],
    restoreMocks: true,
  },
});
