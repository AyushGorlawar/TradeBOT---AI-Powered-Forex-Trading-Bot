#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the Backtester module
"""

import sys
import os
import logging
import json
from datetime import datetime, timedelta

# Add src directory to path
sys.path.append('src')

# Import backtester only
from backtester import Backtester

# Create mock classes for testing
class MockConfig:
    def __init__(self):
        self.config = {
            'backtest': {
                'initial_balance': 10000,
                'commission': 0.0001,
                'slippage': 0.0001,
                'leverage': 1,
                'results_dir': 'backtest_results'
            }
        }
    
    def get_config(self):
        return self.config
        
    def load_config(self, path):
        try:
            with open(path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")

class MockDataFetcher:
    def __init__(self, config):
        self.config = config
    
    def get_historical_data(self, pair, timeframe, limit=None):
        # Return mock data
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # Create date range (last 'limit' hours)
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=limit or 100)
        date_range = pd.date_range(start=start_date, end=end_date, freq='H')
        
        # Create mock OHLCV data
        data = {
            'timestamp': date_range,
            'open': np.random.normal(1.1, 0.01, len(date_range)),
            'high': np.random.normal(1.11, 0.01, len(date_range)),
            'low': np.random.normal(1.09, 0.01, len(date_range)),
            'close': np.random.normal(1.1, 0.01, len(date_range)),
            'volume': np.random.randint(100, 1000, len(date_range))
        }
        
        return pd.DataFrame(data)

class MockIndicators:
    def __init__(self, config):
        self.config = config
    
    def calculate_all(self, df):
        # Add mock indicators
        df['rsi'] = 50
        df['macd'] = 0
        df['macd_signal'] = 0
        df['macd_hist'] = 0
        df['bb_upper'] = df['close'] + 0.01
        df['bb_middle'] = df['close']
        df['bb_lower'] = df['close'] - 0.01
        return df
    
    def calculate_indicators(self, df):
        # For backward compatibility
        return self.calculate_all(df)

class MockSignalGenerator:
    def __init__(self, config, indicators):
        self.config = config
        self.indicators = indicators
    
    def generate_signals(self, df, pair=None):
        # Add mock signals
        import numpy as np
        df['signal'] = np.random.choice([-1, 0, 1], size=len(df))
        df['signal_strength'] = np.random.random(len(df))
        return df

class MockRiskManager:
    def __init__(self, config):
        self.config = config
    
    def calculate_position_size(self, balance, pair, direction, entry_price, stop_loss=None):
        # Return mock position size
        return 0.1 * balance
    
    def calculate_stop_loss(self, pair, direction, entry_price, current_row=None, atr=None):
        # Return mock stop loss
        import pandas as pd
        if isinstance(direction, pd.Series):
            direction = direction.iloc[0] if not direction.empty else 0
            
        if direction == 1:  # Long
            return entry_price * 0.99  # 1% below entry
        else:  # Short
            return entry_price * 1.01  # 1% above entry
    
    def calculate_take_profit(self, pair, direction, entry_price, current_row=None):
        # Return mock take profit
        import pandas as pd
        if isinstance(direction, pd.Series):
            direction = direction.iloc[0] if not direction.empty else 0
            
        if direction == 1:  # Long
            return entry_price * 1.02  # 2% above entry
        else:  # Short
            return entry_price * 0.98  # 2% below entry

class MockVisualizer:
    def __init__(self, config):
        self.config = config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("TradeBOT.TestBacktester")

def main():
    # Load configuration
    config = MockConfig()
    try:
        config.load_config('config/config.json')
    except Exception as e:
        logger.warning(f"Could not load config file, using default: {e}")
    
    # Initialize mock components
    data_fetcher = MockDataFetcher(config)
    indicators = MockIndicators(config)
    signal_generator = MockSignalGenerator(config, indicators)
    risk_manager = MockRiskManager(config)
    visualizer = MockVisualizer(config)
    
    # Initialize backtester
    backtester = Backtester(
        config=config.get_config(),
        data_fetcher=data_fetcher,
        indicators=indicators,
        signal_generator=signal_generator,
        risk_manager=risk_manager,
        visualizer=visualizer
    )
    
    logger.info("Backtester initialized successfully")
    
    # Test the calculate_performance method which had the syntax error
    logger.info("Testing calculate_performance method...")
    performance = backtester.calculate_performance()
    logger.info("Performance calculation successful")
    
    # Test a simple backtest if needed
    if '--run-backtest' in sys.argv:
        pair = "EUR_USD"
        timeframe = "H1"
        start_date = datetime.now() - timedelta(days=5)  # Use fewer days for faster testing
        end_date = datetime.now()
        
        logger.info(f"Running backtest for {pair} on {timeframe} from {start_date.date()} to {end_date.date()}")
        
        try:
            # Reset backtester results
            backtester.reset_results()
            
            # Run backtest for a single pair
            results = backtester.backtest_pair(
                pair=pair,
                start_date=start_date,
                end_date=end_date,
                timeframe=timeframe
            )
            
            # Calculate performance metrics
            performance = backtester.calculate_performance()
            
            # Print performance summary
            logger.info("Backtest completed successfully")
            logger.info(f"Total trades: {performance['total_trades']}")
            logger.info(f"Win rate: {performance['win_rate']*100:.2f}%")
            logger.info(f"Profit factor: {performance['profit_factor']:.2f}")
            logger.info(f"Total P&L: ${performance['total_pnl']:.2f}")
            logger.info(f"Return: {performance['return_pct']:.2f}%")
            logger.info(f"Max drawdown: {performance['max_drawdown_pct']*100:.2f}%")
            
        except Exception as e:
            logger.error(f"Error during backtest: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        logger.info("Skipping backtest run. Use --run-backtest to run a full backtest.")
        logger.info("Syntax check completed successfully.")
        logger.info("The error in backtester.py has been fixed.")


if __name__ == "__main__":
    main()