import pandas as pd

def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def calculate_stop_loss(entry_price, atr_value, k=2.0, position="long"):
    if position == "long":
        return entry_price - (k * atr_value)
    else:
        return entry_price + (k * atr_value)

def calculate_ema(close, span=20):
    return close.ewm(span=span, adjust=False).mean()

def calculate_sma(close, window=20):
    return close.rolling(window=window, min_periods=window).mean()

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100)

def calculate_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_metrics(data, entry_price, atr_period=14, ema_span=20, sma_window=20, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9, k=2.0):
    close = data["Close"]
    high = data["High"]
    low = data["Low"]

    atr = calculate_atr(high, low, close, period=atr_period)
    ema = calculate_ema(close, span=ema_span)
    sma = calculate_sma(close, window=sma_window)
    rsi = calculate_rsi(close, period=rsi_period)
    macd_line, signal_line, macd_histogram = calculate_macd(
        close, fast=macd_fast, slow=macd_slow, signal=macd_signal
    )

    latest_atr = atr.iloc[-1]
    stop_loss = calculate_stop_loss(entry_price, latest_atr, k=k)

    return {
        "ATR": atr,
        "StopLoss": stop_loss,
        "EMA": ema,
        "RSI": rsi,
        "MACD": macd_line,
        "MACD_signal": signal_line,
        "MACD_histogram": macd_histogram,
        "SMA": sma,
    }