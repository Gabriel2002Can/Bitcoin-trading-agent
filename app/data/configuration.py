import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Union

import gspread
from dotenv import load_dotenv

Cells_value = Union[int, float, str, None]


class Configuration:
    """Stores information about the current configuration settings.

    The class prefers Google Sheets when credentials are available, but it caches
    the last successful snapshot to a JSON file and falls back to that snapshot if
    the sheet is stale or unavailable.
    """

    portfolio_options = ["Portfolio Value $", "Portfolio Value BTC"]

    # Contains all options presented in the google sheet
    options = [
        "Tick Interval",
        "ATR Period",
        "EMA Span",
        "SMA Window",
        "RSI Period",
        "MACD Fast",
        "MACD Slow",
        "MACD Signal",
        "Strategy",
        "Stop Loss Multiplier",
        "DCA Time",
        "DCA Amount",
        "Swing Buy Amount",
        "Swing Sell Amount",
    ]

    cache_refresh_interval = timedelta(minutes=30)
    cache_file_name = "config_cache.json"

    config_aliases = {
        "Tick Interval": "tick_interval",
        "ATR Period": "atr_period",
        "EMA Span": "ema_span",
        "SMA Window": "sma_window",
        "RSI Period": "rsi_period",
        "MACD Fast": "macd_fast",
        "MACD Slow": "macd_slow",
        "MACD Signal": "macd_signal_period",
        "Strategy": "strategy",
        "Stop Loss Multiplier": "stop_loss_multiplier",
        "DCA Time": "dca_time",
        "DCA Amount": "dca_amount",
        "Swing Buy Amount": "buy_amount",
        "Swing Sell Amount": "sell_amount",
        "Portfolio Value $": "portfolio_value",
        "Portfolio Value BTC": "portfolio_btc",
    }

    default_all = {
        "Tick Interval": "60",
        "ATR Period": "14",
        "EMA Span": "20",
        "SMA Window": "20",
        "RSI Period": "14",
        "MACD Fast": "12",
        "MACD Slow": "26",
        "MACD Signal": "9",
        "Strategy": "Hybrid",
        "Stop Loss Multiplier": "1.5",
        "DCA Time": "14",
        "DCA Amount": "500",
        "Swing Buy Amount": "250",
        "Swing Sell Amount": "10%",
    }

    default_portfolio = {
        "Portfolio Value $": "0",
        "Portfolio Value BTC": "0",
    }

    def __init__(self, config_names: list[str] = options, sheet_name: str = "Settings") -> None:
        load_dotenv()

        self.config_names = config_names
        self.sheet_name = sheet_name
        self.cache_path = self._resolve_cache_path()

        self.sheet = self._build_sheet_client()
        self.portfolio: dict[str, Any] = {}
        self.all: dict[str, Any] = {}

        self._load_configuration()

    def _resolve_cache_path(self) -> Path:
        cache_override = os.getenv("CONFIG_CACHE_PATH")
        if cache_override:
            return Path(cache_override)

        return Path(__file__).resolve().with_name(self.cache_file_name)

    def _build_sheet_client(self):
        credential_path = os.getenv("BOT_CREDENTIALS_PATH")

        if not credential_path or not os.path.exists(credential_path):
            return None

        try:
            gc = gspread.service_account(filename=credential_path)
            return gc.open(self.sheet_name).sheet1
        except Exception:
            return None

    def _cache_timestamp(self, payload: dict[str, Any]) -> datetime | None:
        raw_timestamp = payload.get("updated_at") or payload.get("cached_at")
        if not raw_timestamp:
            return None

        try:
            normalized_value = str(raw_timestamp).replace("Z", "+00:00")
            parsed_value = datetime.fromisoformat(normalized_value)

            if parsed_value.tzinfo is None:
                return parsed_value.replace(tzinfo=timezone.utc)

            return parsed_value.astimezone(timezone.utc)
        except Exception:
            return None

    def _read_cache(self) -> dict[str, Any] | None:
        if not self.cache_path.exists():
            return None

        try:
            with self.cache_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return None

    def _write_cache(self, payload: dict[str, Any]) -> None:
        cache_payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "all": payload.get("all", {}),
            "portfolio": payload.get("portfolio", {}),
        }

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("w", encoding="utf-8") as file:
            json.dump(cache_payload, file, indent=4)

    def _cache_is_fresh(self, payload: dict[str, Any]) -> bool:
        updated_at = self._cache_timestamp(payload)
        if updated_at is None:
            return False

        return datetime.now(timezone.utc) - updated_at < self.cache_refresh_interval

    def _normalize_config_keys(self, values: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(values)

        for source_key, alias_key in self.config_aliases.items():
            if source_key in normalized and alias_key not in normalized:
                normalized[alias_key] = normalized[source_key]
            if alias_key in normalized and source_key not in normalized:
                normalized[source_key] = normalized[alias_key]

        return normalized

    def _apply_payload(self, payload: dict[str, Any]) -> None:
        self.all = self._normalize_config_keys(dict(payload.get("all", {})))
        self.portfolio = self._normalize_config_keys(dict(payload.get("portfolio", {})))

    def _build_default_payload(self) -> dict[str, Any]:
        return {
            "all": dict(self.default_all),
            "portfolio": dict(self.default_portfolio),
        }

    def _get_config(self, name: str) -> tuple[str, Cells_value]:
        cell_obj = self.sheet.find(name)
        return self.sheet.cell(cell_obj.row, cell_obj.col + 1).value, self.sheet.cell(cell_obj.row, cell_obj.col + 2).value

    def _fetch_sheet_payload(self) -> dict[str, Any] | None:
        if self.sheet is None:
            return None

        payload = {"all": {}, "portfolio": {}}

        for option in self.portfolio_options:
            option_key, option_value = self._get_config(option)
            payload["portfolio"][option_key] = option_value

        for name in self.config_names:
            option_key, option_value = self._get_config(name)
            payload["all"][option_key] = option_value

        return payload

    def _load_configuration(self) -> None:
        cached_payload = self._read_cache()

        if cached_payload and self._cache_is_fresh(cached_payload):
            self._apply_payload(cached_payload)
            return

        sheet_payload = None

        try:
            sheet_payload = self._fetch_sheet_payload()
        except Exception:
            sheet_payload = None

        if sheet_payload:
            self._apply_payload(sheet_payload)
            self._write_cache(sheet_payload)
            return

        if cached_payload:
            self._apply_payload(cached_payload)
            return

        default_payload = self._build_default_payload()
        self._apply_payload(default_payload)
        self._write_cache(default_payload)

    # Value change in dollars, like 100 or -250; Value in BTC, total value, like 0.41 or -0.1 bitcoin
    def change_portfolio(self, diff_dollar=None, diff_btc=None) -> None:
        def _to_float(value: Any) -> float:
            try:
                return float(str(value).replace(",", "."))
            except Exception:
                return 0.0

        current_dollar = _to_float(
            self.portfolio.get("portfolio_value", self.portfolio.get("Portfolio Value $", 0))
        )
        current_btc = _to_float(
            self.portfolio.get("portfolio_btc", self.portfolio.get("Portfolio Value BTC", 0))
        )

        if diff_dollar is not None:
            current_dollar += float(diff_dollar)

        if diff_btc is not None:
            current_btc += float(diff_btc)

        try:
            if self.sheet is not None:
                cell_obj_dollar = self.sheet.find("Portfolio Value $")
                cell_obj_btc = self.sheet.find("Portfolio Value BTC")
                self.sheet.update_cell(cell_obj_dollar.row, cell_obj_dollar.col + 2, current_dollar)
                self.sheet.update_cell(cell_obj_btc.row, cell_obj_btc.col + 2, current_btc)

                self._load_configuration()
            else:
                raise RuntimeError("sheet_unavailable")
        except Exception:
            self.portfolio["portfolio_value"] = str(current_dollar)
            self.portfolio["portfolio_btc"] = str(current_btc)
            self.portfolio["Portfolio Value $"] = str(current_dollar)
            self.portfolio["Portfolio Value BTC"] = str(current_btc)

        self._write_cache({"all": self.all, "portfolio": self.portfolio})
