import type { Difficulty } from '$lib/constants/game';
import { writable } from 'svelte/store';

export type HistoryRecord = {
  /** UUID игры */
  id: string;
  /** Время окончания игры (мс) */
  date: number;
  difficulty: Difficulty;
  multiplier: number;
  /** Ставка в звёздах */
  bet: number;
  /** Выплата в звёздах */
  payout: number;
  /** Данные для проверки честности (у старых записей их нет) */
  fair?: {
    sessionHash: string;
    clientSeed: string;
    nonce: number;
    rulesHash: string;
    rows: number;
    risk: string;
    binIndex: number;
  };
};

/** Игра, открытая в окне подробностей */
export const selectedGame = writable<HistoryRecord | null>(null);

const STORAGE_KEY = 'plinko_history';
const MAX_RECORDS = 100;

/** История игр, новые сверху. Хранится в localStorage. */
export const history = writable<HistoryRecord[]>([]);

export function loadHistory() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    history.set(Array.isArray(parsed) ? parsed : []);
  } catch {
    history.set([]);
  }
}

export function addHistory(record: HistoryRecord) {
  history.update((list) => {
    const next = [record, ...list].slice(0, MAX_RECORDS);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // localStorage может быть недоступен — история просто не сохранится
    }
    return next;
  });
}
