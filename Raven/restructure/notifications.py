from telegram import Bot


async def send_telegram_message(message):
    bot_token = "7395837585:AAFDBNfMIzpMqshb1fIX8U5cIyG0O5XwXc0"
    chat_id = "1353536439"
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)