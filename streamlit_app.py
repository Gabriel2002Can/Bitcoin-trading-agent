import streamlit as st
import requests
from typing import Any, Dict

st.set_page_config(page_title="Trading Agent Dashboard", layout="wide")

st.title("Trading Agent — Latest Suggested Trade")

api_url = st.sidebar.text_input("API URL", value="http://127.0.0.1:8000/tick")
if "payload" not in st.session_state:
    st.session_state.payload = None

def fetch_tick(url: str) -> Dict[str, Any] | None:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Failed to fetch tick: {e}")
        st.caption("Tip: ensure FastAPI is running and allow a few seconds for /tick to compute.")
        return None

if st.sidebar.button("Refresh"):
    st.session_state.payload = fetch_tick(api_url)

payload = st.session_state.payload

# Auto-fetch once on page load if we don't have data yet
if payload is None:
    with st.spinner("Fetching latest recommendation..."):
        st.session_state.payload = fetch_tick(api_url)
    payload = st.session_state.payload

if not payload:
    st.warning("No data available. Use 'Refresh' in the sidebar to try again.")
else:
    # Top summary metrics
    action = payload.get("action", "n/a")
    reason = payload.get("reason", "n/a")
    value = payload.get("value", 0)
    scores = payload.get("scores", "")
    strategy = payload.get("strategy", "n/a")

    def action_label(a: str) -> str:
        return "🟢 BUY" if str(a).lower() == "buy" else ("🔴 SELL" if str(a).lower() == "sell" else "⚪ HOLD")

    col1, col2, col3, col4 = st.columns([1.2, 1, 1, 1])
    col1.metric("Recommendation", action_label(action))
    col2.metric("Strategy", strategy)
    try:
        val_display = f"${float(value):,.2f}" if isinstance(value, (int, float)) else str(value)
    except Exception:
        val_display = str(value)
    col3.metric("Value", val_display)
    col4.metric("Scores", scores)

    # Model opinion card
    st.markdown("---")
    opinion = payload.get("opinion", {})
    op_bias = opinion.get("bias", "neutral")
    op_conf = opinion.get("confidence", 0.0)
    op_rationale = opinion.get("rationale", "")

    op_col1, op_col2 = st.columns([2, 3])
    with op_col1:
        st.subheader("Model Opinion")
        st.write(f"**Bias:** {op_bias.capitalize()}  ")
        st.write(f"**Rationale:** {op_rationale}")
    with op_col2:
        st.subheader("Confidence")
        try:
            st.progress(min(max(float(op_conf), 0.0), 1.0))
        except Exception:
            st.write(op_conf)

    # Market data and context
    st.markdown("---")
    market = payload.get("market", {})
    context = payload.get("context", {}) or {}

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Price", f"${market.get('currentPrice', 'n/a')}")
    m2.metric("Open", f"${market.get('open', 'n/a')}")
    m3.metric("Day Low", f"${market.get('dayLow', 'n/a')}")
    m4.metric("Day High", f"${market.get('dayHigh', 'n/a')}")

    # Context indicators table
    st.subheader("Context Indicators")
    # pick a set of useful keys and present them in two columns
    keys = ["current_price", "previous_close", "price_change_pct", "stop_loss", "rsi", "ema", "sma", "macd", "macd_histogram", "atr", "dca_amount", "buy_amount", "sell_amount"]
    rows = []
    for k in keys:
        if k in context:
            rows.append({"metric": k, "value": context.get(k)})

    if rows:
        st.table(rows)
    else:
        st.write(context)

    # Raw payload for debugging
    with st.expander("Raw payload"):
        st.json(payload)
