#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data fetcher module for retrieving forex data from various sources
"""

import os
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# API libraries
import requests
import websocket
import json
import ccxt
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments

logger = logging.getLogger("TradeBOT.DataFetcher")


class DataFetcher:
    """Class for fetching forex data from various sources"""
    
    def __init__(self, config):
        """Initialize the data fetcher
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.data_source = config.get('data_source', 'oanda')
        self.cache = {}
        self.websocket_connections = {}
        self.price_buffers = {}
        
        # Initialize data source connections
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize connections to data sources"""
        if self.data_source == 'oanda':
            self._initialize_oanda()
        elif self.data_source == 'ccxt':
            self._initialize_ccxt()
        else:
            logger.warning(f"Unknown data source: {self.data_source}, defaulting to OANDA")
            self.data_source = 'oanda'
            self._initialize_oanda()
    
    def _initialize_oanda(self):
        """Initialize OANDA API connection"""
        try:
            oanda_config = self.config.get('oanda', {})
            self.oanda_api_key = oanda_config.get('api_key')
            self.oanda_account_id = oanda_config.get('account_id')
            self.oanda_base_url = oanda_config.get('base_url')
            
            if not self.oanda_api_key or not self.oanda_account_id:
                logger.error("OANDA API key or account ID not provided")
                return
            
            self.oanda_client = API(access_token=self.oanda_api_key, environment="practice")
            logger.info("OANDA API connection initialized")
        except Exception as e:
            logger.error(f"Error initializing OANDA connection: {str(e)}")
    
    def _initialize_ccxt(self):
        """Initialize CCXT exchange connection"""
        try:
            ccxt_config = self.config.get('ccxt', {})
            exchange_id = ccxt_config.get('exchange_id', 'oanda')
            api_key = ccxt_config.get('api_key')
            secret = ccxt_config.get('secret')
            
            exchange_class = getattr(ccxt, exchange_id)
            self.ccxt_client = exchange_class({
                'apiKey': api_key,
                'secret': secret,
                'timeout': 30000,
                'enableRateLimit': True,
            })
            logger.info(f"CCXT {exchange_id} connection initialized")
        except Exception as e:
            logger.error(f"Error initializing CCXT connection: {str(e)}")
    
    def get_historical_data(self, symbol, timeframe='1m', limit=1000):
        """Get historical price data for a symbol
        
        Args:
            symbol (str): Currency pair symbol
            timeframe (str): Timeframe/interval for the data
            limit (int): Number of candles to retrieve
            
        Returns:
            pandas.DataFrame: DataFrame with historical price data
        """
        if self.data_source == 'oanda':
            return self._get_oanda_historical_data(symbol, timeframe, limit)
        elif self.data_source == 'ccxt':
            return self._get_ccxt_historical_data(symbol, timeframe, limit)
        else:
            logger.error(f"Unsupported data source: {self.data_source}")
            return pd.DataFrame()
    
    def _get_oanda_historical_data(self, symbol, timeframe='1m', limit=1000):
        """Get historical data from OANDA"""
        try:
            # Convert timeframe to granularity format for OANDA
            granularity_map = {
                '1m': 'M1',
                '5m': 'M5',
                '15m': 'M15',
                '30m': 'M30',
                '1h': 'H1',
                '4h': 'H4',
                '1d': 'D',
                '1w': 'W'
            }
            granularity = granularity_map.get(timeframe, 'M1')
            
            # Calculate from time based on limit and granularity
            now = datetime.utcnow()
            if granularity == 'M1':
                from_time = now - timedelta(minutes=limit)
            elif granularity == 'M5':
                from_time = now - timedelta(minutes=5*limit)
            elif granularity == 'M15':
                from_time = now - timedelta(minutes=15*limit)
            elif granularity == 'M30':
                from_time = now - timedelta(minutes=30*limit)
            elif granularity == 'H1':
                from_time = now - timedelta(hours=limit)
            elif granularity == 'H4':
                from_time = now - timedelta(hours=4*limit)
            elif granularity == 'D':
                from_time = now - timedelta(days=limit)
            elif granularity == 'W':
                from_time = now - timedelta(weeks=limit)
            else:
                from_time = now - timedelta(minutes=limit)
            
            # Format dates for OANDA API
            from_str = from_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            to_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Create request parameters
            params = {
                "granularity": granularity,
                "from": from_str,
                "to": to_str,
                "count": limit
            }
            
            # Make API request
            request = instruments.InstrumentsCandles(instrument=symbol, params=params)
            response = self.oanda_client.request(request)
            
            # Process response into DataFrame
            candles = response['candles']
            data = []
            for candle in candles:
                if candle['complete']:
                    data.append({
                        'timestamp': candle['time'],
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c']),
                        'volume': float(candle['volume'])
                    })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Error fetching OANDA historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def _get_ccxt_historical_data(self, symbol, timeframe='1m', limit=1000):
        """Get historical data from CCXT exchange"""
        try:
            # Convert symbol format if needed (e.g., EUR_USD to EUR/USD)
            ccxt_symbol = symbol.replace('_', '/')
            
            # Fetch OHLCV data
            ohlcv = self.ccxt_client.fetch_ohlcv(ccxt_symbol, timeframe, limit=limit)
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Error fetching CCXT historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_latest_data(self, symbol, timeframe='1m'):
        """Get the latest price data for a symbol
        
        Args:
            symbol (str): Currency pair symbol
            timeframe (str): Timeframe/interval for the data
            
        Returns:
            dict: Latest price data
        """
        if self.data_source == 'oanda':
            return self._get_oanda_latest_data(symbol, timeframe)
        elif self.data_source == 'ccxt':
            return self._get_ccxt_latest_data(symbol, timeframe)
        else:
            logger.error(f"Unsupported data source: {self.data_source}")
            return {}
    
    def _get_oanda_latest_data(self, symbol, timeframe='1m'):
        """Get latest data from OANDA"""
        try:
            # Convert timeframe to granularity format for OANDA
            granularity_map = {
                '1m': 'M1',
                '5m': 'M5',
                '15m': 'M15',
                '30m': 'M30',
                '1h': 'H1',
                '4h': 'H4',
                '1d': 'D',
                '1w': 'W'
            }
            granularity = granularity_map.get(timeframe, 'M1')
            
            # Create request parameters
            params = {
                "granularity": granularity,
                "count": 1
            }
            
            # Make API request
            request = instruments.InstrumentsCandles(instrument=symbol, params=params)
            response = self.oanda_client.request(request)
            
            # Process response
            candles = response['candles']
            if candles and len(candles) > 0:
                candle = candles[0]
                return {
                    'timestamp': candle['time'],
                    'open': float(candle['mid']['o']),
                    'high': float(candle['mid']['h']),
                    'low': float(candle['mid']['l']),
                    'close': float(candle['mid']['c']),
                    'volume': float(candle['volume']),
                    'complete': candle['complete']
                }
            else:
                logger.warning(f"No candles returned for {symbol}")
                return {}
        
        except Exception as e:
            logger.error(f"Error fetching OANDA latest data for {symbol}: {str(e)}")
            return {}
    
    def _get_ccxt_latest_data(self, symbol, timeframe='1m'):
        """Get latest data from CCXT exchange"""
        try:
            # Convert symbol format if needed
            ccxt_symbol = symbol.replace('_', '/')
            
            # Fetch latest ticker
            ticker = self.ccxt_client.fetch_ticker(ccxt_symbol)
            
            # Get latest OHLCV for more complete data
            ohlcv = self.ccxt_client.fetch_ohlcv(ccxt_symbol, timeframe, limit=1)
            
            if ohlcv and len(ohlcv) > 0:
                latest = ohlcv[0]
                return {
                    'timestamp': datetime.fromtimestamp(latest[0]/1000).isoformat(),
                    'open': float(latest[1]),
                    'high': float(latest[2]),
                    'low': float(latest[3]),
                    'close': float(latest[4]),
                    'volume': float(latest[5]),
                    'complete': True  # Assume complete for simplicity
                }
            else:
                logger.warning(f"No OHLCV data returned for {symbol}")
                return {}
        
        except Exception as e:
            logger.error(f"Error fetching CCXT latest data for {symbol}: {str(e)}")
            return {}
    
    def start_streaming(self, symbol, callback):
        """Start streaming real-time data for a symbol
        
        Args:
            symbol (str): Currency pair symbol
            callback (function): Callback function for handling incoming data
        """
        if self.data_source == 'oanda':
            self._start_oanda_streaming(symbol, callback)
        else:
            logger.error(f"Streaming not implemented for data source: {self.data_source}")
    
    def _start_oanda_streaming(self, symbol, callback):
        """Start streaming data from OANDA"""
        # Implementation would depend on OANDA's streaming API
        # This is a placeholder for actual implementation
        logger.info(f"OANDA streaming not implemented yet for {symbol}")
    
    def stop_streaming(self, symbol):
        """Stop streaming data for a symbol
        
        Args:
            symbol (str): Currency pair symbol
        """
        if symbol in self.websocket_connections:
            try:
                self.websocket_connections[symbol].close()
                del self.websocket_connections[symbol]
                logger.info(f"Stopped streaming for {symbol}")
            except Exception as e:
                logger.error(f"Error stopping stream for {symbol}: {str(e)}")