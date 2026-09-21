// Unified Stars API: balance + Plinko.
// New users start with 200 ⭐. Existing users are migrated to 200 ⭐ once.

import express from 'express';
import cors from 'cors';
import crypto from 'node:crypto';
import pg from 'pg';
const { Pool } = pg;

const app = express();
app.use(cors());
app.use(express.json({ limit: '1mb' }));

const PORT = process.env.PORT || 3000;
const BOT_TOKEN = process.env.BOT_TOKEN || '';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL ? { rejectUnauthorized: false } : false,
});

const MIN_BET = 25;

const PAYOUTS = {
  8: {
    LOW: [5.6, 2.1, 1.1, 1.0, 0.5, 1.0, 1.1, 2.1, 5.6],
    MEDIUM: [5.2, 1.6, 1.2, 1.0, 0.4, 1.0, 1.2, 1.6, 5.2],
    HIGH: [29.0, 4.0, 1.5, 0.3, 0.2, 0.3, 1.5, 4.0, 29.0],
  },
  9: {
    LOW: [5.6, 2.0, 1.6, 1.0, 0.7, 0.7, 1.0, 1.6, 2.0, 5.6],
    MEDIUM: [18.0, 4.0, 1.7, 0.9, 0.5, 0.5, 0.9, 1.7, 4.0, 18.0],
    HIGH: [43.0, 7.0, 2.0, 0.6, 0.2, 0.2, 0.6, 2.0, 7.0, 43.0],
  },
  10: {
    LOW: [8.9, 3.0, 1.4, 1.1, 1.0, 0.5, 1.0, 1.1, 1.4, 3.0, 8.9],
    MEDIUM: [22.0, 5.0, 2.0, 1.4, 0.6, 0.4, 0.6, 1.4, 2.0, 5.0, 22.0],
    HIGH: [76.0, 10.0, 3.0, 0.9, 0.3, 0.2, 0.3, 0.9, 3.0, 10.0, 76.0],
  },
  11: {
    LOW: [8.4, 3.0, 1.9, 1.3, 1.0, 0.7, 0.7, 1.0, 1.3, 1.9, 3.0, 8.4],
    MEDIUM: [24.0, 6.0, 3.0, 1.8, 0.7, 0.5, 0.5, 0.7, 1.8, 3.0, 6.0, 24.0],
    HIGH: [120.0, 14.0, 5.2, 1.4, 0.4, 0.2, 0.2, 0.4, 1.4, 5.2, 14.0, 120.0],
  },
  12: {
    LOW: [10.0, 3.0, 1.6, 1.4, 1.1, 1.0, 0.5, 1.0, 1.1, 1.4, 1.6, 3.0, 10.0],
    MEDIUM: [33.0, 11.0, 4.0, 2.0, 1.1, 0.6, 0.3, 0.6, 1.1, 2.0, 4.0, 11.0, 33.0],
    HIGH: [170.0, 24.0, 8.1, 2.0, 0.7, 0.2, 0.2, 0.2, 0.7, 2.0, 8.1, 24.0, 170.0],
  },
  13: {
    LOW: [8.1, 4.0, 3.0, 1.9, 1.2, 0.9, 0.7, 0.7, 0.9, 1.2, 1.9, 3.0, 4.0, 8.1],
    MEDIUM: [43.0, 13.0, 6.0, 3.0, 1.3, 0.7, 0.4, 0.4, 0.7, 1.3, 3.0, 6.0, 13.0, 43.0],
    HIGH: [260.0, 37.0, 11.0, 4.0, 1.0, 0.2, 0.2, 0.2, 0.2, 1.0, 4.0, 11.0, 37.0, 260.0],
  },
  14: {
    LOW: [7.1, 4.0, 1.9, 1.4, 1.3, 1.1, 1.0, 0.5, 1.0, 1.1, 1.3, 1.4, 1.9, 4.0, 7.1],
    MEDIUM: [58.0, 15.0, 7.0, 4.0, 1.9, 1.0, 0.5, 0.2, 0.5, 1.0, 1.9, 4.0, 7.0, 15.0, 58.0],
    HIGH: [420.0, 56.0, 18.0, 5.0, 1.9, 0.3, 0.2, 0.2, 0.2, 0.3, 1.9, 5.0, 18.0, 56.0, 420.0],
  },
  15: {
    LOW: [15.0, 8.0, 3.0, 2.0, 1.5, 1.1, 1.0, 0.7, 0.7, 1.0, 1.1, 1.5, 2.0, 3.0, 8.0, 15.0],
    MEDIUM: [88.0, 18.0, 11.0, 5.0, 3.0, 1.3, 0.5, 0.3, 0.3, 0.5, 1.3, 3.0, 5.0, 11.0, 18.0, 88.0],
    HIGH: [620.0, 83.0, 27.0, 8.0, 3.0, 0.5, 0.2, 0.2, 0.2, 0.2, 0.5, 3.0, 8.0, 27.0, 83.0, 620.0],
  },
  16: {
    LOW: [16.0, 9.0, 2.0, 1.4, 1.4, 1.2, 1.1, 1.0, 0.5, 1.0, 1.1, 1.2, 1.4, 1.4, 2.0, 9.0, 16.0],
    MEDIUM: [110.0, 41.0, 10.0, 5.0, 3.0, 1.5, 1.0, 0.5, 0.3, 0.5, 1.0, 1.5, 3.0, 5.0, 10.0, 41.0, 110.0],
    HIGH: [1000.0, 130.0, 26.0, 9.0, 4.0, 2.0, 0.2, 0.2, 0.2, 0.2, 0.2, 2.0, 4.0, 9.0, 26.0, 130.0, 1000.0],
  },
};

