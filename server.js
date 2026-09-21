const express = require("express");
const cors = require("cors");
const crypto = require("crypto");
const { Pool } = require("pg");

const app = express();

app.use(cors());
app.use(express.json({ limit: "1mb" }));

const PORT = process.env.PORT || 3000;
const DATABASE_URL = process.env.DATABASE_URL;

if (!DATABASE_URL) {
  console.error("ERROR: DATABASE_URL is not set.");
  process.exit(1);
}

const pool = new Pool({
  connectionString: DATABASE_URL,
  ssl:
    process.env.NODE_ENV === "production"
      ? { rejectUnauthorized: false }
      : false,
});

// ============================================
// DATABASE
// ============================================

async function initDb() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      id BIGSERIAL PRIMARY KEY,
      telegram_id TEXT UNIQUE NOT NULL,
      balance NUMERIC(18,2) NOT NULL DEFAULT 200,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  // Всем существующим пользователям устанавливаем 200 ⭐
  await pool.query(`
    UPDATE users
    SET balance = 200,
        updated_at = NOW()
  `);
}

// ============================================
// TELEGRAM INIT DATA
// ============================================

function verifyTelegramInitData(initData) {
  const botToken = process.env.BOT_TOKEN;

  if (!botToken || !initData) {
    return null;
  }

  try {
    const params = new URLSearchParams(initData);
    const hash = params.get("hash");

    if (!hash) {
      return null;
    }

    params.delete("hash");

    const dataCheckString = [...params.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, value]) => `${key}=${value}`)
      .join("\n");

    const secretKey = crypto
      .createHmac("sha256", "WebAppData")
      .update(botToken)
      .digest();

    const calculatedHash = crypto
      .createHmac("sha256", secretKey)
      .update(dataCheckString)
      .digest("hex");

    if (
      calculatedHash.length !== hash.length ||
      !crypto.timingSafeEqual(
        Buffer.from(calculatedHash),
        Buffer.from(hash)
      )
    ) {
      return null;
    }

    const userRaw = params.get("user");

    if (!userRaw) {
      return null;
    }

    return JSON.parse(userRaw);
  } catch (error) {
    return null;
  }
}

// ============================================
// GET USER ID
// ============================================

function getUserId(req) {
  const initData =
    req.headers["x-telegram-init-data"] ||
    req.body?.initData;

  const telegramUser = verifyTelegramInitData(initData);

  if (telegramUser?.id) {
    return String(telegramUser.id);
  }

  const userId =
    req.body?.userId ??
    req.body?.telegramId ??
    req.query?.userId;

  if (
    userId !== undefined &&
    userId !== null &&
    String(userId).trim() !== ""
  ) {
    return String(userId).trim();
  }

  return null;
}

// ============================================
// CREATE / GET USER
// ============================================

async function getOrCreateUser(telegramId, client = pool) {
  const result = await client.query(
    `
    INSERT INTO users (
      telegram_id,
      balance
    )
    VALUES ($1, 200)

    ON CONFLICT (telegram_id)
    DO UPDATE SET updated_at = NOW()

    RETURNING
      id,
      telegram_id,
      balance
    `,
    [telegramId]
  );

  return result.rows[0];
}

// ============================================
// MAIN PAGE
// ============================================

app.get("/", (req, res) => {
  res.json({
    ok: true,
    service: "Stars App API",
    balance: "unified",
    startingBalance: 200,
  });
});

// ============================================
// HEALTH CHECK
// ============================================

app.get("/health", async (req, res) => {
  try {
    await pool.query("SELECT 1");

    res.json({
      ok: true,
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      ok: false,
      error: "Database unavailable",
    });
  }
});

// ============================================
// GET BALANCE
// ============================================

app.get("/api/balance", async (req, res) => {
  try {
    const userId = getUserId(req);

    if (!userId) {
      return res.status(400).json({
        ok: false,
        error: "userId is required",
      });
    }

    const user = await getOrCreateUser(userId);

    res.json({
      ok: true,
      userId: user.telegram_id,
      balance: Number(user.balance),
    });
  } catch (error) {
    console.error("GET /api/balance:", error);

    res.status(500).json({
      ok: false,
      error: "Server error",
    });
  }
});

// ============================================
// PLINKO BET
// ============================================

app.post("/api/plinko/bet", async (req, res) => {
  const amount = Number(req.body?.amount);
  const userId = getUserId(req);

  if (!userId) {
    return res.status(400).json({
      ok: false,
      error: "userId is required",
    });
  }

  if (!Number.isFinite(amount) || amount <= 0) {
    return res.status(400).json({
      ok: false,
      error: "Invalid bet amount",
    });
  }

  const client = await pool.connect();

  try {
    await client.query("BEGIN");

    const user = await getOrCreateUser(userId, client);

    const balance = Number(user.balance);

    if (balance < amount) {
      await client.query("ROLLBACK");

      return res.status(400).json({
        ok: false,
        error: "Недостаточно ⭐",
        balance,
      });
    }

    const updated = await client.query(
      `
      UPDATE users
      SET
        balance = balance - $1,
        updated_at = NOW()
      WHERE telegram_id = $2

      RETURNING balance
      `,
      [amount, userId]
    );

    await client.query("COMMIT");

    res.json({
      ok: true,
      balance: Number(updated.rows[0].balance),
      bet: amount,
    });
  } catch (error) {
    await client.query("ROLLBACK").catch(() => {});

    console.error("POST /api/plinko/bet:", error);

    res.status(500).json({
      ok: false,
      error: "Server error",
    });
  } finally {
    client.release();
  }
});

// ============================================
// PLINKO SETTLE
// ============================================

app.post("/api/plinko/settle", async (req, res) => {
  const amount = Number(req.body?.amount);
  const multiplier = Number(req.body?.multiplier);
  const userId = getUserId(req);

  if (!userId) {
    return res.status(400).json({
      ok: false,
      error: "userId is required",
    });
  }

  if (!Number.isFinite(amount) || amount <= 0) {
    return res.status(400).json({
      ok: false,
      error: "Invalid bet amount",
    });
  }

  if (!Number.isFinite(multiplier) || multiplier < 0) {
    return res.status(400).json({
      ok: false,
      error: "Invalid multiplier",
    });
  }

  const payout = Number(
    (amount * multiplier).toFixed(2)
  );

  const client = await pool.connect();

  try {
    await client.query("BEGIN");

    const user = await getOrCreateUser(userId, client);

    const updated = await client.query(
      `
      UPDATE users
      SET
        balance = balance + $1,
        updated_at = NOW()
      WHERE telegram_id = $2

      RETURNING balance
      `,
      [payout, userId]
    );

    await client.query("COMMIT");

    res.json({
      ok: true,
      payout,
      multiplier,
      balance: Number(updated.rows[0].balance),
    });
  } catch (error) {
    await client.query("ROLLBACK").catch(() => {});

    console.error("POST /api/plinko/settle:", error);

    res.status(500).json({
      ok: false,
      error: "Server error",
    });
  } finally {
    client.release();
  }
});

// ============================================
// START SERVER
// ============================================

initDb()
  .then(() => {
    app.listen(PORT, "0.0.0.0", () => {
      console.log(
        `Server started on port ${PORT}`
      );
    });
  })
  .catch((error) => {
    console.error(
      "Database initialization failed:",
      error
    );

    process.exit(1);
  });