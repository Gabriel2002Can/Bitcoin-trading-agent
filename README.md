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
uvicorn[standard]==0.46.0
streamlit==1.57.0
requests==2.32.5
python-dotenv==1.2.2
pandas==2.3.3
yfinance==1.3.0
gspread==6.2.1
groq==1.2.0
python-telegram-bot==22.7
```
### External Services Setup

#### Groq API Key (for LLM advisor)
1. Create an account at Groq APIs: https://console.groq.com/home.

2. Go to API Keys: https://console.groq.com/keys, create a new API key and record the secret key.

3. In your `.env` file, set the `GROQ_KEY` variable to the copied API key.

---

#### Telegram Bot (for real-time alerts)
1. Log in to your Telegram account.

2. Open a chat with **BotFather**, type /newbot, and follow the instructions to create a new bot. Copy the bot token provided.

3. To retrieve your Chat ID:
   - Navigate to `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` (replace <YOUR_BOT_TOKEN> with your actual token).
   - Send any message to your bot (you can find the direct chat link in BotFather’s response).
   - Reload the page. In the JSON response, locate your `chat_id` (usually under result[0].message.chat.id).

4. In your `.env` file:
   - Set `TELEGRAM_BOT_TOKEN` to the token received from BotFather.
   - Set `TELEGRAM_CHAT_ID` to the chat ID obtained from the JSON response.
  
---

####  Google Sheet with the expected columns (see Configuration.options)
1. Make a copy of this template Google Sheet: https://docs.google.com/spreadsheets/d/1QJig5aCdzKrp1wfKpPtMHTy-gtvz8-nGq9-VHwFRjUc/edit?usp=sharing.

2. Customize the parameter values to your preference, but do **not change the cell locations or structure**.

---

####  Google Service Account (for Google Sheets config) — JSON key file
> **Note:** These steps are adapted from the official gspread authentication documentation. If you encounter any issues, refer to the official guide for the most up-to-date instructions.

1. Go to the https://console.cloud.google.com/apis/dashboard and create a new project (or select the one you already have).

2. In the search bar labeled “Search for APIs and Services”, enable the following APIs:
   - Google Drive API
   - Google Sheets API

4. Navigate to APIs & Services > Credentials, then click Create credentials > Service account.

5. Fill in the service account details and complete the creation process.

6. Click Manage service accounts, locate your newly created service account, click the three-dot menu (⋮) next to it, and select Manage keys > Add Key > Create new key.

7. Choose JSON as the key type and click **Create**. Download the JSON file.

8. Place the downloaded JSON file in the project at` secrets/google-credentials.json` (create the secrets folder if it does not exist).

9. Open your Google Sheet and share it with the `client_email` address found inside the JSON file.

10. In your `.env` file, set `BOT_CREDENTIALS_PATH` to the path of the JSON file (e.g., `secrets/google-credentials.json`).

---

####  Gmail Account with App Password (for weekly reports)
1. Ensure that **2-Step Verification** is enabled on your Google account.

2. Go to Google App Passwords and sign in with the same account: https://myaccount.google.com/apppasswords.

3. Create a new app and record the password.

4. In your `.env` file:
   - Set `GMAIL_APP_PASSWORD` to the generated app password.
   - Set `GMAIL_ADDRESS` to the Gmail address that will send the weekly reports (creating a dedicated bot email is recommended).
   - Set `GMAIL_TO_EMAIL` to the email address that will receive the reports.

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
