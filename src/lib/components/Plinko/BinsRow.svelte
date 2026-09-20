<script lang="ts">
  import { binPayouts } from '$lib/constants/game';
  import { plinkoEngine, riskLevel, rowCount, winRecords } from '$lib/stores/game';
  import { isAnimationOn } from '$lib/stores/settings';
  import type { Action } from 'svelte/action';

  /**
   * Bounce animations for each bin, which is played when a ball falls into the bin.
   */
  let binAnimations: Animation[] = $state([]);

  // NOTE: Not using $effect because it'll play animation if we toggle on animation in settings
  winRecords.subscribe((value) => {
    if (value.length) {
      const lastWinBinIndex = value[value.length - 1].binIndex;
      playAnimation(lastWinBinIndex);
    }
  });

  const initAnimation: Action<HTMLDivElement> = (node) => {
    const bounceAnimation = node.animate(
      [
        { transform: 'translateY(0)' },
        { transform: 'translateY(12%)' },
        { transform: 'translateY(0)' },
      ],
      {
        duration: 300,
        easing: 'cubic-bezier(0.18, 0.89, 0.32, 1.28)',
      },
    );
    bounceAnimation.pause(); // Don't run the animation immediately
    binAnimations.push(bounceAnimation);

    return {
      destroy: () => {
        // Убираем анимацию удалённой ячейки, чтобы индексы не сбивались при смене сложности
        const i = binAnimations.indexOf(bounceAnimation);
        if (i !== -1) binAnimations.splice(i, 1);
      },
    };
  };

  function playAnimation(binIndex: number) {
    if (!$isAnimationOn) {
      return;
    }

    const animation = binAnimations[binIndex];
    if (!animation) return;

    // Always reset animation before playing. Safari has a weird behavior where
    // the animation will not play the second time if it's not cancelled.
    animation.cancel();

    animation.play();
  }

  /** Цвет ячейки по множителю: красный → оранжевый → зелёный → жёлтый. */
  function tone(multiplier: number): string {
    if (multiplier >= 3) return '#ff3b30';
    if (multiplier >= 1.5) return '#ff9f0a';
    if (multiplier >= 1) return '#3ddc4a';
    return '#f2d024';
  }

  const format = (m: number) => (m >= 1000 ? `${m / 1000}k` : String(m));

  let payouts = $derived(binPayouts[$rowCount][$riskLevel]);
</script>

<div class="flex h-12 w-full justify-center">
  {#if $plinkoEngine}
    <div
      class="flex h-full"
      style:width={`${($plinkoEngine.binsWidthPercentage ?? 0) * 100}%`}
      style:container-type="inline-size"
    >
      {#each payouts as payout, binIndex (binIndex)}
        {@const color = tone(payout)}
        <div
          use:initAnimation
          class="flex min-w-0 flex-1 items-end justify-center pb-1.5 font-semibold"
          style:color
          style:font-size={`max(8px, calc(100cqw / ${payouts.length * 2.4}))`}
          style:background={`linear-gradient(to top, color-mix(in srgb, ${color} 26%, transparent), transparent)`}
          style:box-shadow={`inset 0 -2px 0 ${color}`}
        >
          {format(payout)}
        </div>
      {/each}
    </div>
  {/if}
</div>
