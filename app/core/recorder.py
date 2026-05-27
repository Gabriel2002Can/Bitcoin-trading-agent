import json
from datetime import datetime, timedelta, timezone
import glob
class Recorder:

    def __init__(self, folder="logs/"):
        self.folder = folder

    def _log_files(self):
        return sorted(glob.glob(f"{self.folder}*.jsonl"))

    def _parse_trade(self, trade, source_file=None):
        if not isinstance(trade, dict):
            return None

        parsed_trade = dict(trade)
        parsed_trade.setdefault("source_file", source_file)
        return parsed_trade

    def save_trade(self, trade):

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        path = f"{self.folder}{today}.jsonl"

        trade["timestamp"] = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )

        import os
        os.makedirs(self.folder, exist_ok=True)

        with open(path, "a", encoding="utf-8") as file:

            file.write(json.dumps(trade) + "\n")

    def load_all_trades(self):

        trades = []

        for file_path in self._log_files():

            source_file = file_path.split("/")[-1].split("\\")[-1]

            with open(file_path, "r", encoding="utf-8") as file:

                for line in file:

                    raw_line = line.strip()

                    if not raw_line:
                        continue

                    try:
                        trade = json.loads(raw_line)
                    except Exception:
                        continue

                    parsed_trade = self._parse_trade(trade, source_file=source_file)
                    if parsed_trade is not None:
                        trades.append(parsed_trade)

        return trades

    def load_trades_since(self, since_datetime):

        trades = []

        for trade in self.load_all_trades():

            timestamp = trade.get("timestamp")
            if not timestamp:
                continue

            try:
                trade_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                if trade_time >= since_datetime:
                    trades.append(trade)

            except Exception:
                continue

        return trades

    def load_trades_between(self, start_datetime, end_datetime):

        trades = []

        for trade in self.load_all_trades():

            timestamp = trade.get("timestamp")
            if not timestamp:
                continue

            try:
                trade_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                if start_datetime <= trade_time <= end_datetime:
                    trades.append(trade)

            except Exception:
                continue

        return trades

    def load_today_trades(self):

        start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return self.load_trades_since(start_of_day)

    def load_weekly_trades(self):

        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        return self.load_trades_since(one_week_ago)