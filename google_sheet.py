import gspread
import os
from dotenv import load_dotenv

load_dotenv()
credential_path = os.getenv("BOT_CREDENTIALS_PATH")

gc = gspread.service_account(filename=credential_path)

# Sheet object
sh = gc.open("Settings")

print(sh.sheet1.get('A1'))