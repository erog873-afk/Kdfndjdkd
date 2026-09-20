import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  // Consult https://kit.svelte.dev/docs/integrations#preprocessors
  // for more information about preprocessors
  preprocess: vitePreprocess(),

  kit: {
    // На GitHub Pages сайт живёт в подпапке /<имя-репозитория> — её задаёт BASE_PATH в workflow
    paths: { base: process.env.BASE_PATH ?? '' },

    // Один файл: весь JS и CSS вставляется прямо в build/index.html
    output: { bundleStrategy: 'inline' },

    // Static site generation (SSG) is used: https://kit.svelte.dev/docs/adapter-static
    adapter: adapter({
      strict: false,
    }),
  },
};

export default config;
