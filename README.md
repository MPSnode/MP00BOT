# 🚀 Futures Signal Bot

A sophisticated 24/7 cryptocurrency futures signal bot that analyzes multiple timeframes and generates high-probability trading signals using technical indicators confluence.

## 📋 Features

### 🎯 Multi-Mode Signal Generation
- **Scalping Mode** (1m/5m): Quick 0.3-2% trades, duration: minutes to hours
- **Intraday Mode** (15m/1h): Daily trend capture, duration: hours to days  
- **Swing Mode** (4h/1d): Major trend following, duration: 2-7+ days

### 📊 Technical Analysis
- **Indicators**: EMA, RSI, StochRSI, Bollinger Bands, ATR, ADX, MACD, Ichimoku, OBV
- **Multi-Timeframe Confluence**: Primary + Confirmation timeframes
- **Scoring System**: 0-100 signal strength scoring with configurable thresholds
- **Volume Analysis**: Volume boost detection and validation

### 🎛️ Risk Management
- **Position Sizing**: Automatic calculation based on risk percentage
- **SL/TP Management**: ATR-based stop loss and take profit levels
- **Trailing Stops**: Dynamic trailing stop management
- **Daily Loss Cap**: Automatic signal stopping on daily loss limits
- **Cooldown Periods**: Prevents overtrading after losses

### 📱 Telegram Integration
- **Real-time Notifications**: Beautifully formatted signal messages
- **Result Tracking**: Automatic WIN/LOSE notifications
- **Daily Summaries**: Performance metrics and statistics
- **System Alerts**: Error notifications and status updates

### 📈 Performance Tracking
- **Signal Monitoring**: Real-time entry/exit detection
- **Metrics Calculation**: Win rate, average RR, PnL tracking
- **Database Storage**: Complete signal history and analytics
- **Reporting**: Daily/weekly performance reports

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Binance account (or other supported exchange)
- Telegram Bot Token
- SQLite database (included)

### 1. Clone Repository
```bash
git clone <repository-url>
cd futures-signal-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Exchange Configuration
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_SECRET=your_secret_here
EXCHANGE_SANDBOX=true

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Configuration
INITIAL_EQUITY=10000
RISK_PER_TRADE=0.01
DAILY_LOSS_CAP=0.03
MAX_CONCURRENT_SIGNALS=3

# Symbols (comma-separated)
SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT,DOTUSDT,LINKUSDT
```

### 4. Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot)
4. Add both to your `.env` file

### 5. Exchange API Setup

1. Create API keys on your exchange (Binance recommended)
2. Enable futures trading permissions
3. **Important**: Use sandbox/testnet for testing
4. Add API credentials to `.env` file

## 🚀 Running the Bot

### Start the Bot
```bash
python main.py
```

### The bot will:
1. ✅ Test all connections (Exchange, Telegram, Database)
2. 🔄 Start monitoring active signals
3. 📊 Begin signal generation cycles
4. 📱 Send startup notification to Telegram

### Signal Generation Frequencies:
- **Scalping**: Every 1 minute
- **Intraday**: Every 5 minutes  
- **Swing**: Every 15 minutes

## 📊 Signal Format

### New Signal Example:
```
🚀 NEW SIGNAL

PAIR      : BTCUSDT
MODE      : SCALPING
SIGNAL    : LONG 🟩 | Trend: EMA200(5m)↑ | ADX: 28.5
ENTRY     : 43250.50   (qty 0.002314)
SL/TP     : 43100.25  | 43500.75   (RR 1:1.7, trail 0.3%)
VOL/ATR   : Vol +22.3% vs 20-candle | ATR(14)=0.85%
CODE      : SIG01151234ABCD

Score: 67 | Confidence: MEDIUM
```

### Result Notification:
```
✅ SIGNAL RESULT

CODE      : SIG01151234ABCD
PAIR      : BTCUSDT
SIGNAL    : LONG 🟩
ENTRY     : 43250.50   (qty 0.002314)
INFO      : HIT TP | 43500.75 | WIN
PnL       : +1.67% 💰
```

## ⚙️ Configuration Details

### Mode Settings

| Parameter | Scalping | Intraday | Swing |
|-----------|----------|----------|-------|
| Primary TF | 1m | 15m | 4h |
| Confirm TF | 5m | 1h | 1d |
| ADX Min | 22 | 20 | 18 |
| Volume Boost | 15% | 20% | 10% |
| SL ATR Mult | 1.0x | 1.25x | 1.5x |
| TP ATR Mult | 1.5-2.0x | 2.0-3.0x | 2.5-3.5x |
| Score Min | 55 | 60 | 65 |
| Order Validity | 15min | 75min | 12h |
| Cooldown | 15min | 60min | 4h |

