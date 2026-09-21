<script lang="ts">
  import { difficultyOptions } from '$lib/constants/game';
  import { history, selectedGame } from '$lib/stores/history';
  import { isHistoryOpen } from '$lib/stores/layout';
  import StarIcon from './StarIcon.svelte';

  const labels = Object.fromEntries(difficultyOptions.map((o) => [o.value, o.label]));

  const dateFormat = new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  /** "7828...7645" из UUID */
  function shortId(id: string): string {
    const clean = id.replaceAll('-', '');
    return `${clean.slice(0, 4)}...${clean.slice(-4)}`;
  }

  const close = () => ($isHistoryOpen = false);

  // Внутри Telegram используем нативную кнопку «Назад», вне Telegram — свою.
  const tg = typeof window !== 'undefined' ? (window as any).Telegram?.WebApp : undefined;
  const inTelegram = Boolean(tg?.initData);
</script>

{#if $isHistoryOpen}
  <div
    class="fixed inset-0 z-40 overflow-y-auto bg-[#1b1d22]"
    role="dialog"
    aria-modal="true"
    aria-label="История игр"
  >
    <div
      class="mx-auto max-w-xl px-4 pt-[calc(20px+env(safe-area-inset-top,0px))] pb-[calc(24px+env(safe-area-inset-bottom,0px))]"
    >
      {#if !inTelegram}
        <button
          type="button"
          onclick={close}
          class="mb-2 flex h-11 items-center gap-2 rounded-full bg-[#2d2e33] pr-5 pl-3 text-base font-semibold text-white"
        >
          <svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M11 6l-6 6 6 6" />
          </svg>
          Назад
        </button>
      {/if}

      <h1 class="mt-4 text-center text-[32px] leading-tight font-bold text-white">История игр</h1>
      <p class="mt-2 text-center text-lg font-medium text-[#8b8d94]">Ваши ставки в Plinko</p>

      {#if $history.length === 0}
        <p class="mt-24 text-center text-lg font-medium text-[#6b6d74]">
          Пока нет игр. Сделайте первую ставку.
        </p>
      {:else}
        <ul class="mt-9 flex flex-col gap-[22px]">
          {#each $history as record (record.id)}
            {@const isWin = record.multiplier >= 1}
            <li>
             <button
              type="button"
              onclick={() => ($selectedGame = record)}
              class="w-full rounded-[36px] bg-gradient-to-b from-[#404247] to-[#36373c] px-[22px] pt-[22px] pb-[26px] text-left transition-transform active:scale-[0.98]"
            >
              <div class="flex items-center justify-between text-lg font-semibold text-[#8b8d94]">
                <span>Игра #{shortId(record.id)}</span>
                <span class="tabular-nums">{dateFormat.format(record.date)}</span>
              </div>

              <div class="mt-4 flex items-center gap-[22px]">
                <StarIcon size={52} />

                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-3">
                    <span class="text-[26px] leading-none font-semibold text-white">
                      {labels[record.difficulty]}
                    </span>
                    <span
                      class="rounded-full px-3 py-1 text-base leading-none font-semibold {isWin
                        ? 'bg-[#24452c] text-[#3ddc4a]'
                        : 'bg-[#5a2a3a] text-[#ff4d7a]'}"
                    >
                      {record.multiplier}×
                    </span>
                  </div>
                  <div class="mt-2 flex items-center gap-2 text-xl font-semibold text-[#9a9ba2]">
                    <span>Ставка: {record.bet}</span>
                    <StarIcon size={24} />
                  </div>
                </div>

                <div class="flex items-center gap-2 text-[26px] font-semibold text-[#f5b400] tabular-nums">
                  <StarIcon size={28} />
                  <span>{record.payout}</span>
                </div>
              </div>
             </button>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>
{/if}
