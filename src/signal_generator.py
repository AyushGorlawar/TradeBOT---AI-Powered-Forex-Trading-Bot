#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal Generator module for generating trading signals based on technical analysis and ML predictions
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger("TradeBOT.SignalGenerator")


class SignalGenerator:
    """Class for generating trading signals based on technical analysis and ML predictions"""
    
    def __init__(self, config=None, ml_model=None):
        """Initialize the signal generator
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
            ml_model (MLClassifier, optional): Trained ML model. Defaults to None.
        """
        self.config = config or {}
        self.signal_config = self.config.get('signals', {})
        self.ml_model = ml_model
        self.signal_methods = {
            'rsi': self._rsi_signal,
            'macd': self._macd_signal,
            'bollinger': self._bollinger_signal,
            'moving_average': self._moving_average_signal,
            'stochastic': self._stochastic_signal,
            'ml': self._ml_signal,
            'combined': self._combined_signal
        }
    
    def generate_signals(self, data, method='combined'):
        """Generate trading signals based on the specified method
        
        Args:
            data (pandas.DataFrame): DataFrame with price data and indicators
            method (str, optional): Signal generation method. Defaults to 'combined'.
            
        Returns:
            pandas.DataFrame: DataFrame with added signal columns
        """
        if data.empty:
            logger.warning("Empty DataFrame provided for signal generation")
            return data
        
        # Make a copy to avoid modifying the original
        df = data.copy()
        
        # Check if the method exists
        if method not in self.signal_methods:
            logger.warning(f"Unknown signal method: {method}, defaulting to 'combined'")
            method = 'combined'
        
        # Generate signals using the specified method
        df = self.signal_methods[method](df)
        
        # Add signal strength
        df = self._calculate_signal_strength(df)
        
        # Add signal metadata
        df['signal_method'] = method
        df['signal_timestamp'] = datetime.now()
        
        return df
    
    def _rsi_signal(self, df):
        """Generate signals based on RSI indicator
        
        Args:
            df (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            pandas.DataFrame: DataFrame with added signal columns
        """
        # Check if RSI column exists
        if 'rsi' not in df.columns:
            logger.warning("RSI column not found in DataFrame")
            df['signal'] = 0
            return df
        
        # Get RSI thresholds from config or use defaults
        rsi_config = self.signal_config.get('rsi', {})
        oversold = rsi_config.get('oversold', 30)
        overbought = rsi_config.get('overbought', 70)
        
        # Generate signals
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell
        
        # Buy signal: RSI crosses above oversold level
        df.loc[(df['rsi'] > oversold) & (df['rsi'].shift(1) <= oversold), 'signal'] = 1
        
        # Sell signal: RSI crosses below overbought level
        df.loc[(df['rsi'] < overbought) & (df['rsi'].shift(1) >= overbought), 'signal'] = -1
        
        return df
    
    def _macd_signal(self, df):
        """Generate signals based on MACD indicator
        
        Args:
            df (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            pandas.DataFrame: DataFrame with added signal columns
        """
        # Check if MACD columns exist
        required_columns = ['macd', 'macd_signal']
        if not all(col in df.columns for col in required_columns):
            logger.warning("MACD columns not found in DataFrame")
            df['signal'] = 0
            return df
        
        # Generate signals
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell
        
        # Buy signal: MACD crosses above signal line
        df.loc[(df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1)), 'signal'] = 1
        
        # Sell signal: MACD crosses below signal line
        df.loc[(df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1)), 'signal'] = -1
        
        # Additional signal: MACD histogram changes direction
        if 'macd_histogram' in df.columns:
            # Buy signal: MACD histogram turns positive from negative
            df.loc[(df['macd_histogram'] > 0) & (df['macd_histogram'].shift(1) <= 0), 'signal'] = 1
            
            # Sell signal: MACD histogram turns negative from positive
            df.loc[(df['macd_histogram'] < 0) & (df['macd_histogram'].shift(1) >= 0), 'signal'] = -1
        
        return df
    
    def _bollinger_signal(self, df):
        """Generate signals based on Bollinger Bands indicator
        
        Args:
            df (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            pandas.DataFrame: DataFrame with added signal columns
        """
        # Check if Bollinger Bands columns exist
        required_columns = ['bb_upper', 'bb_middle', 'bb_lower']
        if not all(col in df.columns for col in required_columns):
            logger.warning("Bollinger Bands columns not found in DataFrame")
            df['signal'] = 0
            return df
        
        # Generate signals
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell
        
        # Buy signal: Price crosses above lower band
        df.loc[(df['close'] > df['bb_lower']) & (df['close'].shift(1) <= df['bb_lower'].shift(1)), 'signal'] = 1
        
        # Sell signal: Price crosses below upper band
        df.loc[(df['close'] < df['bb_upper']) & (df['close'].shift(1) >= df['bb_upper'].shift(1)), 'signal'] = -1
        
        # Additional signal: Bollinger Band squeeze (volatility contraction)
        if 'bb_width' in df.columns:
            bb_config = self.signal_config.get('bollinger', {})
            squeeze_threshold = bb_config.get('squeeze_threshold', 0.1)
            
            # Buy signal: BB width expands after contraction
            df.loc[(df['bb_width'] > df['bb_width'].shift(1)) & 
                   (df['bb_width'].shift(1) < squeeze_threshold) & 
                   (df['close'] > df['bb_middle']), 'signal'] = 1
            
            # Sell signal: BB width expands after contraction
            df.loc[(df['bb_width'] > df['bb_width'].shift(1)) & 
                   (df['bb_width'].shift(1) < squeeze_threshold) & 
                   (df['close'] < df['bb_middle']), 'signal'] = -1
        
        return df
    
    def _moving_average_signal(self, df):
        """Generate signals based on Moving Average crossovers
        
        Args:
            df (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            pandas.DataFrame: DataFrame with added signal columns
        """
        # Check if Moving Average columns exist
        ma_config = self.signal_config.get('moving_average', {})
        fast_ma = ma_config.get('fast_ma', 'sma_20')
        slow_ma = ma_config.get('slow_ma', 'sma_50')
        
        if fast_ma not in df.columns or slow_ma not in df.columns:
            logger.warning(f"Moving Average columns ({fast_ma}, {slow_ma}) not found in DataFrame")
            df['signal'] = 0
            return df
        
        # Generate signals
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell
        
        # Buy signal: Fast MA crosses above Slow MA
        df.loc[(df[fast_ma] > df[slow_ma]) & (df[fast_ma].shift(1) <= df[slow_ma].shift(1)), 'signal'] = 1
        
        # Sell signal: Fast MA crosses below Slow MA
        df.loc[(df[fast_ma] < df[slow_ma]) & (df[fast_ma].shift(1) >= df[slow_ma].shift(1)), 'signal'] = -1
        
        return df
    
    def _stochastic_signal(self, df):
        """Generate signals based on Stochastic Oscillator
        
        Args:
            df (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            pandas.DataFrame: DataFrame with added signal columns
        """
        # Check if Stochastic columns exist
        required_columns = ['stoch_k', 'stoch_d']
        if not all(col in df.columns for col in required_columns):
            logger.warning("Stochastic columns not found in DataFrame")
            df['signal'] = 0
            return df
        
        # Get Stochastic thresholds from config or use defaults
        stoch_config = self.signal_config.get('stochastic', {})
        oversold = stoch_config.get('oversold', 20)
        overbought = stoch_config.get('overbought', 80)
        
        # Generate signals
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell
        
        # Buy signal: K crosses above D in oversold region
        df.loc[(df['stoch_k'] > df['stoch_d']) & 
               (df['stoch_k'].shift(1) <= df['stoch_d'].shift(1)) & 
               (df['stoch_k'] < oversold), 'signal'] = 1
        
        # Sell signal: K crosses below D in overbought region
        df.loc[(df['stoch_k'] < df['stoch_d']) & 
               (df['stoch_k'].shift(1) >= df['stoch_d'].shift(1)) & 
               (df['stoch_k'] > overbought), 'signal'] = -1
        
        return df
    
    def _ml_signal(self, df):
        """Generate signals based on ML model predictions
        
        Args:
            df (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            pandas.DataFrame: DataFrame with added signal columns
        """
        # Check if ML model is available
        if self.ml_model is None:
            logger.warning("ML model not available for signal generation")
            df['signal'] = 0
            return df
        
        # Generate signals
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell
        
        try:
            # Get the latest data point for prediction
            latest_data = df.iloc[-1:].copy()
            
            # Make prediction
            if hasattr(self.ml_model, 'predict_proba'):
                # Get probability predictions
                proba = self.ml_model.predict_proba(latest_data)
                
                # Get prediction threshold from config or use default
                ml_config = self.signal_config.get('ml', {})
                threshold = ml_config.get('threshold', 0.6)
                
                # Generate signal based on probability
                if proba.shape[1] == 2:  # Binary classification
                    if proba[0, 1] > threshold:  # Probability of class 1 (buy)
                        df.loc[df.index[-1], 'signal'] = 1
                    elif proba[0, 0] > threshold:  # Probability of class 0 (sell)
                        df.loc[df.index[-1], 'signal'] = -1
                else:  # Multi-class classification
                    pred_class = np.argmax(proba[0])
                    pred_prob = proba[0, pred_class]
                    
                    if pred_prob > threshold:
                        if pred_class == 1:  # Buy
                            df.loc[df.index[-1], 'signal'] = 1
                        elif pred_class == 2:  # Sell
                            df.loc[df.index[-1], 'signal'] = -1
            else:
                # Get class predictions
                pred = self.ml_model.predict(latest_data)
                
                # Generate signal based on predicted class
                if pred[0] == 1:  # Buy
                    df.loc[df.index[-1], 'signal'] = 1
                elif pred[0] == -1 or pred[0] == 2:  # Sell
                    df.loc[df.index[-1], 'signal'] = -1
        
        except Exception as e:
            logger.error(f"Error generating ML signals: {str(e)}")
        
        return df
    
    def _combined_signal(self, df):
        """Generate signals based on a combination of indicators
        
        Args:
            df (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            pandas.DataFrame: DataFrame with added signal columns
        """
        # Get enabled signal methods from config
        combined_config = self.signal_config.get('combined', {})
        enabled_methods = combined_config.get('enabled_methods', ['rsi', 'macd', 'bollinger'])
        
        # Initialize signal columns for each method
        for method in enabled_methods:
            if method in self.signal_methods and method != 'combined':
                method_df = self.signal_methods[method](df.copy())
                df[f'signal_{method}'] = method_df['signal']
        
        # Generate combined signal
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell
        
        # Get voting method from config
        voting_method = combined_config.get('voting_method', 'majority')
        
        if voting_method == 'majority':
            # Count buy and sell signals
            buy_count = 0
            sell_count = 0
            
            for method in enabled_methods:
                if f'signal_{method}' in df.columns:
                    buy_count += (df[f'signal_{method}'] == 1).astype(int)
                    sell_count += (df[f'signal_{method}'] == -1).astype(int)
            
            # Get threshold from config or use default
            threshold = combined_config.get('threshold', 0.5)
            min_votes = max(1, int(len(enabled_methods) * threshold))
            
            # Generate signal based on majority vote
            df.loc[buy_count >= min_votes, 'signal'] = 1
            df.loc[sell_count >= min_votes, 'signal'] = -1
            
            # In case of tie, prioritize the latest signal
            df.loc[(buy_count == sell_count) & (buy_count >= min_votes), 'signal'] = 0
        
        elif voting_method == 'unanimous':
            # All signals must agree
            signal_columns = [f'signal_{method}' for method in enabled_methods if f'signal_{method}' in df.columns]
            
            if signal_columns:
                # Buy signal: all methods agree on buy
                df.loc[df[signal_columns].eq(1).all(axis=1), 'signal'] = 1
                
                # Sell signal: all methods agree on sell
                df.loc[df[signal_columns].eq(-1).all(axis=1), 'signal'] = -1
        
        elif voting_method == 'weighted':
            # Get weights from config or use equal weights
            weights = combined_config.get('weights', {})
            
            # Calculate weighted signal
            weighted_signal = 0
            total_weight = 0
            
            for method in enabled_methods:
                if f'signal_{method}' in df.columns:
                    weight = weights.get(method, 1)
                    weighted_signal += df[f'signal_{method}'] * weight
                    total_weight += weight
            
            if total_weight > 0:
                weighted_signal = weighted_signal / total_weight
                
                # Get threshold from config or use default
                threshold = combined_config.get('threshold', 0.3)
                
                # Generate signal based on weighted vote
                df.loc[weighted_signal >= threshold, 'signal'] = 1
                df.loc[weighted_signal <= -threshold, 'signal'] = -1
        
        return df
    
    def _calculate_signal_strength(self, df):
        """Calculate the strength of the signal
        
        Args:
            df (pandas.DataFrame): DataFrame with signal column
            
        Returns:
            pandas.DataFrame: DataFrame with added signal_strength column
        """
        # Initialize signal strength
        df['signal_strength'] = 0.0
        
        # If no signals, return early
        if 'signal' not in df.columns or df['signal'].abs().sum() == 0:
            return df
        
        # Calculate signal strength based on available indicators
        strength_factors = []
        
        # RSI strength
        if 'rsi' in df.columns:
            rsi_config = self.signal_config.get('rsi', {})
            oversold = rsi_config.get('oversold', 30)
            overbought = rsi_config.get('overbought', 70)
            
            # Buy strength: how oversold
            buy_strength = (oversold - df['rsi']) / oversold
            buy_strength = buy_strength.clip(0, 1)
            
            # Sell strength: how overbought
            sell_strength = (df['rsi'] - overbought) / (100 - overbought)
            sell_strength = sell_strength.clip(0, 1)
            
            # Combine based on signal direction
            rsi_strength = np.where(df['signal'] > 0, buy_strength, 
                                  np.where(df['signal'] < 0, sell_strength, 0))
            
            strength_factors.append(rsi_strength)
        
        # MACD strength
        if all(col in df.columns for col in ['macd', 'macd_signal']):
            # Normalize MACD histogram
            if 'macd_histogram' in df.columns:
                hist_max = df['macd_histogram'].abs().max()
                if hist_max > 0:
                    macd_strength = df['macd_histogram'].abs() / hist_max
                    macd_strength = macd_strength.clip(0, 1)
                    
                    strength_factors.append(macd_strength)
        
        # Bollinger Bands strength
        if all(col in df.columns for col in ['bb_upper', 'bb_middle', 'bb_lower']):
            # Calculate distance from price to middle band
            bb_distance = (df['close'] - df['bb_middle']).abs() / (df['bb_upper'] - df['bb_lower'])
            bb_strength = bb_distance.clip(0, 1)
            
            strength_factors.append(bb_strength)
        
        # Stochastic strength
        if all(col in df.columns for col in ['stoch_k', 'stoch_d']):
            stoch_config = self.signal_config.get('stochastic', {})
            oversold = stoch_config.get('oversold', 20)
            overbought = stoch_config.get('overbought', 80)
            
            # Buy strength: how oversold
            buy_strength = (oversold - df['stoch_k']) / oversold
            buy_strength = buy_strength.clip(0, 1)
            
            # Sell strength: how overbought
            sell_strength = (df['stoch_k'] - overbought) / (100 - overbought)
            sell_strength = sell_strength.clip(0, 1)
            
            # Combine based on signal direction
            stoch_strength = np.where(df['signal'] > 0, buy_strength, 
                                    np.where(df['signal'] < 0, sell_strength, 0))
            
            strength_factors.append(stoch_strength)
        
        # ML model strength
        if self.ml_model is not None and hasattr(self.ml_model, 'predict_proba'):
            try:
                # Get probability predictions for the entire DataFrame
                proba = self.ml_model.predict_proba(df)
                
                if proba.shape[1] == 2:  # Binary classification
                    # Buy strength: probability of class 1 (buy)
                    buy_strength = proba[:, 1]
                    
                    # Sell strength: probability of class 0 (sell)
                    sell_strength = proba[:, 0]
                    
                    # Combine based on signal direction
                    ml_strength = np.where(df['signal'] > 0, buy_strength, 
                                         np.where(df['signal'] < 0, sell_strength, 0))
                    
                    strength_factors.append(ml_strength)
                
                elif proba.shape[1] > 2:  # Multi-class classification
                    # Get the probability of the predicted class
                    pred_class = np.argmax(proba, axis=1)
                    pred_prob = np.array([proba[i, pred_class[i]] for i in range(len(pred_class))])
                    
                    # Only use probability if it matches the signal direction
                    ml_strength = np.where(
                        (df['signal'] > 0) & (pred_class == 1), pred_prob,
                        np.where((df['signal'] < 0) & (pred_class == 2), pred_prob, 0)
                    )
                    
                    strength_factors.append(ml_strength)
            
            except Exception as e:
                logger.error(f"Error calculating ML signal strength: {str(e)}")
        
        # Calculate average strength if we have any factors
        if strength_factors:
            # Convert to numpy arrays for easier calculation
            strength_factors = np.array(strength_factors)
            
            # Calculate average strength
            avg_strength = np.mean(strength_factors, axis=0)
            
            # Apply direction
            df['signal_strength'] = avg_strength * df['signal']
        
        return df
    
    def get_latest_signal(self, data):
        """Get the latest trading signal
        
        Args:
            data (pandas.DataFrame): DataFrame with price data and indicators
            
        Returns:
            dict: Latest signal information
        """
        # Generate signals
        signal_method = self.signal_config.get('default_method', 'combined')
        signals_df = self.generate_signals(data, method=signal_method)
        
        # Get the latest signal
        if signals_df.empty:
            return {
                'signal': 0,
                'strength': 0.0,
                'timestamp': datetime.now(),
                'method': signal_method
            }
        
        latest = signals_df.iloc[-1]
        
        return {
            'signal': int(latest.get('signal', 0)),
            'strength': float(latest.get('signal_strength', 0.0)),
            'timestamp': latest.index if isinstance(latest.index, datetime) else datetime.now(),
            'method': signal_method,
            'price': float(latest.get('close', 0.0))
        }