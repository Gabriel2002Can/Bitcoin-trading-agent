from configuration import Configuration
from metrics import Metrics
from advisor import Advisor
import json
import datetime
import os

try:
    import requests
except Exception:
    requests = None

# Helper Function
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
            "buy_amount":self.configuration.all.get("buy_amount",250),
            "sell_amount":self.configuration.all.get("sell_amount","10%"),
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

        dca_trigger_pct = _parse_percent(context.get("dca_trigger_raw"))

        dca_triggered = False

        metrics_score = 0

        # compute price drop pct (negative when price fell)
        price_change = context.get("price_change_pct", 0.0)

        strategy = str(context.get("strategy", self.configuration.all.get("Strategy", "Long Term"))).strip().lower()

        # Strategy selection is authoritative and determines rule set

        # TODO: add a sell function for Long Term
        # Long Term: prioritize DCA trigger —> buy when price dropped at least the configured percent
        if strategy == "long term" or strategy == "long_term" or strategy == "long-term":
            if price_change <= -dca_trigger_pct:
                dca_triggered = True

        # Swing Trade: follow the model opinion primarily
        elif strategy == "swing trade" or strategy == "swing_trade" or strategy == "swing-trade":

            rsi_score  = (50 - context.get("rsi", 50)) / 50.0   # Value between 1 and -1
            macd_score = max(-1, min(1, context.get("macd_histogram", 0) / 50.0))   # Value between 1 and -1
            sma_score  = max(-1, min(1, (context.get("current_price", 0) - context.get("sma", 1)) / context.get("sma", 1))) # Value between 1 and -1

            # sma score should impact less the score that the other metrics
            metrics_score = (rsi_score * (0.4)) + (macd_score * (0.4)) + (sma_score * (0.2)) # Value between = 1 and -1

        # Hybrid or unknown: combine DCA trigger and model
        else:
            if price_change <= -dca_trigger_pct:
                dca_triggered = True
            else:
                
                rsi_score  = (50 - context.get("rsi", 50)) / 50.0   # Value between 1 and -1
                macd_score = max(-1, min(1, context.get("macd_histogram", 0) / 50.0))   # Value between 1 and -1
                sma_score  = max(-1, min(1, (context.get("current_price", 0) - context.get("sma", 1)) / context.get("sma", 1))) # Value between 1 and -1

                # sma score should impact less the score that the other metrics
                metrics_score = (rsi_score * (0.4)) + (macd_score * (0.4)) + (sma_score * (0.2)) # Value between = 1 and -1

        return {
            "strategy": context["strategy"],
            "opinion": opinion, # Model's opinion
            "dca_triggered": dca_triggered, # If DCA was triggered
            "dca_trigger_pct": dca_trigger_pct, # The drop percentage it drops
            "metrics_score": metrics_score, # The total scored throught all metrics
            "context": context, # Context dict
        }

    def execute_strategies(self, decision):
        current = decision["context"]["current_price"]
        stop_loss = decision["context"]["stop_loss"]

        # Getting and normalizing model's opinion
        model_opinion = decision["opinion"]
        multiplier = 1 if model_opinion["bias"] == "bullish" else 0 if model_opinion["bias"] == "neutral" else -1
        model_score = model_opinion["confidence"] * multiplier

        # Get both model suggestion and numeric
        final_score = (model_score * 0.4) + (decision["metrics_score"] * 0.6)

        # TODO: Configure sensibility threshold via config sheet
        buy_trigger = final_score >= 0.4
        sell_trigger = final_score <= - 0.4

        # Base values definied on the config sheet
        buy_base_value = float(decision["context"]["buy_amount"])
        sell_base_value = _parse_percent(decision["context"]["sell_amount"])

        dca_base_value = decision["context"]["dca_amount"]

        decision["scores"] = f'Models score: {model_score} Metrics score: {decision["metrics_score"]}'

        # If stop loss triggered SELL
        if current <= stop_loss:
            decision["action"] = "sell"
            decision["reason"] = "stop_loss_triggered"
            decision["value"] = sell_base_value 
            return decision

        # Opportunistic SELL
        if sell_trigger:
            decision["action"] = "sell"
            decision["reason"] = "opportunistic_sell"
            decision["value"] = sell_base_value * (abs(1 + final_score)) # In Percentage
            return decision

        # If DCA TRIGGERED
        if decision.get("dca_triggered", False):
            decision["action"] = "buy"
            decision["reason"] = "dca_triggered"
            decision["value"] = dca_base_value
            return decision
        
        # Opportunistic BUY
        if buy_trigger:
            decision["action"] = "buy"
            decision["reason"] = "opportunistic_buy"
            decision["value"] = buy_base_value * (1 + final_score)
            return decision

        # HOLD if current context is not ideal
        decision["action"] = "hold"
        decision["value"] = 0.0
        decision["reason"] = "neutral_market"
        return decision
        # decision:
        # "action": X
        # "reason": Y
        # "value": Z

    def tick(self):
        decision = self.evaluate_strategies()
        final_decision = self.execute_strategies(decision)
        # attempt to notify an external endpoint if configured
        notify_url = os.getenv("FASTAPI_NOTIFY_URL", None)
        if notify_url:
            try:
                self.notify(final_decision, notify_url)
            except Exception:
                pass
        return final_decision

    def serialize_decision(self, decision: dict) -> dict:
        """Return a JSON-safe version of the decision dict.

        - Ensures `opinion` is a plain dict.
        - Converts pandas/numpy types to native Python types.
        - Normalizes sell_amount percentages into numeric and flags.
        - Adds an ISO8601 `timestamp`.
        """
        out = {}

        # shallow copy of simple fields
        for k in ["strategy", "dca_triggered", "dca_trigger_pct", "metrics_score", "scores", "action", "reason", "value"]:
            if k in decision:
                try:
                    out[k] = float(decision[k]) if isinstance(decision[k], (int, float)) and not isinstance(decision[k], bool) and k in ("dca_trigger_pct","metrics_score","value") else decision[k]
                except Exception:
                    out[k] = decision[k]

        # opinion normalization
        opinion = decision.get("opinion", None)
        if opinion is None:
            out["opinion"] = {"bias": "neutral", "confidence": 0.5, "risk_adjustment": 0.5, "rationale": "no_opinion"}
        else:
            if isinstance(opinion, dict):
                out["opinion"] = opinion
            else:
                # try to extract JSON content
                parsed = None
                try:
                    if hasattr(opinion, "content"):
                        parsed = json.loads(opinion.content)
                    elif hasattr(opinion, "message") and hasattr(opinion.message, "content"):
                        parsed = json.loads(opinion.message.content)
                    elif isinstance(opinion, str):
                        parsed = json.loads(opinion)
                except Exception:
                    parsed = None

                if parsed and isinstance(parsed, dict):
                    out["opinion"] = parsed
                else:
                    out["opinion"] = {"bias": "neutral", "confidence": 0.5, "risk_adjustment": 0.5, "rationale": str(opinion)}

        # context normalization
        context = decision.get("context", {}) or {}
        ctx_out = {}
        for key, val in context.items():
            try:
                if val is None:
                    ctx_out[key] = None
                elif isinstance(val, (int, float, str, bool)):
                    ctx_out[key] = val
                else:
                    # try convert pandas/numpy scalar
                    try:
                        ctx_out[key] = float(val)
                    except Exception:
                        ctx_out[key] = str(val)
            except Exception:
                ctx_out[key] = str(val)

        # handle sell_amount normalization
        sell_amount = ctx_out.get("sell_amount", None)
        if isinstance(sell_amount, str) and sell_amount.strip().endswith("%"):
            try:
                pct = float(sell_amount.strip().rstrip("%")) / 100.0
                ctx_out["sell_amount"] = pct
                ctx_out["sell_amount_is_percent"] = True
            except Exception:
                ctx_out["sell_amount_is_percent"] = False
        else:
            ctx_out["sell_amount_is_percent"] = False

        out["context"] = ctx_out

        # timestamp
        out["timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        return out

    def tick_json(self) -> dict:
        """Call `tick()` and return a JSON-safe dict suitable for APIs or frontends."""
        dec = self.tick()
        try:
            return self.serialize_decision(dec)
        except Exception:
            return {"error": "serialization_failed"}

    def notify(self, decision: dict, endpoint: str) -> None:
        """POST the serialized decision to `endpoint` as JSON. Requires `requests` package."""
        if requests is None:
            return
        payload = self.serialize_decision(decision)
        try:
            requests.post(endpoint, json=payload, timeout=2)
        except Exception:
            pass