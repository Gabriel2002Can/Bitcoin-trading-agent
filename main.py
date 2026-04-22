from calculations import calculate_metrics
from data import get_data

BTC = get_data()

metrics = calculate_metrics(BTC['history'], entry_price=BTC['currentPrice'], k=2.0)

print("Bitcoin Price Now : ", BTC['currentPrice'])
print("Bitcoin Open : ", BTC['open'])
print("        Day     : ", BTC['dayLow'], "-", BTC['dayHigh'])

print("Latest stop loss:", metrics["StopLoss"])
print("Latest RSI:", metrics["RSI"].iloc[-1])
print("Latest EMA:", metrics["EMA"].iloc[-1])
print("Latest SMA:", metrics["SMA"].iloc[-1])