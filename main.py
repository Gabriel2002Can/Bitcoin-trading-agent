from metrics import Metrics
from data import get_data
from configuration import Configuration
from advisor import Advisor
from tradingAgent import TradingAgent

BTC = get_data()

config = Configuration()
metrics_info = Metrics(config=config, data=BTC["history"], entry_price=BTC["currentPrice"])
advisor = Advisor()
trading_agent = TradingAgent(config,metrics_info,advisor)

print("Bitcoin Price Now : ", BTC['currentPrice'])
print("Bitcoin Open : ", BTC['open'])
print("        Day     : ", BTC['dayLow'], "-", BTC['dayHigh'])

metrics_info.print_metric("StopLoss")
metrics_info.print_metrics(["RSI", "EMA", "SMA", "MACD", "MACD_histogram"])

print("\n"*5)

print(config.all)

print("\n"*5)

print(trading_agent.tick())

# print("\n"*5)

# print(trading_agent.model.analyze(trading_agent.build_context()))