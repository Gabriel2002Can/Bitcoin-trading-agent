# Bitcoin Trading Agent — Log-Driven Dashboard and Automation

> An intelligent Bitcoin trading bot with real-time decision making, technical analysis, AI-powered advice (via Groq), logging, notifications, and a beautiful Streamlit dashboard.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)

## Features

- **Automated Trading Loop**: Runs at configurable intervals (1-60 minutes)
- **Multi-Strategy Support**: Swing trading, DCA (Dollar Cost Averaging), and more
- **Technical Analysis**: Uses ATR, EMA, SMA, RSI, MACD indicators
- **AI Advisor**: Leverages Groq LLM for contextual trading suggestions
- **Configuration via Google Sheets**: Live config with local JSON caching fallback
- **Logging System**: All trades and decisions saved to `logs/`
- **Notifications**: Telegram alerts + Weekly Gmail reports
- **Streamlit Dashboard**: Real-time visualization of performance and logs
- **Docker Support**: Easy deployment with `docker-compose`

## System Architecture & How It Works

### Core Components

The system is modular and follows a clean separation of concerns:

1. **Configuration (`app/data/configuration.py`)**:
   - Reads parameters from a Google Sheet (preferred) or local cache
   - Parameters include: Tick Interval, technical indicator periods, strategy selection, risk parameters (Stop Loss, DCA, Buy/Sell amounts), sensibilities

2. **Data Fetching (`app/data/finance_data.py`)**:
   - Uses `yfinance` to get real-time and historical BTC data

3. **Metrics & Analysis (`app/core/metrics.py`)**:
   - Calculates all technical indicators
   - Provides market context (trend strength, volatility, momentum)

4. **Advisor (`app/core/advisor.py`)**:
   - Uses Groq LLM to analyze current market conditions and suggest actions

5. **Trading Agent (`app/core/trading_agent.py`)**:
   - Main decision engine
   - Combines metrics + configuration + AI advice
   - Decides Buy, Sell, Hold, or DCA
   - Manages position sizing and risk

6. **Recorder (`app/core/recorder.py`)**:
   - Logs every decision and trade to timestamped JSON files in `logs/`

7. **Notifier (`app/core/notifier_bot.py`)**:
   - Sends Telegram messages for trades
   - Sends weekly summary reports via Gmail

8. **Time Manager (`app/core/time_manager.py`)**:
   - Controls tick scheduling and weekly report cadence

9. **Dashboard (`app/interfaces/streamlit_app.py`)**:
   - Visualizes logs, performance, and current status

### Trading Flow

1. **Tick Triggered** → Load latest config
2. **Fetch Market Data** → Calculate technical indicators
3. **Generate Context** → Build rich prompt for AI + metrics
4. **Decision Made** → Execute logic (simulated or real depending on implementation)
5. **Record & Notify** → Save to logs + send alerts
6. **Sleep** until next tick

**Weekly Reports**: Summarize trade count, win rate, market conditions, and bot behavior.

---

## Requirements

### Python Dependencies (`requirements.txt`)

```txt
uvicorn[standard]
streamlit
requests
python-dotenv
pandas
yfinance
gspread
groq
python-telegram-bot
```
### External Services Setup

- Groq API Key (for LLM advisor)
- Telegram Bot (for real-time alerts)
- Gmail Account with App Password (for weekly reports)
- Google Service Account (for Google Sheets config) — JSON key file
- Google Sheet with the expected columns (see Configuration.options)

### Environment Variables (.env)

Copy .env.example to .env and fill in:
```env
GROQ_KEY_PATH=replace-with-your-groq-api-key
TELEGRAM_BOT_TOKEN=replace-with-your-telegram-bot-token
TELEGRAM_CHAT_ID=replace-with-your-telegram-chat-id
GMAIL_ADDRESS=replace-with-your-gmail-address
GMAIL_APP_PASSWORD=replace-with-your-gmail-app-password
GMAIL_TO_EMAIL=replace-with-your-report-recipient
BOT_CREDENTIALS_PATH=secrets/google-credentials.json
```
Place your Google service account JSON at secrets/google-credentials.json.

---

## How to Run the Project Locally

### Option 1: Docker (Recommended)
```bash
# 1. Clone the repo
git clone https://github.com/Gabriel2002Can/Bitcoin-trading-agent.git
cd Bitcoin-trading-agent

# 2. Setup secrets
cp .env.example .env
# Edit .env with your keys
mkdir -p secrets
# Place google-credentials.json in secrets/

# 3. Build and run
docker compose build
docker compose up
```
- **Trader:** Runs the trading loop
- **Dashboard:** Available at http://localhost:8501

### Option 2: Local Development
```bash
# 1. Clone and setup
git clone https://github.com/Gabriel2002Can/Bitcoin-trading-agent.git
cd Bitcoin-trading-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables and secrets (same as above)

# 5. Run the dashboard
streamlit run app/interfaces/streamlit_app.py

# 6. In another terminal, run the trading agent
python -m app.run_agent
```

---

## Project Structure
```text
Bitcoin-trading-agent/
├── app/
│   ├── core/              # Trading logic and components
│   ├── data/              # Configuration + data fetching
│   ├── interfaces/        # Streamlit dashboard
│   └── run_agent.py       # Main trading loop
├── logs/                  # Trade history (auto-generated)
├── runtime/               # Persistent state
├── secrets/               # Google credentials
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Development & Testing

- Run tests: python -m pytest tests/
- The system is designed to be safe: always check logs before live trading
- Configuration is live-editable via Google Sheets

## Disclaimer
**This is for educational and simulation purposes. Trading cryptocurrencies involves significant risk. Use at your own risk and never trade with money you cannot afford to lose.**
