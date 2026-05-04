from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

MetricValue = Union[pd.Series, float]

class Metrics:
    """Stores information about the current metrics gathered from the source.
    """

    def __init__(
        self,
        config: Optional[Union[Dict[str, Any], Any]] = None,
        data: Optional[pd.DataFrame] = None,
        entry_price: Optional[float] = None,
    ) -> None:
        # defaults
        defaults = {
            "atr_period": 14,
            "ema_span": 20,
            "sma_window": 20,
            "rsi_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "k": 2.0
        }

        # read config values (support multiple potential key names)
        self.atr_period = self._get_config_value(config, ["atr_period", "ATR Period"], int, defaults["atr_period"])
        self.ema_span = self._get_config_value(config, ["ema_span", "EMA Span"], int, defaults["ema_span"])
        self.sma_window = self._get_config_value(config, ["sma_window", "SMA Window"], int, defaults["sma_window"])
        self.rsi_period = self._get_config_value(config, ["rsi_period", "RSI Period"], int, defaults["rsi_period"])
        self.macd_fast = self._get_config_value(config, ["macd_fast", "MACD Fast"], int, defaults["macd_fast"])
        self.macd_slow = self._get_config_value(config, ["macd_slow", "MACD Slow"], int, defaults["macd_slow"])
        self.macd_signal = self._get_config_value(config, ["macd_signal", "MACD Signal"], int, defaults["macd_signal"])
        self.k = self._get_config_value(config, ["k", "Stop Loss Multiplier", "stop_loss_multiplier"], float, defaults["k"])

        self.data = data
        self.entry_price = entry_price
        self.metrics: Dict[str, MetricValue] = {}

        if data is not None and entry_price is not None:
            self.calculate_metrics(data, entry_price)

    def _get_config_value(self, config: Optional[Union[Dict[str, Any], Any]],
                          names: List[str],
                          cast_type: Any,
                          default: Any) -> Any:

        if config is None:
            return default

        # support Configuration-like object with `.all` attribute
        cfg: Dict[str, Any]
        if hasattr(config, "all") and isinstance(getattr(config, "all"), dict):
            cfg = config.all  # type: ignore[arg-type]
        elif isinstance(config, dict):
            cfg = config
        else:
            cfg = {k: getattr(config, k, None) for k in dir(config) if not k.startswith("__")}

        for name in names:
            if name in cfg and cfg[name] is not None:
                val = cfg[name]
                try:
                    return cast_type(val)
                except Exception:
                    try:
                        return cast_type(str(val).strip())
                    except Exception:
                        return default

        # try normalized keys (lower + underscores)
        for name in names:
            norm = name.lower().replace(" ", "_")
            if norm in cfg and cfg[norm] is not None:
                val = cfg[norm]
                try:
                    return cast_type(val)
                except Exception:
                    try:
                        return cast_type(str(val).strip())
                    except Exception:
                        return default

        return default

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1 / self.atr_period, adjust=False).mean()

    def _calculate_stop_loss(self, entry_price: float, atr_value: float, position: str = "long") -> float:
        if position == "long":
            return entry_price - (self.k * atr_value)
        return entry_price + (self.k * atr_value)

    def _calculate_ema(self, close: pd.Series) -> pd.Series:
        return close.ewm(span=self.ema_span, adjust=False).mean()

    def _calculate_sma(self, close: pd.Series) -> pd.Series:
        return close.rolling(window=self.sma_window, min_periods=self.sma_window).mean()

    def _calculate_rsi(self, close: pd.Series) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1 / self.rsi_period, min_periods=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / self.rsi_period, min_periods=self.rsi_period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(100)

    def _calculate_macd(self, close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = close.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def calculate_metrics(self, data: pd.DataFrame, entry_price: float) -> Dict[str, MetricValue]:
        self.data = data
        self.entry_price = entry_price

        close = data["Close"]
        high = data["High"]
        low = data["Low"]

        atr = self._calculate_atr(high, low, close)
        ema = self._calculate_ema(close)
        sma = self._calculate_sma(close)
        rsi = self._calculate_rsi(close)
        macd_line, signal_line, macd_histogram = self._calculate_macd(close)

        latest_atr = float(atr.iloc[-1])
        stop_loss = self._calculate_stop_loss(entry_price, latest_atr)

        self.metrics = {
            "ATR": atr,
            "StopLoss": stop_loss,
            "EMA": ema,
            "RSI": rsi,
            "MACD": macd_line,
            "MACD_signal": signal_line,
            "MACD_histogram": macd_histogram,
            "SMA": sma,
        }
        return self.metrics

    def get_latest_value(self, metric_name: str) -> float:
        metric = self.metrics[metric_name]
        if isinstance(metric, pd.Series):
            return float(metric.iloc[-1])
        return float(metric)

    def print_metric(self, metric_name: str) -> None:
        print(f"{metric_name}: {self.get_latest_value(metric_name)}")

    def print_metrics(self, metric_names: Optional[List[str]] = None) -> None:
        names = metric_names if metric_names is not None else list(self.metrics.keys())
        for metric_name in names:
            self.print_metric(metric_name)