/**
 * Связь с сервером основного приложения: общий баланс.
 *
 * Внутри Telegram (есть initData) баланс хранится на сервере и общий с главным приложением.
 * Вне Telegram игра работает в демо-режиме с локальным балансом.
 *
 * Адрес API берётся из ?api=... (его подставляет главная страница), иначе — значение по умолчанию.
 */
const DEFAULT_API = 'https://kdfndjdkd-2.onrender.com';

function getApiBase(): string {
  try {
    const fromQuery = new URLSearchParams(window.location.search).get('api');
    if (fromQuery) return fromQuery.replace(/\/$/, '');
  } catch {
    // ignore
  }
  return ((window as any).TASK_API_BASE || DEFAULT_API).replace(/\/$/, '');
}

export function getInitData(): string {
  return (window as any).Telegram?.WebApp?.initData ?? '';
}

/** true — баланс на сервере (Telegram), false — демо с локальным балансом */
export function isServerMode(): boolean {
  return typeof window !== 'undefined' && Boolean(getInitData());
}

async function post<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(getApiBase() + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: getInitData(), ...body }),
  });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

/** Текущий баланс с сервера или null, если не получилось */
export async function fetchServerBalance(): Promise<number | null> {
  try {
    const res = await fetch(`${getApiBase()}/api/balance?init_data=${encodeURIComponent(getInitData())}`, {
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data.balance === 'number' ? data.balance : null;
  } catch {
    return null;
  }
}

/** Списать ставку. Сервер проверяет баланс и возвращает id игры и новый баланс. */
export function serverPlaceBet(amount: number, rows: number, risk: string) {
  return post<{ game_id: string; balance: number }>('/api/plinko/bet', { amount, rows, risk });
}

/** Завершить игру: сервер считает выплату по ячейке и зачисляет её. */
export function serverSettle(gameId: string, binIndex: number) {
  return post<{ balance: number; payout?: number; multiplier?: number }>('/api/plinko/settle', {
    game_id: gameId,
    bin_index: binIndex,
  });
}
