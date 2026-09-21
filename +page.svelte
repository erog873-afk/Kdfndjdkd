<script lang="ts">
  import BalancePill from '$lib/components/BalancePill.svelte';
  import BetPanel from '$lib/components/BetPanel.svelte';
  import HistoryDetail from '$lib/components/HistoryDetail.svelte';
  import FairSheet from '$lib/components/FairSheet.svelte';
  import HistoryPage from '$lib/components/HistoryPage.svelte';
  import Plinko from '$lib/components/Plinko';
  import TopControls from '$lib/components/TopControls.svelte';
  import { initFairSession } from '$lib/utils/fair';
  import { isFairOpen, isHistoryOpen, isLiveStatsOpen } from '$lib/stores/layout';
  import { get } from 'svelte/store';
  import { loadHistory, selectedGame } from '$lib/stores/history';
  import { loadBalance, writeBalanceToLocalStorage } from '$lib/utils/game';

  $effect(() => {
    loadBalance();
    loadHistory();
    initFairSession();

    // Telegram Mini App: раскрыть на весь экран и покрасить шапку
    const tg = (window as any).Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      tg.setHeaderColor?.('#1b1d22');
      tg.setBackgroundColor?.('#1b1d22');
    }
  });

  // Кнопка «Назад» Telegram на всех экранах: сначала закрывает открытое окно
  // (детали игры, «Честная игра», история, статистика), а на главном экране Plinko
  // возвращает в основное приложение.
  $effect(() => {
    const tg = (window as any).Telegram?.WebApp;
    if (!tg?.BackButton) return;
    const onBack = () => {
      if (get(selectedGame)) return selectedGame.set(null);
      if (get(isFairOpen)) return isFairOpen.set(false);
      if (get(isHistoryOpen)) return isHistoryOpen.set(false);
      if (get(isLiveStatsOpen)) return isLiveStatsOpen.set(false);
      if (window.history.length > 1) window.history.back();
      else tg.close();
    };
    tg.BackButton.show();
    tg.BackButton.onClick(onBack);
    return () => {
      tg.BackButton.offClick(onBack);
      tg.BackButton.hide();
    };
  });
</script>

<!-- Баланс общий с главным приложением: обновляем, когда пользователь возвращается на экран -->
<svelte:window
  onbeforeunload={writeBalanceToLocalStorage}
  onfocus={loadBalance}
  onvisibilitychange={() => document.visibilityState === 'visible' && loadBalance()}
/>

<div
  class="mx-auto flex min-h-dvh w-full max-w-xl flex-col gap-4 px-4 pt-4 pb-[calc(24px+env(safe-area-inset-bottom,0px))]"
>
  <BalancePill />

  <Plinko />

  <div>
    <TopControls />
  </div>

  <div class="flex-1"></div>

  <BetPanel />
</div>

<HistoryPage />
<HistoryDetail />
<FairSheet />

<style lang="postcss">
  @reference "../app.css";

  :global(body) {
    background-color: #1b1d22;
    color: #fff;
  }
</style>
