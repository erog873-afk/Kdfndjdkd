import os

TOKEN = os.getenv("BOT_TOKEN", "")
APP_URL = os.getenv("APP_URL", "https://kdfndjdkd-2.onrender.com")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/your_channel")
CHAT_URL = os.getenv("CHAT_URL", "https://t.me/your_chat")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
