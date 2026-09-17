import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder


TOKEN = os.getenv("8762994126:AAEPxOKqTNMj3BHH8LUC7EzjhB2Iio06zKQ")

# Replace these with your real links.
APP_URL = "https://kdfndjdkd-2.onrender.com"
CHANNEL_URL = "https://t.me/your_channel"
CHAT_URL = "https://t.me/your_chat"

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: types.Message):
    keyboard = InlineKeyboardBuilder()

    # First row: one button
    keyboard.row(
        types.InlineKeyboardButton(
            text="⭐ Открыть приложение",
            web_app=types.WebAppInfo(url=APP_URL)
        )
    )

    # Second row: two buttons
    keyboard.row(
        types.InlineKeyboardButton(
            text="Подписаться на канал",
            url=CHANNEL_URL
        ),
        types.InlineKeyboardButton(
            text="Подписаться на чат",
            url=CHAT_URL
        )
    )

    await message.answer(
        "⭐ Зарабатывайте звёзды и NFT-подарки, "
        "выполняя очень простые задания и играя в игры 👇",
        reply_markup=keyboard.as_markup()
    )


async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    bot = Bot(TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
