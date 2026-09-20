<script lang="ts">
  import { difficultyOptions, rowsByDifficulty, type Difficulty } from '$lib/constants/game';
  import { betAmountOfExistingBalls, difficulty, rowCount } from '$lib/stores/game';
  import { isFairOpen, isHistoryOpen } from '$lib/stores/layout';

  // Смена сложности пересоздаёт поле и убирает летящие шарики,
  // поэтому пока шарики в полёте — переключатель заблокирован.
  let hasOutstandingBalls = $derived(Object.keys($betAmountOfExistingBalls).length > 0);

  let activeIndex = $derived(difficultyOptions.findIndex((o) => o.value === $difficulty));

  function select(value: Difficulty) {
    if (hasOutstandingBalls) return;
    $difficulty = value;
    $rowCount = rowsByDifficulty[value];
  }
</script>

<div class="flex items-stretch gap-2">
  <button
    type="button"
    aria-label="История"
    onclick={() => ($isHistoryOpen = true)}
    class="grid size-[62px] shrink-0 place-items-center rounded-[22px] bg-[#3a3d43] text-white transition-transform active:scale-95"
  >
    <svg
      viewBox="0 0 24 24"
      class="size-[30px]"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
      <path d="M3 3.5v4.2h4.2" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  </button>

  <div
    role="radiogroup"
    aria-label="Сложность"
    class="relative grid flex-1 grid-cols-3 rounded-[32px] bg-white/12 p-[5px]"
  >
    <div
      class="absolute top-[5px] bottom-[5px] left-[5px] w-[calc((100%-10px)/3)] rounded-3xl bg-[#54575d] transition-transform duration-250 ease-out motion-reduce:transition-none"
      style:transform={`translateX(${activeIndex * 100}%)`}
    ></div>
    {#each difficultyOptions as { value, label }}
      <button
        type="button"
        role="radio"
        aria-checked={$difficulty === value}
        disabled={hasOutstandingBalls}
        onclick={() => select(value)}
        class="relative z-10 h-[52px] text-[17px] font-semibold transition-colors disabled:cursor-not-allowed {$difficulty ===
        value
          ? 'text-white'
          : 'text-[#a2a4aa]'}"
      >
        {label}
      </button>
    {/each}
  </div>
</div>

<nav class="mt-3 flex justify-center gap-11 text-[15px] font-semibold text-[#55585f]">
  <a href="#about">Об игре</a>
  <button type="button" onclick={() => ($isFairOpen = true)}>Честная игра</button>
</nav>