### Scoring System

Each signal is scored 0-100 based on:

- **Trend Alignment** (+20): HTF trend direction
- **MACD Cross** (+20): Momentum confirmation  
- **ADX Strength** (+10): Trend strength
- **RSI Cross** (+10): Momentum shift
- **StochRSI Signal** (+10): Oversold/Overbought exit
- **Volume Boost** (+10): Increased participation
- **EMA Retest** (+10): Support/resistance confluence
- **Additional Confluence** (+5-10): BB, Fib, OBV alignment

Signals are only sent if score ≥ minimum threshold for the mode.

## 📈 Performance Monitoring

### Database Tables:
- `signals`: All generated signals and results
- `signal_executions`: Entry/exit tracking
- `daily_metrics`: Performance analytics
- `cooldowns`: Active trading restrictions
- `system_logs`: Bot operation logs

### Key Metrics:
- **Win Rate**: Percentage of profitable signals
- **Average RR**: Risk/Reward ratio achieved
- **PnL Tracking**: Points, percentage, USD equivalents
- **Signal Quality**: Score distribution and success rates
- **Market Conditions**: ADX, volatility, volume analysis

## 🔧 Customization

### Adding New Indicators
1. Add indicator calculation to `indicators.py`
2. Update signal detection logic in `signal_engine.py`
3. Adjust scoring system weights

### Adding New Exchanges
1. Extend `data_handler.py` with new exchange client
2. Update configuration options
3. Test API integration

### Custom Signal Conditions
1. Modify mode-specific detection in `signal_engine.py`
2. Adjust scoring weights in configuration
3. Update minimum score thresholds

## 🚨 Risk Warnings

### ⚠️ Important Disclaimers:
- **Paper Trading First**: Always test with sandbox/demo accounts
- **Risk Management**: Never risk more than you can afford to lose
- **Market Volatility**: Crypto markets are extremely volatile
- **No Guarantees**: Past performance doesn't predict future results
- **Due Diligence**: Understand all risks before live trading

### 🛡️ Safety Features:
- Daily loss limits with automatic shutdown
- Position sizing based on account balance
- Cooldown periods after losses
- Maximum concurrent signal limits
- Emergency shutdown procedures

## 📝 Logging & Monitoring

### Log Files:
- `signal_bot.log`: Main application logs
- Database: Complete signal and execution history
- Telegram: Real-time notifications and alerts

### Health Checks:
- Exchange connectivity monitoring
- Database integrity checks  
- Telegram bot responsiveness
- Signal monitoring system status

## 🔄 Maintenance

### Regular Tasks:
- Monitor daily performance summaries
- Review signal quality and success rates
- Update configuration based on market conditions
- Clean up old log files and data
- Test backup and recovery procedures

### Troubleshooting:
- Check log files for error messages
- Verify API key permissions and limits
- Test Telegram bot connectivity
- Validate database integrity
- Monitor system resource usage

## 📚 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Handler  │    │ Signal Engine   │    │ Telegram Bot    │
│                 │    │                 │    │                 │
│ • Exchange API  │───▶│ • MTF Analysis  │───▶│ • Notifications │
│ • Price Cache   │    │ • Scoring       │    │ • Formatting    │
│ • Market Data   │    │ • Validation    │    │ • Queue Mgmt    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Indicators    │    │   Database      │    │ Signal Monitor  │
│                 │    │                 │    │                 │
│ • EMA/RSI/MACD  │    │ • Signal Store  │    │ • TP/SL Watch   │
│ • Bollinger     │    │ • Metrics       │    │ • Trailing      │
│ • Volume/ADX    │    │ • History       │    │ • Lifecycle     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │ Main Orchestr.  │
                    │                 │
                    │ • Scheduling    │
                    │ • Risk Mgmt     │
                    │ • Health Check  │
                    └─────────────────┘
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚡ Quick Start Checklist

- [ ] Install Python 3.8+
- [ ] Clone repository
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Copy `.env.example` to `.env`
- [ ] Configure exchange API keys
- [ ] Set up Telegram bot
- [ ] Configure symbols and risk parameters
- [ ] Test with sandbox/demo account
- [ ] Run `python main.py`
- [ ] Verify Telegram notifications work
- [ ] Monitor first signals in paper trading mode

## 📞 Support

- **Issues**: GitHub Issues tab
- **Discussions**: GitHub Discussions  
- **Documentation**: This README and code comments
- **Community**: Telegram group (link in bio)

---

**🚨 DISCLAIMER: This software is for educational purposes only. Trading cryptocurrencies involves significant risk of loss. Never invest more than you can afford to lose. Always do your own research and consider seeking advice from a qualified financial advisor.**