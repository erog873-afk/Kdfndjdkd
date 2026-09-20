"""
Сервер для Plinko: общий баланс с главным приложением.

Два запроса, которые вызывает игра:
  POST /api/plinko/bet     {init_data, amount, rows, risk}   -> {game_id, balance}
  POST /api/plinko/settle  {init_data, game_id, bin_index}   -> {balance, payout, multiplier}

Как подключить (FastAPI):
    from plinko_api import router
    app.include_router(router)
    # и разрешите CORS для адреса сайта на Render (CORSMiddleware, allow_origins=[...])

Вам нужно заполнить BOT_TOKEN и две функции get_balance / change_balance —
они должны работать с той же базой, что отдаёт /api/balance.
"""
import hashlib
import hmac
import json
import math
import threading
import time
import uuid
from urllib.parse import parse_qsl

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

BOT_TOKEN = "8762994126:AAEPxOKqTNMj3BHH8LUC7EzjhB2Iio06zKQ"
MIN_BET = 25
INIT_DATA_MAX_AGE = 24 * 3600  # сек


# ---- Ваша база баланса ----------------------------------------------------
def get_balance(user_id: int) -> float:
    """Верните баланс пользователя (тот же, что в /api/balance)."""
    raise NotImplementedError


def change_balance(user_id: int, delta: float) -> float:
    """Атомарно прибавьте delta (может быть отрицательной), верните новый баланс."""
    raise NotImplementedError
# ---------------------------------------------------------------------------

# Множители по числу рядов и риску (те же, что в игре). Ячеек на 1 больше, чем рядов.
PAYOUTS = {
    8: {
        "LOW": [5.6, 2.1, 1.1, 1.0, 0.5, 1.0, 1.1, 2.1, 5.6],
        "MEDIUM": [5.2, 1.6, 1.2, 1.0, 0.4, 1.0, 1.2, 1.6, 5.2],
        "HIGH": [29.0, 4.0, 1.5, 0.3, 0.2, 0.3, 1.5, 4.0, 29.0],
    },
    9: {
        "LOW": [5.6, 2.0, 1.6, 1.0, 0.7, 0.7, 1.0, 1.6, 2.0, 5.6],
        "MEDIUM": [18.0, 4.0, 1.7, 0.9, 0.5, 0.5, 0.9, 1.7, 4.0, 18.0],
        "HIGH": [43.0, 7.0, 2.0, 0.6, 0.2, 0.2, 0.6, 2.0, 7.0, 43.0],
    },
    10: {
        "LOW": [8.9, 3.0, 1.4, 1.1, 1.0, 0.5, 1.0, 1.1, 1.4, 3.0, 8.9],
        "MEDIUM": [22.0, 5.0, 2.0, 1.4, 0.6, 0.4, 0.6, 1.4, 2.0, 5.0, 22.0],
        "HIGH": [76.0, 10.0, 3.0, 0.9, 0.3, 0.2, 0.3, 0.9, 3.0, 10.0, 76.0],
    },
    11: {
        "LOW": [8.4, 3.0, 1.9, 1.3, 1.0, 0.7, 0.7, 1.0, 1.3, 1.9, 3.0, 8.4],
        "MEDIUM": [24.0, 6.0, 3.0, 1.8, 0.7, 0.5, 0.5, 0.7, 1.8, 3.0, 6.0, 24.0],
        "HIGH": [120.0, 14.0, 5.2, 1.4, 0.4, 0.2, 0.2, 0.4, 1.4, 5.2, 14.0, 120.0],
    },
    12: {
        "LOW": [10.0, 3.0, 1.6, 1.4, 1.1, 1.0, 0.5, 1.0, 1.1, 1.4, 1.6, 3.0, 10.0],
        "MEDIUM": [33.0, 11.0, 4.0, 2.0, 1.1, 0.6, 0.3, 0.6, 1.1, 2.0, 4.0, 11.0, 33.0],
        "HIGH": [170.0, 24.0, 8.1, 2.0, 0.7, 0.2, 0.2, 0.2, 0.7, 2.0, 8.1, 24.0, 170.0],
    },
    13: {
        "LOW": [8.1, 4.0, 3.0, 1.9, 1.2, 0.9, 0.7, 0.7, 0.9, 1.2, 1.9, 3.0, 4.0, 8.1],
        "MEDIUM": [43.0, 13.0, 6.0, 3.0, 1.3, 0.7, 0.4, 0.4, 0.7, 1.3, 3.0, 6.0, 13.0, 43.0],
        "HIGH": [260.0, 37.0, 11.0, 4.0, 1.0, 0.2, 0.2, 0.2, 0.2, 1.0, 4.0, 11.0, 37.0, 260.0],
    },
    14: {
        "LOW": [7.1, 4.0, 1.9, 1.4, 1.3, 1.1, 1.0, 0.5, 1.0, 1.1, 1.3, 1.4, 1.9, 4.0, 7.1],
        "MEDIUM": [58.0, 15.0, 7.0, 4.0, 1.9, 1.0, 0.5, 0.2, 0.5, 1.0, 1.9, 4.0, 7.0, 15.0, 58.0],
        "HIGH": [420.0, 56.0, 18.0, 5.0, 1.9, 0.3, 0.2, 0.2, 0.2, 0.3, 1.9, 5.0, 18.0, 56.0, 420.0],
    },
    15: {
        "LOW": [15.0, 8.0, 3.0, 2.0, 1.5, 1.1, 1.0, 0.7, 0.7, 1.0, 1.1, 1.5, 2.0, 3.0, 8.0, 15.0],
        "MEDIUM": [88.0, 18.0, 11.0, 5.0, 3.0, 1.3, 0.5, 0.3, 0.3, 0.5, 1.3, 3.0, 5.0, 11.0, 18.0, 88.0],
        "HIGH": [620.0, 83.0, 27.0, 8.0, 3.0, 0.5, 0.2, 0.2, 0.2, 0.2, 0.5, 3.0, 8.0, 27.0, 83.0, 620.0],
    },
    16: {
        "LOW": [16.0, 9.0, 2.0, 1.4, 1.4, 1.2, 1.1, 1.0, 0.5, 1.0, 1.1, 1.2, 1.4, 1.4, 2.0, 9.0, 16.0],
        "MEDIUM": [110.0, 41.0, 10.0, 5.0, 3.0, 1.5, 1.0, 0.5, 0.3, 0.5, 1.0, 1.5, 3.0, 5.0, 10.0, 41.0, 110.0],
        "HIGH": [1000.0, 130.0, 26.0, 9.0, 4.0, 2.0, 0.2, 0.2, 0.2, 0.2, 0.2, 2.0, 4.0, 9.0, 26.0, 130.0, 1000.0],
    },
}

