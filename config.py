import os

# НЕ храни токен в открытом коде. На Render задай переменную TOKEN.
TOKEN = os.getenv("TOKEN", "")

APP_URL = os.getenv("APP_URL", "https://kdfndjdkd-2.onrender.com")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/your_channel")
CHAT_URL = os.getenv("CHAT_URL", "https://t.me/your_chat")

# Telegram ID администратора. На Render: ADMIN_ID=123456789
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# База заданий. На Render можно указать /var/data/tasks.db, если подключишь Persistent Disk.
DATABASE_PATH = os.getenv("DATABASE_PATH", "tasks.db")

# HTTP-сервер Mini App/API
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "10000"))
