# Trading Agent — Log-Driven Dashboard and Automation

Run the Streamlit dashboard directly from the project root:

```bash
streamlit run app/interfaces/streamlit_app.py
```

The dashboard reads every trade stored in `logs/` and no longer depends on the FastAPI tick endpoint.

Run the long-running trading loop:

```bash
python -m app.run_agent
```

The trading loop uses the `Tick Interval` configuration as a 1 to 60 minute cadence, keeps a JSON cache in `app/data/config_cache.json` so the app can fall back to the last known settings when Google Sheets is unavailable, and sends the weekly Gmail report whenever the `TimeManager` weekly interval allows it.

The weekly report is built from the stored trade logs and summarizes trade counts, market conditions, and bot behavior over the last seven days.