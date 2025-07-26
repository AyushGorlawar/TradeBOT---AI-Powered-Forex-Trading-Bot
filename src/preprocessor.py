#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data preprocessor module for cleaning and preparing forex data for analysis
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger("TradeBOT.Preprocessor")


class DataPreprocessor:
    """Class for preprocessing and cleaning forex data"""
    
    def __init__(self, config=None):
        """Initialize the data preprocessor
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        self.config = config or {}
    
    def process(self, data):
        """Process and clean the data
        
        Args:
            data (list or pandas.DataFrame): Raw price data
            
        Returns:
            pandas.DataFrame: Processed and cleaned DataFrame
        """
        # Convert list of dictionaries to DataFrame if needed
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                df = pd.DataFrame(data)
            else:
                logger.error("Invalid data format: list items are not dictionaries")
                return pd.DataFrame()
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            logger.error(f"Invalid data type: {type(data)}")
            return pd.DataFrame()
        
        # Process the DataFrame
        df = self._clean_data(df)
        df = self._format_data(df)
        df = self._add_features(df)
        
        return df
    
    def _clean_data(self, df):
        """Clean the data by handling missing values, duplicates, etc.
        
        Args:
            df (pandas.DataFrame): Raw DataFrame
            
        Returns:
            pandas.DataFrame: Cleaned DataFrame
        """
        # Check if DataFrame is empty
        if df.empty:
            logger.warning("Empty DataFrame provided for cleaning")
            return df
        
        # Make sure we have the required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close']
        
        # Check if 'timestamp' is in columns or is the index
        if 'timestamp' not in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            logger.warning("No timestamp column or datetime index found")
            if 'time' in df.columns:
                df['timestamp'] = df['time']
            else:
                # Create a timestamp column with current time
                df['timestamp'] = datetime.now()
        
        # Set timestamp as index if it's not already
        if 'timestamp' in df.columns:
            # Convert to datetime if not already
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            
            # Set as index
            df.set_index('timestamp', inplace=True)
        
        # Check for missing required columns
        missing_columns = [col for col in required_columns[1:] if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing required columns: {missing_columns}")
            # Try to infer missing columns if possible
            if 'open' not in df.columns and 'close' in df.columns:
                df['open'] = df['close'].shift(1)
            if 'high' not in df.columns and 'close' in df.columns and 'open' in df.columns:
                df['high'] = df[['open', 'close']].max(axis=1)
            if 'low' not in df.columns and 'close' in df.columns and 'open' in df.columns:
                df['low'] = df[['open', 'close']].min(axis=1)
        
        # Add volume column if missing
        if 'volume' not in df.columns:
            df['volume'] = 0
        
        # Handle missing values
        # Forward fill missing values (use previous values)
        df.fillna(method='ffill', inplace=True)
        
        # If still have missing values at the beginning, backward fill
        df.fillna(method='bfill', inplace=True)
        
        # If still have missing values, fill with zeros
        df.fillna(0, inplace=True)
        
        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]
        
        # Sort by timestamp
        df.sort_index(inplace=True)
        
        return df
    
    def _format_data(self, df):
        """Format the data for analysis
        
        Args:
            df (pandas.DataFrame): Cleaned DataFrame
            
        Returns:
            pandas.DataFrame: Formatted DataFrame
        """
        # Check if DataFrame is empty
        if df.empty:
            return df
        
        # Convert numeric columns to float
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Ensure all prices are positive
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                df.loc[df[col] <= 0, col] = np.nan
                # Forward fill any new NaNs
                df[col].fillna(method='ffill', inplace=True)
                df[col].fillna(method='bfill', inplace=True)
        
        # Ensure high is the highest price and low is the lowest price
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            # Calculate the max and min of open, high, low, close for each row
            df['true_high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
            df['true_low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
            
            # Replace high and low with true_high and true_low
            df['high'] = df['true_high']
            df['low'] = df['true_low']
            
            # Drop temporary columns
            df.drop(['true_high', 'true_low'], axis=1, inplace=True)
        
        return df
    
    def _add_features(self, df):
        """Add basic features to the data
        
        Args:
            df (pandas.DataFrame): Formatted DataFrame
            
        Returns:
            pandas.DataFrame: DataFrame with added features
        """
        # Check if DataFrame is empty
        if df.empty:
            return df
        
        # Add basic price features
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            # Range and mid-price
            df['range'] = df['high'] - df['low']
            df['mid_price'] = (df['high'] + df['low']) / 2
            
            # Body size and direction
            df['body_size'] = abs(df['close'] - df['open'])
            df['body_ratio'] = df['body_size'] / df['range'].replace(0, np.nan)
            df['direction'] = np.where(df['close'] > df['open'], 1, np.where(df['close'] < df['open'], -1, 0))
            
            # Upper and lower shadows
            df['upper_shadow'] = np.where(df['close'] >= df['open'], 
                                         df['high'] - df['close'], 
                                         df['high'] - df['open'])
            df['lower_shadow'] = np.where(df['close'] >= df['open'], 
                                         df['open'] - df['low'], 
                                         df['close'] - df['low'])
            
            # Shadow ratios
            df['upper_shadow_ratio'] = df['upper_shadow'] / df['range'].replace(0, np.nan)
            df['lower_shadow_ratio'] = df['lower_shadow'] / df['range'].replace(0, np.nan)
        
        # Add time-based features
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6])  # 5=Saturday, 6=Sunday
        
        # Add return features
        df['return'] = df['close'].pct_change()
        df['return_1d'] = df['close'].pct_change(periods=24)  # Assuming 1-hour candles
        
        # Add volatility features
        df['volatility'] = df['return'].rolling(window=24).std()  # 24-hour volatility
        
        # Fill NaN values created by calculations
        df.fillna(method='ffill', inplace=True)
        df.fillna(0, inplace=True)
        
        return df
    
    def create_ml_features(self, df, lookback_periods=5):
        """Create features for machine learning models
        
        Args:
            df (pandas.DataFrame): DataFrame with indicators
            lookback_periods (int, optional): Number of previous periods to include. Defaults to 5.
            
        Returns:
            pandas.DataFrame: DataFrame with ML features
        """
        # Check if DataFrame is empty
        if df.empty:
            return df
        
        # Create a copy to avoid modifying the original
        ml_df = df.copy()
        
        # List of features to include
        feature_columns = [
            'close', 'return', 'range', 'body_size', 'direction',
            'upper_shadow_ratio', 'lower_shadow_ratio', 'volatility'
        ]
        
        # Add indicator columns if they exist
        indicator_columns = [
            'rsi', 'macd', 'macd_histogram', 'bb_width', 
            'stoch_k', 'stoch_d', 'adx', 'atr'
        ]
        
        for col in indicator_columns:
            if col in ml_df.columns:
                feature_columns.append(col)
        
        # Create lagged features
        for col in feature_columns:
            if col in ml_df.columns:
                for i in range(1, lookback_periods + 1):
                    ml_df[f'{col}_lag_{i}'] = ml_df[col].shift(i)
        
        # Drop rows with NaN values (due to lagging)
        ml_df.dropna(inplace=True)
        
        return ml_df
    
    def create_target_variable(self, df, target_type='direction', periods_ahead=1):
        """Create target variable for machine learning models
        
        Args:
            df (pandas.DataFrame): DataFrame with features
            target_type (str, optional): Type of target variable. Defaults to 'direction'.
            periods_ahead (int, optional): Number of periods ahead to predict. Defaults to 1.
            
        Returns:
            pandas.DataFrame: DataFrame with target variable
        """
        # Check if DataFrame is empty
        if df.empty:
            return df
        
        # Create a copy to avoid modifying the original
        target_df = df.copy()
        
        if target_type == 'direction':
            # Direction: 1 (up), -1 (down), 0 (unchanged)
            future_close = target_df['close'].shift(-periods_ahead)
            target_df['target'] = np.where(future_close > target_df['close'], 1, 
                                        np.where(future_close < target_df['close'], -1, 0))
        
        elif target_type == 'return':
            # Future return
            target_df['target'] = target_df['close'].pct_change(periods=periods_ahead).shift(-periods_ahead)
        
        elif target_type == 'volatility':
            # Future volatility
            target_df['target'] = target_df['close'].pct_change(periods=periods_ahead).shift(-periods_ahead).abs()
        
        elif target_type == 'binary':
            # Binary: 1 (up), 0 (down or unchanged)
            future_close = target_df['close'].shift(-periods_ahead)
            target_df['target'] = np.where(future_close > target_df['close'], 1, 0)
        
        else:
            logger.warning(f"Unknown target type: {target_type}, defaulting to 'direction'")
            future_close = target_df['close'].shift(-periods_ahead)
            target_df['target'] = np.where(future_close > target_df['close'], 1, 
                                        np.where(future_close < target_df['close'], -1, 0))
        
        # Drop rows with NaN target values
        target_df.dropna(subset=['target'], inplace=True)
        
        return target_df