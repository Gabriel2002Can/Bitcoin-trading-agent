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
        # compute previous close and percent change where possible
        prev_close = None
        price_change_pct = 0.0
        try:
            if self.metrics.data is not None and "Close" in self.metrics.data.columns and len(self.metrics.data["Close"]) >= 2:
                prev_close = float(self.metrics.data["Close"].iloc[-2])
                price_change_pct = (self.metrics.entry_price - prev_close) / prev_close
        except Exception:
            prev_close = None
            price_change_pct = 0.0

        # parse DCA trigger from config (keeps as raw for model visibility too)
        raw_dca = self.configuration.all.get("DCA Trigger", None)

        return {
            "strategy": self.configuration.all.get("strategy", "Long Term"),
            "current_price": self.metrics.entry_price,
            "previous_close": prev_close,
            "price_change_pct": price_change_pct,
            "dca_trigger_raw": raw_dca,
            "stop_loss": self.metrics.get_latest_value("StopLoss"),
            "rsi": self.metrics.get_latest_value("RSI"),
            "ema": self.metrics.get_latest_value("EMA"),
            "sma": self.metrics.get_latest_value("SMA"),
            "macd": self.metrics.get_latest_value("MACD"),
            "dca_amount": self.configuration.all.get("DCA Amount", 500),
            "macd_signal": self.metrics.get_latest_value("MACD_signal"),
            "macd_histogram": self.metrics.get_latest_value("MACD_histogram"),
            "atr": self.metrics.get_latest_value("ATR"),
        }

    def evaluate_strategies(self):
        context = self.build_context()
        opinion = self.model.analyze(context)

        # Bug Fixed
        # normalize opinion: the model may return a ChatCompletionMessage-like
        # object whose `content` is a JSON string. Parse it into a dict.
        try:
            import json

            if isinstance(opinion, dict):
                pass
            else:
                content = None
                if hasattr(opinion, "content"):
                    content = opinion.content
                elif isinstance(opinion, str):
                    content = opinion
                elif hasattr(opinion, "message") and hasattr(opinion.message, "content"):
                    content = opinion.message.content

                if content:
                    parsed = json.loads(content)
                    opinion = parsed
        except Exception:
            pass

        # parse DCA trigger into a fraction ('3%' -> 0.03)
        def _parse_percent(val, default_pct=0.03):
            try:
                if val is None:
                    return default_pct
                s = str(val).strip()
                if s.endswith("%"):
                    s = s[:-1]
                num = float(s)
                if num > 1:  # treat as percent like 3 -> 3%
                    return num / 100.0
                return num
            except Exception:
                return default_pct

        dca_trigger_pct = _parse_percent(context.get("dca_trigger_raw"))

        dca_triggered = False

        total_score = 0

        # compute price drop pct (negative when price fell)
        price_change = context.get("price_change_pct", 0.0)

        strategy = str(context.get("strategy", self.configuration.all.get("Strategy", "Long Term"))).strip().lower()

        # Strategy selection is authoritative and determines rule set

        # TODO: change logic to accept sells as well

        # Long Term: prioritize DCA trigger —> buy when price dropped at least the configured percent
        if strategy == "long term" or strategy == "long_term" or strategy == "long-term":
            if price_change <= -dca_trigger_pct:
                dca_triggered = True

        # Swing Trade: follow the model opinion primarily
        elif strategy == "swing trade" or strategy == "swing_trade" or strategy == "swing-trade":

            rsi_score = (50 - context.get("rsi",50)) / 50 # Value between = 1 - 0

            macd_score = max( -1, min(1, context.get("macd_histogram", 0) / 100)) # Value between = 1 - 0

            sma_score = max( -1, min(1, context.get("current_price", 0) - context.get("sma", 1) / context.get("sma", 1))) # Value between = 1 - 0

            # sma score should impact less the score that the other metrics
            total_score = (rsi_score * (0.4)) + (macd_score * (0.4)) + (sma_score * (0.2)) # Value between = 1 - 0

        # Hybrid or unknown: combine DCA trigger and model
        else:
            if price_change <= -dca_trigger_pct:
                dca_triggered = True
            else:
                rsi_score = (50 - context.get("rsi",50)) / 50 # Value between = 1 - 0

                macd_score = max( -1, min(1, context.get("macd_histogram", 0) / 100)) # Value between = 1 - 0

                sma_score = max( -1, min(1, context.get("current_price", 0) - context.get("sma", 1) / context.get("sma", 1))) # Value between = 1 - 0

                # sma score should impact less the score that the other metrics
                total_score = (rsi_score * (0.4)) + (macd_score * (0.4)) + (sma_score * (0.2)) # Value between = 1 - 0

        return {
            "strategy": context["strategy"],
            "opinion": opinion, # Model's opinion
            "dca_triggered": dca_triggered, # If DCA was triggered
            "dca_trigger_pct": dca_trigger_pct, # The drop percentage it drops
            "total_score": total_score, # The total scored throught all metrics
            "context": context, # Context dict
        }

    def execute_strategies(self, decision):
        current = decision["context"]["current_price"]
        stop_loss = decision["context"]["stop_loss"]

        model_opinion = decision["opinion"]

        multiplier = 1 if model_opinion["bias"] == "bullish" else 0 if model_opinion["bias"] == "neutral" else -1
        model_score = model_opinion["confidence"] * multiplier

        # Get both model suggestion and numeric
        final_score = (model_score * 0.35) + (decision["context"]["numeric_decision"] * 0.65)

        final_decision = final_score > 0.5 # Alter to constant (sensibility)?

        # If stop loss triggered SELL
        if current <= stop_loss:
            decision["action"] = "sell"
            decision["reason"] = "stop_loss_triggered"
            decision["value"] = 0.0 # TODO: needs to sell correct amount based on final_decision
            return decision

        # Opportunistic SELL
        if final_score < -0.5:
            decision["action"] = "sell"
            decision["reason"] = "opportunistic_sell"
            decision["value"] = 0.0 # TODO: same as previous TODO

        # If DCA TRIGGERED
        if decision.get("dca_triggered", False):
            decision["action"] = "buy"
            decision["reason"] = "dca_triggered"
            decision["value"] = decision["context"]["dca_amount"]
            return decision
        
        # Opportunistic BUY
        if final_score > 0.5:
            decision["action"] = "buy"
            decision["reason"] = "opportunistic_buy"
            decision["value"] = 0.0 # TODO: same as previous TODO
        
        # HOLD if not ideal
        decision["action"] = "hold"
        decision["reason"] = "neutral_market"

        # decision:
        # "action": X
        # "reason": Y
        # "value": Z
        return decision

    def tick(self):
        decision = self.evaluate_strategies()
        final_decision = self.execute_strategies(decision)
        #self.notify(final_decision)
        return final_decision