import json
from datetime import datetime, timedelta, timezone
import glob
class Recorder:

    def __init__(self, folder="logs/"):
        self.folder = folder

    def save_trade(self, trade):

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        path = f"{self.folder}{today}.jsonl"

        trade["timestamp"] = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )

        with open(path, "a", encoding="utf-8") as file:

            file.write(json.dumps(trade) + "\n")

    def load_weekly_trades(self):

        files = glob.glob(f"{self.folder}*.jsonl")

        trades = []

        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        for file_path in files:

            with open(file_path, "r", encoding="utf-8") as file:

                for line in file:

                    trade = json.loads(line)

                    timestamp = trade.get("timestamp")

                    if not timestamp:
                        continue

                    try:
                        trade_time = datetime.fromisoformat(
                            timestamp.replace("Z", "+00:00")
                        )

                        if trade_time >= one_week_ago:
                            trades.append(trade)

                    except Exception:
                        continue

        return trades