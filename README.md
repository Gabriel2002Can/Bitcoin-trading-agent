# Trading Agent — Using FastAPI and Streamlit

Run the FastAPI server (from the project root):

```bash
uvicorn app.interfaces.api:app --reload --port 8000
```

Run the Streamlit app (in another terminal, from project root):

```bash
streamlit run app/interfaces/streamlit_app.py
```

Run the long-running trading loop:

```bash
python -m app.run_agent
```

The trading loop uses the `Tick Interval` configuration as a 1 to 60 minute cadence, and it keeps a JSON cache in `app/data/config_cache.json` so the app can fall back to the last known settings when Google Sheets is unavailable.