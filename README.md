# TradingView to Binance Trading Bot

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file from `.env.example` and add your Binance API credentials:
```bash
cp .env.example .env
```

3. Edit `.env` with your actual API keys:
```
BINANCE_API_KEY=your_actual_api_key
BINANCE_API_SECRET=your_actual_api_secret
```

## Run

```bash
python main.py
```

Server will start on http://localhost:8000

## TradingView Webhook URL

Set your TradingView webhook URL to: `http://your-server:8000/webhook`

## Signal Format

Send POST requests to `/webhook` with:
```json
{
    "action": "buy",
    "symbol": "BTCUSDT",
    "quantity": 0.001,
    "order_type": "market"
}
```

## Endpoints

- `GET /` - Health check
- `POST /webhook` - Receive TradingView signals
- `GET /account` - View account balances

**Warning**: Currently set to testnet. Change `testnet=False` in main.py for live trading.