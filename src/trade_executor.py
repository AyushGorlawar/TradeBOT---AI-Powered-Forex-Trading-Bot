#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trade Executor module for executing trades based on signals
"""

import logging
import uuid
from datetime import datetime

logger = logging.getLogger("TradeBOT.TradeExecutor")


class TradeExecutor:
    """Class for executing trades based on signals"""
    
    def __init__(self, config=None, risk_manager=None):
        """Initialize the trade executor
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
            risk_manager (RiskManager, optional): Risk manager instance. Defaults to None.
        """
        self.config = config or {}
        self.trade_config = self.config.get('trading', {})
        self.risk_manager = risk_manager
        self.api_client = None
        self.open_trades = {}
        self.trade_history = []
        self.is_paper_trading = self.trade_config.get('paper_trading', True)
        self.last_prices = {}
    
    def connect_api(self, api_type='oanda'):
        """Connect to the trading API
        
        Args:
            api_type (str, optional): Type of API to connect to. Defaults to 'oanda'.
            
        Returns:
            bool: True if connected successfully, False otherwise
        """
        try:
            if api_type == 'oanda':
                from .api_clients.oanda_client import OandaClient
                
                # Get API credentials from config
                api_config = self.config.get('api', {}).get('oanda', {})
                api_key = api_config.get('api_key', '')
                account_id = api_config.get('account_id', '')
                is_live = api_config.get('is_live', False)
                
                # Initialize API client
                self.api_client = OandaClient(api_key, account_id, is_live)
                logger.info(f"Connected to Oanda API: {'Live' if is_live else 'Practice'}")
                
                # Update account balance
                if self.risk_manager:
                    account_info = self.api_client.get_account_info()
                    if account_info and 'balance' in account_info:
                        self.risk_manager.update_account_balance(account_info['balance'])
                
                return True
            
            elif api_type == 'ccxt':
                try:
                    import ccxt
                    
                    # Get API credentials from config
                    api_config = self.config.get('api', {}).get('ccxt', {})
                    exchange_id = api_config.get('exchange_id', 'binance')
                    api_key = api_config.get('api_key', '')
                    api_secret = api_config.get('api_secret', '')
                    
                    # Initialize exchange
                    exchange_class = getattr(ccxt, exchange_id)
                    self.api_client = exchange_class({
                        'apiKey': api_key,
                        'secret': api_secret,
                        'enableRateLimit': True
                    })
                    
                    logger.info(f"Connected to {exchange_id} API")
                    
                    # Update account balance
                    if self.risk_manager:
                        balance = self.api_client.fetch_balance()
                        if balance and 'total' in balance and 'USD' in balance['total']:
                            self.risk_manager.update_account_balance(balance['total']['USD'])
                    
                    return True
                
                except ImportError:
                    logger.error("CCXT library not installed")
                    return False
            
            elif api_type == 'paper':
                # Paper trading mode (simulated)
                self.is_paper_trading = True
                logger.info("Using paper trading mode")
                return True
            
            else:
                logger.error(f"Unknown API type: {api_type}")
                return False
        
        except Exception as e:
            logger.error(f"Error connecting to API: {str(e)}")
            return False
    
    def execute_signal(self, pair, signal, price_data):
        """Execute a trading signal
        
        Args:
            pair (str): Currency pair
            signal (dict): Signal information
            price_data (pandas.DataFrame): Price data
            
        Returns:
            dict: Trade information or None if no trade executed
        """
        # Check if signal is valid
        if not signal or 'signal' not in signal or signal['signal'] == 0:
            logger.info(f"No valid signal for {pair}")
            return None
        
        # Get signal direction and strength
        direction = signal['signal']  # 1 for buy, -1 for sell
        strength = signal.get('strength', 1.0)
        
        # Check if trading is enabled
        if not self.trade_config.get('enabled', True):
            logger.warning("Trading is disabled in configuration")
            return None
        
        # Check if we can open a position for this pair
        if self.risk_manager and not self.risk_manager.can_open_position(pair):
            logger.warning(f"Cannot open position for {pair} due to risk management constraints")
            return None
        
        # Get current price
        current_price = self._get_current_price(pair, price_data)
        if current_price <= 0:
            logger.error(f"Invalid current price for {pair}: {current_price}")
            return None
        
        # Calculate stop-loss price
        atr = None
        if 'atr' in price_data.columns:
            atr = price_data['atr'].iloc[-1]
        
        stop_loss = self.risk_manager.calculate_stop_loss(pair, current_price, direction, atr) if self.risk_manager else None
        
        # Calculate take-profit price
        take_profit = self.risk_manager.calculate_take_profit(pair, current_price, stop_loss, direction) if self.risk_manager and stop_loss else None
        
        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(pair, current_price, stop_loss, strength) if self.risk_manager and stop_loss else 0.0
        
        # Check if position size is valid
        if position_size <= 0:
            logger.warning(f"Invalid position size for {pair}: {position_size}")
            return None
        
        # Execute the trade
        trade_id = self._execute_trade(pair, direction, position_size, current_price, stop_loss, take_profit)
        
        if trade_id:
            # Create trade information
            trade_info = {
                'id': trade_id,
                'pair': pair,
                'direction': direction,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'open_time': datetime.now(),
                'signal_strength': strength,
                'signal_method': signal.get('method', 'unknown'),
                'status': 'open',
                'pnl': 0.0,
                'risk_amount': (current_price - stop_loss) * position_size if direction > 0 else (stop_loss - current_price) * position_size
            }
            
            # Add trade to open trades
            self.open_trades[trade_id] = trade_info
            
            # Add position to risk manager
            if self.risk_manager:
                self.risk_manager.add_position(trade_id, trade_info)
            
            logger.info(f"Trade executed: {trade_info}")
            return trade_info
        
        return None
    
    def _execute_trade(self, pair, direction, position_size, price, stop_loss=None, take_profit=None):
        """Execute a trade through the API or paper trading
        
        Args:
            pair (str): Currency pair
            direction (int): Trade direction (1 for buy, -1 for sell)
            position_size (float): Position size
            price (float): Entry price
            stop_loss (float, optional): Stop-loss price. Defaults to None.
            take_profit (float, optional): Take-profit price. Defaults to None.
            
        Returns:
            str: Trade ID or None if execution failed
        """
        try:
            # Generate a unique trade ID
            trade_id = str(uuid.uuid4())
            
            # Paper trading mode
            if self.is_paper_trading or self.api_client is None:
                logger.info(f"Paper trading: {'BUY' if direction > 0 else 'SELL'} {position_size} {pair} @ {price}")
                return trade_id
            
            # Live trading mode
            if isinstance(self.api_client, object) and hasattr(self.api_client, 'create_order'):
                # Prepare order parameters
                order_type = self.trade_config.get('order_type', 'market')
                order_params = {
                    'pair': pair,
                    'type': order_type,
                    'side': 'buy' if direction > 0 else 'sell',
                    'amount': position_size,
                    'price': price if order_type == 'limit' else None
                }
                
                # Add stop-loss and take-profit if supported
                if stop_loss and hasattr(self.api_client, 'supports_order_feature') and self.api_client.supports_order_feature('stopLoss'):
                    order_params['stopLoss'] = stop_loss
                
                if take_profit and hasattr(self.api_client, 'supports_order_feature') and self.api_client.supports_order_feature('takeProfit'):
                    order_params['takeProfit'] = take_profit
                
                # Execute order
                order = self.api_client.create_order(**order_params)
                
                if order and 'id' in order:
                    logger.info(f"Order executed: {order}")
                    return order['id']
                else:
                    logger.error(f"Failed to execute order: {order}")
                    return None
            
            # Oanda-specific implementation
            elif isinstance(self.api_client, object) and hasattr(self.api_client, 'create_market_order'):
                # Execute order
                order = self.api_client.create_market_order(
                    pair,
                    'buy' if direction > 0 else 'sell',
                    position_size,
                    stop_loss,
                    take_profit
                )
                
                if order and 'orderFillTransaction' in order and 'id' in order['orderFillTransaction']:
                    logger.info(f"Order executed: {order}")
                    return order['orderFillTransaction']['id']
                else:
                    logger.error(f"Failed to execute order: {order}")
                    return None
            
            else:
                logger.error("API client does not support order execution")
                return None
        
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return None
    
    def close_trade(self, trade_id, current_price=None, reason="Manual"):
        """Close an open trade
        
        Args:
            trade_id (str): Trade ID
            current_price (float, optional): Current price. Defaults to None (market price).
            reason (str, optional): Reason for closing the trade. Defaults to "Manual".
            
        Returns:
            dict: Closed trade information or None if closure failed
        """
        # Check if trade exists
        if trade_id not in self.open_trades:
            logger.warning(f"Trade {trade_id} not found in open trades")
            return None
        
        # Get trade information
        trade = self.open_trades[trade_id]
        pair = trade['pair']
        direction = trade['direction']
        position_size = trade['position_size']
        entry_price = trade['entry_price']
        
        # Get current price if not provided
        if current_price is None or current_price <= 0:
            current_price = self._get_current_price(pair)
            if current_price <= 0:
                logger.error(f"Invalid current price for {pair}: {current_price}")
                return None
        
        # Calculate profit/loss
        if direction > 0:  # Buy position
            pnl = (current_price - entry_price) * position_size
        else:  # Sell position
            pnl = (entry_price - current_price) * position_size
        
        # Close the trade
        if self._close_trade_execution(trade_id, current_price):
            # Update trade information
            trade['exit_price'] = current_price
            trade['close_time'] = datetime.now()
            trade['pnl'] = pnl
            trade['status'] = 'closed'
            trade['close_reason'] = reason
            
            # Calculate trade duration
            if 'open_time' in trade:
                duration = (trade['close_time'] - trade['open_time']).total_seconds()
                trade['duration'] = duration
            
            # Remove from open trades
            self.open_trades.pop(trade_id)
            
            # Add to trade history
            self.trade_history.append(trade)
            
            # Remove from risk manager
            if self.risk_manager:
                self.risk_manager.remove_position(trade_id, pnl)
            
            logger.info(f"Trade closed: {trade}")
            return trade
        
        return None
    
    def _close_trade_execution(self, trade_id, price):
        """Execute trade closure through the API or paper trading
        
        Args:
            trade_id (str): Trade ID
            price (float): Exit price
            
        Returns:
            bool: True if closure successful, False otherwise
        """
        try:
            # Get trade information
            trade = self.open_trades.get(trade_id)
            if not trade:
                logger.warning(f"Trade {trade_id} not found in open trades")
                return False
            
            pair = trade['pair']
            position_size = trade['position_size']
            direction = trade['direction']
            
            # Paper trading mode
            if self.is_paper_trading or self.api_client is None:
                logger.info(f"Paper trading: Closing {'BUY' if direction > 0 else 'SELL'} {position_size} {pair} @ {price}")
                return True
            
            # Live trading mode
            if isinstance(self.api_client, object) and hasattr(self.api_client, 'create_order'):
                # Prepare order parameters for closing position
                order_type = 'market'
                order_params = {
                    'pair': pair,
                    'type': order_type,
                    'side': 'sell' if direction > 0 else 'buy',  # Opposite of opening direction
                    'amount': position_size
                }
                
                # Execute order
                order = self.api_client.create_order(**order_params)
                
                if order and 'id' in order:
                    logger.info(f"Close order executed: {order}")
                    return True
                else:
                    logger.error(f"Failed to execute close order: {order}")
                    return False
            
            # Oanda-specific implementation
            elif isinstance(self.api_client, object) and hasattr(self.api_client, 'close_trade'):
                # Execute order
                result = self.api_client.close_trade(trade_id)
                
                if result and 'orderFillTransaction' in result:
                    logger.info(f"Close order executed: {result}")
                    return True
                else:
                    logger.error(f"Failed to execute close order: {result}")
                    return False
            
            else:
                logger.error("API client does not support order execution")
                return False
        
        except Exception as e:
            logger.error(f"Error closing trade: {str(e)}")
            return False
    
    def update_open_trades(self, price_data):
        """Update and manage open trades
        
        Args:
            price_data (dict): Current price data for all pairs
            
        Returns:
            list: List of closed trades
        """
        closed_trades = []
        
        # Update last prices
        for pair, data in price_data.items():
            if not data.empty:
                self.last_prices[pair] = data['close'].iloc[-1]
        
        # Check each open trade
        for trade_id in list(self.open_trades.keys()):
            trade = self.open_trades[trade_id]
            pair = trade['pair']
            
            # Get current price
            current_price = self._get_current_price(pair, price_data.get(pair))
            if current_price <= 0:
                continue
            
            # Check if trade should be closed
            if self.risk_manager:
                should_close, reason = self.risk_manager.should_close_position(trade_id, current_price)
                if should_close:
                    closed_trade = self.close_trade(trade_id, current_price, reason)
                    if closed_trade:
                        closed_trades.append(closed_trade)
            
            # Update unrealized PnL
            direction = trade['direction']
            entry_price = trade['entry_price']
            position_size = trade['position_size']
            
            if direction > 0:  # Buy position
                unrealized_pnl = (current_price - entry_price) * position_size
            else:  # Sell position
                unrealized_pnl = (entry_price - current_price) * position_size
            
            self.open_trades[trade_id]['unrealized_pnl'] = unrealized_pnl
            self.open_trades[trade_id]['current_price'] = current_price
        
        return closed_trades
    
    def _get_current_price(self, pair, price_data=None):
        """Get the current price for a pair
        
        Args:
            pair (str): Currency pair
            price_data (pandas.DataFrame, optional): Price data. Defaults to None.
            
        Returns:
            float: Current price
        """
        # Try to get price from provided price data
        if price_data is not None and not price_data.empty:
            return price_data['close'].iloc[-1]
        
        # Try to get price from last prices
        if pair in self.last_prices:
            return self.last_prices[pair]
        
        # Try to get price from API
        if self.api_client and not self.is_paper_trading:
            try:
                if hasattr(self.api_client, 'get_current_price'):
                    price = self.api_client.get_current_price(pair)
                    if price > 0:
                        self.last_prices[pair] = price
                        return price
            except Exception as e:
                logger.error(f"Error getting current price from API: {str(e)}")
        
        logger.warning(f"Could not get current price for {pair}")
        return 0.0
    
    def get_trade_statistics(self):
        """Get statistics about trading performance
        
        Returns:
            dict: Trading statistics
        """
        stats = {
            'total_trades': len(self.trade_history),
            'open_trades': len(self.open_trades),
            'profitable_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'win_rate': 0.0,
            'average_profit': 0.0,
            'average_loss': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0,
            'largest_profit': 0.0,
            'largest_loss': 0.0,
            'average_trade_duration': 0.0
        }
        
        # Calculate statistics from trade history
        if self.trade_history:
            profits = [trade['pnl'] for trade in self.trade_history if trade['pnl'] > 0]
            losses = [trade['pnl'] for trade in self.trade_history if trade['pnl'] <= 0]
            durations = [trade.get('duration', 0) for trade in self.trade_history if 'duration' in trade]
            
            stats['profitable_trades'] = len(profits)
            stats['losing_trades'] = len(losses)
            stats['total_profit'] = sum(profits)
            stats['total_loss'] = sum(losses)
            stats['win_rate'] = stats['profitable_trades'] / stats['total_trades'] if stats['total_trades'] > 0 else 0.0
            stats['average_profit'] = sum(profits) / len(profits) if profits else 0.0
            stats['average_loss'] = sum(losses) / len(losses) if losses else 0.0
            stats['profit_factor'] = abs(stats['total_profit'] / stats['total_loss']) if stats['total_loss'] != 0 else 0.0
            stats['expectancy'] = (stats['win_rate'] * stats['average_profit']) - ((1 - stats['win_rate']) * abs(stats['average_loss'])) if stats['total_trades'] > 0 else 0.0
            stats['largest_profit'] = max(profits) if profits else 0.0
            stats['largest_loss'] = min(losses) if losses else 0.0
            stats['average_trade_duration'] = sum(durations) / len(durations) if durations else 0.0
        
        # Add current account balance
        if self.risk_manager:
            stats['account_balance'] = self.risk_manager.account_balance
        
        return stats
    
    def get_open_positions(self):
        """Get information about open positions
        
        Returns:
            list: List of open positions
        """
        return list(self.open_trades.values())
    
    def get_trade_history(self, limit=None):
        """Get trade history
        
        Args:
            limit (int, optional): Maximum number of trades to return. Defaults to None (all trades).
            
        Returns:
            list: List of closed trades
        """
        if limit is not None and limit > 0:
            return self.trade_history[-limit:]
        return self.trade_history