<script lang="ts">
  import { MIN_BET } from '$lib/constants/game';
  import { balance, betAmount, plinkoEngine } from '$lib/stores/game';
  import StarIcon from './StarIcon.svelte';

  const quickAdd = [100, 500];

  /** Показать красную рамку, если нажали «Отправить», а звёзд не хватает. */
  let insufficient = $state(false);

  // Кнопка активна только когда ставка >= минимальной
  let isDisabled = $derived($plinkoEngine === null || $betAmount < MIN_BET);

  function onInput(e: Event) {
    const value = parseFloat((e.currentTarget as HTMLInputElement).value.replace(',', '.'));
    $betAmount = Number.isNaN(value) ? 0 : Math.max(0, Math.round(value * 100) / 100);
    insufficient = false;
  }

  function addQuick(amount: number) {
    $betAmount = Math.round((($betAmount || 0) + amount) * 100) / 100;
    insufficient = false;
  }

  function submit() {
    if (isDisabled) return;
    if ($betAmount > $balance) {
      insufficient = true; // TODO: тут можно открыть пополнение
      return;
    }
    $plinkoEngine?.dropBall();
  }
</script>

<div class="flex flex-col gap-4">
  <div
    class="flex h-[76px] items-center gap-2 rounded-[32px] border bg-[#1e1e1e] pr-2.5 pl-[22px] {insufficient
      ? 'border-red-500/70'
      : 'border-white/10'}"
  >
    <StarIcon size={30} />
    <input
      type="number"
      inputmode="decimal"
      min={MIN_BET}
      step="any"
      placeholder={String(MIN_BET)}
      aria-label="Ставка"
      value={$betAmount || ''}
      oninput={onInput}
      class="ml-1.5 w-full min-w-0 flex-1 bg-transparent text-2xl font-medium text-white outline-none placeholder:text-[#8b8d94] [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
    />
    {#each quickAdd as amount}
      <button
        type="button"
        onclick={() => addQuick(amount)}
        class="h-11 shrink-0 rounded-[22px] bg-[#4a4a4a] px-[22px] text-base font-semibold text-white transition-transform active:scale-95"
      >
        + {amount}
      </button>
    {/each}
  </div>

  <button
    type="button"
    disabled={isDisabled}
    onclick={submit}
    class="h-[76px] rounded-[40px] text-[26px] font-semibold transition-colors active:not-disabled:scale-[0.98] {isDisabled
      ? 'cursor-not-allowed bg-[#244ca8] text-white/55'
      : 'bg-[#2f6bff] text-white'}"
  >
    Отправить
  </button>
</div>
