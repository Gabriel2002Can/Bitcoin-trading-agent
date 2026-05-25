from app.core.metrics import Metrics
from app.data.finance_data import get_data
from app.data.configuration import Configuration
from app.core.advisor import Advisor
from app.core.trading_agent import TradingAgent

BTC = get_data()

config = Configuration()
metrics_info = Metrics(config=config, data=BTC["history"], entry_price=BTC["currentPrice"])
advisor = Advisor()
trading_agent = TradingAgent(config,metrics_info,advisor)

print(config.all)

print("\n"*5)

print(f'Dollars: ${config.portfolio["portfolio_value"]} --- BTC: {config.portfolio["portfolio_btc"].replace(",",".")}')

print(trading_agent.tick())

print("\n"*5)

print(f'Dollars: ${config.portfolio["portfolio_value"]} --- BTC: {config.portfolio["portfolio_btc"].replace(",",".")}')