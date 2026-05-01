import gspread
import os
from dotenv import load_dotenv

# --------

class Configuration:
    options = ["ATR Period", "EMA Span", "SMA Window", "RSI Period", "MACD Fast", "MACD Slow", "MACD Signal", "Stop Loss Multiplier"]
    
    def __init__(self, config_names = options, sheet_name = "Settings"):

        load_dotenv()
        credential_path = os.getenv("BOT_CREDENTIALS_PATH")
        gc = gspread.service_account(filename=credential_path)

        self.config_names = config_names
        self.sheet_name = sheet_name
        self.sheet = gc.open(self.sheet_name).sheet1 # Sheet object

        self.all = dict()
        self._get_all_config()

    def _get_config(self,name):
        cell_obj = self.sheet.find(name)
        return self.sheet.cell(cell_obj.row, cell_obj.col + 1).value, self.sheet.cell(cell_obj.row, cell_obj.col + 2).value
    
    def _get_all_config(self):

        for name in self.config_names:
            option_key, option_value = self._get_config(name)

            self.all[option_key] = option_value
    
    # Todo: Create a JSON that contains all the configs. It is to serve as a fallback option to the google sheet information