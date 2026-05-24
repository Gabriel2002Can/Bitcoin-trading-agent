import gspread
import os
from dotenv import load_dotenv
from typing import Union

Cells_value = Union[int, float]

class Configuration:
    """ Stores information about the current configurations settings, gathered from google sheets
    """

    portfolio_options = ["Portfolio Value $", "Portfolio Value BTC"]

    # Contains all options presented in the google sheet
    options = ["Tick Interval" , "ATR Period", "EMA Span", "SMA Window", "RSI Period", "MACD Fast", "MACD Slow", "MACD Signal", "Strategy", "Stop Loss Multiplier", "DCA Time", "DCA Amount", "DCA Trigger", "Swing Buy Amount","Swing Sell Amount"]
    
    def __init__(self, config_names: list[str] = options, sheet_name: str = "Settings") -> None:

        load_dotenv()
        credential_path = os.getenv("BOT_CREDENTIALS_PATH")
        gc = gspread.service_account(filename=credential_path)

        self.config_names = config_names
        self.sheet_name = sheet_name
        self.sheet = gc.open(self.sheet_name).sheet1 # Sheet object

        self.portfolio = {}
        self._populate_portfolio()

        self.all = dict()
        self._get_all_config()

    def _get_config(self, name: str) -> tuple[str, Cells_value]:
        cell_obj = self.sheet.find(name)
        return self.sheet.cell(cell_obj.row, cell_obj.col + 1).value, self.sheet.cell(cell_obj.row, cell_obj.col + 2).value

    def _get_all_config(self) -> None:

        for name in self.config_names:
            option_key, option_value = self._get_config(name)

            self.all[option_key] = option_value
    
    def _populate_portfolio(self, options: list[str] = portfolio_options) -> None:

        for option in options:
            option_key, option_value = self._get_config(option)

            self.portfolio[option_key] = option_value

    # Value change in dollars, like 100 or - 250; Value in BTC, total value, like 0.41 or -0.1 bitcoin
    def change_portfolio(self, diff_dollar = None, diff_btc = None) -> None:
        
        if diff_dollar:
            cell_obj_dollar = self.sheet.find("Portfolio Value $")
            value = float(self.portfolio["portfolio_value"]) + float(diff_dollar)

            self.sheet.update_cell(cell_obj_dollar.row, cell_obj_dollar.col + 2, value)
        
        if diff_btc:
            cell_obj_btc = self.sheet.find("Portfolio Value BTC")
            value = float(self.portfolio["portfolio_btc"]) + float(diff_btc)

            self.sheet.update_cell(cell_obj_btc.row, cell_obj_btc.col + 2, value)
        
        self._populate_portfolio()

    # TODO: Create a JSON that contains all the configs. It will serve as a fallback option to the google sheet information