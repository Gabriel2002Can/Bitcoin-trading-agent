import json
import os
from datetime import datetime, timedelta, timezone

class TimeManager:
    def __init__(self, config):
        self.dca_cooldown = self._load_dca_cooldown(config)
        self.last_dca, self.last_weekly_report = self._load_last_data()

    def _load_last_data(self, file_name="time_info.json"):

        path = f"app/data/{file_name}"

        if not os.path.exists(path):

            default_data = {
                "last_dca_trade": None,
                "last_weekly_report": None
            }

            with open(path, "w") as file:
                json.dump(default_data, file, indent=4)

            return None, None

        with open(path, "r") as file:
            data = json.load(file)

            last_trade = data.get("last_dca_trade")
            last_weekly_report = data.get("last_weekly_report")

            parsed_trade = (
                datetime.fromisoformat(last_trade)
                if last_trade
                else None
            )

            parsed_report = (
                datetime.fromisoformat(last_weekly_report)
                if last_weekly_report
                else None
            )

            return parsed_trade, parsed_report
    
    def _load_dca_cooldown(self, config):
        return timedelta(days=int(config.all["dca_time"]))

    # TODO: Check how to implement this part
    # def _load_tick_interval(self, config):
    #     return timedelta(minutes=int(config.all["Tick Interval"]))
    
    def check_dca_cooldown(self) -> bool:
          
        if self.last_dca is None:
            return True

        return datetime.now(timezone.utc) - self.last_dca >= self.dca_cooldown
    
    def check_weekly_report_cooldown(self) -> bool:

        if self.last_weekly_report is None:
            return True

        return datetime.now(timezone.utc) - self.last_weekly_report >= timedelta(days=7)

    def update_last_dca_trade(self, file_name="time_info.json") -> None:

        path = f"app/data/{file_name}"

        with open(path, "r") as file:
            data = json.load(file)

        data["last_dca_trade"] = (
            datetime.now(timezone.utc).isoformat()
        )

        with open(path, "w") as file:
            json.dump(data, file, indent=4)

        self.last_dca = datetime.now(timezone.utc)
    
    def update_last_weekly_report(self, file_name="time_info.json"):

        path = f"app/data/{file_name}"

        config_data = {
                "last_weekly_report": datetime.now(timezone.utc).isoformat()
            }

        with open(path, "w") as file:
            json.dump(config_data, file, indent=4)

        return None