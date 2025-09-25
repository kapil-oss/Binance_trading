# Alsa Trade Backend

A comprehensive trading automation platform that integrates TradingView webhooks with Binance futures trading, featuring a modern web interface for strategy management and real-time execution monitoring.

## Overview

This project provides a complete trading automation solution that:
- Receives trading signals from TradingView webhooks
- Executes trades automatically on Binance Futures
- Provides comprehensive position and risk management
- Offers detailed execution tracking and performance analytics
- Features a responsive web interface for configuration and monitoring

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   TradingView   │────│  Alsa Trade App  │────│  Binance API    │
│   Webhooks      │    │                  │    │  (Futures)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────┐
                       │ PostgreSQL   │
                       │ Database     │
                       └──────────────┘
```

### Components

- **Backend API** (FastAPI): Handles webhooks, trading logic, and data management
- **Frontend Web UI** (Vanilla JavaScript): Configuration interface and monitoring dashboard
- **Database** (PostgreSQL): Stores signals, executions, preferences, and analytics
- **Trading Engine**: Advanced position management with leverage and capital allocation

## Features

### Trading Automation
- **Signal Processing**: Receives and validates TradingView webhook signals
- **Strategy Filtering**: Configurable strategy matching and validation
- **Direction Controls**: Long-only, short-only, or bidirectional trading modes
- **Dynamic Leverage**: Per-trade leverage configuration with Binance integration
- **Capital Allocation**: Percentage-based position sizing with balance integration

### Risk Management
- **Position Validation**: Symbol-specific quantity precision handling
- **Balance Checks**: Real-time account balance integration for position sizing
- **Error Handling**: Comprehensive error tracking and recovery
- **Execution Monitoring**: Detailed timing analysis for trade execution latency

### Analytics & Monitoring
- **Real-time Dashboard**: Live execution monitoring with status indicators
- **Performance Tracking**: P&L analysis, win rates, and trading metrics
- **Detailed Logging**: Comprehensive audit trail for all trading activities
- **Account Snapshots**: Balance tracking and position monitoring

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Binance account with API access
- TradingView account (for webhook setup)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AlsaTradeBackend-python
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file with:
   ```env
   DATABASE_URL=postgresql://username:password@localhost/alsatrade
   BINANCE_API_KEY=your_binance_api_key
   BINANCE_API_SECRET=your_binance_api_secret
   BINANCE_USE_TESTNET=1
   ```

4. **Initialize database**
   ```bash
   python migrate_database.py
   ```

5. **Start the application**
   ```bash
   python main.py
   ```

The application will be available at:
- **API**: http://localhost:8000
- **Web Interface**: http://localhost:8000/ui

## Configuration

### Strategy Preferences

Access the web interface to configure:

1. **Product Selection**: Choose target trading instruments (BTC, ETH, etc.)
2. **Strategy Selection**: Configure strategy matching for webhook filtering
3. **Direction Control**: Set allowed trading directions
4. **Leverage Settings**: Configure leverage multipliers
5. **Capital Allocation**: Set percentage of account balance to use

### TradingView Webhook Setup

Configure TradingView alerts to send webhooks to:
```
POST http://your-domain:8000/webhook
```

Required webhook payload format:
```json
{
  "action": "buy",
  "symbol": "BTCUSDT",
  "quantity": 0.001,
  "price": 45000,
  "strategy": "ALSAPRO 1",
  "time": "2024-01-01T12:00:00Z"
}
```

## API Documentation

### Core Endpoints

- `POST /webhook` - Receive TradingView signals
- `GET /executions` - Retrieve execution history
- `GET /account/summary` - Get account balance information
- `GET /preferences/current` - Get current strategy preferences
- `POST /preferences/{type}` - Update strategy preferences

### Database Schema

Key models include:
- **StrategyPreference**: User trading preferences
- **Signal**: Incoming webhook data
- **Execution**: Trade execution records with timing
- **AccountSnapshot**: Balance history
- **Position**: Active position tracking
- **Order**: Binance order details

## Web Interface

The responsive web interface provides:

### Dashboard
- Real-time account balance display
- Active position monitoring
- Recent execution history
- Strategy allocation visualization

### Configuration Panel
- Product and strategy selection
- Direction mode controls
- Leverage configuration
- Capital allocation settings

### Monitoring Tools
- Detailed execution logs with timing analysis
- Performance metrics and analytics
- Error tracking and diagnostics
- Account activity history

## Development

### File Structure
```
├── api/
│   ├── preferences.py     # Strategy preference management
│   └── trading.py         # Core trading logic and execution
├── frontend/
│   └── app.js            # Web interface JavaScript
├── config.py             # Application configuration
├── database.py           # Database models and utilities
├── main.py              # FastAPI application entry point
└── requirements.txt     # Python dependencies
```

### Key Classes

- **BinanceTrader**: Handles all Binance API interactions
- **StrategyPreference**: Database model for user preferences
- **Signal/Execution**: Models for tracking trade lifecycle
- **Database utilities**: Session management and data operations

### Testing

Run the application in testnet mode by setting:
```env
BINANCE_USE_TESTNET=1
```

This uses Binance testnet for safe development and testing.

## Security Considerations

- API keys are stored in environment variables
- Database connections use connection pooling
- Input validation on all webhook endpoints
- Error handling prevents information disclosure
- Audit logging for all trading activities

## Performance

- Async/await patterns for concurrent operations
- Database indexing on frequently queried fields
- Efficient batch operations for large datasets
- Caching for frequently accessed configuration data
- Connection pooling for database and API connections

## Monitoring & Maintenance

### Logs
- Application logs track all significant events
- Database logs capture all trading activities
- Error logs provide detailed stack traces
- Performance logs monitor execution timing

### Health Checks
- Database connectivity monitoring
- Binance API status verification
- Webhook endpoint availability testing
- Balance and position consistency checks

## Support & Documentation

For issues or questions:
1. Check the execution logs in the web interface
2. Review database records for detailed transaction history
3. Verify Binance API connectivity and permissions
4. Ensure TradingView webhook configuration is correct

## License

This project is proprietary software. All rights reserved.