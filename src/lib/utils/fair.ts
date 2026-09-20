import { binPayouts } from '$lib/constants/game';
import type { RiskLevel, RowCount } from '$lib/types';
import { sha256 } from './sha256';

/**
 * «Честная игра» (commit–reveal).
 *
 * Одна сессия = одна игра (один server seed). Пока сессия идёт, показывается только его хэш (sessionHash).
 * После ставки для следующей игры создаётся новая сессия, а server seed прошлой раскрывается,
 * и любую сыгранную игру можно перепроверить: sha256(serverSeed) === sessionHash.
 * Каждая ставка получает сквозной nonce (порядковый номер ставки).
 *
 * ВНИМАНИЕ: пока всё считается в браузере, а исход шарика определяет физика.
 * Настоящая provably fair-схема требует, чтобы исход считал сервер по
 * server seed + client seed + nonce. Когда появится бэкенд — отдавайте эти значения оттуда.
 */
export type FairData = {
  sessionHash: string;
  clientSeed: string;
  nonce: number;
  rulesHash: string;
};

type Session = { serverSeed: string; sessionHash: string; clientSeed: string; nonce: number };

const SESSION_KEY = 'plinko_fair_session';
const REVEALED_KEY = 'plinko_fair_revealed';

function randomHex(bytes: number): string {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, '0')).join('');
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore
  }
}

let session: Session | null = null;

function createSession(): Session {
  const serverSeed = randomHex(32);
  return {
    serverSeed,
    sessionHash: sha256(serverSeed),
    clientSeed: randomHex(32),
    nonce: 0,
  };
}

/** Закрыть текущую сессию (раскрыть её server seed) и начать новую: новый хэш и новый client seed. */
export function startNewSession(): void {
  const old = readJson<Session | null>(SESSION_KEY, null);
  if (old?.serverSeed) {
    const revealed = readJson<Record<string, string>>(REVEALED_KEY, {});
    revealed[old.sessionHash] = old.serverSeed;
    writeJson(REVEALED_KEY, revealed);
  }
  session = createSession();
  session.nonce = old?.nonce ?? 0; // сквозной номер ставки не сбрасывается
  writeJson(SESSION_KEY, session);
}

function getSession(): Session {
  if (!session) {
    const stored = readJson<Session | null>(SESSION_KEY, null);
    if (stored?.serverSeed && stored.sessionHash === sha256(stored.serverSeed)) {
      session = stored;
    } else {
      startNewSession();
    }
  }
  return session!;
}

/** Вызывать при запуске приложения: подхватывает текущий хэш (или создаёт первый). */
export function initFairSession(): void {
  session = null;
  getSession();
}

/** Server seed завершённой сессии или null, если сессия ещё идёт. */
export function getRevealedServerSeed(sessionHash: string): string | null {
  if (getSession().sessionHash === sessionHash) return null;
  return readJson<Record<string, string>>(REVEALED_KEY, {})[sessionHash] ?? null;
}

/** Правила ячейки: по ним считается хэш правил. */
export function rulesString(rows: RowCount, risk: RiskLevel): string {
  return JSON.stringify({ game: 'plinko', rows, risk, multipliers: binPayouts[rows][risk] });
}

export function getRulesHash(rows: RowCount, risk: RiskLevel): string {
  return sha256(rulesString(rows, risk));
}

/** Данные текущей сессии для экрана «Честная игра». */
export function getFairData(rows: RowCount, risk: RiskLevel): FairData {
  const s = getSession();
  return {
    sessionHash: s.sessionHash,
    clientSeed: s.clientSeed,
    nonce: s.nonce,
    rulesHash: getRulesHash(rows, risk),
  };
}

/**
 * Вызывается при броске шарика. Игра получает текущий хэш и client seed,
 * а для следующей игры сразу создаётся новая пара — у каждой игры свой хэш.
 * Server seed завершённой сессии раскрывается.
 */
export function takeNonce(): { sessionHash: string; clientSeed: string; nonce: number } {
  const s = getSession();
  s.nonce += 1;
  writeJson(SESSION_KEY, s);
  const snapshot = { sessionHash: s.sessionHash, clientSeed: s.clientSeed, nonce: s.nonce };
  startNewSession();
  return snapshot;
}

export type VerifyInput = {
  sessionHash: string;
  serverSeed: string;
  rows: RowCount;
  risk: RiskLevel;
  rulesHash: string;
  binIndex: number;
  multiplier: number;
  bet: number;
  payout: number;
};

/** Перепроверка игры в браузере. */
export function verifyGame(i: VerifyInput) {
  const table = binPayouts[i.rows]?.[i.risk];
  const seed = sha256(i.serverSeed) === i.sessionHash;
  const rules = getRulesHash(i.rows, i.risk) === i.rulesHash;
  const cell = Boolean(table) && i.binIndex >= 0 && i.binIndex < table.length;
  const coef = cell && table[i.binIndex] === i.multiplier;
  const sum = Math.floor(i.bet * i.multiplier) === i.payout;
  return { ok: seed && rules && cell && coef && sum, seed, rules, cell, coef, sum };
}

/** "02ef699b...7e9db4e2" */
export function shorten(value: string, head = 8, tail = 8): string {
  return value.length <= head + tail ? value : `${value.slice(0, head)}...${value.slice(-tail)}`;
}

/** Копирование в буфер: с запасным способом для http-адресов, где clipboard API недоступен. */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const area = document.createElement('textarea');
      area.value = text;
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(area);
      return ok;
    } catch {
      return false;
    }
  }
}
