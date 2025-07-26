#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration settings for the TradeBOT
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for TradeBOT"""
    
    def __init__(self, config_file=None):
        """Initialize configuration
        
        Args:
            config_file (str, optional): Path to custom config file. Defaults to None.
        """
        self.config_file = config_file or os.path.join(os.path.dirname(__file__), 'config.json')
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Create default configuration
            default_config = self._create_default_config()
            self._save_config(default_config)
            return default_config
    
    def _create_default_config(self):
        """Create default configuration settings"""
        return {
            # General settings
            "app_name": "TradeBOT",
            "version": "1.0.0",
            "log_level": "INFO",
            "loop_interval": 60,  # seconds between iterations
            "buffer_size": 100,   # max size of price buffer
            "min_buffer_size": 30,  # min data points needed for analysis
            
            # Data settings
            "default_timeframe": "1m",  # 1 minute candles
            "historical_days": 30,      # days of historical data to fetch
            
            # Trading settings
            "default_mode": "paper",  # 'live', 'paper', or 'backtest'
            "max_open_positions": 5,  # maximum number of open positions
            "default_leverage": 1,    # default leverage (1 = no leverage)
            
            # Risk management
            "risk_per_trade": 0.02,    # percentage of account to risk per trade (2%)
            "max_risk_per_day": 0.06,  # maximum daily risk (6%)
            "default_stop_loss": 0.02,  # default stop loss percentage (2%)
            "default_take_profit": 0.04,  # default take profit percentage (4%)
            "trailing_stop": True,       # use trailing stop
            "trailing_stop_activation": 0.01,  # activate trailing stop after 1% profit
            "trailing_stop_distance": 0.01,   # trailing stop follows price at 1% distance
            
            # Technical indicators
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "overbought": 70,
                    "oversold": 30
                },
                "macd": {
                    "enabled": True,
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9
                },
                "bollinger_bands": {
                    "enabled": True,
                    "period": 20,
                    "std_dev": 2
                },
                "moving_averages": {
                    "enabled": True,
                    "periods": [20, 50, 200]
                }
            },
            
            # ML model settings
            "model": {
                "type": "classifier",  # classifier or regressor
                "algorithm": "random_forest",  # random_forest, xgboost, neural_network
                "features": ["rsi", "macd", "bollinger_bands", "moving_averages"],
                "target": "direction",  # price direction (up/down)
                "train_test_split": 0.2,  # 20% test data
                "lookback_periods": 5,  # use 5 previous candles for prediction
                "prediction_threshold": 0.65,  # minimum probability for signal
                "retrain_interval": 7,  # days between model retraining
            },
            
            # API settings
            "oanda": {
                "api_key": os.getenv("OANDA_API_KEY", ""),
                "account_id": os.getenv("OANDA_ACCOUNT_ID", ""),
                "base_url": "https://api-fxpractice.oanda.com",  # practice account
                # "base_url": "https://api-fxtrade.oanda.com",  # live account
            }
        }
    
    def _save_config(self, config):
        """Save configuration to file"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
    
    def get_config(self):
        """Get the current configuration"""
        return self.config
    
    def update_config(self, updates):
        """Update configuration with new values
        
        Args:
            updates (dict): Dictionary of configuration updates
        """
        # Recursively update nested dictionaries
        def update_nested(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    update_nested(d[k], v)
                else:
                    d[k] = v
        
        update_nested(self.config, updates)
        self._save_config(self.config)
        return self.config


# Create config.json file if it doesn't exist
if __name__ == "__main__":
    config = Config()
    print(f"Configuration file created/loaded at: {config.config_file}")
    print(json.dumps(config.get_config(), indent=4))