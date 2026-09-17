import asyncio
import hashlib
import hmac
import json
import sqlite3
import time
from html import escape
from urllib.parse import parse_qsl

from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    TOKEN, APP_URL, CHANNEL_URL, CHAT_URL,
    ADMIN_ID, DATABASE_PATH, HOST, PORT
)

dp = Dispatcher(storage=MemoryStorage())


# -------------------- DATABASE --------------------

def db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            url TEXT DEFAULT '',
            reward REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_completions (
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            completed_at INTEGER NOT NULL,
            PRIMARY KEY (user_id, task_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def get_tasks(active_only=True):
    conn = db()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE active=1 ORDER BY id DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY id DESC"
        ).fetchall()
    conn.close()
    return rows


def get_task(task_id):
    conn = db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return row


def get_balance(user_id):
    conn = db()
    row = conn.execute(
        "SELECT balance FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return float(row["balance"]) if row else 0.0


# -------------------- TELEGRAM AUTH --------------------

def verify_init_data(init_data: str):
    """
    Проверяет Telegram WebApp initData по официальному алгоритму.
    Возвращает user dict или None.
    """
    if not init_data or not TOKEN:
        return None

    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        auth_date = int(pairs.get("auth_date", "0"))

        if not received_hash:
            return None

        # Не принимаем слишком старые initData.
        if abs(int(time.time()) - auth_date) > 86400:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(pairs.items())
        )
        secret_key = hmac.new(
            b"WebAppData",
            TOKEN.encode(),
            hashlib.sha256
        ).digest()
        calculated = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated, received_hash):
            return None

        user = json.loads(pairs.get("user", "{}"))
        if not user.get("id"):
            return None
        return user
    except Exception:
        return None


def request_user(request):
    return verify_init_data(
        request.headers.get("X-Telegram-Init-Data", "")
    )


# -------------------- MINI APP API --------------------

async def api_tasks(request):
    rows = get_tasks(True)
    return web.json_response({
        "tasks": [
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "url": row["url"],
                "reward": row["reward"],
            }
            for row in rows
        ]
    })


async def api_balance(request):
    user = request_user(request)
    if not user:
        return web.json_response({"balance": 0}, status=401)
    return web.json_response({"balance": get_balance(user["id"])})


async def api_complete(request):
    user = request_user(request)
    if not user:
        return web.json_response(
            {"error": "Откройте приложение через Telegram."}, status=401
        )

    try:
        task_id = int(request.match_info["task_id"])
    except ValueError:
        return web.json_response({"error": "Некорректное задание."}, status=400)

    conn = db()
    task = conn.execute(
        "SELECT * FROM tasks WHERE id=? AND active=1", (task_id,)
    ).fetchone()

    if not task:
        conn.close()
        return web.json_response({"error": "Задание больше недоступно."}, status=404)

    already = conn.execute(
        "SELECT 1 FROM task_completions WHERE user_id=? AND task_id=?",
        (user["id"], task_id)
    ).fetchone()

    if already:
        balance = conn.execute(
            "SELECT balance FROM users WHERE user_id=?", (user["id"],)
        ).fetchone()
        conn.close()
        return web.json_response({
            "error": "Это задание уже выполнено.",
            "balance": float(balance["balance"]) if balance else 0
        }, status=409)

    conn.execute(
        "INSERT OR IGNORE INTO users(user_id,balance) VALUES(?,0)",
        (user["id"],)
    )
    conn.execute(
        "UPDATE users SET balance=balance+? WHERE user_id=?",
        (float(task["reward"]), user["id"])
    )
    conn.execute(
        "INSERT INTO task_completions(user_id,task_id,completed_at) VALUES(?,?,?)",
        (user["id"], task_id, int(time.time()))
    )
    row = conn.execute(
        "SELECT balance FROM users WHERE user_id=?", (user["id"],)
    ).fetchone()
    conn.commit()
    conn.close()

    return web.json_response({"ok": True, "balance": float(row["balance"])})


# -------------------- ADMIN BOT --------------------

def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить задание", callback_data="admin:add")],
        [InlineKeyboardButton(text="📋 Все задания", callback_data="admin:list")],
    ])


class AddTask(StatesGroup):
    title = State()
    description = State()
    url = State()
    reward = State()


class EditTask(StatesGroup):
    value = State()


