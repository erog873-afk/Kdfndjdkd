import asyncio
import hashlib
import hmac
import json
import math
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import TOKEN, ADMIN_ID

BASE_DIR = Path(__file__).resolve().parent
TASKS_FILE = BASE_DIR / "tasks.json"
USERS_FILE = BASE_DIR / "users.json"
APP_URL = os.getenv("RENDER_EXTERNAL_URL", "https://kdfndjdkd-2.onrender.com")

# Ссылки для кнопок "Канал" и "Чат" в приветственном сообщении.
# Замени на настоящие ссылки твоего канала и чата.
CHANNEL_URL = "https://t.me/your_channel"
CHAT_URL = "https://t.me/your_chat"

# Шаблон задания уже есть в Mini App — администратор вводит только ссылку на канал.
TASK_TITLE = "Подписаться на канал"
TASK_DESCRIPTION = "Перейдите в канал, подпишитесь на него, вернитесь сюда и нажмите кнопку «Проверить»"
TASK_REWARD = 0.5
TASK_TYPE = "Разовое задание"

ADMIN_IDS = {int(ADMIN_ID)} if ADMIN_ID else set()
waiting_for_channel = set()
waiting_for_limit = {}  # admin_id -> {"username": str, "chat_id": int}
dp = Dispatcher()

# ---- Plinko: баланс и ставки ----------------------------------------------
# Минимальная ставка в игре Plinko. Совпадает со значением MIN_BET на фронтенде
# (Plinko/src/lib/constants/game.ts). Баланс пользователей маленький (0.5-2 ⭐
# за задания) — если реальные ставки нужны меньше, уменьшите оба значения одинаково.
PLINKO_MIN_BET = 0.1

