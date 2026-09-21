<script lang="ts">
  import starSrc from '$lib/assets/star.png';
  /**
   * Иконка звезды. Положите свою картинку в Plinko/src/lib/assets/star.png (встраивается в сборку) —
   * если файла нет, показывается эмодзи ⭐.
   */
  let { size = 30 }: { size?: number } = $props();
  let failed = $state(false);
</script>

{#if failed}
  <span class="leading-none select-none" style:font-size={`${size * 0.87}px`} aria-hidden="true">⭐</span>
{:else}
  <img
    src={starSrc}
    alt=""
    width={size}
    height={size}
    class="shrink-0 object-contain select-none"
    onerror={() => (failed = true)}
  />
{/if}
