import { LOCAL_STORAGE_KEY } from '$lib/constants/game';
import { balance, betAmountOfExistingBalls } from '$lib/stores/game';
import { get } from 'svelte/store';
import { fetchServerBalance, isServerMode } from './api';

/** Баланс при запуске: с сервера (Telegram) или из localStorage (демо). */
export async function loadBalance() {
  if (isServerMode()) {
    // Пока шарики летят, локальный баланс точнее серверного — не перезаписываем
    if (Object.keys(get(betAmountOfExistingBalls)).length > 0) return;
    const real = await fetchServerBalance();
    balance.set(real ?? 0);
    return;
  }
  setBalanceFromLocalStorage();
}

export function setBalanceFromLocalStorage() {
  const rawValue = window.localStorage.getItem(LOCAL_STORAGE_KEY.BALANCE);
  const parsedValue = parseFloat(rawValue ?? '');
  if (!isNaN(parsedValue)) {
    balance.set(parsedValue);
  }
}

export function writeBalanceToLocalStorage() {
  if (isServerMode()) return; // на сервере баланс хранится сам
  const balanceVal = get(balance);
  if (!isNaN(balanceVal)) {
    const balanceValStr = balanceVal.toFixed(2);
    window.localStorage.setItem(LOCAL_STORAGE_KEY.BALANCE, balanceValStr);
  }
}
