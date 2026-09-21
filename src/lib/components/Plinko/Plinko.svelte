<script lang="ts">
  import { plinkoEngine } from '$lib/stores/game';
  import CircleNotch from 'phosphor-svelte/lib/CircleNotch';
  import type { Action } from 'svelte/action';
  import BinsRow from './BinsRow.svelte';
  import PlinkoEngine from './PlinkoEngine';

  const { WIDTH, HEIGHT } = PlinkoEngine;

  const initPlinko: Action<HTMLCanvasElement> = (node) => {
    $plinkoEngine = new PlinkoEngine(node);
    $plinkoEngine.start();

    return {
      destroy: () => {
        $plinkoEngine?.stop();
      },
    };
  };
</script>

<!-- Труба стоит над полем: шарик выпадает из неё за верхним краем и падает на кегли -->
<div class="relative pt-8">
  <div
    aria-hidden="true"
    class="absolute top-0 left-1/2 z-10 h-9 w-[11%] -translate-x-1/2 rounded-t-lg bg-gradient-to-r from-[#55565a] via-[#a0a1a5] to-[#55565a]"
  ></div>

  <div
    class="relative overflow-hidden rounded-[40px] bg-gradient-to-b from-[#3d3e42] to-[#2b2c30] ring-1 ring-white/5"
  >
    <div class="mx-auto flex h-full flex-col" style:max-width={`${WIDTH}px`}>
      <div class="relative w-full" style:aspect-ratio={`${WIDTH} / ${HEIGHT}`}>
        {#if $plinkoEngine === null}
          <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
            <CircleNotch class="size-16 animate-spin text-white/30" weight="bold" />
          </div>
        {/if}

        <canvas use:initPlinko width={WIDTH} height={HEIGHT} class="absolute inset-0 h-full w-full">
        </canvas>
      </div>
      <BinsRow />
    </div>
  </div>
</div>
