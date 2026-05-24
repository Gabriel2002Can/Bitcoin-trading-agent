from app.core.metrics import Metrics
from app.data.finance_data import get_data
from app.data.configuration import Configuration
from app.core.advisor import Advisor
from app.core.tradingAgent import TradingAgent
from app.core.time_manager import TimeManager

BTC = get_data()

config = Configuration()
metrics_info = Metrics(config=config, data=BTC["history"], entry_price=BTC["currentPrice"])
advisor = Advisor()
trading_agent = TradingAgent(config,metrics_info,advisor)

time_manager = TimeManager(config)

print("Bitcoin Price Now : ", BTC['currentPrice'])
print("Bitcoin Open : ", BTC['open'])
print("        Day     : ", BTC['dayLow'], "-", BTC['dayHigh'])

metrics_info.print_metric("StopLoss")
metrics_info.print_metrics(["RSI", "EMA", "SMA", "MACD", "MACD_histogram"])

print("\n"*5)

print(config.all)

print("\n"*5)

print(f'Dollars: ${config.portfolio["portfolio_value"]} --- BTC: {config.portfolio["portfolio_btc"]}')

print(trading_agent.tick())

print("\n"*5)

print(f'Dollars: ${config.portfolio["portfolio_value"]} --- BTC: {config.portfolio["portfolio_btc"]}')