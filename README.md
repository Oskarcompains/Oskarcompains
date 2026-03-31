# Polymarket Arbitrage Bot

Automated arbitrage trading bot for [Polymarket](https://polymarket.com) with a **real-time web dashboard**.

Built with Python (`py-clob-client` SDK) + FastAPI backend + React/Tailwind frontend.

---

## Dashboard

Dark-themed live dashboard with:
- Real-time P&L chart
- Opportunity feed (WebSocket-powered)
- Open positions table
- Bot start/stop controls

### Run locally

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Build the React frontend
cd dashboard && npm install && npm run build && cd ..

# 3. Start the server (serves bot API + dashboard)
python server.py

# Dashboard → http://localhost:8000
```

### Deploy to your domain

```bash
# On your server:
git clone <repo> && cd Oskarcompains
pip install -r requirements.txt
cd dashboard && npm install && npm run build && cd ..

# Run with systemd / pm2 / screen:
python server.py --host 0.0.0.0 --port 80

# Or behind nginx (recommended):
# proxy_pass http://127.0.0.1:8000;
```

### Dev mode (hot reload)

```bash
# Terminal 1 — FastAPI backend
python server.py --reload

# Terminal 2 — Vite dev server (http://localhost:5173)
cd dashboard && npm run dev
```

---

## Strategy

The bot exploits **intra-market arbitrage** on Polymarket binary prediction markets:

> If `YES_ask + NO_ask < 1.0`, buying both tokens guarantees a **$1 payout** at resolution regardless of outcome — locking in a risk-free profit equal to `1 - YES_ask - NO_ask - fees`.

## Project Structure

```
.
├── config/
│   ├── config.yaml          # Bot configuration (edit this)
│   └── config.example.yaml  # Reference template
├── src/
│   ├── client.py            # Polymarket API client (auth + orders)
│   ├── market_monitor.py    # Real-time price/orderbook polling
│   ├── arbitrage.py         # Arbitrage opportunity detection
│   ├── order_manager.py     # Order execution (supports dry_run)
│   ├── risk_manager.py      # Position limits, stop-loss, circuit breaker
│   ├── portfolio.py         # Position tracking and P&L reporting
│   └── logger.py            # Logging with file rotation
├── logs/                    # Auto-generated log files
├── main.py                  # Entry point
├── requirements.txt
└── .env.example
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your Polygon wallet credentials:

```env
POLYMARKET_PRIVATE_KEY=0x_your_private_key
POLYMARKET_FUNDER=0x_your_wallet_address
POLYMARKET_CHAIN_ID=137
```

> **Security**: Never commit your `.env` file. Keep your private key safe.

### 3. Configure bot parameters

Edit `config/config.yaml`:

```yaml
bot:
  poll_interval: 5        # seconds between scans
  dry_run: true           # START WITH TRUE — simulate without real orders

arbitrage:
  min_profit_threshold: 0.02  # 2% minimum net profit
  max_order_size: 100.0       # max $100 per trade leg

risk:
  max_position_size: 200.0    # max $200 per market
  max_total_exposure: 1000.0  # max $1000 total
  stop_loss_pct: 0.15         # 15% stop-loss
  trade_cooldown: 60          # 60s cooldown per market
```

## Usage

### Test connectivity

```bash
python main.py --test-connection
```

Verifies authentication and lists available markets.

### Scan for opportunities (no trades)

```bash
python main.py --scan-once
```

Runs a single scan and prints any arbitrage opportunities found without placing orders.

### View portfolio report

```bash
python main.py --report
```

### Run the bot

```bash
# Always test in dry_run mode first!
python main.py
```

Set `dry_run: false` in `config/config.yaml` only when you are confident in the bot's behavior.

## Risk Warning

- **Start with `dry_run: true`** and observe the bot for several cycles before enabling real trading.
- Arbitrage opportunities on prediction markets are rare and often tiny. Fees can eat into profits.
- Always set conservative position limits (`max_total_exposure`) that match your risk tolerance.
- This bot is provided as-is for educational purposes. Trading involves financial risk.

## How Intra-Market Arbitrage Works

On Polymarket, every binary market has two tokens: **YES** and **NO**.
At resolution, exactly one token pays $1 and the other pays $0.

If you can buy **both** at a combined cost below $1:

```
cost = YES_ask + NO_ask = 0.45 + 0.52 = 0.97
profit = 1.00 - 0.97 - fees = ~0.025 (2.5%)
```

The bot detects these windows and executes both legs simultaneously.

## Logs

Logs are written to `logs/bot.log` with rotation (10 MB max, 5 backups).
Portfolio state is persisted to `logs/portfolio_state.json` and survives restarts.
