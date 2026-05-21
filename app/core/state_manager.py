import json
import os
from datetime import datetime, timedelta, timezone

class StateManager:
    def __init__(self, config):
        self.dca_cooldown = self.load_dca_cooldown(config)
        self.last_dca = self.load_last_dca_trade()

    def _load_last_dca_trade(self, file_name="dca_info.json"):

        path = f"app/data/{file_name}"

        if not os.path.exists(path):

            default_data = {
                "last_dca_trade": None
            }

            with open(path, "w") as file:
                json.dump(default_data, file, indent=4)

            return None

        with open(path, "r") as file:
            data = json.load(file)

            last_trade = data.get("last_dca_trade")

            if last_trade is None:
                return None

            return datetime.fromisoformat(last_trade)
    
    def _load_dca_cooldown(self, config):
        return timedelta(days=int(config.all["DCA Time"]))
    
    def _load_tick_interval(self, config):
        return 
    
    def _check_cooldown(self):
         
        if self.last_dca is None:
            return True

        return datetime.now(timezone.utc) - self.last_dca >= self.dca_cooldown