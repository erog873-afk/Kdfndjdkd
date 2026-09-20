<script lang="ts">
  import { isFairOpen } from '$lib/stores/layout';
  import { riskLevel, rowCount } from '$lib/stores/game';
  import { copyText, getFairData, shorten, type FairData } from '$lib/utils/fair';

  let data: FairData | null = $state(null);
  let copied = $state<'hash' | 'seed' | 'all' | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;

  // Хэш один на игру: сколько ни открывай окно, он тот же, пока не сыграна следующая ставка
  $effect(() => {
    data = $isFairOpen ? getFairData($rowCount, $riskLevel) : null;
  });

  const close = () => ($isFairOpen = false);

  let rows: { kind: 'hash' | 'seed'; title: string; value: string }[] = $derived(
    data
      ? [
          { kind: 'hash', title: 'Хэш сессии', value: data.sessionHash },
          { kind: 'seed', title: 'Client seed', value: data.clientSeed },
        ]
      : [],
  );

  async function copy(kind: 'hash' | 'seed' | 'all') {
    if (!data) return;
    const text =
      kind === 'hash'
        ? data.sessionHash
        : kind === 'seed'
          ? data.clientSeed
          : `Хэш сессии: ${data.sessionHash}\nClient seed: ${data.clientSeed}`;
    if (await copyText(text)) {
      copied = kind;
      clearTimeout(timer);
      timer = setTimeout(() => (copied = null), 1600);
    }
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && $isFairOpen && close()} />

{#if $isFairOpen && data}
  <div class="fixed inset-0 z-50 flex flex-col justify-end" role="dialog" aria-modal="true" aria-label="Честная игра">
    <button
      type="button"
      aria-label="Закрыть"
      onclick={close}
      class="absolute inset-0 cursor-default bg-black/80 backdrop-blur-md"
    ></button>

    <div
      class="relative mx-auto w-full max-w-xl rounded-t-[40px] bg-gradient-to-b from-[#2a2b30] to-[#1f2024] px-7 pt-7 pb-[calc(24px+env(safe-area-inset-bottom,0px))] sm:rounded-b-[40px]"
    >
      <div class="relative flex items-center justify-center pb-6">
        <h2 class="text-[32px] leading-tight font-bold text-white">Честная игра</h2>
        <button
          type="button"
          aria-label="Закрыть"
          onclick={close}
          class="absolute top-1/2 right-0 grid size-10 -translate-y-1/2 place-items-center rounded-full text-[#9a9ba2]"
        >
          <svg viewBox="0 0 24 24" class="size-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
            <path d="M5 5l14 14M19 5L5 19" />
          </svg>
        </button>
      </div>

      <div class="flex flex-col gap-6 rounded-[32px] bg-gradient-to-b from-[#3d3f44] to-[#35363b] p-6">
        {#each rows as row (row.kind)}
          <div class="flex items-center justify-between gap-4">
            <div class="min-w-0">
              <div class="text-[23px] leading-tight font-bold text-white">{row.title}</div>
              <div class="mt-1 truncate text-xl font-medium text-[#8b8d94]">{shorten(row.value)}</div>
            </div>
            <button
              type="button"
              aria-label="Скопировать: {row.title}"
              onclick={() => copy(row.kind)}
              class="grid size-11 shrink-0 place-items-center rounded-xl transition-colors {copied === row.kind
                ? 'text-[#3ddc4a]'
                : 'text-[#7d7f86]'}"
            >
              {#if copied === row.kind}
                <svg viewBox="0 0 24 24" class="size-7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12.5l4.5 4.5L19 7.5" />
                </svg>
              {:else}
                <svg viewBox="0 0 24 24" class="size-7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
                  <rect x="9" y="9" width="11" height="11" rx="3" />
                  <path d="M15 9V6.5A2.5 2.5 0 0 0 12.5 4h-6A2.5 2.5 0 0 0 4 6.5v6A2.5 2.5 0 0 0 6.5 15H9" />
                </svg>
              {/if}
            </button>
          </div>
        {/each}
      </div>

      <button
        type="button"
        onclick={() => copy('all')}
        class="mt-6 h-[58px] w-full rounded-[29px] bg-[#4a4c51] text-lg font-semibold text-white transition-transform active:scale-[0.98]"
      >
        {copied === 'all' ? 'Скопировано' : 'Скопировать'}
      </button>
    </div>
  </div>
{/if}
