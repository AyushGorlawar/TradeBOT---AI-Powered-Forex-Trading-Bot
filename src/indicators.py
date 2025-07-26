#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Technical indicators module for calculating various technical analysis indicators
"""

import logging
import pandas as pd
import numpy as np
import ta

logger = logging.getLogger("TradeBOT.Indicators")


class TechnicalIndicators:
    """Class for calculating technical indicators on price data"""
    
    def __init__(self, config=None):
        """Initialize the technical indicators calculator
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        self.config = config or {}
        self.indicators_config = self.config.get('indicators', {})
    
    def calculate_all(self, df):
        """Calculate all configured technical indicators
        
        Args:
            df (pandas.DataFrame): DataFrame with price data (OHLCV)
            
        Returns:
            pandas.DataFrame: DataFrame with added technical indicators
        """
        df = df.copy()
        
        # Make sure we have the required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"Missing required columns: {missing_columns}")
            # Add missing columns with NaN values
            for col in missing_columns:
                if col == 'volume':  # Default volume to 0 if missing
                    df[col] = 0
                else:
                    df[col] = np.nan
        
        # Calculate indicators based on configuration
        if self.indicators_config.get('rsi', {}).get('enabled', True):
            df = self.add_rsi(df)
        
        if self.indicators_config.get('macd', {}).get('enabled', True):
            df = self.add_macd(df)
        
        if self.indicators_config.get('bollinger_bands', {}).get('enabled', True):
            df = self.add_bollinger_bands(df)
        
        if self.indicators_config.get('moving_averages', {}).get('enabled', True):
            df = self.add_moving_averages(df)
        
        if self.indicators_config.get('stochastic', {}).get('enabled', False):
            df = self.add_stochastic(df)
        
        if self.indicators_config.get('atr', {}).get('enabled', False):
            df = self.add_atr(df)
        
        if self.indicators_config.get('adx', {}).get('enabled', False):
            df = self.add_adx(df)
        
        # Add custom indicators
        df = self.add_custom_indicators(df)
        
        return df
    
    def add_rsi(self, df, period=None):
        """Add Relative Strength Index (RSI) to the DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            period (int, optional): RSI period. Defaults to None (uses config).
            
        Returns:
            pandas.DataFrame: DataFrame with added RSI
        """
        try:
            rsi_config = self.indicators_config.get('rsi', {})
            period = period or rsi_config.get('period', 14)
            
            # Calculate RSI
            rsi = ta.momentum.RSIIndicator(close=df['close'], window=period)
            df['rsi'] = rsi.rsi()
            
            # Add overbought/oversold signals
            overbought = rsi_config.get('overbought', 70)
            oversold = rsi_config.get('oversold', 30)
            
            df['rsi_overbought'] = df['rsi'] > overbought
            df['rsi_oversold'] = df['rsi'] < oversold
            
            return df
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            df['rsi'] = np.nan
            df['rsi_overbought'] = False
            df['rsi_oversold'] = False
            return df
    
    def add_macd(self, df, fast_period=None, slow_period=None, signal_period=None):
        """Add Moving Average Convergence Divergence (MACD) to the DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            fast_period (int, optional): Fast period. Defaults to None (uses config).
            slow_period (int, optional): Slow period. Defaults to None (uses config).
            signal_period (int, optional): Signal period. Defaults to None (uses config).
            
        Returns:
            pandas.DataFrame: DataFrame with added MACD
        """
        try:
            macd_config = self.indicators_config.get('macd', {})
            fast_period = fast_period or macd_config.get('fast_period', 12)
            slow_period = slow_period or macd_config.get('slow_period', 26)
            signal_period = signal_period or macd_config.get('signal_period', 9)
            
            # Calculate MACD
            macd_indicator = ta.trend.MACD(
                close=df['close'],
                window_fast=fast_period,
                window_slow=slow_period,
                window_sign=signal_period
            )
            
            df['macd'] = macd_indicator.macd()
            df['macd_signal'] = macd_indicator.macd_signal()
            df['macd_histogram'] = macd_indicator.macd_diff()
            
            # Add crossover signals
            df['macd_bullish_crossover'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
            df['macd_bearish_crossover'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
            
            return df
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            df['macd'] = np.nan
            df['macd_signal'] = np.nan
            df['macd_histogram'] = np.nan
            df['macd_bullish_crossover'] = False
            df['macd_bearish_crossover'] = False
            return df
    
    def add_bollinger_bands(self, df, period=None, std_dev=None):
        """Add Bollinger Bands to the DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            period (int, optional): Bollinger Bands period. Defaults to None (uses config).
            std_dev (float, optional): Standard deviation multiplier. Defaults to None (uses config).
            
        Returns:
            pandas.DataFrame: DataFrame with added Bollinger Bands
        """
        try:
            bb_config = self.indicators_config.get('bollinger_bands', {})
            period = period or bb_config.get('period', 20)
            std_dev = std_dev or bb_config.get('std_dev', 2)
            
            # Calculate Bollinger Bands
            bollinger = ta.volatility.BollingerBands(
                close=df['close'],
                window=period,
                window_dev=std_dev
            )
            
            df['bb_upper'] = bollinger.bollinger_hband()
            df['bb_middle'] = bollinger.bollinger_mavg()
            df['bb_lower'] = bollinger.bollinger_lband()
            df['bb_width'] = bollinger.bollinger_wband()
            
            # Add signals
            df['bb_upper_breakout'] = df['close'] > df['bb_upper']
            df['bb_lower_breakout'] = df['close'] < df['bb_lower']
            
            return df
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            df['bb_upper'] = np.nan
            df['bb_middle'] = np.nan
            df['bb_lower'] = np.nan
            df['bb_width'] = np.nan
            df['bb_upper_breakout'] = False
            df['bb_lower_breakout'] = False
            return df
    
    def add_moving_averages(self, df, periods=None):
        """Add Simple Moving Averages (SMA) to the DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            periods (list, optional): List of periods. Defaults to None (uses config).
            
        Returns:
            pandas.DataFrame: DataFrame with added SMAs
        """
        try:
            ma_config = self.indicators_config.get('moving_averages', {})
            periods = periods or ma_config.get('periods', [20, 50, 200])
            
            # Calculate SMAs for each period
            for period in periods:
                sma = ta.trend.SMAIndicator(close=df['close'], window=period)
                df[f'sma_{period}'] = sma.sma_indicator()
            
            # Add crossover signals for common combinations
            if 20 in periods and 50 in periods:
                df['sma_20_50_bullish_crossover'] = (df['sma_20'] > df['sma_50']) & (df['sma_20'].shift(1) <= df['sma_50'].shift(1))
                df['sma_20_50_bearish_crossover'] = (df['sma_20'] < df['sma_50']) & (df['sma_20'].shift(1) >= df['sma_50'].shift(1))
            
            if 50 in periods and 200 in periods:
                df['sma_50_200_bullish_crossover'] = (df['sma_50'] > df['sma_200']) & (df['sma_50'].shift(1) <= df['sma_200'].shift(1))
                df['sma_50_200_bearish_crossover'] = (df['sma_50'] < df['sma_200']) & (df['sma_50'].shift(1) >= df['sma_200'].shift(1))
            
            return df
        except Exception as e:
            logger.error(f"Error calculating Moving Averages: {str(e)}")
            for period in periods or [20, 50, 200]:
                df[f'sma_{period}'] = np.nan
            return df
    
    def add_stochastic(self, df, k_period=None, d_period=None, slowing=None):
        """Add Stochastic Oscillator to the DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            k_period (int, optional): %K period. Defaults to None (uses config).
            d_period (int, optional): %D period. Defaults to None (uses config).
            slowing (int, optional): Slowing period. Defaults to None (uses config).
            
        Returns:
            pandas.DataFrame: DataFrame with added Stochastic Oscillator
        """
        try:
            stoch_config = self.indicators_config.get('stochastic', {})
            k_period = k_period or stoch_config.get('k_period', 14)
            d_period = d_period or stoch_config.get('d_period', 3)
            slowing = slowing or stoch_config.get('slowing', 3)
            
            # Calculate Stochastic Oscillator
            stoch = ta.momentum.StochasticOscillator(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=k_period,
                smooth_window=d_period
            )
            
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            # Add overbought/oversold signals
            overbought = stoch_config.get('overbought', 80)
            oversold = stoch_config.get('oversold', 20)
            
            df['stoch_overbought'] = df['stoch_k'] > overbought
            df['stoch_oversold'] = df['stoch_k'] < oversold
            
            # Add crossover signals
            df['stoch_bullish_crossover'] = (df['stoch_k'] > df['stoch_d']) & (df['stoch_k'].shift(1) <= df['stoch_d'].shift(1))
            df['stoch_bearish_crossover'] = (df['stoch_k'] < df['stoch_d']) & (df['stoch_k'].shift(1) >= df['stoch_d'].shift(1))
            
            return df
        except Exception as e:
            logger.error(f"Error calculating Stochastic Oscillator: {str(e)}")
            df['stoch_k'] = np.nan
            df['stoch_d'] = np.nan
            df['stoch_overbought'] = False
            df['stoch_oversold'] = False
            df['stoch_bullish_crossover'] = False
            df['stoch_bearish_crossover'] = False
            return df
    
    def add_atr(self, df, period=None):
        """Add Average True Range (ATR) to the DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            period (int, optional): ATR period. Defaults to None (uses config).
            
        Returns:
            pandas.DataFrame: DataFrame with added ATR
        """
        try:
            atr_config = self.indicators_config.get('atr', {})
            period = period or atr_config.get('period', 14)
            
            # Calculate ATR
            atr = ta.volatility.AverageTrueRange(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=period
            )
            
            df['atr'] = atr.average_true_range()
            
            # Add ATR percentage (ATR relative to price)
            df['atr_percent'] = (df['atr'] / df['close']) * 100
            
            return df
        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            df['atr'] = np.nan
            df['atr_percent'] = np.nan
            return df
    
    def add_adx(self, df, period=None):
        """Add Average Directional Index (ADX) to the DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            period (int, optional): ADX period. Defaults to None (uses config).
            
        Returns:
            pandas.DataFrame: DataFrame with added ADX
        """
        try:
            adx_config = self.indicators_config.get('adx', {})
            period = period or adx_config.get('period', 14)
            
            # Calculate ADX
            adx_indicator = ta.trend.ADXIndicator(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=period
            )
            
            df['adx'] = adx_indicator.adx()
            df['adx_pos'] = adx_indicator.adx_pos()
            df['adx_neg'] = adx_indicator.adx_neg()
            
            # Add trend strength signals
            trend_threshold = adx_config.get('trend_threshold', 25)
            df['adx_strong_trend'] = df['adx'] > trend_threshold
            
            # Add directional signals
            df['adx_bullish'] = (df['adx_pos'] > df['adx_neg']) & df['adx_strong_trend']
            df['adx_bearish'] = (df['adx_pos'] < df['adx_neg']) & df['adx_strong_trend']
            
            return df
        except Exception as e:
            logger.error(f"Error calculating ADX: {str(e)}")
            df['adx'] = np.nan
            df['adx_pos'] = np.nan
            df['adx_neg'] = np.nan
            df['adx_strong_trend'] = False
            df['adx_bullish'] = False
            df['adx_bearish'] = False
            return df
    
    def add_custom_indicators(self, df):
        """Add custom indicators to the DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with price data
            
        Returns:
            pandas.DataFrame: DataFrame with added custom indicators
        """
        # Add price momentum
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        
        # Add volatility indicator
        df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
        
        # Add price distance from moving averages
        if 'sma_20' in df.columns:
            df['price_distance_sma_20'] = (df['close'] - df['sma_20']) / df['sma_20']
        
        if 'sma_50' in df.columns:
            df['price_distance_sma_50'] = (df['close'] - df['sma_50']) / df['sma_50']
        
        # Add combined signal indicators
        if all(col in df.columns for col in ['rsi', 'macd', 'macd_signal']):
            # Combined oversold condition
            df['combined_oversold'] = (df['rsi'] < 30) & (df['macd'] < 0) & (df['macd'] > df['macd_signal'])
            
            # Combined overbought condition
            df['combined_overbought'] = (df['rsi'] > 70) & (df['macd'] > 0) & (df['macd'] < df['macd_signal'])
        
        return df