# Множители по числу рядов и уровню риска. Ячеек на 1 больше, чем рядов.
PLINKO_PAYOUTS = {
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

_plinko_games = {}  # game_id -> {"user": int, "amount": float, "rows": int, "risk": str}
_plinko_lock = threading.Lock()


def plinko_change_balance(user_id, delta):
    """Атомарно прибавляет delta (может быть отрицательной) к балансу пользователя в users.json."""
    users, key, record = get_user_record(user_id)
    new_balance = round(float(record.get("balance", 0.81)) + float(delta), 2)
    record["balance"] = new_balance
    users[key] = record
    write_users(users)
    return new_balance
# ---------------------------------------------------------------------------


def read_tasks():
    if not TASKS_FILE.exists():
        return []
    try:
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def write_tasks(tasks):
    tmp = TASKS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(TASKS_FILE)


def read_users():
    if not USERS_FILE.exists():
        return {}
    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_users(users):
    tmp = USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(USERS_FILE)


def get_user_record(user_id):
    users = read_users()
    key = str(user_id)
    record = users.get(key)
    if not isinstance(record, dict):
        record = {"balance": 0.81, "completed": []}
        users[key] = record
        write_users(users)
    record.setdefault("balance", 0.81)
    record.setdefault("completed", [])
    return users, key, record


def credit_user(user_id, task_id, reward):
    users, key, record = get_user_record(user_id)
    completed = [str(x) for x in record.get("completed", [])]
    if str(task_id) in completed:
        return float(record.get("balance", 0.81)), False
    record["balance"] = round(float(record.get("balance", 0.81)) + float(reward), 2)
    completed.append(str(task_id))
    record["completed"] = completed
    users[key] = record
    write_users(users)
    return float(record["balance"]), True


def next_task_id(tasks):
    ids = [int(t.get("id", 0)) for t in tasks if str(t.get("id", "")).isdigit()]
    return str(max(ids + [0]) + 1)


def register_task_completion(task_id):
    """Увеличивает счётчик выполнивших задание и удаляет задание,
    если достигнут лимит подписчиков (limit)."""
    tasks = read_tasks()
    remaining = []
    changed = False
    for t in tasks:
        if str(t.get("id")) == str(task_id):
            changed = True
            t["completed_count"] = int(t.get("completed_count", 0)) + 1
            limit = t.get("limit")
            if limit is not None and int(limit) > 0 and t["completed_count"] >= int(limit):
                continue  # лимит достигнут — задание не сохраняем, оно удаляется
        remaining.append(t)
    if changed:
        write_tasks(remaining)


def parse_channel_link(text):
    value = text.strip()
    if value.startswith("@") and re.fullmatch(r"@[A-Za-z0-9_]{5,32}", value):
        return value[1:]
    m = re.fullmatch(r"(?:https?://)?t\.me/([A-Za-z0-9_]{5,32})/?(?:\?.*)?", value, re.I)
    return m.group(1) if m else None


def telegram_api(method, params):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(payload.get("description", "Telegram API error"))
    return payload["result"]


def validate_webapp_init_data(init_data):
    if not init_data:
        raise ValueError("Telegram WebApp data is missing")
    parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
    received_hash = parsed.get("hash", [""])[0]
    if not received_hash:
        raise ValueError("Invalid Telegram WebApp data")
    pairs = []
    for key in sorted(k for k in parsed.keys() if k != "hash"):
        pairs.append(f"{key}={parsed[key][0]}")
    data_check_string = "\n".join(pairs)
    secret_key = hmac.new(b"WebAppData", TOKEN.encode("utf-8"), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise ValueError("Invalid Telegram WebApp signature")
    auth_date = int(parsed.get("auth_date", ["0"])[0])
    if not auth_date or time.time() - auth_date > 86400:
        raise ValueError("Telegram WebApp data expired")
    user_raw = parsed.get("user", [""])[0]
    user = json.loads(user_raw) if user_raw else {}
    user_id = int(user.get("id", 0))
    if not user_id:
        raise ValueError("Telegram user is missing")
    return user_id


class AppHandler(BaseHTTPRequestHandler):
    def send_body(self, status, body, content_type="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(data)

    def body_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/tasks":
            tasks = [t for t in read_tasks() if t.get("active", True)]
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            init_data = query.get("init_data", [""])[0]
            if init_data:
                try:
                    user_id = validate_webapp_init_data(init_data)
                    users = read_users()
                    completed = {str(x) for x in users.get(str(user_id), {}).get("completed", [])}
                    tasks = [t for t in tasks if str(t.get("id")) not in completed]
                except Exception:
                    pass
            self.send_body(200, json.dumps(tasks, ensure_ascii=False))
            return
        if path == "/api/balance":
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                init_data = query.get("init_data", [""])[0]
                user_id = validate_webapp_init_data(init_data)
                _, _, record = get_user_record(user_id)
                self.send_body(200, json.dumps({"balance": round(float(record.get("balance", 0.81)), 2)}, ensure_ascii=False))
            except Exception:
                self.send_body(200, '{"balance":0.81}')
            return
        if path == "/health":
            self.send_body(200, '{"ok":true}')
            return
        rel = path.lstrip("/") or "index.html"
        target = (BASE_DIR / rel).resolve()
        if BASE_DIR not in target.parents and target != BASE_DIR:
            self.send_body(403, "Forbidden", "text/plain; charset=utf-8")
            return
        if not target.is_file():
            self.send_body(404, "Not found", "text/plain; charset=utf-8")
            return
        types_map = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
        }
        self.send_body(200, target.read_bytes(), types_map.get(target.suffix, "application/octet-stream"))

    def do_OPTIONS(self):
        self.send_body(204, b"", "text/plain; charset=utf-8")

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/plinko/bet":
            self.handle_plinko_bet()
            return
        if path == "/api/plinko/settle":
            self.handle_plinko_settle()
            return
        if path != "/api/tasks/verify":
            self.send_body(404, '{"error":"not_found"}')
            return
        try:
            payload = self.body_json()
            task_id = str(payload.get("task_id", ""))
            user_id = validate_webapp_init_data(str(payload.get("init_data", "")))
            task = next((t for t in read_tasks() if str(t.get("id")) == task_id and t.get("active", True)), None)
            if not task:
                self.send_body(404, '{"error":"task_not_found"}')
                return
            member = telegram_api("getChatMember", {"chat_id": task["chat_id"], "user_id": user_id})
            subscribed = member.get("status") in {"creator", "administrator", "member"} or (
                member.get("status") == "restricted" and member.get("is_member") is True
            )
            if not subscribed:
                self.send_body(200, json.dumps({"subscribed": False, "credited": False}, ensure_ascii=False))
                return
            balance, credited = credit_user(user_id, task_id, float(task.get("reward", TASK_REWARD)))
            if credited:
                register_task_completion(task_id)
            self.send_body(200, json.dumps({
                "subscribed": True,
                "credited": credited,
                "already_completed": not credited,
                "balance": balance,
            }, ensure_ascii=False))
        except Exception as exc:
            self.send_body(400, json.dumps({"error": str(exc)}, ensure_ascii=False))

    def handle_plinko_bet(self):
        try:
            payload = self.body_json()
            user_id = validate_webapp_init_data(str(payload.get("init_data", "")))
            rows = int(payload.get("rows", 0))
            risk = str(payload.get("risk", "")).upper()
            amount = float(payload.get("amount", 0))
            if rows not in PLINKO_PAYOUTS or risk not in PLINKO_PAYOUTS[rows]:
                self.send_body(400, '{"error":"bad_params"}')
                return
            if amount < PLINKO_MIN_BET:
                self.send_body(400, '{"error":"bet_too_small"}')
                return
            with _plinko_lock:
                _, _, record = get_user_record(user_id)
                if float(record.get("balance", 0)) < amount:
                    self.send_body(402, '{"error":"not_enough_balance"}')
                    return
                balance = plinko_change_balance(user_id, -amount)
                game_id = uuid.uuid4().hex
                _plinko_games[game_id] = {
                    "user": user_id, "amount": amount, "rows": rows, "risk": risk,
                }
            self.send_body(200, json.dumps({"game_id": game_id, "balance": balance}, ensure_ascii=False))
        except Exception as exc:
            self.send_body(400, json.dumps({"error": str(exc)}, ensure_ascii=False))

    def handle_plinko_settle(self):
        try:
            payload = self.body_json()
            user_id = validate_webapp_init_data(str(payload.get("init_data", "")))
            game_id = str(payload.get("game_id", ""))
            bin_index = int(payload.get("bin_index", -1))
            with _plinko_lock:
                game = _plinko_games.pop(game_id, None)  # pop: выплата ровно один раз
                if not game or game["user"] != user_id:
                    self.send_body(404, '{"error":"game_not_found"}')
                    return
                table = PLINKO_PAYOUTS[game["rows"]][game["risk"]]
                if not (0 <= bin_index < len(table)):
                    self.send_body(400, '{"error":"bad_bin"}')
                    return
                multiplier = table[bin_index]
                payout = round(game["amount"] * multiplier, 2)
                if payout:
                    balance = plinko_change_balance(user_id, payout)
                else:
                    _, _, record = get_user_record(user_id)
                    balance = float(record.get("balance", 0))
            self.send_body(200, json.dumps(
                {"balance": balance, "payout": payout, "multiplier": multiplier}, ensure_ascii=False
            ))
        except Exception as exc:
            self.send_body(400, json.dumps({"error": str(exc)}, ensure_ascii=False))

    def log_message(self, *args):
        pass


def run_http_server():
    port = int(os.getenv("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), AppHandler).serve_forever()


def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить задание", callback_data="add_task"))
    kb.row(types.InlineKeyboardButton(text="📋 Мои задания", callback_data="list_tasks"))
    kb.row(types.InlineKeyboardButton(text="⭐ Открыть приложение", web_app=types.WebAppInfo(url=APP_URL)))
    return kb.as_markup()


def format_task_button_text(task):
    url = task.get("url", "")
    channel = url.split("/")[-1] if url else task.get("title", "Задание")
    count = int(task.get("completed_count", 0))
    limit = task.get("limit")
    progress = f"{count}/{limit}" if limit else f"{count}/∞"
    return f"@{channel} — {progress}"


def tasks_list_keyboard():
    tasks = read_tasks()
    kb = InlineKeyboardBuilder()
    if not tasks:
        kb.row(types.InlineKeyboardButton(text="Заданий пока нет", callback_data="noop"))
    else:
        for t in tasks:
            kb.row(types.InlineKeyboardButton(
                text=format_task_button_text(t),
                callback_data=f"view_task:{t.get('id')}",
            ))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back"))
    return kb.as_markup()


def task_view_text(task):
    limit = task.get("limit")
    limit_text = str(limit) if limit else "без лимита"
    return (
        f"Канал: {task.get('url', '—')}\n"
        f"Награда: {task.get('reward', TASK_REWARD)} ⭐\n"
        f"Подписалось: {int(task.get('completed_count', 0))}\n"
        f"Лимит: {limit_text}"
    )


def task_view_keyboard(task_id):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_task:{task_id}"))
    kb.row(types.InlineKeyboardButton(text="⬅️ К списку", callback_data="list_tasks"))
    return kb.as_markup()


@dp.message(CommandStart())
async def start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="⭐ Открыть приложение", web_app=types.WebAppInfo(url=APP_URL)))
    kb.row(
        types.InlineKeyboardButton(text="Канал", url=CHANNEL_URL),
        types.InlineKeyboardButton(text="Чат", url=CHAT_URL),
    )
    await message.answer(
        "⭐ Зарабатывайте звёзды и NFT-подарки, выполняя очень простые задания и играя в игры 👇",
        reply_markup=kb.as_markup(),
    )


@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        await start(message)
        return
    await message.answer("Панель администратора", reply_markup=admin_menu())


@dp.callback_query(F.data == "add_task")
async def add_task_start(callback: types.CallbackQuery):
    if not callback.from_user or callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    waiting_for_channel.add(callback.from_user.id)
    await callback.message.answer("📢 Отправьте ссылку на Telegram-канал.\nНапример: https://t.me/example")
    await callback.answer()


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    if not callback.from_user or callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        await callback.message.edit_text("Панель администратора", reply_markup=admin_menu())
    except Exception:
        await callback.message.answer("Панель администратора", reply_markup=admin_menu())
    await callback.answer()


@dp.callback_query(F.data == "list_tasks")
async def list_tasks(callback: types.CallbackQuery):
    if not callback.from_user or callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        await callback.message.edit_text("📋 Задания на подписку:", reply_markup=tasks_list_keyboard())
    except Exception:
        await callback.message.answer("📋 Задания на подписку:", reply_markup=tasks_list_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("view_task:"))
async def view_task(callback: types.CallbackQuery):
    if not callback.from_user or callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    task_id = callback.data.split(":", 1)[1]
    task = next((t for t in read_tasks() if str(t.get("id")) == task_id), None)
    if not task:
        await callback.answer("Задание не найдено (возможно, уже удалено)", show_alert=True)
        try:
            await callback.message.edit_text("📋 Задания на подписку:", reply_markup=tasks_list_keyboard())
        except Exception:
            pass
        return
    try:
        await callback.message.edit_text(task_view_text(task), reply_markup=task_view_keyboard(task_id))
    except Exception:
        await callback.message.answer(task_view_text(task), reply_markup=task_view_keyboard(task_id))
    await callback.answer()


@dp.callback_query(F.data.startswith("delete_task:"))
async def delete_task(callback: types.CallbackQuery):
    if not callback.from_user or callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    task_id = callback.data.split(":", 1)[1]
    tasks = read_tasks()
    remaining = [t for t in tasks if str(t.get("id")) != task_id]
    if len(remaining) != len(tasks):
        write_tasks(remaining)
        await callback.answer("Задание удалено", show_alert=True)
    else:
        await callback.answer("Задание не найдено", show_alert=True)
    try:
        await callback.message.edit_text("📋 Задания на подписку:", reply_markup=tasks_list_keyboard())
    except Exception:
        await callback.message.answer("📋 Задания на подписку:", reply_markup=tasks_list_keyboard())


@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()


@dp.message()
async def any_message(message: types.Message):
    is_admin = bool(message.from_user and message.from_user.id in ADMIN_IDS)

    # Админ, ожидающий ссылку на канал после "➕ Добавить задание".
    if is_admin and message.from_user.id in waiting_for_channel:
        username = parse_channel_link(message.text or "")
        if not username:
            await message.answer("Нужна ссылка на публичный канал вида https://t.me/username")
            return

        try:
            bot = message.bot
            chat = await bot.get_chat(f"@{username}")
            if chat.type != "channel":
                await message.answer("Эта ссылка ведёт не на канал. Отправьте ссылку именно на Telegram-канал.")
                return
            me = await bot.get_me()
            member = await bot.get_chat_member(chat.id, me.id)
            if member.status not in {"administrator", "creator"}:
                await message.answer("Добавьте бота администратором канала, чтобы он мог проверять подписку.")
                return

            waiting_for_channel.discard(message.from_user.id)
            waiting_for_limit[message.from_user.id] = {"username": username, "chat_id": chat.id}
            await message.answer(
                "Сколько человек должно подписаться, чтобы задание закрылось само?\n"
                "Введите число (например 1000) или 0, если лимит не нужен."
            )
        except Exception:
            await message.answer("Не удалось проверить канал. Убедитесь, что ссылка правильная и бот добавлен в канал администратором.")
        return

    # Админ, которому только что задали вопрос про лимит подписчиков.
    if is_admin and message.from_user.id in waiting_for_limit:
        raw = (message.text or "").strip()
        if not raw.isdigit():
            await message.answer("Введите число, например 1000, или 0, если лимит не нужен.")
            return

        limit = int(raw)
        pending = waiting_for_limit.pop(message.from_user.id)
        tasks = read_tasks()
        task = {
            "id": next_task_id(tasks),
            "title": TASK_TITLE,
            "description": TASK_DESCRIPTION,
            "reward": TASK_REWARD,
            "url": f"https://t.me/{pending['username']}",
            "chat_id": pending["chat_id"],
            "type": TASK_TYPE,
            "active": True,
            "limit": limit if limit > 0 else None,
            "completed_count": 0,
        }
        tasks.append(task)
        write_tasks(tasks)
        limit_text = str(limit) if limit > 0 else "без лимита"
        await message.answer(
            f"✅ Задание добавлено.\nКанал: {task['url']}\nНаграда: {TASK_REWARD} ⭐\nЛимит подписчиков: {limit_text}\n"
            "Оно уже будет отдано Mini App через /api/tasks."
        )
        return

    # Любое другое сообщение (любое слово, любая буква, не только /start) —
    # присылаем обычное приветствие с кнопками. Панель админа открывается
    # только по отдельной команде /admin.
    await start(message)



async def main():
    if not TOKEN:
        raise RuntimeError("В config.py нужно указать TOKEN")
    if not ADMIN_IDS:
        raise RuntimeError("В config.py нужно указать ADMIN_ID")
    threading.Thread(target=run_http_server, daemon=True).start()
    bot = Bot(token=TOKEN)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