@dp.message(CommandStart())
async def start(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(types.InlineKeyboardButton(
        text="⭐ Открыть приложение",
        web_app=types.WebAppInfo(url=APP_URL)
    ))
    keyboard.row(
        types.InlineKeyboardButton(text="Канал", url=CHANNEL_URL),
        types.InlineKeyboardButton(text="Чат", url=CHAT_URL)
    )

    await message.answer(
        "⭐ Зарабатывайте звёзды и NFT-подарки, "
        "выполняя простые задания и играя в игры 👇",
        reply_markup=keyboard.as_markup()
    )


@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=admin_keyboard())


@dp.callback_query(F.data == "admin:panel")
async def admin_panel(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await call.message.edit_text(
        "🛠 <b>Админ-панель</b>", reply_markup=admin_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "admin:add")
async def admin_add_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AddTask.title)
    await call.message.answer(
        "➕ <b>Добавление задания</b>\n\n"
        "Шаг 1/4. Напиши название задания:"
    )
    await call.answer()


@dp.message(AddTask.title)
async def add_title(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    title = message.text.strip()
    if not title:
        await message.answer("Название не может быть пустым. Напиши ещё раз:")
        return
    await state.update_data(title=title)
    await state.set_state(AddTask.description)
    await message.answer(
        "Шаг 2/4. Напиши описание задания.\n"
        "Если описание не нужно — отправь <code>-</code>."
    )


@dp.message(AddTask.description)
async def add_description(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    description = message.text.strip()
    if description == "-":
        description = ""
    await state.update_data(description=description)
    await state.set_state(AddTask.url)
    await message.answer(
        "Шаг 3/4. Отправь ссылку на задание.\n"
        "Например: <code>https://t.me/...</code>\n"
        "Если ссылки нет — отправь <code>-</code>."
    )


@dp.message(AddTask.url)
async def add_url(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    url = message.text.strip()
    if url == "-":
        url = ""
    elif not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("Ссылка должна начинаться с http:// или https://. Попробуй ещё раз:")
        return
    await state.update_data(url=url)
    await state.set_state(AddTask.reward)
    await message.answer("Шаг 4/4. Напиши награду в звёздах, например <code>10</code>:")


@dp.message(AddTask.reward)
async def add_reward(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        reward = float(message.text.replace(",", "."))
        if reward <= 0 or reward > 1000000:
            raise ValueError
    except ValueError:
        await message.answer("Укажи положительное число, например 10 или 25:")
        return

    data = await state.get_data()
    conn = db()
    conn.execute(
        "INSERT INTO tasks(title,description,url,reward,active,created_at) VALUES(?,?,?,?,1,?)",
        (data["title"], data["description"], data["url"], reward, int(time.time()))
    )
    conn.commit()
    conn.close()
    await state.clear()

    await message.answer(
        f"✅ Задание добавлено!\n\n"
        f"<b>{escape(data['title'])}</b>\n"
        f"Награда: ⭐ {reward:g}",
        reply_markup=admin_keyboard()
    )


@dp.callback_query(F.data == "admin:list")
async def admin_list(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    rows = get_tasks(False)
    if not rows:
        await call.message.edit_text(
            "📋 Заданий пока нет.", reply_markup=admin_keyboard()
        )
        await call.answer()
        return

    builder = InlineKeyboardBuilder()
    for row in rows:
        status = "🟢" if row["active"] else "⚪"
        title = row["title"][:35]
        builder.row(InlineKeyboardButton(
            text=f"{status} {title} · ⭐{row['reward']:g}",
            callback_data=f"admin:task:{row['id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:panel"))

    await call.message.edit_text(
        "📋 <b>Задания</b>\n\n"
        "🟢 — активно\n⚪ — выключено",
        reply_markup=builder.as_markup()
    )
    await call.answer()


@dp.callback_query(F.data.startswith("admin:task:"))
async def admin_task(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    task_id = int(call.data.rsplit(":", 1)[1])
    task = get_task(task_id)
    if not task:
        await call.answer("Задание не найдено", show_alert=True)
        return

    status = "🟢 включено" if task["active"] else "⚪ выключено"
    text = (
        f"📌 <b>{escape(task['title'])}</b>\n\n"
        f"{escape(task['description'] or 'Без описания')}\n\n"
        f"Награда: ⭐ <b>{task['reward']:g}</b>\n"
        f"Статус: {status}"
    )
    if task["url"]:
        text += f"\nСсылка: {escape(task['url'])}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Название", callback_data=f"edit:title:{task_id}"),
            InlineKeyboardButton(text="📝 Описание", callback_data=f"edit:description:{task_id}")
        ],
        [
            InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"edit:url:{task_id}"),
            InlineKeyboardButton(text="⭐ Награда", callback_data=f"edit:reward:{task_id}")
        ],
        [InlineKeyboardButton(
            text="🔴 Выключить" if task["active"] else "🟢 Включить",
            callback_data=f"toggle:{task_id}"
        )],
        [InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"delete:{task_id}"
        )],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="admin:list")]
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("toggle:"))
async def toggle_task(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    task_id = int(call.data.split(":")[1])
    conn = db()
    conn.execute("UPDATE tasks SET active=1-active WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    await call.answer("Готово")
    # Re-open task card
    fake = types.CallbackQuery(
        id=call.id, from_user=call.from_user, chat_instance=call.chat_instance,
        message=call.message, data=f"admin:task:{task_id}"
    )
    # Directly call function is simpler and preserves current message.
    await admin_task(fake)


@dp.callback_query(F.data.startswith("delete:"))
async def delete_task(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    task_id = int(call.data.split(":")[1])
    conn = db()
    conn.execute("DELETE FROM task_completions WHERE task_id=?", (task_id,))
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    await call.answer("Задание удалено")
    # list again
    await admin_list(call)


@dp.callback_query(F.data.startswith("edit:"))
async def edit_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    _, field, task_id_s = call.data.split(":")
    task_id = int(task_id_s)
    task = get_task(task_id)
    if not task:
        await call.answer("Задание не найдено", show_alert=True)
        return

    labels = {
        "title": "новое название",
        "description": "новое описание (или -)",
        "url": "новую ссылку (или -)",
        "reward": "новую награду в звёздах",
    }
    await state.set_state(EditTask.value)
    await state.update_data(task_id=task_id, field=field)
    await call.message.answer(
        f"✏️ Отправь {labels.get(field, 'новое значение')}:"
    )
    await call.answer()


@dp.message(EditTask.value)
async def edit_value(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    task_id = int(data["task_id"])
    field = data["field"]
    value = message.text.strip()

    if field == "title":
        if not value:
            await message.answer("Название не может быть пустым.")
            return
    elif field == "description":
        value = "" if value == "-" else value
    elif field == "url":
        if value == "-":
            value = ""
        elif not (value.startswith("http://") or value.startswith("https://")):
            await message.answer("Ссылка должна начинаться с http:// или https://.")
            return
    elif field == "reward":
        try:
            value = float(value.replace(",", "."))
            if value <= 0 or value > 1000000:
                raise ValueError
        except ValueError:
            await message.answer("Укажи положительное число.")
            return

    conn = db()
    conn.execute(f"UPDATE tasks SET {field}=? WHERE id=?", (value, task_id))
    conn.commit()
    conn.close()
    await state.clear()

    await message.answer("✅ Изменения сохранены.", reply_markup=admin_keyboard())


# -------------------- WEB SERVER --------------------

async def health(request):
    return web.json_response({"ok": True})


async def start_web_server():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/api/tasks", api_tasks)
    app.router.add_get("/api/balance", api_balance)
    app.router.add_post("/api/tasks/{task_id}/complete", api_complete)

    # CORS для Mini App / Render
    async def options(request):
        return web.Response(status=204)

    for path in ["/api/tasks", "/api/balance", "/api/tasks/{task_id}/complete"]:
        app.router.add_route("OPTIONS", path, options)

    async def cors_middleware(app, handler):
        async def middleware_handler(request):
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            return response
        return middleware_handler

    # aiohttp middleware must be passed at application creation; add manually isn't supported.
    # Instead use a wrapping on_response_prepare.
    async def add_cors(request, response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"

    app.on_response_prepare.append(add_cors)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    print(f"API запущен на {HOST}:{PORT}")
    return runner


async def main():
    if not TOKEN:
        raise RuntimeError(
            "Не задан TOKEN. На Render создай Environment Variable TOKEN."
        )
    if not ADMIN_ID:
        print("ВНИМАНИЕ: ADMIN_ID не задан — админ-панель будет недоступна.")

    init_db()
    bot = Bot(token=TOKEN)
    runner = await start_web_server()

    print("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
