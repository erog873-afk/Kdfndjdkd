// Сервер баланса звёзд для Telegram Mini App.
// Хранит баланс каждого пользователя (по его telegram_id) в PostgreSQL,
// чтобы все страницы (Игры, Магазин, Профиль и т.д.) видели одно и то же число.

const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');

const app = express();
app.use(cors());
app.use(express.json());

// Render автоматически даёт переменную окружения DATABASE_URL,
// когда ты подключаешь Postgres-базу к этому Web Service.
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.DATABASE_URL ? { rejectUnauthorized: false } : false
});

// Создаём таблицу при старте, если её ещё нет.
async function initDb() {
    await pool.query(`
        CREATE TABLE IF NOT EXISTS users (
            telegram_id TEXT PRIMARY KEY,
            username TEXT,
            balance NUMERIC(14,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    `);
    console.log('DB готова');
}
initDb().catch(err => console.error('Ошибка инициализации БД:', err));

// Получить (или создать с балансом 0) пользователя и вернуть его баланс.
async function getOrCreateUser(telegramId, username) {
    const existing = await pool.query('SELECT * FROM users WHERE telegram_id=$1', [telegramId]);
    if (existing.rows.length > 0) return existing.rows[0];
    const inserted = await pool.query(
        'INSERT INTO users (telegram_id, username, balance) VALUES ($1,$2,0) RETURNING *',
        [telegramId, username || null]
    );
    return inserted.rows[0];
}

// GET /api/balance/:telegramId  -> { balance: 128.5 }
app.get('/api/balance/:telegramId', async (req, res) => {
    try {
        const user = await getOrCreateUser(req.params.telegramId, req.query.username);
        res.json({ balance: Number(user.balance) });
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'server_error' });
    }
});

// POST /api/balance/:telegramId/add   body: { amount: 50 }
app.post('/api/balance/:telegramId/add', async (req, res) => {
    try {
        const amount = Number(req.body.amount);
        if (!amount || amount <= 0) return res.status(400).json({ error: 'bad_amount' });
        await getOrCreateUser(req.params.telegramId, req.body.username);
        const result = await pool.query(
            `UPDATE users SET balance = balance + $1, updated_at=NOW()
             WHERE telegram_id=$2 RETURNING balance`,
            [amount, req.params.telegramId]
        );
        res.json({ balance: Number(result.rows[0].balance) });
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'server_error' });
    }
});

// POST /api/balance/:telegramId/withdraw   body: { amount: 50 }
app.post('/api/balance/:telegramId/withdraw', async (req, res) => {
    try {
        const amount = Number(req.body.amount);
        if (!amount || amount <= 0) return res.status(400).json({ error: 'bad_amount' });
        const user = await getOrCreateUser(req.params.telegramId, req.body.username);
        if (Number(user.balance) < amount) {
            return res.status(400).json({ error: 'insufficient_funds', balance: Number(user.balance) });
        }
        const result = await pool.query(
            `UPDATE users SET balance = balance - $1, updated_at=NOW()
             WHERE telegram_id=$2 RETURNING balance`,
            [amount, req.params.telegramId]
        );
        res.json({ balance: Number(result.rows[0].balance) });
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'server_error' });
    }
});

app.get('/', (req, res) => res.send('Stars backend работает'));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log('Сервер запущен на порту ' + PORT));
