from metrics import Metrics
from data import get_data
from configuration import Configuration

BTC = get_data()

metrics_info = Metrics(k=2.0, data=BTC["history"], entry_price=BTC["currentPrice"])

print("Bitcoin Price Now : ", BTC['currentPrice'])
print("Bitcoin Open : ", BTC['open'])
print("        Day     : ", BTC['dayLow'], "-", BTC['dayHigh'])

metrics_info.print_metric("StopLoss")
metrics_info.print_metrics(["RSI", "EMA", "SMA"])

config = Configuration()

print("\n"*5)

print(config.all)