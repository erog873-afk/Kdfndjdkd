import asyncio
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import TOKEN, APP_URL, CHANNEL_URL, CHAT_URL, ADMIN_PASSWORD, ADMIN_IDS

BASE_DIR = Path(__file__).resolve().parent
TASKS_FILE = BASE_DIR / "tasks.json"
dp = Dispatcher()

REWARD = 0.5
TASK_TITLE = "Подписаться на канал"
TASK_DESCRIPTION = "Подпишитесь на канал"
TASK_TYPE = "Подписка на канал"


class AddTask(StatesGroup):
    waiting_channel_link = State()


def read_tasks():
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def write_tasks(tasks):
    tmp = TASKS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(TASKS_FILE)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_ok(handler):
    return bool(ADMIN_PASSWORD) and handler.headers.get("X-Admin-Password", "") == ADMIN_PASSWORD


def admin_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить задание", callback_data="admin:add")
    kb.button(text="📋 Мои задания", callback_data="admin:list")
    kb.adjust(1)
    return kb.as_markup()


def task_type_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Подписка на канал", callback_data="task:add_subscription")
    kb.button(text="◀️ Назад", callback_data="admin:back")
    kb.adjust(1)
    return kb.as_markup()


async def show_admin(message: types.Message):
    await message.answer(
        "🔐 Админ-панель\n\nВыберите действие:",
        reply_markup=admin_keyboard(),
    )


@dp.message(CommandStart())
async def start(message: types.Message):
    # /start admin открывает админку, обычный /start оставляет пользовательское меню.
    if is_admin(message.from_user.id) and len(message.text.split()) > 1 and message.text.split()[1].lower() in {"admin", "админ"}:
        await show_admin(message)
        return

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
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await show_admin(message)


@dp.callback_query(F.data == "admin:add")
async def admin_add(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "➕ Добавление задания\n\nВыберите тип:",
        reply_markup=task_type_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data == "task:add_subscription")
async def add_subscription_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AddTask.waiting_channel_link)
    await callback.message.edit_text(
        "📢 Подписка на канал\n\n"
        "Пришлите ссылку на публичный Telegram-канал, например:\n"
        "https://t.me/my_channel\n\n"
        "Я проверю ссылку и доступ бота к каналу.\n"
        "После этого задание создастся автоматически:\n"
        "⭐ 0,5 — «Подписаться на канал».\n\n"
        "❗ Бот должен быть администратором канала, чтобы проверять подписку пользователей.\n\n"
        "Для отмены: /cancel"
    )
    await callback.answer()


@dp.message(AddTask.waiting_channel_link)
async def receive_channel_link(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ Доступ запрещён.")
        return

    link = message.text.strip() if message.text else ""
    parsed = urlparse(link)
    host = parsed.netloc.lower().split(":")[0]
    path = parsed.path.strip("/")

    if host not in {"t.me", "telegram.me", "www.t.me", "www.telegram.me"} or not path or path.startswith("+"):
        await message.answer(
            "❌ Не удалось проверить ссылку.\n\n"
            "Пришлите ссылку на публичный канал вида:\n"
            "https://t.me/имя_канала"
        )
        return

    username = path.split("/")[0]
    if not re.fullmatch(r"[A-Za-z0-9_]{5,}", username):
        await message.answer("❌ Ссылка должна вести на публичный Telegram-канал.")
        return

    try:
        chat = await bot.get_chat("@" + username)
    except Exception:
        await message.answer(
            "❌ Канал по этой ссылке не найден или бот не может его открыть.\n\n"
            "Проверьте ссылку и убедитесь, что канал существует."
        )
        return

    if chat.type != "channel":
        await message.answer("❌ Эта ссылка ведёт не на Telegram-канал.")
        return

    try:
        bot_member = await bot.get_chat_member(chat.id, bot.id)
    except Exception:
        await message.answer(
            "❌ Не получилось проверить права бота в канале.\n\n"
            "Добавьте бота администратором канала и попробуйте ещё раз."
        )
        return

    if bot_member.status not in {"administrator", "creator"}:
        await message.answer(
            "❌ Бот не является администратором этого канала.\n\n"
            "Сначала добавьте бота администратором, затем отправьте ссылку ещё раз."
        )
        return

    tasks = read_tasks()
    ids = [int(t["id"]) for t in tasks if str(t.get("id", "")).isdigit()]
    task = {
        "id": str(max(ids + [0]) + 1),
        "title": TASK_TITLE,
        "description": TASK_DESCRIPTION,
        "reward": REWARD,
        "url": f"https://t.me/{username}",
        "type": TASK_TYPE,
        "active": True,
        "channel_id": chat.id,
        "channel_username": username,
    }
    tasks.append(task)
    write_tasks(tasks)
    await state.clear()

    await message.answer(
        "✅ Задание добавлено!\n\n"
        f"📢 Канал: @{username}\n"
        "📝 Задание: Подписаться на канал\n"
        "⭐ Награда: 0,5\n\n"
        "Ссылка проверена, бот имеет права администратора и сможет проверять подписку.",
        reply_markup=admin_keyboard(),
    )


@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    if is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_keyboard())


