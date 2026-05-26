import time

from app.core.advisor import Advisor
from app.core.metrics import Metrics
from app.core.time_manager import TimeManager
from app.core.trading_agent import TradingAgent
from app.data.configuration import Configuration
from app.data.finance_data import get_data

def build_agent():
    btc_data = get_data()
    config = Configuration()
    metrics = Metrics(config=config, data=btc_data["history"], entry_price=btc_data["currentPrice"])
    advisor = Advisor()

    return TradingAgent(config, metrics, advisor), btc_data

def run_forever(polling_pause_seconds: int = 60) -> None:
    while True:
        try:
            probe_config = Configuration()
            time_manager = TimeManager(probe_config)

            sleep_seconds = int(time_manager.time_until_next_tick().total_seconds())
            if sleep_seconds > 0:
                time.sleep(max(1, sleep_seconds))
                continue

            agent, btc_data = build_agent()
            decision = agent.tick()

            print(decision)
            print({
                "currentPrice": btc_data.get("currentPrice"),
                "open": btc_data.get("open"),
                "dayLow": btc_data.get("dayLow"),
                "dayHigh": btc_data.get("dayHigh"),
            })
        except KeyboardInterrupt:
            raise
        except Exception as error:
            print(f"runner_error: {error}")
            time.sleep(max(1, polling_pause_seconds))


if __name__ == "__main__":
    run_forever()