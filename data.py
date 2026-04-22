import yfinance as yf

def get_data(period = "1mo", interval = "30m"):

    BTC = yf.Ticker("BTC-USD")

    history = BTC.history(period,interval)
    
    return {
        "history": history,
        "close": history["Close"],
        "high": history["High"],
        "low": history["Low"],
        "currentPrice": BTC.fast_info['lastPrice'],
        "open": round(BTC.info['open'],0),
        "dayLow": round(BTC.info['dayLow'],0),
        "dayHigh": round(BTC.info['dayHigh'],0)
    }