<script lang="ts">
  import { selectedGame } from '$lib/stores/history';
  import { copyText, getRevealedServerSeed, shorten, verifyGame } from '$lib/utils/fair';
  import type { RiskLevel, RowCount } from '$lib/types';
  import StarIcon from './StarIcon.svelte';

  const close = () => ($selectedGame = null);

  let record = $derived($selectedGame);
  let fair = $derived(record?.fair);
  let serverSeed = $derived(fair ? getRevealedServerSeed(fair.sessionHash) : null);
  let isWin = $derived(record ? record.multiplier >= 1 : false);

  // null — ещё не проверяли, иначе результат
  let result: ReturnType<typeof verifyGame> | null = $state(null);
  let copied = $state(false);
  let timer: ReturnType<typeof setTimeout> | undefined;

  // При открытии другой игры сбрасываем результат проверки
  $effect(() => {
    void $selectedGame;
    result = null;
    copied = false;
  });

  let rows = $derived(
    fair
      ? [
          { title: 'Хэш сессии', value: fair.sessionHash },
          { title: 'Client seed', value: fair.clientSeed },
          { title: 'Nonce', value: String(fair.nonce), short: false },
          {
            title: 'Server seed',
            value: serverSeed ?? '',
            pending: serverSeed === null,
          },
          { title: 'Хэш правил', value: fair.rulesHash },
        ]
      : [],
  );

  function verify() {
    if (!record || !fair || !serverSeed) return;
    result = verifyGame({
      sessionHash: fair.sessionHash,
      serverSeed,
      rows: fair.rows as RowCount,
      risk: fair.risk as RiskLevel,
      rulesHash: fair.rulesHash,
      binIndex: fair.binIndex,
      multiplier: record.multiplier,
      bet: record.bet,
      payout: record.payout,
    });
  }

  async function copyAll() {
    if (!record || !fair) return;
    const text = [
      `Игра: ${record.id}`,
      `Хэш сессии: ${fair.sessionHash}`,
      `Client seed: ${fair.clientSeed}`,
      `Nonce: ${fair.nonce}`,
      `Server seed: ${serverSeed ?? 'ещё недоступен'}`,
      `Хэш правил: ${fair.rulesHash}`,
    ].join('\n');
    if (await copyText(text)) {
      copied = true;
      clearTimeout(timer);
      timer = setTimeout(() => (copied = false), 1600);
    }
  }

  async function copyOne(value: string) {
    if (value) await copyText(value);
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && $selectedGame && close()} />

