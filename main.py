#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TradeBOT - AI-Powered Forex Trading Bot
Main entry point for the trading bot
"""
import os
import sys
import time
import logging
import argparse
from datetime import datetime, timedelta
import threading
from dotenv import load_dotenv

# Local imports
from src.data_fetcher import DataFetcher
from src.preprocessor import DataPreprocessor
from src.indicators import TechnicalIndicators
from src.signal_generator import SignalGenerator
from src.trade_executor import TradeExecutor
from src.risk_manager import RiskManager
from src.ml_model import MLModel
from src.visualizer import Visualizer
from src.web_interface import WebInterface
from src.backtester import Backtester
from config.config import Config
from config.pairs import CURRENCY_PAIRS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tradebot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TradeBOT")

# Load environment variables
load_dotenv()


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="TradeBOT - AI-Powered Forex Trading Bot")
    parser.add_argument('--mode', type=str, default='live', choices=['live', 'paper', 'backtest', 'web'],
                        help='Trading mode: live, paper, backtest, or web interface')
    parser.add_argument('--pairs', type=str, nargs='+', default=None,
                        help='Specific currency pairs to trade (default: all configured pairs)')
    parser.add_argument('--timeframe', type=str, default='1h',
                        help='Trading timeframe (e.g., 1m, 5m, 15m, 1h, 4h, 1d)')
    parser.add_argument('--strategy', type=str, default='ml',
                        help='Trading strategy to use (ml, combined, rsi, macd, bollinger, moving_average, stochastic)')
    parser.add_argument('--backtest-days', type=int, default=30,
                        help='Number of days to backtest (only used in backtest mode)')
    return parser.parse_args()


class TradeBOT:
    """Main TradeBOT class that orchestrates the trading system"""
    
    def __init__(self, config, mode='live', pairs=None, timeframe='1h', strategy='ml'):
        """
        Initialize TradeBOT
        
        Args:
            config (dict): Configuration dictionary
            mode (str): Trading mode ('live', 'paper', 'backtest', 'web')
            pairs (list): List of currency pairs to trade
            timeframe (str): Trading timeframe
            strategy (str): Trading strategy to use
        """
        self.config = config
        self.mode = mode
        self.timeframe = timeframe
        self.strategy = strategy
        
        # Use specified pairs or all configured pairs
        self.pairs = pairs if pairs else list(CURRENCY_PAIRS.keys())
        logger.info(f"Initializing TradeBOT with {len(self.pairs)} currency pairs")
        
        # Initialize components
        self.data_fetcher = DataFetcher(config)
        self.preprocessor = DataPreprocessor()
        self.indicators = TechnicalIndicators()
        self.risk_manager = RiskManager(config)
        
        # Initialize ML model
        self.ml_model = MLModel(config)
        self.ml_model.load_model()
        
        # Initialize signal generator
        self.signal_generator = SignalGenerator(config, self.ml_model)
        
        # Initialize trade executor
        self.trade_executor = TradeExecutor(config, self.risk_manager)
        # Set paper trading mode if not live
        if mode != 'live':
            self.trade_executor.is_paper_trading = True
        
        # Initialize visualizer
        self.visualizer = Visualizer(config)
        
        # Initialize backtester
        self.backtester = Backtester(
            config=config,
            data_fetcher=self.data_fetcher,
            indicators=self.indicators,
            signal_generator=self.signal_generator,
            risk_manager=self.risk_manager,
            visualizer=self.visualizer
        )
        
        # Initialize web interface
        self.web_interface = None
        if mode == 'web' or config.get('web_interface', {}).get('enabled', False):
            self.web_interface = WebInterface(
                config=config,
                data_fetcher=self.data_fetcher,
                signal_generator=self.signal_generator,
                risk_manager=self.risk_manager,
                trade_executor=self.trade_executor,
                visualizer=self.visualizer
            )
        
        # Data storage for each pair
        self.price_buffers = {pair: [] for pair in self.pairs}
        
        # Trading state
        self.is_running = False
        self.trading_thread = None
        
        logger.info(f"TradeBOT initialized in {mode} mode with {strategy} strategy")
    
    def start(self):
        """Start the trading bot"""
        if self.mode == 'backtest':
            self.run_backtest()
        elif self.mode == 'web':
            self.start_web_interface()
        else:
            self.start_trading()
    
    def start_trading(self):
        """Start the trading loop in a separate thread"""
        if self.is_running:
            logger.warning("Trading already running")
            return
        
        self.is_running = True
        self.trading_thread = threading.Thread(target=self.trading_loop)
        self.trading_thread.daemon = True
        self.trading_thread.start()
        
        logger.info("Trading started")
        
        # Start web interface if enabled
        if self.web_interface:
            self.start_web_interface()
    
    def stop_trading(self):
        """Stop the trading loop"""
        self.is_running = False
        if self.trading_thread:
            self.trading_thread.join(timeout=5.0)
            self.trading_thread = None
        
        logger.info("Trading stopped")
    
    def trading_loop(self):
        """Main trading loop"""
        logger.info("Starting TradeBOT trading loop")
        
        try:
            while self.is_running:
                for pair in self.pairs:
                    try:
                        # Fetch latest price data
                        latest_data = self.data_fetcher.get_historical_data(
                            pair, self.timeframe, limit=100
                        )
                        
                        if latest_data.empty:
                            logger.warning(f"No data received for {pair}")
                            continue
                        
                        # Preprocess data
                        processed_data = self.preprocessor.process(latest_data)
                        
                        # Calculate technical indicators
                        data_with_indicators = self.indicators.calculate_all(processed_data)
                        
                        # Generate trading signal
                        signal_data = self.signal_generator.generate_signals(
                            data_with_indicators, method=self.strategy
                        )
                        
                        # Get the latest signal
                        signal = self.signal_generator.get_latest_signal(signal_data)
                        
                        if signal['signal'] != 0:  # If we have a buy or sell signal
                            # Execute trade
                            self.trade_executor.execute_signal(
                                pair, signal, data_with_indicators
                            )
                    
                    except Exception as e:
                        logger.error(f"Error processing {pair}: {str(e)}")
                
                # Check for closed trades
                self.trade_executor.check_open_trades()
                
                # Sleep to avoid API rate limits
                time.sleep(self.config.get('loop_interval', 60))
        
        except Exception as e:
            logger.error(f"TradeBOT trading loop encountered an error: {str(e)}")
        finally:
            logger.info("Trading loop stopped")
    
    def run_backtest(self):
        """Run backtest on historical data"""
        logger.info("Starting backtest")
        
        # Get backtest parameters
        backtest_days = self.config.get('backtest', {}).get('days', 30)
        initial_balance = self.config.get('backtest', {}).get('initial_balance', 10000)
        
        # Run backtest for each pair
        for pair in self.pairs:
            try:
                logger.info(f"Running backtest for {pair} over {backtest_days} days")
                
                # Calculate start and end dates for backtest
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=backtest_days)).strftime('%Y-%m-%d')
                
                # Run backtest
                results = self.backtester.run_backtest(
                    pairs=[pair],
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=self.timeframe
                )
                
                # Print backtest results
                print(f"\nBacktest Results for {pair}:")
                print(f"Total Return: {results['performance']['return_pct']:.2f}%")
                print(f"Total P&L: ${results['performance']['total_pnl']:.2f}")
                print(f"Win Rate: {results['performance']['win_rate']*100:.2f}%")
                print(f"Profit Factor: {results['performance']['profit_factor']:.2f}")
                print(f"Max Drawdown: {results['performance']['max_drawdown_pct']:.2f}%")
                print(f"Sharpe Ratio: {results['performance']['sharpe_ratio']:.2f}")
                print(f"Total Trades: {results['performance']['total_trades']}")
                
                # Generate and save backtest report
                report_path = self.backtester.generate_report(results, pair, self.timeframe, self.strategy)
                if report_path:
                    print(f"Backtest report saved to: {report_path}")
                
                # Generate and save equity curve chart
                chart_path = self.visualizer.create_performance_chart(
                    results['trades'],
                    results['balance_history'],
                    f"charts/{pair}_{self.timeframe}_{self.strategy}_equity.png"
                )
                if chart_path:
                    print(f"Equity curve chart saved to: {chart_path}")
            
            except Exception as e:
                logger.error(f"Error running backtest for {pair}: {str(e)}")
        
        logger.info("Backtest completed")
    
    def start_web_interface(self):
        """Start the web interface"""
        if not self.web_interface:
            logger.error("Web interface not initialized")
            return
        
        try:
            # Start web interface
            web_config = self.config.get('web_interface', {})
            host = web_config.get('host', '127.0.0.1')
            port = web_config.get('port', 5000)
            debug = web_config.get('debug', False)
            
            logger.info(f"Starting web interface on {host}:{port}")
            self.web_interface.run(host=host, port=port, debug=debug)
        
        except Exception as e:
            logger.error(f"Error starting web interface: {str(e)}")


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config = Config().get_config()
    
    # Initialize and run the bot
    bot = TradeBOT(
        config=config,
        mode=args.mode,
        pairs=args.pairs,
        timeframe=args.timeframe,
        strategy=args.strategy
    )
    
    # Start the bot
    bot.start()