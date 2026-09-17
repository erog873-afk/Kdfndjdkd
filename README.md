# Telegram Bot for Render

## Files
- bot.py — Telegram bot
- requirements.txt — Python dependency
- .python-version — Python version

## Render
Use a Background Worker.

Build Command:
pip install -r requirements.txt

Start Command:
python bot.py

## Environment Variable
Add this variable in Render:

BOT_TOKEN=YOUR_BOT_TOKEN

Do not put the bot token directly into bot.py.

## Before deployment
Open bot.py and replace:
- APP_URL
- CHANNEL_URL
- CHAT_URL

with your real links.
