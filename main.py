import yfinance as yf
from calculations import calculate_metrics

def get_data():

    return yf.Ticker("BTC-USD")

BTC = get_data() 

print("Bitcoin Open : ", round(BTC.info['open'],0))
print("        Day     : ", round(BTC.info['dayLow'], 0), "-", round(BTC.info['dayHigh'], 0))
print("        52 Week : ", round(BTC.info['fiftyTwoWeekLow'], 0), "-", round(BTC.info['fiftyTwoWeekHigh'], 0))

CurrentPrice = BTC.fast_info['lastPrice']

historic_data = BTC.history(period="1mo", interval="30m")

close = historic_data["Close"]
high = historic_data["High"]
low = historic_data["Low"]

metrics = calculate_metrics(historic_data, entry_price=CurrentPrice, k=2.0)
print("Latest stop loss:", metrics["StopLoss"])
print("Latest RSI:", metrics["RSI"].iloc[-1])
print("Latest EMA:", metrics["EMA"].iloc[-1])
print("Latest SMA:", metrics["SMA"].iloc[-1])