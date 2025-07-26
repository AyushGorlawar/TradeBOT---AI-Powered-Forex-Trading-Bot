#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualizer module for generating charts and visualizing trading signals
"""

import logging
import os
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger("TradeBOT.Visualizer")


class Visualizer:
    """Class for generating charts and visualizing trading signals"""
    
    def __init__(self, config=None):
        """Initialize the visualizer
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        self.config = config or {}
        self.viz_config = self.config.get('visualization', {})
        self.chart_dir = self.viz_config.get('chart_dir', 'charts')
        
        # Create chart directory if it doesn't exist
        os.makedirs(self.chart_dir, exist_ok=True)
        
        # Set default chart style
        self.chart_style = self.viz_config.get('chart_style', 'dark_background')
        self.chart_type = self.viz_config.get('chart_type', 'candlestick')
        self.chart_size = self.viz_config.get('chart_size', (12, 8))
        
        # Initialize plotting libraries
        self._init_plotting_libs()
    
    def _init_plotting_libs(self):
        """Initialize plotting libraries based on availability"""
        self.plotting_lib = self.viz_config.get('plotting_lib', 'matplotlib')
        
        try:
            if self.plotting_lib == 'plotly':
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                self.go = go
                self.make_subplots = make_subplots
                logger.info("Using Plotly for visualization")
            else:  # Default to matplotlib
                import matplotlib.pyplot as plt
                import matplotlib.dates as mdates
                from matplotlib.ticker import FuncFormatter
                from mplfinance.original_flavor import candlestick_ohlc
                self.plt = plt
                self.mdates = mdates
                self.FuncFormatter = FuncFormatter
                self.candlestick_ohlc = candlestick_ohlc
                
                # Set matplotlib style
                try:
                    plt.style.use(self.chart_style)
                except Exception:
                    plt.style.use('dark_background')
                
                logger.info("Using Matplotlib for visualization")
        
        except ImportError as e:
            logger.warning(f"Could not import plotting library: {str(e)}. Visualization will be limited.")
            self.plotting_lib = None
    
    def create_chart(self, data, pair, indicators=None, signals=None, trades=None, save_path=None):
        """Create a chart with price data, indicators, signals, and trades
        
        Args:
            data (pandas.DataFrame): Price data
            pair (str): Currency pair
            indicators (list, optional): List of indicators to plot. Defaults to None.
            signals (pandas.DataFrame, optional): Signal data. Defaults to None.
            trades (list, optional): List of trades. Defaults to None.
            save_path (str, optional): Path to save the chart. Defaults to None.
            
        Returns:
            object: Figure object or None if visualization is not available
        """
        if self.plotting_lib is None:
            logger.warning("No plotting library available")
            return None
        
        if data.empty:
            logger.warning("Empty data provided for visualization")
            return None
        
        # Make a copy of the data to avoid modifying the original
        df = data.copy()
        
        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df.set_index('timestamp', inplace=True)
            else:
                logger.warning("No datetime index or timestamp column found")
                return None
        
        # Create chart based on selected library
        if self.plotting_lib == 'plotly':
            return self._create_plotly_chart(df, pair, indicators, signals, trades, save_path)
        else:  # Default to matplotlib
            return self._create_matplotlib_chart(df, pair, indicators, signals, trades, save_path)
    
    def _create_plotly_chart(self, df, pair, indicators=None, signals=None, trades=None, save_path=None):
        """Create a chart using Plotly
        
        Args:
            df (pandas.DataFrame): Price data
            pair (str): Currency pair
            indicators (list, optional): List of indicators to plot. Defaults to None.
            signals (pandas.DataFrame, optional): Signal data. Defaults to None.
            trades (list, optional): List of trades. Defaults to None.
            save_path (str, optional): Path to save the chart. Defaults to None.
            
        Returns:
            plotly.graph_objects.Figure: Plotly figure
        """
        # Determine number of rows based on indicators
        n_rows = 2  # Price chart and volume
        indicator_rows = {}
        
        if indicators:
            for indicator in indicators:
                if indicator in ['rsi', 'stoch_k', 'stoch_d', 'cci']:
                    if 'oscillators' not in indicator_rows:
                        indicator_rows['oscillators'] = n_rows
                        n_rows += 1
                elif indicator in ['macd', 'macd_signal', 'macd_histogram']:
                    if 'macd' not in indicator_rows:
                        indicator_rows['macd'] = n_rows
                        n_rows += 1
                elif indicator in ['adx', 'dmi_plus', 'dmi_minus']:
                    if 'dmi' not in indicator_rows:
                        indicator_rows['dmi'] = n_rows
                        n_rows += 1
        
        # Create subplot grid
        fig = self.make_subplots(
            rows=n_rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.5] + [0.1] * (n_rows - 1),
            subplot_titles=([f"{pair} - {df.index[-1].strftime('%Y-%m-%d %H:%M')}"] + 
                            ["Volume"] + 
                            [k.upper() for k in indicator_rows.keys()])
        )
        
        # Add price data
        if self.chart_type == 'candlestick':
            fig.add_trace(
                self.go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="Price"
                ),
                row=1, col=1
            )
        elif self.chart_type == 'line':
            fig.add_trace(
                self.go.Scatter(
                    x=df.index,
                    y=df['close'],
                    mode='lines',
                    name="Price"
                ),
                row=1, col=1
            )
        elif self.chart_type == 'ohlc':
            fig.add_trace(
                self.go.Ohlc(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="Price"
                ),
                row=1, col=1
            )
        
        # Add volume
        colors = np.where(df['close'] > df['open'], 'green', 'red')
        fig.add_trace(
            self.go.Bar(
                x=df.index,
                y=df['volume'],
                name="Volume",
                marker_color=colors
            ),
            row=2, col=1
        )
        
        # Add indicators
        if indicators:
            for indicator in indicators:
                if indicator in df.columns:
                    # Determine which subplot to use
                    row = 1  # Default to price chart
                    
                    # Moving averages go on the price chart
                    if indicator.startswith('sma_') or indicator.startswith('ema_'):
                        row = 1
                    # RSI, Stochastic go on the oscillator chart
                    elif indicator in ['rsi', 'stoch_k', 'stoch_d', 'cci']:
                        row = indicator_rows.get('oscillators', 1)
                    # MACD goes on its own chart
                    elif indicator in ['macd', 'macd_signal', 'macd_histogram']:
                        row = indicator_rows.get('macd', 1)
                    # DMI goes on its own chart
                    elif indicator in ['adx', 'dmi_plus', 'dmi_minus']:
                        row = indicator_rows.get('dmi', 1)
                    # Bollinger Bands go on the price chart
                    elif indicator in ['bb_upper', 'bb_middle', 'bb_lower']:
                        row = 1
                    
                    # Add the indicator trace
                    if indicator == 'macd_histogram':
                        # MACD histogram as bar chart
                        colors = np.where(df[indicator] > 0, 'green', 'red')
                        fig.add_trace(
                            self.go.Bar(
                                x=df.index,
                                y=df[indicator],
                                name=indicator,
                                marker_color=colors
                            ),
                            row=row, col=1
                        )
                    else:
                        # Line chart for other indicators
                        fig.add_trace(
                            self.go.Scatter(
                                x=df.index,
                                y=df[indicator],
                                mode='lines',
                                name=indicator
                            ),
                            row=row, col=1
                        )
        
        # Add signals
        if signals is not None and not signals.empty:
            # Buy signals
            buy_signals = signals[signals['signal'] > 0]
            if not buy_signals.empty:
                fig.add_trace(
                    self.go.Scatter(
                        x=buy_signals.index,
                        y=buy_signals['close'],
                        mode='markers',
                        name='Buy Signal',
                        marker=dict(
                            symbol='triangle-up',
                            size=10,
                            color='green',
                            line=dict(width=2, color='darkgreen')
                        )
                    ),
                    row=1, col=1
                )
            
            # Sell signals
            sell_signals = signals[signals['signal'] < 0]
            if not sell_signals.empty:
                fig.add_trace(
                    self.go.Scatter(
                        x=sell_signals.index,
                        y=sell_signals['close'],
                        mode='markers',
                        name='Sell Signal',
                        marker=dict(
                            symbol='triangle-down',
                            size=10,
                            color='red',
                            line=dict(width=2, color='darkred')
                        )
                    ),
                    row=1, col=1
                )
        
        # Add trades
        if trades:
            for trade in trades:
                if trade['status'] == 'open':
                    # Open trade
                    entry_time = trade.get('open_time')
                    entry_price = trade.get('entry_price')
                    direction = trade.get('direction')
                    
                    if entry_time and entry_price:
                        # Entry point
                        fig.add_trace(
                            self.go.Scatter(
                                x=[entry_time],
                                y=[entry_price],
                                mode='markers',
                                name=f"Trade {trade['id']} Entry",
                                marker=dict(
                                    symbol='circle',
                                    size=12,
                                    color='green' if direction > 0 else 'red',
                                    line=dict(width=2, color='white')
                                )
                            ),
                            row=1, col=1
                        )
                        
                        # Stop-loss and take-profit lines
                        if 'stop_loss' in trade:
                            fig.add_shape(
                                type="line",
                                x0=entry_time,
                                y0=trade['stop_loss'],
                                x1=df.index[-1],
                                y1=trade['stop_loss'],
                                line=dict(color="red", width=1, dash="dash"),
                                row=1, col=1
                            )
                        
                        if 'take_profit' in trade:
                            fig.add_shape(
                                type="line",
                                x0=entry_time,
                                y0=trade['take_profit'],
                                x1=df.index[-1],
                                y1=trade['take_profit'],
                                line=dict(color="green", width=1, dash="dash"),
                                row=1, col=1
                            )
                
                elif trade['status'] == 'closed':
                    # Closed trade
                    entry_time = trade.get('open_time')
                    entry_price = trade.get('entry_price')
                    exit_time = trade.get('close_time')
                    exit_price = trade.get('exit_price')
                    direction = trade.get('direction')
                    pnl = trade.get('pnl', 0)
                    
                    if entry_time and entry_price and exit_time and exit_price:
                        # Entry and exit points
                        fig.add_trace(
                            self.go.Scatter(
                                x=[entry_time, exit_time],
                                y=[entry_price, exit_price],
                                mode='lines+markers',
                                name=f"Trade {trade['id']}",
                                line=dict(color='green' if pnl > 0 else 'red', width=2),
                                marker=dict(
                                    symbol=['circle', 'circle'],
                                    size=8,
                                    color=['green' if direction > 0 else 'red', 'red' if direction > 0 else 'green'],
                                    line=dict(width=1, color='white')
                                )
                            ),
                            row=1, col=1
                        )
        
        # Update layout
        fig.update_layout(
            title=f"{pair} - {df.index[-1].strftime('%Y-%m-%d %H:%M')}",
            xaxis_title="Date",
            yaxis_title="Price",
            height=200 * n_rows,
            width=1000,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template="plotly_dark" if self.chart_style == 'dark_background' else "plotly_white"
        )
        
        # Hide weekend gaps in forex
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        
        # Save the chart if a path is provided
        if save_path:
            if not save_path.endswith('.html'):
                save_path += '.html'
            fig.write_html(save_path)
            logger.info(f"Chart saved to {save_path}")
        
        return fig
    
    def _create_matplotlib_chart(self, df, pair, indicators=None, signals=None, trades=None, save_path=None):
        """Create a chart using Matplotlib
        
        Args:
            df (pandas.DataFrame): Price data
            pair (str): Currency pair
            indicators (list, optional): List of indicators to plot. Defaults to None.
            signals (pandas.DataFrame, optional): Signal data. Defaults to None.
            trades (list, optional): List of trades. Defaults to None.
            save_path (str, optional): Path to save the chart. Defaults to None.
            
        Returns:
            matplotlib.figure.Figure: Matplotlib figure
        """
        # Determine number of subplots based on indicators
        n_rows = 2  # Price chart and volume
        indicator_rows = {}
        
        if indicators:
            for indicator in indicators:
                if indicator in ['rsi', 'stoch_k', 'stoch_d', 'cci']:
                    if 'oscillators' not in indicator_rows:
                        indicator_rows['oscillators'] = n_rows
                        n_rows += 1
                elif indicator in ['macd', 'macd_signal', 'macd_histogram']:
                    if 'macd' not in indicator_rows:
                        indicator_rows['macd'] = n_rows
                        n_rows += 1
                elif indicator in ['adx', 'dmi_plus', 'dmi_minus']:
                    if 'dmi' not in indicator_rows:
                        indicator_rows['dmi'] = n_rows
                        n_rows += 1
        
        # Create figure and subplots
        fig, axs = self.plt.subplots(n_rows, 1, figsize=self.chart_size, sharex=True, gridspec_kw={'height_ratios': [3, 1] + [1] * (n_rows - 2)})
        
        # Convert to list if only one subplot
        if n_rows == 1:
            axs = [axs]
        
        # Format date axis
        axs[-1].xaxis.set_major_formatter(self.mdates.DateFormatter('%Y-%m-%d %H:%M'))
        self.plt.xticks(rotation=45)
        
        # Plot price data
        ax_price = axs[0]
        
        if self.chart_type == 'candlestick':
            # Convert date to matplotlib format
            ohlc = df[['open', 'high', 'low', 'close']].copy()
            ohlc.index = self.mdates.date2num(ohlc.index.to_pydatetime())
            ohlc = ohlc.reset_index()
            
            # Plot candlestick chart
            self.candlestick_ohlc(ax_price, ohlc.values, width=0.6, colorup='green', colordown='red', alpha=0.8)
        
        elif self.chart_type == 'line':
            ax_price.plot(df.index, df['close'], label='Close')
        
        elif self.chart_type == 'ohlc':
            # Convert date to matplotlib format
            ohlc = df[['open', 'high', 'low', 'close']].copy()
            ohlc.index = self.mdates.date2num(ohlc.index.to_pydatetime())
            ohlc = ohlc.reset_index()
            
            # Plot OHLC chart
            self.candlestick_ohlc(ax_price, ohlc.values, width=0.6, colorup='green', colordown='red', alpha=0.8)
        
        ax_price.set_title(f"{pair} - {df.index[-1].strftime('%Y-%m-%d %H:%M')}")
        ax_price.set_ylabel('Price')
        ax_price.grid(True, alpha=0.3)
        
        # Plot volume
        ax_volume = axs[1]
        ax_volume.bar(df.index, df['volume'], color=np.where(df['close'] > df['open'], 'green', 'red'), alpha=0.5)
        ax_volume.set_ylabel('Volume')
        ax_volume.grid(True, alpha=0.3)
        
        # Plot indicators
        if indicators:
            for indicator in indicators:
                if indicator in df.columns:
                    # Determine which subplot to use
                    ax = ax_price  # Default to price chart
                    
                    # Moving averages go on the price chart
                    if indicator.startswith('sma_') or indicator.startswith('ema_'):
                        ax = ax_price
                    # RSI, Stochastic go on the oscillator chart
                    elif indicator in ['rsi', 'stoch_k', 'stoch_d', 'cci']:
                        row_idx = indicator_rows.get('oscillators', 0)
                        ax = axs[row_idx]
                        if indicator == 'rsi':
                            ax.axhline(70, color='red', linestyle='--', alpha=0.5)
                            ax.axhline(30, color='green', linestyle='--', alpha=0.5)
                        elif indicator in ['stoch_k', 'stoch_d']:
                            ax.axhline(80, color='red', linestyle='--', alpha=0.5)
                            ax.axhline(20, color='green', linestyle='--', alpha=0.5)
                        ax.set_ylabel('Oscillators')
                    # MACD goes on its own chart
                    elif indicator in ['macd', 'macd_signal', 'macd_histogram']:
                        row_idx = indicator_rows.get('macd', 0)
                        ax = axs[row_idx]
                        ax.set_ylabel('MACD')
                    # DMI goes on its own chart
                    elif indicator in ['adx', 'dmi_plus', 'dmi_minus']:
                        row_idx = indicator_rows.get('dmi', 0)
                        ax = axs[row_idx]
                        ax.set_ylabel('DMI')
                    # Bollinger Bands go on the price chart
                    elif indicator in ['bb_upper', 'bb_middle', 'bb_lower']:
                        ax = ax_price
                    
                    # Plot the indicator
                    if indicator == 'macd_histogram':
                        # MACD histogram as bar chart
                        ax.bar(df.index, df[indicator], color=np.where(df[indicator] > 0, 'green', 'red'), alpha=0.5, label=indicator)
                    else:
                        # Line chart for other indicators
                        ax.plot(df.index, df[indicator], label=indicator)
                    
                    ax.grid(True, alpha=0.3)
                    ax.legend(loc='upper left')
        
        # Plot signals
        if signals is not None and not signals.empty:
            # Buy signals
            buy_signals = signals[signals['signal'] > 0]
            if not buy_signals.empty:
                ax_price.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='Buy Signal')
            
            # Sell signals
            sell_signals = signals[signals['signal'] < 0]
            if not sell_signals.empty:
                ax_price.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='Sell Signal')
        
        # Plot trades
        if trades:
            for trade in trades:
                if trade['status'] == 'open':
                    # Open trade
                    entry_time = trade.get('open_time')
                    entry_price = trade.get('entry_price')
                    direction = trade.get('direction')
                    
                    if entry_time and entry_price:
                        # Entry point
                        ax_price.scatter([entry_time], [entry_price], marker='o', color='green' if direction > 0 else 'red', s=100, zorder=5)
                        
                        # Stop-loss and take-profit lines
                        if 'stop_loss' in trade:
                            ax_price.axhline(trade['stop_loss'], color='red', linestyle='--', alpha=0.5)
                        
                        if 'take_profit' in trade:
                            ax_price.axhline(trade['take_profit'], color='green', linestyle='--', alpha=0.5)
                
                elif trade['status'] == 'closed':
                    # Closed trade
                    entry_time = trade.get('open_time')
                    entry_price = trade.get('entry_price')
                    exit_time = trade.get('close_time')
                    exit_price = trade.get('exit_price')
                    direction = trade.get('direction')
                    pnl = trade.get('pnl', 0)
                    
                    if entry_time and entry_price and exit_time and exit_price:
                        # Plot trade line
                        ax_price.plot([entry_time, exit_time], [entry_price, exit_price], color='green' if pnl > 0 else 'red', linewidth=2)
                        
                        # Entry and exit points
                        ax_price.scatter([entry_time], [entry_price], marker='o', color='green' if direction > 0 else 'red', s=80, zorder=5)
                        ax_price.scatter([exit_time], [exit_price], marker='o', color='red' if direction > 0 else 'green', s=80, zorder=5)
        
        # Add legend to price chart
        ax_price.legend(loc='upper left')
        
        # Adjust layout
        self.plt.tight_layout()
        
        # Save the chart if a path is provided
        if save_path:
            if not save_path.endswith(('.png', '.jpg', '.jpeg', '.pdf', '.svg')):
                save_path += '.png'
            self.plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Chart saved to {save_path}")
        
        return fig
    
    def create_performance_chart(self, trade_history, account_balance_history=None, save_path=None):
        """Create a performance chart showing trade results and account balance
        
        Args:
            trade_history (list): List of closed trades
            account_balance_history (list, optional): List of account balance history. Defaults to None.
            save_path (str, optional): Path to save the chart. Defaults to None.
            
        Returns:
            object: Figure object or None if visualization is not available
        """
        if self.plotting_lib is None:
            logger.warning("No plotting library available")
            return None
        
        if not trade_history:
            logger.warning("Empty trade history provided for visualization")
            return None
        
        # Create performance chart based on selected library
        if self.plotting_lib == 'plotly':
            return self._create_plotly_performance_chart(trade_history, account_balance_history, save_path)
        else:  # Default to matplotlib
            return self._create_matplotlib_performance_chart(trade_history, account_balance_history, save_path)
    
    def _create_plotly_performance_chart(self, trade_history, account_balance_history=None, save_path=None):
        """Create a performance chart using Plotly
        
        Args:
            trade_history (list): List of closed trades
            account_balance_history (list, optional): List of account balance history. Defaults to None.
            save_path (str, optional): Path to save the chart. Defaults to None.
            
        Returns:
            plotly.graph_objects.Figure: Plotly figure
        """
        # Create subplot grid
        fig = self.make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.5, 0.25, 0.25],
            subplot_titles=("Account Balance", "Trade P&L", "Cumulative P&L")
        )
        
        # Extract trade data
        trade_times = [trade.get('close_time', datetime.now()) for trade in trade_history]
        trade_pnls = [trade.get('pnl', 0) for trade in trade_history]
        trade_pairs = [trade.get('pair', 'Unknown') for trade in trade_history]
        trade_directions = [trade.get('direction', 0) for trade in trade_history]
        
        # Calculate cumulative P&L
        cumulative_pnl = np.cumsum(trade_pnls)
        
        # Plot account balance if available
        if account_balance_history:
            balance_times = [entry.get('timestamp', datetime.now()) for entry in account_balance_history]
            balance_values = [entry.get('balance', 0) for entry in account_balance_history]
            
            fig.add_trace(
                self.go.Scatter(
                    x=balance_times,
                    y=balance_values,
                    mode='lines',
                    name="Account Balance"
                ),
                row=1, col=1
            )
        elif cumulative_pnl.size > 0:
            # If no balance history, use initial balance + cumulative P&L
            initial_balance = 10000  # Default initial balance
            balance_values = initial_balance + cumulative_pnl
            
            fig.add_trace(
                self.go.Scatter(
                    x=trade_times,
                    y=balance_values,
                    mode='lines',
                    name="Account Balance"
                ),
                row=1, col=1
            )
        
        # Plot individual trade P&L
        colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
        hover_texts = [f"Pair: {pair}<br>Direction: {'Buy' if direction > 0 else 'Sell'}<br>P&L: {pnl:.2f}" 
                      for pair, direction, pnl in zip(trade_pairs, trade_directions, trade_pnls)]
        
        fig.add_trace(
            self.go.Bar(
                x=trade_times,
                y=trade_pnls,
                name="Trade P&L",
                marker_color=colors,
                hovertext=hover_texts,
                hoverinfo="text"
            ),
            row=2, col=1
        )
        
        # Plot cumulative P&L
        fig.add_trace(
            self.go.Scatter(
                x=trade_times,
                y=cumulative_pnl,
                mode='lines',
                name="Cumulative P&L",
                line=dict(color='yellow', width=2)
            ),
            row=3, col=1
        )
        
        # Add zero line to P&L charts
        fig.add_shape(
            type="line",
            x0=trade_times[0],
            y0=0,
            x1=trade_times[-1],
            y1=0,
            line=dict(color="white", width=1, dash="dash"),
            row=2, col=1
        )
        
        fig.add_shape(
            type="line",
            x0=trade_times[0],
            y0=0,
            x1=trade_times[-1],
            y1=0,
            line=dict(color="white", width=1, dash="dash"),
            row=3, col=1
        )
        
        # Update layout
        fig.update_layout(
            title="Trading Performance",
            height=800,
            width=1000,
            template="plotly_dark" if self.chart_style == 'dark_background' else "plotly_white"
        )
        
        # Save the chart if a path is provided
        if save_path:
            if not save_path.endswith('.html'):
                save_path += '.html'
            fig.write_html(save_path)
            logger.info(f"Performance chart saved to {save_path}")
        
        return fig
    
    def create_performance_chart(self, trade_history, account_balance_history=None, save_path=None):
        """Create a performance chart
        
        Args:
            trade_history (list): List of closed trades
            account_balance_history (list, optional): List of account balance history. Defaults to None.
            save_path (str, optional): Path to save the chart. Defaults to None.
            
        Returns:
            object: Figure object or None if visualization is not available
        """
        if self.plotting_lib is None:
            logger.warning("No plotting library available")
            return None
        
        if not trade_history:
            logger.warning("No trade history provided for visualization")
            return None
        
        # Create chart based on selected library
        if self.plotting_lib == 'plotly':
            return self._create_plotly_performance_chart(trade_history, account_balance_history, save_path)
        else:  # Default to matplotlib
            return self._create_matplotlib_performance_chart(trade_history, account_balance_history, save_path)
    
    def _create_matplotlib_performance_chart(self, trade_history, account_balance_history=None, save_path=None):
        """Create a performance chart using Matplotlib
        
        Args:
            trade_history (list): List of closed trades
            account_balance_history (list, optional): List of account balance history. Defaults to None.
            save_path (str, optional): Path to save the chart. Defaults to None.
            
        Returns:
            matplotlib.figure.Figure: Matplotlib figure
        """
        # Create figure and subplots
        fig, axs = self.plt.subplots(3, 1, figsize=self.chart_size, sharex=True, gridspec_kw={'height_ratios': [2, 1, 1]})
        
        # Extract trade data
        trade_times = [trade.get('close_time', datetime.now()) for trade in trade_history]
        trade_pnls = [trade.get('pnl', 0) for trade in trade_history]
        trade_pairs = [trade.get('pair', 'Unknown') for trade in trade_history]
        trade_directions = [trade.get('direction', 0) for trade in trade_history]
        
        # Calculate cumulative P&L
        cumulative_pnl = np.cumsum(trade_pnls)
        
        # Plot account balance if available
        ax_balance = axs[0]
        ax_balance.set_title("Trading Performance")
        ax_balance.set_ylabel("Account Balance")
        
        if account_balance_history:
            balance_times = [entry.get('timestamp', datetime.now()) for entry in account_balance_history]
            balance_values = [entry.get('balance', 0) for entry in account_balance_history]
            
            ax_balance.plot(balance_times, balance_values, label="Account Balance")
        elif cumulative_pnl.size > 0:
            # If no balance history, use initial balance + cumulative P&L
            initial_balance = 10000  # Default initial balance
            balance_values = initial_balance + cumulative_pnl
            
            ax_balance.plot(trade_times, balance_values, label="Account Balance")
        
        ax_balance.grid(True, alpha=0.3)
        ax_balance.legend(loc='upper left')
        
        # Plot individual trade P&L
        ax_pnl = axs[1]
        ax_pnl.set_ylabel("Trade P&L")
        
        colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
        ax_pnl.bar(trade_times, trade_pnls, color=colors, alpha=0.7)
        ax_pnl.axhline(0, color='white', linestyle='--', alpha=0.5)
        ax_pnl.grid(True, alpha=0.3)
        
        # Plot cumulative P&L
        ax_cum = axs[2]
        ax_cum.set_ylabel("Cumulative P&L")
        ax_cum.plot(trade_times, cumulative_pnl, color='yellow', linewidth=2)
        ax_cum.axhline(0, color='white', linestyle='--', alpha=0.5)
        ax_cum.grid(True, alpha=0.3)
        
        # Format date axis
        ax_cum.xaxis.set_major_formatter(self.mdates.DateFormatter('%Y-%m-%d'))
        self.plt.xticks(rotation=45)
        
        # Adjust layout
        self.plt.tight_layout()
        
        # Save the chart if a path is provided
        if save_path:
            if not save_path.endswith(('.png', '.jpg', '.jpeg', '.pdf', '.svg')):
                save_path += '.png'
            self.plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Performance chart saved to {save_path}")
        
        return fig