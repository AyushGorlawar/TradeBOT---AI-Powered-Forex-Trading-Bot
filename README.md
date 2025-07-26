# TradeBOT - AI-Powered Forex Trading Bot

TradeBOT is an advanced forex trading bot that uses artificial intelligence to analyze charts and generate buy/sell signals for live forex markets. The bot integrates technical analysis, machine learning, and real-time data processing to make informed trading decisions.

## Features

- Real-time forex data streaming from multiple sources (OANDA, FXCM)
- Technical indicator calculation and analysis (RSI, MACD, Bollinger Bands, Moving Averages, Stochastic)
- AI-powered signal generation using machine learning models
- Live market trading with multiple execution modes (live, paper trading)
- Comprehensive backtesting capabilities
- Risk management with dynamic position sizing, stop-loss and take-profit controls
- Performance tracking and visualization with interactive charts
- Web interface for monitoring and controlling the bot
- Support for multiple currency pairs
- Customizable trading strategies

## Project Structure

```
TradeBOT/
├── config/                  # Configuration files
│   ├── config.py           # Main configuration class
│   ├── config.json         # Configuration settings
│   └── pairs.py            # Currency pairs settings
├── models/                 # Saved ML models
│   └── saved_models/       # Saved model weights
├── src/                    # Source code
│   ├── backtester.py       # Backtesting module
│   ├── data_fetcher.py     # Data retrieval module
│   ├── indicators.py       # Technical indicators
│   ├── ml_model.py         # Machine learning model
│   ├── preprocessor.py     # Data preprocessing
│   ├── risk_manager.py     # Risk management
│   ├── signal_generator.py # Trading signal generation
│   ├── trade_executor.py   # Trading execution
│   ├── visualizer.py       # Data visualization
│   ├── web_interface.py    # Web interface
│   ├── static/             # Static web assets
│   │   ├── css/            # CSS stylesheets
│   │   ├── js/             # JavaScript files
│   │   │   ├── backtest.js # Backtest page functionality
│   │   │   ├── settings.js # Settings page functionality
│   │   │   └── trades.js   # Trades page functionality
│   │   └── img/            # Images
│   └── templates/          # HTML templates
│       ├── backtest.html   # Backtest page
│       ├── base.html       # Base template
│       ├── charts.html     # Charts page
│       ├── dashboard.html  # Dashboard page
│       ├── settings.html   # Settings page
│       └── trades.html     # Trades page
├── main.py                 # Main entry point
└── requirements.txt        # Dependencies
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/TradeBOT.git
   cd TradeBOT
   ```

2. Create a virtual environment (recommended):
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with your API keys:
   ```
   OANDA_API_KEY=your_oanda_api_key
   OANDA_ACCOUNT_ID=your_oanda_account_id
   ```

## Usage

### Running the Trading Bot

```
# Run in live trading mode
python main.py --mode live --strategy ml

# Run in paper trading mode
python main.py --mode paper --strategy combined

# Run with specific currency pairs
python main.py --pairs EUR_USD GBP_USD --timeframe 1h

# Run backtesting
python main.py --mode backtest --pairs EUR_USD --backtest-days 30

# Start the web interface
python main.py --mode web
```

### Using the Web Interface

The web interface provides a user-friendly way to interact with the trading bot:

1. Start the web interface: `python main.py --mode web`
2. Open your browser and navigate to: `http://127.0.0.1:5000`
3. Use the dashboard to monitor performance, view charts, manage trades, and adjust settings

## Configuration

Edit the configuration files in the `config` directory to customize:

- Trading pairs and timeframes
- Technical indicators parameters
- AI model hyperparameters
- Risk management settings
- API connections

## Disclaimer

Trading forex involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. This software is for educational purposes only and should not be used as financial advice.

## License

MIT