# Открытые игры. Для продакшена храните в базе, а не в памяти.
_games: dict = {}
_lock = threading.Lock()
router = APIRouter()


def verify_init_data(init_data: str) -> int:
    """Проверяет подпись Telegram и возвращает id пользователя."""
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received = pairs.pop("hash")
        check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, received):
            raise ValueError("bad hash")
        if time.time() - int(pairs.get("auth_date", "0")) > INIT_DATA_MAX_AGE:
            raise ValueError("expired")
        return int(json.loads(pairs["user"])["id"])
    except Exception:
        raise HTTPException(status_code=401, detail="bad init_data")


class BetIn(BaseModel):
    init_data: str
    amount: int
    rows: int
    risk: str


class SettleIn(BaseModel):
    init_data: str
    game_id: str
    bin_index: int


@router.post("/api/plinko/bet")
def bet(body: BetIn):
    user_id = verify_init_data(body.init_data)
    if body.rows not in PAYOUTS or body.risk not in PAYOUTS[body.rows]:
        raise HTTPException(400, "bad params")
    if body.amount < MIN_BET:
        raise HTTPException(400, "bet too small")
    with _lock:
        if get_balance(user_id) < body.amount:
            raise HTTPException(402, "not enough balance")
        balance = change_balance(user_id, -body.amount)
        game_id = uuid.uuid4().hex
        _games[game_id] = {
            "user": user_id, "amount": body.amount,
            "rows": body.rows, "risk": body.risk,
        }
    return {"game_id": game_id, "balance": balance}


@router.post("/api/plinko/settle")
def settle(body: SettleIn):
    user_id = verify_init_data(body.init_data)
    with _lock:
        game = _games.pop(body.game_id, None)  # pop: выплата ровно один раз
        if not game or game["user"] != user_id:
            raise HTTPException(404, "game not found")
        table = PAYOUTS[game["rows"]][game["risk"]]
        if not 0 <= body.bin_index < len(table):
            raise HTTPException(400, "bad bin")
        multiplier = table[body.bin_index]
        payout = math.floor(game["amount"] * multiplier)
        balance = change_balance(user_id, payout) if payout else get_balance(user_id)
    return {"balance": balance, "payout": payout, "multiplier": multiplier}
