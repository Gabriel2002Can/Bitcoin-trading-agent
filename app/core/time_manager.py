import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _parse_iso_datetime(value):
    if not value:
        return None

    try:
        normalized_value = str(value).replace("Z", "+00:00")
        parsed_value = datetime.fromisoformat(normalized_value)

        if parsed_value.tzinfo is None:
            return parsed_value.replace(tzinfo=timezone.utc)

        return parsed_value.astimezone(timezone.utc)
    except Exception:
        return None

class TimeManager:
    def __init__(self, config):
        self.dca_cooldown = self._load_dca_cooldown(config)
        self.tick_interval = self._load_tick_interval(config)
        self.last_dca, self.last_weekly_report, self.last_tick = self._load_last_data()

    def _time_info_path(self, file_name="time_info.json"):
        override_path = os.getenv("TIME_INFO_PATH")
        if override_path:
            return Path(override_path)

        state_dir = os.getenv("APP_STATE_DIR")
        if state_dir:
            return Path(state_dir) / file_name

        return Path(__file__).resolve().parent.parent / "data" / file_name

    def _load_last_data(self, file_name="time_info.json"):
        path = self._time_info_path(file_name)
        default_data = {
            "last_dca_trade": None,
            "last_weekly_report": None,
            "last_tick": None,
        }

        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as file:
                json.dump(default_data, file, indent=4)

            return None, None, None

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as file:
                json.dump(default_data, file, indent=4)

            return None, None, None

        data = {**default_data, **data}

        if data != default_data:
            with path.open("w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

        return (
            _parse_iso_datetime(data.get("last_dca_trade")),
            _parse_iso_datetime(data.get("last_weekly_report")),
            _parse_iso_datetime(data.get("last_tick")),
        )
    
    def _load_dca_cooldown(self, config):
        return timedelta(days=int(config.all["dca_time"]))

    def _load_tick_interval(self, config):
        raw_interval = None

        if hasattr(config, "all") and isinstance(config.all, dict):
            raw_interval = config.all.get("tick_interval", config.all.get("Tick Interval", 60))

        interval_minutes = self._parse_tick_interval_minutes(raw_interval)
        interval_minutes = max(1, min(interval_minutes, 60))

        return timedelta(minutes=interval_minutes)

    def _parse_tick_interval_minutes(self, raw_interval):
        if isinstance(raw_interval, timedelta):
            return max(1, int(raw_interval.total_seconds() / 60))

        if raw_interval is None:
            return 60

        if isinstance(raw_interval, (int, float)):
            return int(raw_interval)

        text = str(raw_interval).strip().lower()
        if not text:
            return 60

        if "hour" in text or text.endswith("h"):
            digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
            return int(float(digits or 1) * 60)

        if "min" in text or text.endswith("m"):
            digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
            return int(float(digits or 60))

        try:
            return int(float(text))
        except Exception:
            return 60
    
    def check_dca_cooldown(self) -> bool:
          
        if self.last_dca is None:
            return True

        return datetime.now(timezone.utc) - self.last_dca >= self.dca_cooldown

    def check_tick_cooldown(self) -> bool:

        if self.last_tick is None:
            return True

        return datetime.now(timezone.utc) - self.last_tick >= self.tick_interval

    def time_until_next_tick(self) -> timedelta:

        if self.last_tick is None:
            return timedelta(0)

        elapsed = datetime.now(timezone.utc) - self.last_tick
        remaining = self.tick_interval - elapsed

        return remaining if remaining > timedelta(0) else timedelta(0)

    def _update_time_field(self, field_name: str, file_name="time_info.json") -> None:

        path = self._time_info_path(file_name)
        path.parent.mkdir(parents=True, exist_ok=True)

        default_data = {
            "last_dca_trade": None,
            "last_weekly_report": None,
            "last_tick": None,
        }

        data = default_data

        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as file:
                    data = {**default_data, **json.load(file)}
            except Exception:
                data = default_data

        data[field_name] = datetime.now(timezone.utc).isoformat()

        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    
    def check_weekly_report_cooldown(self) -> bool:

        if self.last_weekly_report is None:
            return True

        return datetime.now(timezone.utc) - self.last_weekly_report >= timedelta(days=7)

    def update_last_dca_trade(self, file_name="time_info.json") -> None:
        self._update_time_field("last_dca_trade", file_name)
        self.last_dca = datetime.now(timezone.utc)
    
    def update_last_weekly_report(self, file_name="time_info.json"):
        self._update_time_field("last_weekly_report", file_name)
        self.last_weekly_report = datetime.now(timezone.utc)

    def update_last_tick(self, file_name="time_info.json"):
        self._update_time_field("last_tick", file_name)
        self.last_tick = datetime.now(timezone.utc)