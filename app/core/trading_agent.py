from app.data.configuration import Configuration
from app.core.metrics import Metrics
from app.core.advisor import Advisor
from app.core.time_manager import TimeManager
from app.core.notifier_bot import NotifierBot
from app.core.recorder import Recorder
from app.core.helper_functions import *
import json
import datetime
import asyncio

# Helper Function
# parse % into a fraction ('3%' -> 0.03)
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

def _dollar_to_btc(dollar: float, btc_quotation: float) -> float:
    return dollar/btc_quotation

def _btc_to_dollar(btc_amount: float, btc_quotation: float) -> float:
    return btc_amount*btc_quotation
    
class TradingAgent:
    """Uses metrics and the current configurations to evaluate which strategy should be used and its paramethers.
    """

    def __init__(self, configuration: Configuration, metrics: Metrics, model: Advisor):
        self.configuration = configuration
        self.metrics = metrics
        self.model = model

        self.notifier = NotifierBot()

        self.time_manager = TimeManager(self.configuration)

    def _build_context(self):
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

        return {
            "strategy": self.configuration.all.get("strategy", "Long Term"),
            "current_price": self.metrics.entry_price,
            "previous_close": prev_close,
            "price_change_pct": price_change_pct,
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
            "sell_amount":self.configuration.all.get("sell_amount","10%").replace("%",""),
            "buy_sensibility": self.configuration.all.get("buy_sensibility","0.3"),
            "sell_sensibility": self.configuration.all.get("sell_sensibility","0.3")
        }

    def _check_balance(self, dollar_value = None, btc_value = None) -> bool:
        # If portfolio data is unavailable (fallback/offline mode), skip hard balance checks.
        if not hasattr(self.configuration, "portfolio") or not isinstance(self.configuration.portfolio, dict):
            return True

        portfolio = self.configuration.portfolio

        def _to_float(value, default=0.0):
            try:
                return float(str(value).replace(",", "."))
            except Exception:
                return default

        dollar_portfolio = _to_float(
            portfolio.get("portfolio_value", portfolio.get("Portfolio Value $", 0))
        )
        btc_portfolio = _to_float(
            portfolio.get("portfolio_btc", portfolio.get("Portfolio Value BTC", 0))
        )

        if dollar_value and dollar_value > dollar_portfolio:
            return False
        elif btc_value and btc_portfolio <= 0:
            return False

        return True

    def _evaluate_strategies(self):
        context = self._build_context()
        opinion = self.model.analyze(context)

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

        dca_triggered = False

        metrics_score = 0

        strategy = str(context.get("strategy", self.configuration.all.get("Strategy", "Long Term"))).strip().lower()

        # Strategy selection is authoritative and determines rule set

        # Long Term: prioritize DCA  —> buy when it reaches the cooldown
        if strategy == "long term" or strategy == "long_term" or strategy == "long-term":
            if self.time_manager.check_dca_cooldown():
                dca_triggered = True

        # Swing Trade: follow the model opinion primarily
        elif strategy == "swing trade" or strategy == "swing_trade" or strategy == "swing-trade":

            rsi_score  = (50 - context.get("rsi", 50)) / 50.0   # Value between 1 and -1

            atr = max(context.get("atr", 1), 1e-9)
            macd_score = max( -1, min(1, context.get("macd_histogram", 0) / atr)) # Value between 1 and -1

            sma_score = max(-1, min(1, (context.get("current_price", 0) - context.get("sma", 1)) / context.get("sma", 1))) # Value between 1 and -1

            # sma score should impact less the score that the other metrics
            metrics_score = (rsi_score * (0.45)) + (macd_score * (0.4)) + (sma_score * (0.15)) # Value between = 1 and -1

        # Hybrid or unknown: combine DCA trigger and model
        else:
            if self.time_manager.check_dca_cooldown():
                dca_triggered = True
            else:
                
                rsi_score  = (50 - context.get("rsi", 50)) / 50.0   # Value between 1 and -1

                atr = max(context.get("atr", 1), 1e-9)
                macd_score = max( -1, min(1, context.get("macd_histogram", 0) / atr)) # Value between 1 and -1

                sma_score  = max(-1, min(1, (context.get("current_price", 0) - context.get("sma", 1)) / context.get("sma", 1))) # Value between 1 and -1

                # sma score should impact less the score that the other metrics
                metrics_score = (rsi_score * (0.45)) + (macd_score * (0.4)) + (sma_score * (0.15)) # Value between = 1 and -1

        return {
            "strategy": context["strategy"],
            "opinion": opinion, # Model's opinion
            "dca_triggered": dca_triggered, # If DCA was triggered
            "metrics_score": metrics_score, # The total scored throught all metrics
            "context": context, # Context dict
        }

    def _execute_strategies(self, decision):
        current = decision["context"]["current_price"]
        stop_loss = decision["context"]["stop_loss"]

        # Getting and normalizing model's opinion
        model_opinion = decision["opinion"]
        multiplier = 1 if model_opinion["bias"] == "bullish" else 0 if model_opinion["bias"] == "neutral" else -1
        model_score = model_opinion["confidence"] * multiplier

        # Get both model suggestion and numeric
        final_score = (model_score * 0.5) + (decision["metrics_score"] * 0.5)

        buy_sensibility = float(decision["context"]["buy_sensibility"].replace(",","."))
        sell_sensibility = float(decision["context"]["sell_sensibility"].replace(",","."))

        buy_trigger = final_score >= buy_sensibility
        sell_trigger = final_score <= - sell_sensibility

        # Base values definied on the config sheet
        buy_base_value = float(decision["context"]["buy_amount"])
        sell_base_value = _parse_percent(decision["context"]["sell_amount"].replace("%",""))

        dca_base_value = decision["context"]["dca_amount"]

        decision["scores"] = f'Models score: {model_score:.3f} Metrics score: {decision["metrics_score"]:.3f} -> Final score: {final_score:.3f}'

        # If stop loss triggered SELL
        if current <= stop_loss:

            if not self._check_balance(btc_value=sell_base_value):
                decision["action"] = "hold"
                decision["value"] = 0.0
                decision["reason"] = "no_bitcoins_in_portfolio"
                return decision
            
            decision["action"] = "sell"
            decision["reason"] = "stop_loss_triggered"
            decision["value"] = sell_base_value 
            return decision

        # Opportunistic SELL
        if sell_trigger:

            value = sell_base_value * (abs(1 + final_score)) 

            if not self._check_balance(btc_value=value):
                decision["action"] = "hold"
                decision["value"] = 0.0
                decision["reason"] = "no_bitcoins_in_portfolio"
                return decision

            decision["action"] = "sell"
            decision["reason"] = "opportunistic_sell"
            decision["value"] = value # In Percentage
            return decision

        # If DCA TRIGGERED
        if decision.get("dca_triggered", False):

            if not self._check_balance(dollar_value=dca_base_value):
                decision["action"] = "hold"
                decision["value"] = 0.0
                decision["reason"] = "not_enough_balance"
                return decision

            self.time_manager.update_last_dca_trade()
            decision["action"] = "buy"
            decision["reason"] = "dca_triggered"
            decision["value"] = dca_base_value
            return decision
        
        # Opportunistic BUY
        if buy_trigger:

            value = buy_base_value * (1 + final_score)

            if not self._check_balance(dollar_value=value):
                decision["action"] = "hold"
                decision["value"] = 0.0
                decision["reason"] = "not_enough_balance"
                return decision
            
            decision["action"] = "buy"
            decision["reason"] = "opportunistic_buy"
            decision["value"] = value
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

    def _execute_trade(self, decision) -> None:

        if not hasattr(self.configuration, "change_portfolio"):
            return

        action = decision.get("action", "hold")
        value = float(decision.get("value", 0))
        quotation = float(decision["context"].get("current_price", 0))

        if action == "buy":

            diff_dollar = -value
            diff_btc = _dollar_to_btc(value, quotation)

            self.configuration.change_portfolio(diff_dollar, diff_btc)
        
        elif action == "sell":
            
            value = value * float(self.configuration.portfolio["portfolio_btc"].replace(",", "."))

            diff_btc = -value
            diff_dollar = _btc_to_dollar(value, quotation)

            self.configuration.change_portfolio(diff_dollar, diff_btc)

    def _serialize_decision(self, decision: dict) -> dict:
        """Return a JSON-safe version of the decision dict.

        - Ensures `opinion` is a plain dict.
        - Converts pandas/numpy types to native Python types.
        - Normalizes sell_amount percentages into numeric and flags.
        """
        out = {}

        # Copy of simple fields
        for k in ["strategy", "dca_triggered", "metrics_score", "scores", "action", "reason", "value"]:
            if k in decision:
                try:
                    out[k] = float(decision[k]) if isinstance(decision[k], (int, float)) and not isinstance(decision[k], bool) and k in ("metrics_score","value") else decision[k]
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

        portfolio_snapshot = {}
        if hasattr(self.configuration, "portfolio") and isinstance(self.configuration.portfolio, dict):
            def _to_float(value, default=0.0):
                try:
                    return float(str(value).replace(",", "."))
                except Exception:
                    return default

            current_price = _to_float(ctx_out.get("current_price", 0.0))
            cash_balance = _to_float(
                self.configuration.portfolio.get("portfolio_value", self.configuration.portfolio.get("Portfolio Value $", 0.0))
            )
            btc_holdings = _to_float(
                self.configuration.portfolio.get("portfolio_btc", self.configuration.portfolio.get("Portfolio Value BTC", 0.0))
            )

            portfolio_snapshot = {
                "cash_balance": cash_balance,
                "btc_holdings": btc_holdings,
                "btc_price": current_price,
                "total_portfolio_value": cash_balance + (btc_holdings * current_price),
            }

        out["portfolio_snapshot"] = portfolio_snapshot

        # timestamp
        out["timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        return out

    def tick_json(self, simulate: bool = False) -> dict:
        """Return a JSON-safe decision payload for APIs/frontends.

        simulate=True avoids side effects (portfolio updates, notifications, persistence),
        which is the expected behavior for dashboard polling endpoints.
        """
        try:
            if simulate:
                decision = self._evaluate_strategies()
                final_decision = self._execute_strategies(decision)
                return self._serialize_decision(final_decision)

            dec = self.tick()
            return self._serialize_decision(dec)
        except Exception as e:
            return {"error": "tick_json_failed", "detail": str(e)}

    async def _notify(self, decision) -> None:

        message = build_trade_message(decision, self.configuration.portfolio)

        await self.notifier.send_telegram_message(message)

    def _record_trade(self, decision) -> None:
        recorder = Recorder()

        serialized_trade = self._serialize_decision(decision)

        recorder.save_trade(serialized_trade)

    def tick(self) -> dict:
        decision = self._evaluate_strategies()
        final_decision = self._execute_strategies(decision)

        self._execute_trade(final_decision)

        asyncio.run(self._notify(final_decision))

        # Register Locally
        self._record_trade(final_decision)
        self.time_manager.update_last_tick()

        return final_decision