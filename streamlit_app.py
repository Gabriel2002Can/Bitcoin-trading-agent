import streamlit as st
import requests

st.set_page_config(page_title="Trading Agent Dashboard", layout="wide")

st.title("Trading Agent — Latest Suggested Trade")

api_url = st.text_input("API URL", value="http://127.0.0.1:8000/tick")

if st.button("Refresh"):
    try:
        r = requests.get(api_url, timeout=20)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        st.error(f"Failed to fetch tick: {e}")
        st.caption("Tip: /tick can take a few seconds. Keep FastAPI running and try again.")
        payload = None

    if payload:
        # summary
        st.subheader("Summary")
        action = payload.get("action")
        reason = payload.get("reason")
        value = payload.get("value")
        scores = payload.get("scores")
        cols = st.columns(4)
        cols[0].metric("Action", action)
        cols[1].metric("Reason", reason)
        cols[2].metric("Value", value)
        cols[3].metric("Scores", scores)

        st.subheader("Model Opinion")
        opinion = payload.get("opinion", {})
        st.write(opinion)

        st.subheader("Context (selected)")
        ctx = payload.get("context", {})
        st.write({
            "current_price": ctx.get("current_price"),
            "stop_loss": ctx.get("stop_loss"),
            "price_change_pct": ctx.get("price_change_pct"),
            "rsi": ctx.get("rsi"),
            "macd_histogram": ctx.get("macd_histogram"),
        })

        st.subheader("Raw Payload")
        st.json(payload)

else:
    st.info("Press Refresh to fetch the latest tick from the FastAPI server.")
