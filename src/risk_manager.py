#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Risk Manager module for handling position sizing, stop-loss, and take-profit calculations
"""

import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger("TradeBOT.RiskManager")


class RiskManager:
    """Class for managing trading risk, position sizing, and stop-loss/take-profit levels"""
    
    def __init__(self, config=None):
        """Initialize the risk manager
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        self.config = config or {}
        self.risk_config = self.config.get('risk_management', {})
        
        # Set default risk parameters
        self.max_risk_per_trade = self.risk_config.get('max_risk_per_trade', 0.02)  # 2% of account
        self.max_open_positions = self.risk_config.get('max_open_positions', 5)
        self.max_risk_per_pair = self.risk_config.get('max_risk_per_pair', 0.05)  # 5% of account
        self.max_daily_drawdown = self.risk_config.get('max_daily_drawdown', 0.05)  # 5% of account
        self.account_balance = self.risk_config.get('initial_balance', 10000.0)
        self.open_positions = {}
        self.daily_pnl = 0.0
        self.daily_reset_time = self.risk_config.get('daily_reset_time', '00:00:00')
        self.last_reset = datetime.now()
    
    def update_account_balance(self, balance):
        """Update the account balance
        
        Args:
            balance (float): New account balance
        """
        self.account_balance = balance
        logger.info(f"Account balance updated: {self.account_balance}")
    
    def calculate_position_size(self, pair, entry_price, stop_loss, signal_strength=1.0):
        """Calculate the appropriate position size based on risk parameters
        
        Args:
            pair (str): Currency pair
            entry_price (float): Entry price
            stop_loss (float): Stop-loss price
            signal_strength (float, optional): Signal strength (0.0 to 1.0). Defaults to 1.0.
            
        Returns:
            float: Position size in units
        """
        # Check if stop-loss is valid
        if stop_loss <= 0 or entry_price <= 0:
            logger.error(f"Invalid entry price ({entry_price}) or stop-loss ({stop_loss})")
            return 0.0
        
        # Calculate risk amount
        risk_amount = self.account_balance * self.max_risk_per_trade
        
        # Adjust risk based on signal strength
        risk_amount *= signal_strength
        
        # Calculate pip value and risk per pip
        pip_value = self._calculate_pip_value(pair)
        
        # Calculate stop-loss distance in pips
        is_buy = entry_price > stop_loss
        sl_pips = abs(entry_price - stop_loss) / self._get_pip_size(pair)
        
        # Calculate position size
        if sl_pips > 0 and pip_value > 0:
            position_size = risk_amount / (sl_pips * pip_value)
        else:
            logger.error(f"Invalid stop-loss distance ({sl_pips}) or pip value ({pip_value})")
            return 0.0
        
        # Apply position size limits
        position_size = self._apply_position_limits(pair, position_size)
        
        logger.info(f"Calculated position size for {pair}: {position_size} units")
        return position_size
    
    def _calculate_pip_value(self, pair):
        """Calculate the value of one pip for the given pair
        
        Args:
            pair (str): Currency pair
            
        Returns:
            float: Pip value in account currency
        """
        # Get pair configuration
        pair_config = self._get_pair_config(pair)
        
        # If pip value is specified in config, use it
        if pair_config and 'pip_value' in pair_config:
            return pair_config['pip_value']
        
        # Default pip values for major pairs (assuming USD account)
        default_pip_values = {
            'EUR_USD': 10.0,
            'GBP_USD': 10.0,
            'AUD_USD': 10.0,
            'NZD_USD': 10.0,
            'USD_JPY': 9.13,
            'USD_CHF': 10.64,
            'USD_CAD': 7.59,
            'EUR_GBP': 13.15,
            'EUR_JPY': 9.13,
            'GBP_JPY': 9.13
        }
        
        # Normalize pair format
        normalized_pair = pair.replace('/', '_').upper()
        
        # Return default pip value if available, otherwise use a conservative value
        return default_pip_values.get(normalized_pair, 10.0)
    
    def _get_pip_size(self, pair):
        """Get the pip size for the given pair
        
        Args:
            pair (str): Currency pair
            
        Returns:
            float: Pip size
        """
        # Get pair configuration
        pair_config = self._get_pair_config(pair)
        
        # If pip size is specified in config, use it
        if pair_config and 'pip_size' in pair_config:
            return pair_config['pip_size']
        
        # Default pip sizes
        if 'JPY' in pair:
            return 0.01  # 2 decimal places for JPY pairs
        else:
            return 0.0001  # 4 decimal places for other pairs
    
    def _get_pair_config(self, pair):
        """Get the configuration for the given pair
        
        Args:
            pair (str): Currency pair
            
        Returns:
            dict: Pair configuration
        """
        # Normalize pair format
        normalized_pair = pair.replace('/', '_').upper()
        
        # Get pairs configuration
        pairs_config = self.config.get('pairs', {})
        
        # Return pair configuration if available
        return pairs_config.get(normalized_pair, {})
    
    def _apply_position_limits(self, pair, position_size):
        """Apply position size limits based on risk parameters
        
        Args:
            pair (str): Currency pair
            position_size (float): Calculated position size
            
        Returns:
            float: Adjusted position size
        """
        # Get pair configuration
        pair_config = self._get_pair_config(pair)
        
        # Apply pair-specific limits if available
        if pair_config and 'max_position_size' in pair_config:
            position_size = min(position_size, pair_config['max_position_size'])
        
        # Apply global limits
        max_position_size = self.risk_config.get('max_position_size', float('inf'))
        min_position_size = self.risk_config.get('min_position_size', 0.0)
        
        # Ensure position size is within limits
        position_size = min(position_size, max_position_size)
        position_size = max(position_size, min_position_size)
        
        # Round to nearest lot size
        lot_size = self.risk_config.get('lot_size', 1000.0)
        position_size = round(position_size / lot_size) * lot_size
        
        return position_size
    
    def calculate_stop_loss(self, pair, entry_price, direction, atr=None):
        """Calculate the stop-loss price based on risk parameters
        
        Args:
            pair (str): Currency pair
            entry_price (float): Entry price
            direction (int): Trade direction (1 for buy, -1 for sell)
            atr (float, optional): Average True Range. Defaults to None.
            
        Returns:
            float: Stop-loss price
        """
        # Get pair configuration
        pair_config = self._get_pair_config(pair)
        
        # Get stop-loss method from config
        sl_method = self.risk_config.get('stop_loss_method', 'fixed')
        
        # Calculate stop-loss based on method
        if sl_method == 'fixed':
            # Fixed pip distance
            sl_pips = self.risk_config.get('stop_loss_pips', 50)
            
            # Apply pair-specific stop-loss if available
            if pair_config and 'stop_loss_pips' in pair_config:
                sl_pips = pair_config['stop_loss_pips']
            
            # Calculate stop-loss price
            pip_size = self._get_pip_size(pair)
            sl_distance = sl_pips * pip_size
            
            if direction > 0:  # Buy
                stop_loss = entry_price - sl_distance
            else:  # Sell
                stop_loss = entry_price + sl_distance
        
        elif sl_method == 'percent':
            # Percentage of entry price
            sl_percent = self.risk_config.get('stop_loss_percent', 0.01)  # 1%
            
            # Apply pair-specific stop-loss if available
            if pair_config and 'stop_loss_percent' in pair_config:
                sl_percent = pair_config['stop_loss_percent']
            
            # Calculate stop-loss price
            if direction > 0:  # Buy
                stop_loss = entry_price * (1 - sl_percent)
            else:  # Sell
                stop_loss = entry_price * (1 + sl_percent)
        
        elif sl_method == 'atr' and atr is not None:
            # ATR multiple
            atr_multiple = self.risk_config.get('atr_multiple', 2.0)
            
            # Apply pair-specific ATR multiple if available
            if pair_config and 'atr_multiple' in pair_config:
                atr_multiple = pair_config['atr_multiple']
            
            # Calculate stop-loss price
            sl_distance = atr * atr_multiple
            
            if direction > 0:  # Buy
                stop_loss = entry_price - sl_distance
            else:  # Sell
                stop_loss = entry_price + sl_distance
        
        else:
            # Default to fixed method
            logger.warning(f"Unknown stop-loss method: {sl_method}, defaulting to fixed")
            
            # Fixed pip distance
            sl_pips = self.risk_config.get('stop_loss_pips', 50)
            
            # Calculate stop-loss price
            pip_size = self._get_pip_size(pair)
            sl_distance = sl_pips * pip_size
            
            if direction > 0:  # Buy
                stop_loss = entry_price - sl_distance
            else:  # Sell
                stop_loss = entry_price + sl_distance
        
        # Ensure stop-loss is positive
        stop_loss = max(stop_loss, 0.00001)
        
        logger.info(f"Calculated stop-loss for {pair}: {stop_loss}")
        return stop_loss
    
    def calculate_take_profit(self, pair, entry_price, stop_loss, direction):
        """Calculate the take-profit price based on risk parameters
        
        Args:
            pair (str): Currency pair
            entry_price (float): Entry price
            stop_loss (float): Stop-loss price
            direction (int): Trade direction (1 for buy, -1 for sell)
            
        Returns:
            float: Take-profit price
        """
        # Get pair configuration
        pair_config = self._get_pair_config(pair)
        
        # Get take-profit method from config
        tp_method = self.risk_config.get('take_profit_method', 'risk_reward')
        
        # Calculate take-profit based on method
        if tp_method == 'fixed':
            # Fixed pip distance
            tp_pips = self.risk_config.get('take_profit_pips', 100)
            
            # Apply pair-specific take-profit if available
            if pair_config and 'take_profit_pips' in pair_config:
                tp_pips = pair_config['take_profit_pips']
            
            # Calculate take-profit price
            pip_size = self._get_pip_size(pair)
            tp_distance = tp_pips * pip_size
            
            if direction > 0:  # Buy
                take_profit = entry_price + tp_distance
            else:  # Sell
                take_profit = entry_price - tp_distance
        
        elif tp_method == 'percent':
            # Percentage of entry price
            tp_percent = self.risk_config.get('take_profit_percent', 0.02)  # 2%
            
            # Apply pair-specific take-profit if available
            if pair_config and 'take_profit_percent' in pair_config:
                tp_percent = pair_config['take_profit_percent']
            
            # Calculate take-profit price
            if direction > 0:  # Buy
                take_profit = entry_price * (1 + tp_percent)
            else:  # Sell
                take_profit = entry_price * (1 - tp_percent)
        
        elif tp_method == 'risk_reward':
            # Risk-reward ratio
            risk_reward_ratio = self.risk_config.get('risk_reward_ratio', 2.0)
            
            # Apply pair-specific risk-reward ratio if available
            if pair_config and 'risk_reward_ratio' in pair_config:
                risk_reward_ratio = pair_config['risk_reward_ratio']
            
            # Calculate take-profit price
            sl_distance = abs(entry_price - stop_loss)
            tp_distance = sl_distance * risk_reward_ratio
            
            if direction > 0:  # Buy
                take_profit = entry_price + tp_distance
            else:  # Sell
                take_profit = entry_price - tp_distance
        
        else:
            # Default to risk-reward method
            logger.warning(f"Unknown take-profit method: {tp_method}, defaulting to risk_reward")
            
            # Risk-reward ratio
            risk_reward_ratio = self.risk_config.get('risk_reward_ratio', 2.0)
            
            # Calculate take-profit price
            sl_distance = abs(entry_price - stop_loss)
            tp_distance = sl_distance * risk_reward_ratio
            
            if direction > 0:  # Buy
                take_profit = entry_price + tp_distance
            else:  # Sell
                take_profit = entry_price - tp_distance
        
        # Ensure take-profit is positive
        take_profit = max(take_profit, 0.00001)
        
        logger.info(f"Calculated take-profit for {pair}: {take_profit}")
        return take_profit
    
    def can_open_position(self, pair):
        """Check if a new position can be opened based on risk parameters
        
        Args:
            pair (str): Currency pair
            
        Returns:
            bool: True if a new position can be opened, False otherwise
        """
        # Check if max open positions reached
        if len(self.open_positions) >= self.max_open_positions:
            logger.warning(f"Max open positions reached: {len(self.open_positions)}/{self.max_open_positions}")
            return False
        
        # Check if max positions per pair reached
        pair_positions = [p for p in self.open_positions if p.startswith(pair)]
        max_positions_per_pair = self.risk_config.get('max_positions_per_pair', 1)
        
        if len(pair_positions) >= max_positions_per_pair:
            logger.warning(f"Max positions for {pair} reached: {len(pair_positions)}/{max_positions_per_pair}")
            return False
        
        # Check if max risk per pair reached
        pair_risk = sum(pos.get('risk_amount', 0) for pos_id, pos in self.open_positions.items() if pos_id.startswith(pair))
        max_risk_per_pair_amount = self.account_balance * self.max_risk_per_pair
        
        if pair_risk >= max_risk_per_pair_amount:
            logger.warning(f"Max risk for {pair} reached: {pair_risk}/{max_risk_per_pair_amount}")
            return False
        
        # Check if max daily drawdown reached
        if self.daily_pnl <= -self.account_balance * self.max_daily_drawdown:
            logger.warning(f"Max daily drawdown reached: {self.daily_pnl}/{-self.account_balance * self.max_daily_drawdown}")
            return False
        
        # Check if trading is allowed for this pair
        pair_config = self._get_pair_config(pair)
        if pair_config and not pair_config.get('enabled', True):
            logger.warning(f"Trading disabled for {pair}")
            return False
        
        return True
    
    def add_position(self, position_id, position_data):
        """Add a new position to the open positions
        
        Args:
            position_id (str): Position ID
            position_data (dict): Position data
            
        Returns:
            bool: True if position added successfully, False otherwise
        """
        # Check if position already exists
        if position_id in self.open_positions:
            logger.warning(f"Position {position_id} already exists")
            return False
        
        # Add position
        self.open_positions[position_id] = position_data
        logger.info(f"Position {position_id} added: {position_data}")
        
        return True
    
    def remove_position(self, position_id, pnl=0.0):
        """Remove a position from the open positions
        
        Args:
            position_id (str): Position ID
            pnl (float, optional): Profit/loss amount. Defaults to 0.0.
            
        Returns:
            bool: True if position removed successfully, False otherwise
        """
        # Check if position exists
        if position_id not in self.open_positions:
            logger.warning(f"Position {position_id} does not exist")
            return False
        
        # Remove position
        position = self.open_positions.pop(position_id)
        logger.info(f"Position {position_id} removed: {position}")
        
        # Update daily PnL
        self.daily_pnl += pnl
        logger.info(f"Daily PnL updated: {self.daily_pnl}")
        
        # Update account balance
        self.account_balance += pnl
        logger.info(f"Account balance updated: {self.account_balance}")
        
        return True
    
    def update_position(self, position_id, position_data):
        """Update an existing position
        
        Args:
            position_id (str): Position ID
            position_data (dict): Updated position data
            
        Returns:
            bool: True if position updated successfully, False otherwise
        """
        # Check if position exists
        if position_id not in self.open_positions:
            logger.warning(f"Position {position_id} does not exist")
            return False
        
        # Update position
        self.open_positions[position_id].update(position_data)
        logger.info(f"Position {position_id} updated: {self.open_positions[position_id]}")
        
        return True
    
    def check_daily_reset(self):
        """Check if daily reset is needed and reset daily PnL if necessary
        
        Returns:
            bool: True if reset performed, False otherwise
        """
        now = datetime.now()
        reset_time = datetime.strptime(self.daily_reset_time, '%H:%M:%S').time()
        
        # Check if it's a new day and past reset time
        if (now.date() > self.last_reset.date() or 
            (now.date() == self.last_reset.date() and now.time() >= reset_time and self.last_reset.time() < reset_time)):
            # Reset daily PnL
            self.daily_pnl = 0.0
            self.last_reset = now
            logger.info(f"Daily PnL reset at {now}")
            return True
        
        return False
    
    def calculate_trailing_stop(self, position_id, current_price):
        """Calculate trailing stop-loss price
        
        Args:
            position_id (str): Position ID
            current_price (float): Current price
            
        Returns:
            float: New stop-loss price or None if no update needed
        """
        # Check if position exists
        if position_id not in self.open_positions:
            logger.warning(f"Position {position_id} does not exist")
            return None
        
        # Get position data
        position = self.open_positions[position_id]
        
        # Check if trailing stop is enabled
        if not position.get('trailing_stop_enabled', False):
            return None
        
        # Get trailing stop parameters
        entry_price = position.get('entry_price', 0.0)
        current_stop = position.get('stop_loss', 0.0)
        direction = position.get('direction', 0)  # 1 for buy, -1 for sell
        activation_percent = position.get('trailing_stop_activation', 0.01)  # 1%
        trailing_distance = position.get('trailing_stop_distance', 0.005)  # 0.5%
        
        # Check if trailing stop is activated
        if direction > 0:  # Buy position
            # Calculate activation price
            activation_price = entry_price * (1 + activation_percent)
            
            # Check if price has reached activation level
            if current_price >= activation_price:
                # Calculate new stop-loss
                new_stop = current_price * (1 - trailing_distance)
                
                # Only update if new stop is higher than current stop
                if new_stop > current_stop:
                    logger.info(f"Trailing stop updated for {position_id}: {current_stop} -> {new_stop}")
                    return new_stop
        
        elif direction < 0:  # Sell position
            # Calculate activation price
            activation_price = entry_price * (1 - activation_percent)
            
            # Check if price has reached activation level
            if current_price <= activation_price:
                # Calculate new stop-loss
                new_stop = current_price * (1 + trailing_distance)
                
                # Only update if new stop is lower than current stop
                if new_stop < current_stop:
                    logger.info(f"Trailing stop updated for {position_id}: {current_stop} -> {new_stop}")
                    return new_stop
        
        return None
    
    def should_close_position(self, position_id, current_price):
        """Check if a position should be closed based on stop-loss, take-profit, or other criteria
        
        Args:
            position_id (str): Position ID
            current_price (float): Current price
            
        Returns:
            tuple: (bool, str) - True if position should be closed, False otherwise, and reason
        """
        # Check if position exists
        if position_id not in self.open_positions:
            logger.warning(f"Position {position_id} does not exist")
            return False, "Position does not exist"
        
        # Get position data
        position = self.open_positions[position_id]
        
        # Get position parameters
        entry_price = position.get('entry_price', 0.0)
        stop_loss = position.get('stop_loss', 0.0)
        take_profit = position.get('take_profit', 0.0)
        direction = position.get('direction', 0)  # 1 for buy, -1 for sell
        max_loss = position.get('max_loss', float('-inf'))
        max_profit = position.get('max_profit', float('-inf'))
        
        # Calculate current profit/loss
        if direction > 0:  # Buy position
            pnl = (current_price - entry_price) / entry_price
        else:  # Sell position
            pnl = (entry_price - current_price) / entry_price
        
        # Update max profit/loss
        max_profit = max(max_profit, pnl)
        max_loss = max(max_loss, -pnl if pnl < 0 else max_loss)
        
        # Update position data
        self.open_positions[position_id]['max_profit'] = max_profit
        self.open_positions[position_id]['max_loss'] = max_loss
        
        # Check stop-loss
        if direction > 0 and current_price <= stop_loss:  # Buy position
            logger.info(f"Stop-loss triggered for {position_id}: {current_price} <= {stop_loss}")
            return True, "Stop-loss"
        elif direction < 0 and current_price >= stop_loss:  # Sell position
            logger.info(f"Stop-loss triggered for {position_id}: {current_price} >= {stop_loss}")
            return True, "Stop-loss"
        
        # Check take-profit
        if direction > 0 and current_price >= take_profit:  # Buy position
            logger.info(f"Take-profit triggered for {position_id}: {current_price} >= {take_profit}")
            return True, "Take-profit"
        elif direction < 0 and current_price <= take_profit:  # Sell position
            logger.info(f"Take-profit triggered for {position_id}: {current_price} <= {take_profit}")
            return True, "Take-profit"
        
        # Check trailing stop
        new_stop = self.calculate_trailing_stop(position_id, current_price)
        if new_stop is not None:
            self.open_positions[position_id]['stop_loss'] = new_stop
        
        # Check time-based exit
        if 'max_duration' in position and 'open_time' in position:
            max_duration = position['max_duration']  # in seconds
            open_time = position['open_time']
            elapsed = (datetime.now() - open_time).total_seconds()
            
            if elapsed >= max_duration:
                logger.info(f"Time-based exit triggered for {position_id}: {elapsed} >= {max_duration}")
                return True, "Time-based exit"
        
        # Check drawdown exit
        if 'max_drawdown' in position:
            max_drawdown = position['max_drawdown']  # as a decimal
            drawdown_from_max = (max_profit - pnl) / (1 + max_profit) if max_profit > 0 else 0
            
            if drawdown_from_max >= max_drawdown:
                logger.info(f"Drawdown exit triggered for {position_id}: {drawdown_from_max} >= {max_drawdown}")
                return True, "Drawdown exit"
        
        return False, ""