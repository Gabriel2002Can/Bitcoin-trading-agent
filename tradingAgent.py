from configuration import Configuration
from metrics import Metrics
from advisor import Advisor

class TradingAgent:
    """Uses metrics and the current configurations to evaluate which strategy should be used and its paramethers.
    """

    def __init__(self, configuration: Configuration, metrics: Metrics, model: Advisor):
        self.configuration = configuration
        self.metrics = metrics
        self.model = model

    def build_context(self):
        return {
            "strategy": self.configuration.all.get("Strategy", "dca"), # IMPLEMENT STRATEGY
            "current_price": self.metrics.entry_price, # REVIEW
            "stop_loss": self.metrics.get_latest_value("StopLoss"),
            "rsi": self.metrics.get_latest_value("RSI"),
            "ema": self.metrics.get_latest_value("EMA"),
            "sma": self.metrics.get_latest_value("SMA"),
            "macd": self.metrics.get_latest_value("MACD"),
            "macd_signal": self.metrics.get_latest_value("MACD_signal"),
            "macd_histogram": self.metrics.get_latest_value("MACD_histogram"),
            "atr": self.metrics.get_latest_value("ATR"),
        }

    def evaluate_strategies(self):
        context = self.build_context()
        opinion = self.model.analyze(context)

        base_dca = float(self.configuration.all.get("DCA Amount", 500)) # IMPLEMENT
        confidence = float(opinion["confidence"])

        if opinion["bias"] == "bullish":
            multiplier = 1.0 + confidence
        elif opinion["bias"] == "bearish":
            multiplier = max(0.0, 1.0 - confidence)
        else:
            multiplier = 1.0

        suggested_fiat = base_dca * multiplier
        suggested_btc = suggested_fiat / context["current_price"]

        return {
            "strategy": context["strategy"],
            "opinion": opinion,
            "suggested_fiat": suggested_fiat,
            "suggested_btc": suggested_btc,
            "context": context,
        }

    def execute_strategies(self, decision):
        if decision["context"]["current_price"] <= decision["context"]["stop_loss"]:
            decision["action"] = "hold"
            decision["reason"] = "stop_loss_triggered"
            decision["suggested_fiat"] = 0.0
            decision["suggested_btc"] = 0.0
        else:
            decision["action"] = "buy" if decision["suggested_fiat"] > 0 else "hold"
            decision["reason"] = "model_and_rules_agree"
        return decision

    def tick(self):
        decision = self.evaluate_strategies()
        final_decision = self.execute_strategies(decision)
        self.notify(final_decision)
        return final_decision