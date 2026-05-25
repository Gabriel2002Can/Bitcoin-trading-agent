from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.data.finance_data import get_data
from app.data.configuration import Configuration
from app.core.metrics import Metrics
from app.core.advisor import Advisor
from app.core.trading_agent import TradingAgent
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimpleConfig:
    def __init__(self):
        self.all = {
            "dca_amount": 500,
            "dca_time": "14",
            "buy_amount": 250,
            "sell_amount": "10%",
            "strategy": "Hybrid",
        }

def build_agent():
    # get fresh market data
    try:
        BTC = get_data()
    except Exception as e:
        return None, None

    # configuration (fallback if Google Sheets not available)
    try:
        config = Configuration()
    except Exception:
        config = SimpleConfig()

    # metrics
    try:
        metrics = Metrics(config=config, data=BTC["history"], entry_price=BTC["currentPrice"])
    except Exception:
        metrics = Metrics(config=config, data=None, entry_price=BTC.get("currentPrice", None))

    # advisor (fallback to neutral if model/client not available)
    try:
        advisor = Advisor()
    except Exception:
        class DummyAdvisor:
            def analyze(self, context):
                return {"bias": "neutral", "confidence": 0.5, "risk_adjustment": 0.5, "rationale": "fallback"}

        advisor = DummyAdvisor()

    agent = TradingAgent(config, metrics, advisor)
    return agent, BTC

@app.get("/tick")
def get_tick():
    agent, BTC = build_agent()
    if agent is None:
        return JSONResponse({"error": "failed_to_get_data"}, status_code=500)
    try:
        payload = agent.tick_json()
        # include a few basic market fields
        if BTC:
            payload.setdefault("market", {})
            payload["market"]["currentPrice"] = BTC.get("currentPrice")
            payload["market"]["open"] = BTC.get("open")
            payload["market"]["dayLow"] = BTC.get("dayLow")
            payload["market"]["dayHigh"] = BTC.get("dayHigh")
        return JSONResponse(payload)
    except Exception as e:
        return JSONResponse({"error": "internal_error", "detail": str(e)}, status_code=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "TradingAgent API is running",
        "routes": ["/tick", "/health", "/docs"],
    }
