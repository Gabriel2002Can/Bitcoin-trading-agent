import time
import asyncio

from app.core.advisor import Advisor
from app.core.metrics import Metrics
from app.core.helper_functions import generate_weekly_report
from app.core.recorder import Recorder
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

            if agent.time_manager.check_weekly_report_cooldown():
                weekly_trades = Recorder().load_weekly_trades()
                weekly_report = generate_weekly_report(weekly_trades)
                asyncio.run(agent.notifier.send_gmail_email(weekly_report, subject="Weekly Trading Report"))
                agent.time_manager.update_last_weekly_report()

            print("\n"*3)
            print(decision)
            print("\n"*3)
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