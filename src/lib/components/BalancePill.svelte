<script lang="ts">
  import { balance } from '$lib/stores/game';
  import { isServerMode } from '$lib/utils/api';
  import StarIcon from './StarIcon.svelte';

  /** Как в главном приложении: два знака после запятой через запятую — «0,81» */
  let text = $derived($balance.toFixed(2).replace('.', ','));

  function plus() {
    if (isServerMode()) {
      // Пополнение делается в главном приложении — возвращаемся туда
      history.back();
    } else {
      $balance += 100; // демо-режим: тестовые звёзды
    }
  }
</script>

<!-- Размеры и цвета один в один как BalanceItem (size-md) из главного приложения -->
<div
  class="ml-auto flex h-10 shrink-0 items-center justify-center gap-2 rounded-[14px] bg-[#4f4f4f] px-5 text-white"
  style="font-family: ui-sans-serif, system-ui, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';"
>
  <StarIcon size={20} />
  <span class="text-base leading-normal font-semibold text-white">{text}</span>
  <button
    type="button"
    aria-label="Пополнить"
    onclick={plus}
    class="flex size-5 items-center justify-center rounded-full bg-white"
  >
    <svg viewBox="0 0 24 24" class="size-[14px]" fill="none" stroke="#000" stroke-linecap="round" stroke-linejoin="round" stroke-width="3">
      <path d="M12 20V12M12 12V4M12 12H20M12 12H4" />
    </svg>
  </button>
</div>
