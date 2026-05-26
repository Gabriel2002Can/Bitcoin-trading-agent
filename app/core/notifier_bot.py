from telegram import Bot
import smtplib
from email.message import EmailMessage
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
    
    async def send_gmail_email(self, message='test', subject='Trading Report'):

        load_dotenv()
        gmail_address = os.getenv("GMAIL_ADDRESS")
        gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
        to_email = os.getenv("GMAIL_TO_EMAIL")

        if not gmail_address or not gmail_app_password or not to_email:
            print("Gmail credentials are not configured; skipping email report.")
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = gmail_address
        msg["To"] = to_email
        msg.set_content(message)

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(gmail_address, gmail_app_password)
            smtp.send_message(msg)
            print(f"Email sent to {to_email}.")