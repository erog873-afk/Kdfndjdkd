<script lang="ts">
  import type { Snippet } from 'svelte';
  import '../app.css';

  let { children }: { children: Snippet } = $props();
</script>

<svelte:head>
  <title>Plinko</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
  <link
    href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap&subset=cyrillic"
    rel="stylesheet"
  />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="Plinko" />
  <meta property="og:url" content="https://plinko-web-game.netlify.app/" />
</svelte:head>

{@render children?.()}