const games = new Map();

function verifyInitData(initData) {
  if (!BOT_TOKEN || !initData) return null;
  try {
    const params = new URLSearchParams(initData);
    const hash = params.get('hash');
    if (!hash) return null;
    params.delete('hash');
    const dataCheckString = [...params.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${k}=${v}`)
      .join('\n');
    const secret = crypto.createHmac('sha256', 'WebAppData').update(BOT_TOKEN).digest();
    const expected = crypto.createHmac('sha256', secret).update(dataCheckString).digest('hex');
    if (expected.length !== hash.length || !crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(hash))) return null;
    const authDate = Number(params.get('auth_date') || 0);
    if (!authDate || Math.floor(Date.now() / 1000) - authDate > 86400) return null;
    const user = JSON.parse(params.get('user') || '{}');
    return user.id ? { id: String(user.id), username: user.username || null } : null;
  } catch (_) {
    return null;
  }
}

function userFromRequest(req) {
  const initData = req.query?.init_data || req.body?.init_data || req.headers['x-telegram-init-data'] || '';
  const tg = verifyInitData(initData);
  if (tg) return tg;
  const fallback = req.params.telegramId || req.body?.telegramId || req.body?.userId || req.query?.telegramId;
  if (fallback !== undefined && fallback !== null && String(fallback).trim()) return { id: String(fallback), username: req.body?.username || req.query?.username || null };
  return null;
}

async function getOrCreateUser(telegramId, username = null, client = pool) {
  const result = await client.query(`
    INSERT INTO users (telegram_id, username, balance)
    VALUES ($1, $2, 200)
    ON CONFLICT (telegram_id)
    DO UPDATE SET username = COALESCE(EXCLUDED.username, users.username), updated_at = NOW()
    RETURNING *
  `, [String(telegramId), username || null]);
  return result.rows[0];
}

async function initDb() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      telegram_id TEXT PRIMARY KEY,
      username TEXT,
      balance NUMERIC(14,2) NOT NULL DEFAULT 200,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `);
  await pool.query(`
    CREATE TABLE IF NOT EXISTS app_settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
  `);
  const marker = await pool.query(`SELECT value FROM app_settings WHERE key='balance_200_migration'`);
  if (marker.rows.length === 0) {
    await pool.query(`UPDATE users SET balance=200, updated_at=NOW()`);
    await pool.query(`INSERT INTO app_settings(key,value) VALUES('balance_200_migration','done')`);
    console.log('Однократная миграция: существующим пользователям установлено 200 ⭐');
  }
}

app.get('/', (req, res) => res.json({ ok: true, service: 'Stars API', startingBalance: 200 }));
app.get('/health', async (req, res) => {
  try { await pool.query('SELECT 1'); res.json({ ok: true }); }
  catch (_) { res.status(500).json({ ok: false }); }
});

app.get('/api/balance', async (req, res) => {
  try {
    const user = userFromRequest(req);
    if (!user) return res.status(401).json({ error: 'bad_init_data' });
    const row = await getOrCreateUser(user.id, user.username);
    res.json({ balance: Number(row.balance) });
  } catch (err) {
    console.error(err); res.status(500).json({ error: 'server_error' });
  }
});

app.get('/api/balance/:telegramId', async (req, res) => {
  try {
    const row = await getOrCreateUser(req.params.telegramId, req.query.username);
    res.json({ balance: Number(row.balance) });
  } catch (err) { console.error(err); res.status(500).json({ error: 'server_error' }); }
});

app.post('/api/balance/:telegramId/add', async (req, res) => {
  try {
    const amount = Number(req.body.amount);
    if (!Number.isFinite(amount) || amount <= 0) return res.status(400).json({ error: 'bad_amount' });
    await getOrCreateUser(req.params.telegramId, req.body.username);
    const result = await pool.query(`UPDATE users SET balance=balance+$1, updated_at=NOW() WHERE telegram_id=$2 RETURNING balance`, [amount, req.params.telegramId]);
    res.json({ balance: Number(result.rows[0].balance) });
  } catch (err) { console.error(err); res.status(500).json({ error: 'server_error' }); }
});

app.post('/api/balance/:telegramId/withdraw', async (req, res) => {
  try {
    const amount = Number(req.body.amount);
    if (!Number.isFinite(amount) || amount <= 0) return res.status(400).json({ error: 'bad_amount' });
    await getOrCreateUser(req.params.telegramId, req.body.username);
    const result = await pool.query(`UPDATE users SET balance=balance-$1, updated_at=NOW() WHERE telegram_id=$2 AND balance >= $1 RETURNING balance`, [amount, req.params.telegramId]);
    if (!result.rows.length) return res.status(400).json({ error: 'insufficient_funds' });
    res.json({ balance: Number(result.rows[0].balance) });
  } catch (err) { console.error(err); res.status(500).json({ error: 'server_error' }); }
});

app.post('/api/plinko/bet', async (req, res) => {
  const user = userFromRequest(req);
  const amount = Number(req.body?.amount);
  const rows = Number(req.body?.rows);
  const risk = String(req.body?.risk || '').toUpperCase();
  if (!user) return res.status(401).json({ error: 'bad_init_data' });
  if (!PAYOUTS[rows] || !PAYOUTS[rows][risk]) return res.status(400).json({ error: 'bad_params' });
  if (!Number.isFinite(amount) || amount < MIN_BET) return res.status(400).json({ error: 'bet_too_small' });

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const current = await getOrCreateUser(user.id, user.username, client);
    const updated = await client.query(`UPDATE users SET balance=balance-$1, updated_at=NOW() WHERE telegram_id=$2 AND balance >= $1 RETURNING balance`, [amount, user.id]);
    if (!updated.rows.length) {
      await client.query('ROLLBACK');
      return res.status(402).json({ error: 'not_enough_balance', balance: Number(current.balance) });
    }
    const gameId = crypto.randomUUID();
    games.set(gameId, { user: user.id, amount, rows, risk });
    await client.query('COMMIT');
    res.json({ game_id: gameId, balance: Number(updated.rows[0].balance) });
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    console.error(err); res.status(500).json({ error: 'server_error' });
  } finally { client.release(); }
});

