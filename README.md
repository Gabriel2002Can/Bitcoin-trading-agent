# Trading Agent — Log-Driven Dashboard and Automation

## Docker

Build the image:

```bash
docker compose build
```

Set the runtime secrets as shell variables or create a `.env` file from `.env.example`. Place the Google service-account JSON at `secrets/google-credentials.json` so the container can read it through `BOT_CREDENTIALS_PATH`.

Start both services:

```bash
docker compose up
```

The `trader` service runs `python -m app.run_agent`, and the `dashboard` service runs Streamlit on port `8501`. Both services share the `logs` volume, and the runtime state files are persisted through the shared `runtime` volume.

If you only want the dashboard, you can start that service alone with `docker compose up dashboard`.

Run the Streamlit dashboard directly from the project root:

```bash
streamlit run app/interfaces/streamlit_app.py
```

The dashboard reads every trade stored in `logs/`.

Run the long-running trading loop:

```bash
python -m app.run_agent
```

The trading loop uses the `Tick Interval` configuration as a 1 to 60 minute cadence, keeps a JSON cache in `app/data/config_cache.json` so the app can fall back to the last known settings when Google Sheets is unavailable, and sends the weekly Gmail report whenever the `TimeManager` weekly interval allows it.

The weekly report is built from the stored trade logs and summarizes trade counts, market conditions, and bot behavior over the last seven days.