{#if record}
  <div class="fixed inset-0 z-50 flex flex-col justify-end" role="dialog" aria-modal="true" aria-label="Результат игры">
    <button type="button" aria-label="Закрыть" onclick={close} class="absolute inset-0 cursor-default bg-black/80 backdrop-blur-md"></button>

    <div
      class="relative mx-auto max-h-dvh w-full max-w-xl overflow-y-auto rounded-t-[40px] bg-gradient-to-b from-[#2a2b30] to-[#1f2024] px-6 pt-6 pb-[calc(24px+env(safe-area-inset-bottom,0px))] sm:rounded-b-[40px]"
    >
      <div class="relative flex flex-col items-center gap-3 pb-5">
        <span class="rounded-full bg-gradient-to-r from-[#0e6fa0] to-[#2bc4d6] px-6 py-2 text-[26px] leading-none font-bold text-white">
          Plinko
        </span>
        <h2 class="text-[34px] leading-tight font-bold text-white">
          {isWin ? 'Вы выиграли' : 'Вы проиграли'}
        </h2>
        <button
          type="button"
          aria-label="Закрыть"
          onclick={close}
          class="absolute top-0 right-0 grid size-10 place-items-center rounded-full text-[#9a9ba2]"
        >
          <svg viewBox="0 0 24 24" class="size-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
            <path d="M5 5l14 14M19 5L5 19" />
          </svg>
        </button>
      </div>

      <!-- Призы: иконка звезды (static/star.png) + сумма выплаты -->
      <div class="rounded-[32px] bg-gradient-to-b from-[#3d3f44] to-[#35363b] p-6">
        <div class="text-center text-[23px] font-bold text-[#9a9ba2]">Призы</div>
        <div class="mt-5 flex">
          <div
            class="flex size-[132px] flex-col items-center justify-center gap-1 rounded-[32px] border-2 border-[#5b34d6] bg-gradient-to-b from-[#3a1f9e] to-[#4a2bc0]"
          >
            <StarIcon size={54} />
            <span class="text-[32px] leading-none font-bold text-white tabular-nums">{record.payout}</span>
          </div>
        </div>
      </div>

      <!-- Подтверждение честности -->
      <div class="mt-5 rounded-[32px] bg-gradient-to-b from-[#3d3f44] to-[#35363b] p-6">
        <div class="text-center text-[23px] font-bold text-[#9a9ba2]">Подтверждение честности</div>

        {#if fair}
          <div class="mt-5 flex flex-col gap-5">
            {#each rows as row (row.title)}
              <div class="flex items-center justify-between gap-4">
                <div class="min-w-0">
                  <div class="text-[22px] leading-tight font-bold text-white">{row.title}</div>
                  <div class="mt-1 truncate text-lg font-medium {row.pending ? 'text-[#6b6d74]' : 'text-[#8b8d94]'}">
                    {row.pending ? 'Ещё недоступен' : row.short === false ? row.value : shorten(row.value)}
                  </div>
                </div>
                <button
                  type="button"
                  aria-label="Скопировать: {row.title}"
                  disabled={row.pending}
                  onclick={() => copyOne(row.value)}
                  class="grid size-11 shrink-0 place-items-center rounded-xl text-[#7d7f86] disabled:opacity-40"
                >
                  <svg viewBox="0 0 24 24" class="size-7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
                    <rect x="9" y="9" width="11" height="11" rx="3" />
                    <path d="M15 9V6.5A2.5 2.5 0 0 0 12.5 4h-6A2.5 2.5 0 0 0 4 6.5v6A2.5 2.5 0 0 0 6.5 15H9" />
                  </svg>
                </button>
              </div>
            {/each}
          </div>

          {#if result}
            <div class="mt-6 flex flex-col items-center gap-3 text-center">
              <span
                class="rounded-full px-6 py-2 text-[22px] font-semibold {result.ok
                  ? 'bg-[#24452c] text-[#3ddc4a]'
                  : 'bg-[#5a2a3a] text-[#ff4d7a]'}"
              >
                {result.ok ? 'Проверка пройдена' : 'Проверка не пройдена'}
              </span>
              <p class="text-lg leading-snug text-[#8b8d94]">
                {result.ok
                  ? 'Совпали хэш seed, хэш правил, ячейка, коэффициент и сумма выигрыша. Проверка выполнена в браузере.'
                  : `Не совпало: ${[
                      !result.seed && 'хэш seed',
                      !result.rules && 'хэш правил',
                      !result.cell && 'ячейка',
                      !result.coef && 'коэффициент',
                      !result.sum && 'сумма выигрыша',
                    ]
                      .filter(Boolean)
                      .join(', ')}.`}
              </p>
            </div>
          {:else if serverSeed === null}
            <p class="mt-5 text-center text-base leading-snug text-[#6b6d74]">
              Server seed откроется после завершения сессии.
            </p>
          {/if}
        {:else}
          <p class="mt-5 text-center text-lg text-[#8b8d94]">Для этой игры нет данных проверки.</p>
        {/if}
      </div>

      <div class="mt-5 flex gap-3">
        <button
          type="button"
          onclick={verify}
          disabled={!fair || !serverSeed}
          class="h-[58px] flex-1 rounded-[29px] bg-[#4a4c51] text-lg font-semibold text-white transition-transform active:scale-[0.98] disabled:opacity-50"
        >
          Проверить
        </button>
        <button
          type="button"
          onclick={copyAll}
          disabled={!fair}
          class="h-[58px] flex-1 rounded-[29px] bg-[#4a4c51] text-lg font-semibold text-white transition-transform active:scale-[0.98] disabled:opacity-50"
        >
          {copied ? 'Скопировано' : 'Скопировать'}
        </button>
      </div>
    </div>
  </div>
{/if}