@dp.callback_query(F.data == "admin:back")
async def admin_back(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("🔐 Админ-панель\n\nВыберите действие:", reply_markup=admin_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "admin:list")
async def admin_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    tasks = read_tasks()
    if not tasks:
        await callback.message.edit_text("📋 Заданий пока нет.", reply_markup=admin_keyboard())
        await callback.answer()
        return

    kb = InlineKeyboardBuilder()
    lines = ["📋 Задания:\n"]
    for task in tasks:
        username = task.get("channel_username", "")
        lines.append(f"#{task.get('id')} — @{username} — ⭐ 0,5")
        kb.button(text=f"🗑 Удалить #{task.get('id')}", callback_data=f"task:delete:{task.get('id')}")
    kb.button(text="◀️ Назад", callback_data="admin:back")
    kb.adjust(1)
    await callback.message.edit_text("\n".join(lines), reply_markup=kb.as_markup())
    await callback.answer()


@dp.callback_query(F.data.startswith("task:delete:"))
async def delete_task(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    task_id = callback.data.rsplit(":", 1)[-1]
    tasks = read_tasks()
    new_tasks = [t for t in tasks if str(t.get("id")) != task_id]
    if len(new_tasks) == len(tasks):
        await callback.answer("Задание не найдено", show_alert=True)
        return
    write_tasks(new_tasks)
    await callback.answer("Задание удалено")
    # Повторно показываем список.
    await admin_list(callback)


class AppHandler(BaseHTTPRequestHandler):
    def send_body(self, status, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def body_json(self):
        n = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/tasks":
            self.send_body(200, json.dumps(read_tasks(), ensure_ascii=False))
            return
        if path == "/admin":
            f = BASE_DIR / "admin.html"
            self.send_body(200, f.read_bytes(), "text/html; charset=utf-8") if f.exists() else self.send_body(404, "admin.html not found", "text/plain; charset=utf-8")
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
        types_map = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8"}
        self.send_body(200, target.read_bytes(), types_map.get(target.suffix, "application/octet-stream"))

    def do_POST(self):
        if urlparse(self.path).path != "/api/tasks":
            self.send_body(404, '{"error":"not_found"}')
            return
        if not admin_ok(self):
            self.send_body(401, '{"error":"unauthorized"}')
            return
        try:
            p = self.body_json()
            url = str(p.get("url", "")).strip()
            if not url:
                raise ValueError("url is required")
            # Веб-админка оставлена для совместимости, но тип задания фиксированный.
            tasks = read_tasks()
            ids = [int(t["id"]) for t in tasks if str(t.get("id", "")).isdigit()]
            task = {"id": str(max(ids + [0]) + 1), "title": TASK_TITLE, "description": TASK_DESCRIPTION, "reward": REWARD, "url": url, "type": TASK_TYPE, "active": True}
            tasks.append(task)
            write_tasks(tasks)
            self.send_body(201, json.dumps(task, ensure_ascii=False))
        except (ValueError, json.JSONDecodeError) as e:
            self.send_body(400, json.dumps({"error": str(e)}, ensure_ascii=False))

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/tasks/"):
            self.send_body(404, '{"error":"not_found"}')
            return
        if not admin_ok(self):
            self.send_body(401, '{"error":"unauthorized"}')
            return
        tid = path.rsplit("/", 1)[-1]
        tasks = read_tasks()
        new = [t for t in tasks if str(t.get("id")) != tid]
        if len(new) == len(tasks):
            self.send_body(404, '{"error":"task_not_found"}')
            return
        write_tasks(new)
        self.send_body(200, '{"ok":true}')

    def log_message(self, *args):
        pass


def run_http_server():
    port = int(os.getenv("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), AppHandler).serve_forever()


async def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")
    threading.Thread(target=run_http_server, daemon=True).start()
    bot = Bot(token=TOKEN)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
