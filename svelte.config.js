import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),

  kit: {
    // На GitHub Pages сайт живёт в подпапке /<имя-репозитория> — её задаёт BASE_PATH в workflow
    paths: { base: process.env.BASE_PATH ?? '' },

    // Один файл: весь JS и CSS вставляется прямо в build/index.html
    output: { bundleStrategy: 'inline' },

    adapter: adapter({
      strict: false,
    }),

    // Не роняем сборку из-за ссылок на иконки и #about — только предупреждение в лог
    prerender: {
      handleMissingId: 'warn',
      handleHttpError: 'warn',
    },
  },
};

export default config;