app.post('/api/plinko/settle', async (req, res) => {
  const user = userFromRequest(req);
  const gameId = String(req.body?.game_id || '');
  const binIndex = Number(req.body?.bin_index);
  if (!user) return res.status(401).json({ error: 'bad_init_data' });
  const game = games.get(gameId);
  if (!game || game.user !== user.id) return res.status(404).json({ error: 'game_not_found' });
  const table = PAYOUTS[game.rows][game.risk];
  if (!Number.isInteger(binIndex) || binIndex < 0 || binIndex >= table.length) return res.status(400).json({ error: 'bad_bin' });

  games.delete(gameId);
  const multiplier = table[binIndex];
  const payout = Number((game.amount * multiplier).toFixed(2));
  try {
    const result = await pool.query(`UPDATE users SET balance=balance+$1, updated_at=NOW() WHERE telegram_id=$2 RETURNING balance`, [payout, user.id]);
    res.json({ balance: Number(result.rows[0].balance), payout, multiplier });
  } catch (err) { console.error(err); res.status(500).json({ error: 'server_error' }); }
});

initDb().then(() => {
  app.listen(PORT, '0.0.0.0', () => console.log(`Stars API started on ${PORT}`));
}).catch(err => { console.error('DB init error:', err); process.exit(1); });
