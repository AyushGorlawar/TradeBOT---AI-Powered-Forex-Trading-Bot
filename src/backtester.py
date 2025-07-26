#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Backtester module for testing trading strategies on historical data
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os
import json
from tqdm import tqdm

logger = logging.getLogger("TradeBOT.Backtester")


class Backtester:
    """Class for backtesting trading strategies on historical data"""
    
    def __init__(self, config, data_fetcher, indicators, signal_generator, risk_manager, visualizer=None):
        """Initialize the backtester
        
        Args:
            config (dict): Configuration dictionary
            data_fetcher (DataFetcher): Data fetcher instance
            indicators (Indicators): Technical indicators instance
            signal_generator (SignalGenerator): Signal generator instance
            risk_manager (RiskManager): Risk manager instance
            visualizer (Visualizer, optional): Visualizer instance. Defaults to None.
        """
        self.config = config
        self.data_fetcher = data_fetcher
        self.indicators = indicators
        self.signal_generator = signal_generator
        self.risk_manager = risk_manager
        self.visualizer = visualizer
        
        # Backtest configuration
        self.backtest_config = self.config.get('backtest', {})
        self.initial_balance = self.backtest_config.get('initial_balance', 10000)
        self.commission = self.backtest_config.get('commission', 0.0001)  # 1 pip commission by default
        self.slippage = self.backtest_config.get('slippage', 0.0001)  # 1 pip slippage by default
        self.leverage = self.backtest_config.get('leverage', 1)
        
        # Results storage
        self.results_dir = self.backtest_config.get('results_dir', 'backtest_results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Initialize results
        self.reset_results()
    
    def reset_results(self):
        """Reset backtest results"""
        self.balance_history = [{'timestamp': datetime.now(), 'balance': self.initial_balance}]
        self.equity_history = [{'timestamp': datetime.now(), 'equity': self.initial_balance}]
        self.trades = []
        self.open_positions = {}
        self.current_balance = self.initial_balance
        self.current_equity = self.initial_balance
        self.trade_id = 0
    
    def run_backtest(self, pairs, start_date, end_date, timeframe='H1'):
        """Run backtest on multiple pairs
        
        Args:
            pairs (list): List of currency pairs to backtest
            start_date (str): Start date in format 'YYYY-MM-DD'
            end_date (str): End date in format 'YYYY-MM-DD'
            timeframe (str, optional): Timeframe to use. Defaults to 'H1'.
            
        Returns:
            dict: Backtest results
        """
        logger.info(f"Starting backtest from {start_date} to {end_date} on {len(pairs)} pairs")
        
        # Reset results
        self.reset_results()
        
        # Convert dates to datetime
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Run backtest for each pair
        all_pair_results = {}
        for pair in tqdm(pairs, desc="Backtesting pairs"):
            pair_results = self.backtest_pair(pair, start_dt, end_dt, timeframe)
            all_pair_results[pair] = pair_results
        
        # Calculate overall performance metrics
        performance = self.calculate_performance()
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = os.path.join(self.results_dir, f"backtest_{timestamp}.json")
        
        # Prepare results for saving
        results = {
            'config': {
                'pairs': pairs,
                'start_date': start_date,
                'end_date': end_date,
                'timeframe': timeframe,
                'initial_balance': self.initial_balance,
                'commission': self.commission,
                'slippage': self.slippage,
                'leverage': self.leverage
            },
            'performance': performance,
            'trades': self.prepare_trades_for_json()
        }
        
        # Save results
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=4, default=str)
        
        logger.info(f"Backtest completed. Results saved to {results_file}")
        
        # Generate equity curve chart if visualizer is available
        if self.visualizer:
            chart_path = os.path.join(self.results_dir, f"backtest_performance_{timestamp}.png")
            self.visualizer.create_performance_chart(self.trades, self.balance_history, chart_path)
        
        return {
            'performance': performance,
            'trades': self.trades,
            'balance_history': self.balance_history,
            'equity_history': self.equity_history,
            'results_file': results_file
        }
    
    def backtest_pair(self, pair, start_date, end_date, timeframe):
        """Run backtest on a single pair
        
        Args:
            pair (str): Currency pair
            start_date (datetime): Start date
            end_date (datetime): End date
            timeframe (str): Timeframe
            
        Returns:
            dict: Pair backtest results
        """
        logger.info(f"Backtesting {pair} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Fetch historical data
        try:
            # Calculate limit based on timeframe and date range
            if timeframe == '1h':
                limit = int((end_date - start_date).total_seconds() / 3600) + 24  # Add buffer
            elif timeframe == '1d':
                limit = (end_date - start_date).days + 5  # Add buffer
            else:
                limit = 1000  # Default limit
                
            data = self.data_fetcher.get_historical_data(pair, timeframe, limit)
            if data.empty:
                logger.warning(f"No data available for {pair} in the specified date range")
                return {'error': 'No data available'}
        except Exception as e:
            logger.error(f"Error fetching data for {pair}: {str(e)}")
            return {'error': str(e)}
        
        # Calculate indicators
        data = self.indicators.calculate_all(data)
        
        # Generate signals
        signals = self.signal_generator.generate_signals(data, pair)
        
        # Run through each candle and simulate trading
        pair_trades = []
        
        for i in range(1, len(data)):
            current_time = data.index[i]
            current_row = data.iloc[i]
            previous_row = data.iloc[i-1]
            
            # Update open positions
            self.update_positions(current_time, current_row, pair)
            
            # Check for signals at previous candle
            if i-1 in signals.index:
                signal = signals.loc[data.index[i-1]]['signal']
                
                if signal != 0:  # If there's a signal
                    # Calculate position size
                    risk_amount = self.risk_manager.calculate_position_size(
                        self.current_balance, 
                        pair, 
                        signal, 
                        current_row['close']
                    )
                    
                    # Open position if we have a valid risk amount
                    if risk_amount > 0:
                        # Calculate stop loss and take profit
                        stop_loss = self.risk_manager.calculate_stop_loss(
                            pair, 
                            signal, 
                            current_row['close'], 
                            current_row
                        )
                        
                        take_profit = self.risk_manager.calculate_take_profit(
                            pair, 
                            signal, 
                            current_row['close'], 
                            current_row
                        )
                        
                        # Open position
                        self.open_position(
                            pair, 
                            signal, 
                            current_time, 
                            current_row['close'], 
                            risk_amount, 
                            stop_loss, 
                            take_profit
                        )
        
        # Close any remaining open positions at the end of the backtest
        for pair_id, position in list(self.open_positions.items()):
            if position['pair'] == pair:
                self.close_position(
                    position['id'], 
                    data.index[-1], 
                    data.iloc[-1]['close'], 
                    'end_of_backtest'
                )
        
        # Filter trades for this pair
        pair_trades = [trade for trade in self.trades if trade['pair'] == pair]
        
        return {
            'trades': pair_trades,
            'total_trades': len(pair_trades),
            'winning_trades': len([t for t in pair_trades if t['pnl'] > 0]),
            'losing_trades': len([t for t in pair_trades if t['pnl'] < 0])
        }
    
    def open_position(self, pair, direction, timestamp, price, amount, stop_loss, take_profit):
        """Open a new position
        
        Args:
            pair (str): Currency pair
            direction (int): 1 for buy, -1 for sell
            timestamp (datetime): Entry time
            price (float): Entry price
            amount (float): Position size
            stop_loss (float): Stop loss price
            take_profit (float): Take profit price
            
        Returns:
            int: Trade ID
        """
        # Apply slippage
        if direction > 0:  # Buy
            entry_price = price * (1 + self.slippage)
        else:  # Sell
            entry_price = price * (1 - self.slippage)
        
        # Calculate commission
        commission_amount = amount * self.commission
        
        # Deduct commission from balance
        self.current_balance -= commission_amount
        
        # Create trade object
        self.trade_id += 1
        trade = {
            'id': self.trade_id,
            'pair': pair,
            'direction': direction,
            'open_time': timestamp,
            'entry_price': entry_price,
            'amount': amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'commission': commission_amount,
            'status': 'open',
            'pnl': 0,
            'close_time': None,
            'exit_price': None,
            'exit_reason': None
        }
        
        # Add to open positions
        self.open_positions[self.trade_id] = trade
        
        # Log the trade
        logger.info(f"Opened {pair} {'BUY' if direction > 0 else 'SELL'} position at {entry_price} with amount {amount}")
        
        return self.trade_id
    
    def close_position(self, trade_id, timestamp, price, reason):
        """Close an open position
        
        Args:
            trade_id (int): Trade ID
            timestamp (datetime): Exit time
            price (float): Exit price
            reason (str): Exit reason
            
        Returns:
            dict: Closed trade
        """
        if trade_id not in self.open_positions:
            logger.warning(f"Trade ID {trade_id} not found in open positions")
            return None
        
        # Get the trade
        trade = self.open_positions[trade_id]
        
        # Apply slippage
        if trade['direction'] > 0:  # Buy position closing
            exit_price = price * (1 - self.slippage)
        else:  # Sell position closing
            exit_price = price * (1 + self.slippage)
        
        # Calculate P&L
        if trade['direction'] > 0:  # Buy position
            pnl = (exit_price - trade['entry_price']) * trade['amount'] * self.leverage
        else:  # Sell position
            pnl = (trade['entry_price'] - exit_price) * trade['amount'] * self.leverage
        
        # Calculate commission
        commission_amount = trade['amount'] * self.commission
        
        # Deduct commission from P&L
        pnl -= commission_amount
        
        # Update trade object
        trade['close_time'] = timestamp
        trade['exit_price'] = exit_price
        trade['exit_reason'] = reason
        trade['pnl'] = pnl
        trade['status'] = 'closed'
        trade['commission'] += commission_amount  # Add closing commission
        
        # Update balance
        self.current_balance += pnl
        
        # Add to balance history
        self.balance_history.append({
            'timestamp': timestamp,
            'balance': self.current_balance
        })
        
        # Add to trades list
        self.trades.append(trade)
        
        # Remove from open positions
        del self.open_positions[trade_id]
        
        # Log the trade
        logger.info(f"Closed {trade['pair']} {'BUY' if trade['direction'] > 0 else 'SELL'} position at {exit_price} with P&L {pnl:.2f} ({reason})")
        
        return trade
    
    def update_positions(self, timestamp, current_row, pair):
        """Update open positions for a pair
        
        Args:
            timestamp (datetime): Current timestamp
            current_row (pandas.Series): Current price data
            pair (str): Currency pair
        """
        # Update equity
        self.current_equity = self.current_balance
        
        # Check each open position
        for trade_id, position in list(self.open_positions.items()):
            if position['pair'] != pair:
                continue
            
            # Calculate current P&L
            if position['direction'] > 0:  # Buy position
                unrealized_pnl = (current_row['close'] - position['entry_price']) * position['amount'] * self.leverage
            else:  # Sell position
                unrealized_pnl = (position['entry_price'] - current_row['close']) * position['amount'] * self.leverage
            
            # Add to equity
            self.current_equity += unrealized_pnl
            
            # Check stop loss
            if position['direction'] > 0 and current_row['low'] <= position['stop_loss']:  # Buy position
                self.close_position(trade_id, timestamp, position['stop_loss'], 'stop_loss')
            elif position['direction'] < 0 and current_row['high'] >= position['stop_loss']:  # Sell position
                self.close_position(trade_id, timestamp, position['stop_loss'], 'stop_loss')
            
            # Check take profit
            elif position['direction'] > 0 and current_row['high'] >= position['take_profit']:  # Buy position
                self.close_position(trade_id, timestamp, position['take_profit'], 'take_profit')
            elif position['direction'] < 0 and current_row['low'] <= position['take_profit']:  # Sell position
                self.close_position(trade_id, timestamp, position['take_profit'], 'take_profit')
        
        # Add to equity history
        self.equity_history.append({
            'timestamp': timestamp,
            'equity': self.current_equity
        })
    
    def calculate_performance(self):
        """Calculate performance metrics
        
        Returns:
            dict: Performance metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'average_trade': 0,
                'average_winner': 0,
                'average_loser': 0,
                'largest_winner': 0,
                'largest_loser': 0,
                'final_balance': self.initial_balance,
                'return_pct': 0
            }
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl'] > 0])
        losing_trades = len([t for t in self.trades if t['pnl'] < 0])
        break_even_trades = total_trades - winning_trades - losing_trades
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum(t['pnl'] for t in self.trades)
        gross_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        gross_loss = sum(t['pnl'] for t in self.trades if t['pnl'] < 0)
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')
        
        # Average trade metrics
        average_trade = total_pnl / total_trades if total_trades > 0 else 0
        average_winner = gross_profit / winning_trades if winning_trades > 0 else 0
        average_loser = gross_loss / losing_trades if losing_trades > 0 else 0
        
        # Largest trades
        largest_winner = max([t['pnl'] for t in self.trades], default=0)
        largest_loser = min([t['pnl'] for t in self.trades], default=0)
        
        # Drawdown calculation
        balance_values = [entry['balance'] for entry in self.balance_history]
        max_balance = self.initial_balance
        max_drawdown = 0
        max_drawdown_pct = 0
        
        for balance in balance_values:
            if balance > max_balance:
                max_balance = balance
            drawdown = max_balance - balance
            drawdown_pct = drawdown / max_balance if max_balance > 0 else 0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        # Return calculation
        final_balance = self.balance_history[-1]['balance'] if self.balance_history else self.initial_balance
        return_pct = (final_balance - self.initial_balance) / self.initial_balance * 100
        
        # Sharpe ratio calculation (simplified)
        daily_returns = []
        for i in range(1, len(self.balance_history)):
            prev_balance = self.balance_history[i-1]['balance']
            curr_balance = self.balance_history[i]['balance']
            daily_return = (curr_balance - prev_balance) / prev_balance if prev_balance > 0 else 0
            daily_returns.append(daily_return)
        
        if daily_returns:
            avg_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'break_even_trades': break_even_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'average_trade': average_trade,
            'average_winner': average_winner,
            'average_loser': average_loser,
            'largest_winner': largest_winner,
            'largest_loser': largest_loser,
            'final_balance': final_balance,
            'return_pct': return_pct
        }
    
    def prepare_trades_for_json(self):
        """Prepare trades for JSON serialization
        
        Returns:
            list: JSON-serializable trades
        """
        json_trades = []
        
        for trade in self.trades:
            json_trade = trade.copy()
            json_trade['open_time'] = trade['open_time'].strftime('%Y-%m-%d %H:%M:%S')
            if trade['close_time']:
                json_trade['close_time'] = trade['close_time'].strftime('%Y-%m-%d %H:%M:%S')
            json_trades.append(json_trade)
        
        return json_trades
    
    # Removed plot_equity_curve method as we now use visualizer.create_performance_chart
        

    
    def generate_trade_report(self, save_path=None):
        """Generate a detailed trade report
        
        Args:
            save_path (str, optional): Path to save the report. Defaults to None.
            
        Returns:
            str: Report text
        """
        if not self.trades:
            return "No trades available for reporting"
        
        # Calculate performance metrics
        performance = self.calculate_performance()
        
        # Generate report text
        report = "===== BACKTEST REPORT =====\n\n"
        
        # Summary section
        report += "SUMMARY:\n"
        report += f"Initial Balance: ${self.initial_balance:.2f}\n"
        report += f"Final Balance: ${performance['final_balance']:.2f}\n"
        report += f"Total P&L: ${performance['total_pnl']:.2f} ({performance['return_pct']:.2f}%)\n"
        report += f"Total Trades: {performance['total_trades']}\n"
        report += f"Win Rate: {performance['win_rate']*100:.2f}%\n"
        report += f"Profit Factor: {performance['profit_factor']:.2f}\n"
        report += f"Max Drawdown: ${performance['max_drawdown']:.2f} ({performance['max_drawdown_pct']*100:.2f}%)\n"
        report += f"Sharpe Ratio: {performance['sharpe_ratio']:.2f}\n\n"
        
        # Trade statistics section
        report += "TRADE STATISTICS:\n"
        report += f"Winning Trades: {performance['winning_trades']}\n"
        report += f"Losing Trades: {performance['losing_trades']}\n"
        report += f"Break-even Trades: {performance['break_even_trades']}\n"
        report += f"Average Trade: ${performance['average_trade']:.2f}\n"
        report += f"Average Winner: ${performance['average_winner']:.2f}\n"
        report += f"Average Loser: ${performance['average_loser']:.2f}\n"
        report += f"Largest Winner: ${performance['largest_winner']:.2f}\n"
        report += f"Largest Loser: ${performance['largest_loser']:.2f}\n\n"
        
        # Pair performance section
        report += "PAIR PERFORMANCE:\n"
        pairs = set(trade['pair'] for trade in self.trades)
        
        for pair in pairs:
            pair_trades = [trade for trade in self.trades if trade['pair'] == pair]
            pair_pnl = sum(trade['pnl'] for trade in pair_trades)
            pair_win_rate = len([t for t in pair_trades if t['pnl'] > 0]) / len(pair_trades) if pair_trades else 0
            
            report += f"{pair}: {len(pair_trades)} trades, ${pair_pnl:.2f}, Win Rate: {pair_win_rate*100:.2f}%\n"
        
        report += "\n"
        
        # Recent trades section
        report += "RECENT TRADES:\n"
        recent_trades = sorted(self.trades, key=lambda x: x['close_time'] if x['close_time'] else datetime.now(), reverse=True)[:10]
        
        for trade in recent_trades:
            direction = "BUY" if trade['direction'] > 0 else "SELL"
            open_time = trade['open_time'].strftime('%Y-%m-%d %H:%M')
            close_time = trade['close_time'].strftime('%Y-%m-%d %H:%M') if trade['close_time'] else "OPEN"
            
            report += f"ID: {trade['id']}, {trade['pair']} {direction}, "
            report += f"Open: {open_time} @ {trade['entry_price']:.5f}, "
            report += f"Close: {close_time} @ {trade['exit_price']:.5f if trade['exit_price'] else 0:.5f}, "
            report += f"P&L: ${trade['pnl']:.2f}, Reason: {trade['exit_reason'] if trade['exit_reason'] else 'N/A'}\n"
        
        # Save report if path provided
        if save_path:
            with open(save_path, 'w') as f:
                f.write(report)
            logger.info(f"Trade report saved to {save_path}")
        
        return report
    
    def generate_report(self, results, pair, timeframe, strategy):
        """Generate a backtest report and save it to a file
        
        Args:
            results (dict): Backtest results
            pair (str): Currency pair
            timeframe (str): Timeframe
            strategy (str): Strategy name
            
        Returns:
            str: Path to the report file
        """
        # Create report directory if it doesn't exist
        report_dir = os.path.join(self.results_dir, 'reports')
        os.makedirs(report_dir, exist_ok=True)
        
        # Generate report filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"{pair}_{timeframe}_{strategy}_{timestamp}.txt"
        report_path = os.path.join(report_dir, report_filename)
        
        # Generate trade report
        report_text = self.generate_trade_report(report_path)
        
        # Generate equity curve chart if visualizer is available
        if self.visualizer:
            chart_path = os.path.join(report_dir, f"{pair}_{timeframe}_{strategy}_{timestamp}.png")
            if self.visualizer:
                self.visualizer.create_performance_chart(self.trades, self.balance_history, chart_path)
        
        return report_path