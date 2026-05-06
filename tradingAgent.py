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
            "strategy": self.configuration.all.get("Strategy", "Long Term"),
            "current_price": self.metrics.entry_price,
            "previous_close": prev_close,
            "price_change_pct": price_change_pct,
            "dca_trigger_raw": raw_dca,
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
        base_dca = float(self.configuration.all.get("DCA Amount", 500))

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

        suggested_fiat = 0.0
        suggested_btc = 0.0
        dca_triggered = False

        # compute price drop pct (negative when price fell)
        price_change = context.get("price_change_pct", 0.0)

        strategy = str(context.get("strategy", self.configuration.all.get("Strategy", "Long Term"))).strip().lower()

        # Strategy selection is authoritative and determines rule set

        # Long Term: prioritize DCA trigger —> buy when price dropped at least the configured percent
        if strategy == "long term" or strategy == "long_term" or strategy == "long-term":
            if price_change <= -dca_trigger_pct:
                suggested_fiat = base_dca
                dca_triggered = True

        # Swing Trade: follow the model opinion primarily
        elif strategy == "swing trade" or strategy == "swing_trade" or strategy == "swing-trade":
            confidence = float(opinion.get("confidence", 0.0))
            if opinion.get("bias") == "bullish":
                multiplier = 1.0 + confidence
            elif opinion.get("bias") == "bearish":
                multiplier = max(0.0, 1.0 - confidence)
            else:
                multiplier = 1.0
            suggested_fiat = base_dca * multiplier

        # Hybrid or unknown: combine DCA trigger and model
        else:
            if price_change <= -dca_trigger_pct:
                suggested_fiat = base_dca
                dca_triggered = True
            else:
                confidence = float(opinion.get("confidence", 0.0))
                if opinion.get("bias") == "bullish":
                    multiplier = 1.0 + confidence
                elif opinion.get("bias") == "bearish":
                    multiplier = max(0.0, 1.0 - confidence)
                else:
                    multiplier = 1.0
                suggested_fiat = base_dca * multiplier

        # Compute BTC amount
        if context["current_price"] and suggested_fiat > 0:
            suggested_btc = suggested_fiat / context["current_price"]

        return {
            "strategy": context["strategy"],
            "opinion": opinion,
            "suggested_fiat": suggested_fiat,
            "suggested_btc": suggested_btc,
            "dca_triggered": dca_triggered,
            "dca_trigger_pct": dca_trigger_pct,
            "context": context,
        }

    def execute_strategies(self, decision):
        current = decision["context"]["current_price"]
        stop_loss = decision["context"]["stop_loss"]

        # If DCA triggered, allow buy even if below stop loss (DCA overrides stop-loss hold)
        if decision.get("dca_triggered", False) and decision.get("suggested_fiat", 0) > 0:
            decision["action"] = "buy"
            decision["reason"] = "dca_triggered_overrode_rules"
            return decision

        # otherwise respect stop-loss hold rule
        if current <= stop_loss:
            decision["action"] = "hold"
            decision["reason"] = "stop_loss_triggered"
            decision["suggested_fiat"] = 0.0
            decision["suggested_btc"] = 0.0
        else:
            decision["action"] = "buy" if decision.get("suggested_fiat", 0) > 0 else "hold"
            decision["reason"] = "model_and_rules_agree"
        return decision

    def tick(self):
        decision = self.evaluate_strategies()
        final_decision = self.execute_strategies(decision)
        #self.notify(final_decision)
        return final_decision