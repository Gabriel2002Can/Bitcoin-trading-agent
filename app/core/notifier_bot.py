from telegram import Bot
import os
from dotenv import load_dotenv

class NotifierBot():
    
    def __init__(self):
        pass

    async def send_telegram_message(self, message='test'):

        load_dotenv()
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        bot = Bot(token=telegram_bot_token)
        await bot.send_message(chat_id = telegram_chat_id, text= message, parse_mode="Markdown")