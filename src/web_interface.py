#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Web interface module for the trading bot
"""

import logging
import os
import json
from datetime import datetime, timedelta
import threading
import time
import pandas as pd
import numpy as np

logger = logging.getLogger("TradeBOT.WebInterface")


class WebInterface:
    """Class for creating a web interface for the trading bot"""
    
    def __init__(self, config, data_fetcher=None, signal_generator=None, 
                 risk_manager=None, trade_executor=None, visualizer=None):
        """Initialize the web interface
        
        Args:
            config (dict): Configuration dictionary
            data_fetcher (DataFetcher, optional): Data fetcher instance. Defaults to None.
            signal_generator (SignalGenerator, optional): Signal generator instance. Defaults to None.
            risk_manager (RiskManager, optional): Risk manager instance. Defaults to None.
            trade_executor (TradeExecutor, optional): Trade executor instance. Defaults to None.
            visualizer (Visualizer, optional): Visualizer instance. Defaults to None.
        """
        self.config = config
        self.data_fetcher = data_fetcher
        self.signal_generator = signal_generator
        self.risk_manager = risk_manager
        self.trade_executor = trade_executor
        self.visualizer = visualizer
        
        # Web interface configuration
        self.web_config = self.config.get('web_interface', {})
        self.host = self.web_config.get('host', '127.0.0.1')
        self.port = self.web_config.get('port', 5000)
        self.debug = self.web_config.get('debug', False)
        self.secret_key = self.web_config.get('secret_key', 'tradebot_secret_key')
        
        # Data storage
        self.data_dir = self.web_config.get('data_dir', 'web_data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize Flask app
        self._init_flask_app()
        
        # Data cache
        self.price_data_cache = {}
        self.signals_cache = {}
        self.trades_cache = []
        self.performance_cache = {}
        
        # Update thread
        self.update_thread = None
        self.update_interval = self.web_config.get('update_interval', 60)  # seconds
        self.is_running = False
    
    def _init_flask_app(self):
        """Initialize Flask app and routes"""
        try:
            from flask import Flask, render_template, request, jsonify, send_from_directory
            from flask_socketio import SocketIO
            
            self.app = Flask(__name__, 
                             template_folder=os.path.join(os.path.dirname(__file__), '../web/templates'),
                             static_folder=os.path.join(os.path.dirname(__file__), '../web/static'))
            self.app.config['SECRET_KEY'] = self.secret_key
            
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")
            
            # Define routes
            @self.app.route('/')
            def index():
                return render_template('index.html')
            
            @self.app.route('/dashboard')
            def dashboard():
                return render_template('dashboard.html')
            
            @self.app.route('/charts')
            def charts():
                return render_template('charts.html')
            
            @self.app.route('/trades')
            def trades():
                return render_template('trades.html')
            
            @self.app.route('/settings')
            def settings():
                return render_template('settings.html')
            
            @self.app.route('/backtest')
            def backtest():
                return render_template('backtest.html')
            
            # API routes
            @self.app.route('/api/pairs')
            def get_pairs():
                pairs_config = self.config.get('pairs', {})
                return jsonify(pairs_config)
            
            @self.app.route('/api/price_data')
            def get_price_data():
                pair = request.args.get('pair', 'EUR_USD')
                timeframe = request.args.get('timeframe', 'H1')
                limit = int(request.args.get('limit', 100))
                
                # Get data from cache or fetch new data
                cache_key = f"{pair}_{timeframe}"
                if cache_key in self.price_data_cache:
                    data = self.price_data_cache[cache_key]
                else:
                    if self.data_fetcher:
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=30)
                        data = self.data_fetcher.get_historical_data(pair, start_date, end_date, timeframe)
                        if not data.empty:
                            self.price_data_cache[cache_key] = data
                    else:
                        data = pd.DataFrame()
                
                if data.empty:
                    return jsonify({'error': 'No data available'})
                
                # Convert to JSON
                data = data.tail(limit)
                result = {
                    'timestamps': data.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                    'open': data['open'].tolist(),
                    'high': data['high'].tolist(),
                    'low': data['low'].tolist(),
                    'close': data['close'].tolist(),
                    'volume': data['volume'].tolist() if 'volume' in data.columns else [0] * len(data)
                }
                
                # Add indicators if available
                for col in data.columns:
                    if col not in ['open', 'high', 'low', 'close', 'volume']:
                        result[col] = data[col].tolist()
                
                return jsonify(result)
            
            @self.app.route('/api/signals')
            def get_signals():
                pair = request.args.get('pair', 'EUR_USD')
                timeframe = request.args.get('timeframe', 'H1')
                limit = int(request.args.get('limit', 100))
                
                # Get signals from cache or generate new signals
                cache_key = f"{pair}_{timeframe}"
                if cache_key in self.signals_cache:
                    signals = self.signals_cache[cache_key]
                else:
                    if self.signal_generator and cache_key in self.price_data_cache:
                        data = self.price_data_cache[cache_key]
                        signals = self.signal_generator.generate_signals(data, pair)
                        if not signals.empty:
                            self.signals_cache[cache_key] = signals
                    else:
                        signals = pd.DataFrame()
                
                if signals.empty:
                    return jsonify({'error': 'No signals available'})
                
                # Convert to JSON
                signals = signals.tail(limit)
                result = {
                    'timestamps': signals.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                    'signal': signals['signal'].tolist(),
                    'strength': signals['strength'].tolist() if 'strength' in signals.columns else [1] * len(signals)
                }
                
                return jsonify(result)
            
            @self.app.route('/api/trades')
            def get_trades():
                limit = int(request.args.get('limit', 100))
                status = request.args.get('status', 'all')
                
                # Filter trades by status
                if status == 'open':
                    trades = [t for t in self.trades_cache if t['status'] == 'open']
                elif status == 'closed':
                    trades = [t for t in self.trades_cache if t['status'] == 'closed']
                else:
                    trades = self.trades_cache
                
                # Sort by open time (newest first) and limit
                trades = sorted(trades, key=lambda x: x['open_time'], reverse=True)[:limit]
                
                return jsonify(trades)
            
            @self.app.route('/api/performance')
            def get_performance():
                return jsonify(self.performance_cache)
            
            @self.app.route('/api/chart_image')
            def get_chart_image():
                pair = request.args.get('pair', 'EUR_USD')
                timeframe = request.args.get('timeframe', 'H1')
                indicators = request.args.get('indicators', '').split(',')
                
                # Generate chart if visualizer is available
                if self.visualizer and pair in self.price_data_cache:
                    data = self.price_data_cache[pair]
                    signals = self.signals_cache.get(pair, pd.DataFrame())
                    
                    # Get open trades for this pair
                    trades = [t for t in self.trades_cache if t['pair'] == pair and t['status'] == 'open']
                    
                    # Generate chart
                    chart_path = os.path.join(self.data_dir, f"{pair}_{timeframe}_chart")
                    self.visualizer.create_chart(data, pair, indicators, signals, trades, chart_path)
                    
                    return send_from_directory(self.data_dir, f"{pair}_{timeframe}_chart.png")
                
                return jsonify({'error': 'Chart generation failed'})
            
            # WebSocket events
            @self.socketio.on('connect')
            def handle_connect():
                logger.info("Client connected")
            
            @self.socketio.on('disconnect')
            def handle_disconnect():
                logger.info("Client disconnected")
            
            @self.socketio.on('subscribe')
            def handle_subscribe(data):
                room = data.get('room')
                if room:
                    from flask_socketio import join_room
                    join_room(room)
                    logger.info(f"Client subscribed to {room}")
            
            logger.info("Flask app initialized successfully")
        
        except ImportError as e:
            logger.warning(f"Could not initialize Flask app: {str(e)}. Web interface will not be available.")
            self.app = None
            self.socketio = None
    
    def start(self):
        """Start the web interface"""
        if not self.app or not self.socketio:
            logger.error("Flask app not initialized. Cannot start web interface.")
            return False
        
        # Create web directories if they don't exist
        os.makedirs(os.path.join(os.path.dirname(__file__), '../web/templates'), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), '../web/static'), exist_ok=True)
        
        # Create default templates if they don't exist
        self._create_default_templates()
        
        # Start update thread
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Start Flask app
        logger.info(f"Starting web interface on {self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=self.debug)
        
        return True
    
    def stop(self):
        """Stop the web interface"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        logger.info("Web interface stopped")
    
    def _update_loop(self):
        """Background thread to update data"""
        while self.is_running:
            try:
                # Update price data
                self._update_price_data()
                
                # Update signals
                self._update_signals()
                
                # Update trades
                self._update_trades()
                
                # Update performance
                self._update_performance()
                
                # Emit updates via WebSocket
                if self.socketio:
                    self.socketio.emit('data_update', {'timestamp': datetime.now().isoformat()})
            
            except Exception as e:
                logger.error(f"Error in update loop: {str(e)}")
            
            # Sleep until next update
            time.sleep(self.update_interval)
    
    def _update_price_data(self):
        """Update price data cache"""
        if not self.data_fetcher:
            return
        
        pairs_config = self.config.get('pairs', {})
        for pair, pair_config in pairs_config.items():
            if not pair_config.get('enabled', True):
                continue
            
            timeframes = pair_config.get('timeframes', ['H1'])
            for timeframe in timeframes:
                try:
                    # Get latest data
                    latest_data = self.data_fetcher.get_latest_data(pair, timeframe, limit=100)
                    if not latest_data.empty:
                        cache_key = f"{pair}_{timeframe}"
                        self.price_data_cache[cache_key] = latest_data
                        logger.debug(f"Updated price data for {pair} {timeframe}")
                
                except Exception as e:
                    logger.error(f"Error updating price data for {pair} {timeframe}: {str(e)}")
    
    def _update_signals(self):
        """Update signals cache"""
        if not self.signal_generator:
            return
        
        for cache_key, data in self.price_data_cache.items():
            try:
                pair = cache_key.split('_')[0]
                signals = self.signal_generator.generate_signals(data, pair)
                if not signals.empty:
                    self.signals_cache[cache_key] = signals
                    logger.debug(f"Updated signals for {cache_key}")
            
            except Exception as e:
                logger.error(f"Error updating signals for {cache_key}: {str(e)}")
    
    def _update_trades(self):
        """Update trades cache"""
        if not self.trade_executor:
            return
        
        try:
            # Get open positions
            open_positions = self.trade_executor.get_open_positions()
            
            # Get trade history
            trade_history = self.trade_executor.get_trade_history(limit=100)
            
            # Combine open positions and trade history
            self.trades_cache = open_positions + trade_history
            logger.debug(f"Updated trades cache with {len(self.trades_cache)} trades")
        
        except Exception as e:
            logger.error(f"Error updating trades: {str(e)}")
    
    def _update_performance(self):
        """Update performance cache"""
        if not self.trade_executor:
            return
        
        try:
            # Get account info
            account_info = self.trade_executor.get_account_info()
            
            # Get trade statistics
            trade_stats = self.trade_executor.get_trade_statistics()
            
            # Combine into performance data
            self.performance_cache = {
                'account': account_info,
                'statistics': trade_stats,
                'updated_at': datetime.now().isoformat()
            }
            
            logger.debug("Updated performance cache")
        
        except Exception as e:
            logger.error(f"Error updating performance: {str(e)}")
    
    def _create_default_templates(self):
        """Create default HTML templates if they don't exist"""
        templates_dir = os.path.join(os.path.dirname(__file__), '../web/templates')
        static_dir = os.path.join(os.path.dirname(__file__), '../web/static')
        
        # Create base template
        base_template = os.path.join(templates_dir, 'base.html')
        if not os.path.exists(base_template):
            with open(base_template, 'w') as f:
                f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}TradeBOT{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/bootstrap.min.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">TradeBOT</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/dashboard">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/charts">Charts</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/trades">Trades</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/backtest">Backtest</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/settings">Settings</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <footer class="footer mt-5 py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">TradeBOT &copy; {{ now.year }}</span>
        </div>
    </footer>

    <script src="{{ url_for('static', filename='js/jquery-3.6.0.min.js') }}"></script>
    <script src="{{ url_for('static', filename='js/bootstrap.bundle.min.js') }}"></script>
    <script src="{{ url_for('static', filename='js/socket.io.min.js') }}"></script>
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
''')
        
        # Create index template
        index_template = os.path.join(templates_dir, 'index.html')
        if not os.path.exists(index_template):
            with open(index_template, 'w') as f:
                f.write('''
{% extends "base.html" %}

{% block title %}TradeBOT - Home{% endblock %}

{% block content %}
<div class="jumbotron">
    <h1 class="display-4">Welcome to TradeBOT</h1>
    <p class="lead">An AI-powered Forex Trading Bot</p>
    <hr class="my-4">
    <p>Use the navigation menu to access different features of the trading bot.</p>
    <a class="btn btn-primary btn-lg" href="/dashboard" role="button">Go to Dashboard</a>
</div>

<div class="row mt-5">
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Live Trading</h5>
                <p class="card-text">Monitor and manage your live trading operations.</p>
                <a href="/dashboard" class="btn btn-primary">Dashboard</a>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Market Analysis</h5>
                <p class="card-text">View charts and technical analysis for various currency pairs.</p>
                <a href="/charts" class="btn btn-primary">Charts</a>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Backtesting</h5>
                <p class="card-text">Test your trading strategies on historical data.</p>
                <a href="/backtest" class="btn btn-primary">Backtest</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
''')
        
        # Create dashboard template
        dashboard_template = os.path.join(templates_dir, 'dashboard.html')
        if not os.path.exists(dashboard_template):
            with open(dashboard_template, 'w') as f:
                f.write('''
{% extends "base.html" %}

{% block title %}TradeBOT - Dashboard{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
{% endblock %}

{% block content %}
<h2>Trading Dashboard</h2>

<div class="row mt-4">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">Account Summary</div>
            <div class="card-body">
                <div id="account-info">
                    <p>Loading account information...</p>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">Performance</div>
            <div class="card-body">
                <div id="performance-chart" style="height: 250px;">
                    <p>Loading performance data...</p>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">Open Positions</div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped" id="open-positions-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Pair</th>
                                <th>Type</th>
                                <th>Open Time</th>
                                <th>Entry Price</th>
                                <th>Size</th>
                                <th>Stop Loss</th>
                                <th>Take Profit</th>
                                <th>Current P&L</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td colspan="10" class="text-center">Loading open positions...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">Recent Signals</div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped" id="signals-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Pair</th>
                                <th>Signal</th>
                                <th>Strength</th>
                                <th>Price</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td colspan="6" class="text-center">Loading signals...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/chart.min.js') }}"></script>
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
{% endblock %}
''')
        
        # Create charts template
        charts_template = os.path.join(templates_dir, 'charts.html')
        if not os.path.exists(charts_template):
            with open(charts_template, 'w') as f:
                f.write('''
{% extends "base.html" %}

{% block title %}TradeBOT - Charts{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/charts.css') }}">
{% endblock %}

{% block content %}
<h2>Market Charts</h2>

<div class="row mt-4">
    <div class="col-md-3">
        <div class="card">
            <div class="card-header">Chart Settings</div>
            <div class="card-body">
                <form id="chart-settings-form">
                    <div class="mb-3">
                        <label for="pair-select" class="form-label">Currency Pair</label>
                        <select class="form-select" id="pair-select">
                            <option value="EUR_USD">EUR/USD</option>
                            <option value="GBP_USD">GBP/USD</option>
                            <option value="USD_JPY">USD/JPY</option>
                            <option value="AUD_USD">AUD/USD</option>
                            <option value="USD_CAD">USD/CAD</option>
                            <option value="USD_CHF">USD/CHF</option>
                            <option value="NZD_USD">NZD/USD</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="timeframe-select" class="form-label">Timeframe</label>
                        <select class="form-select" id="timeframe-select">
                            <option value="M1">1 Minute</option>
                            <option value="M5">5 Minutes</option>
                            <option value="M15">15 Minutes</option>
                            <option value="M30">30 Minutes</option>
                            <option value="H1" selected>1 Hour</option>
                            <option value="H4">4 Hours</option>
                            <option value="D">Daily</option>
                            <option value="W">Weekly</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Indicators</label>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="sma_20" id="sma-20-check">
                            <label class="form-check-label" for="sma-20-check">SMA 20</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="sma_50" id="sma-50-check">
                            <label class="form-check-label" for="sma-50-check">SMA 50</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="sma_200" id="sma-200-check">
                            <label class="form-check-label" for="sma-200-check">SMA 200</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="ema_20" id="ema-20-check">
                            <label class="form-check-label" for="ema-20-check">EMA 20</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="bb_upper,bb_middle,bb_lower" id="bb-check">
                            <label class="form-check-label" for="bb-check">Bollinger Bands</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="rsi" id="rsi-check">
                            <label class="form-check-label" for="rsi-check">RSI</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="macd,macd_signal,macd_histogram" id="macd-check">
                            <label class="form-check-label" for="macd-check">MACD</label>
                        </div>
                    </div>
                    <div class="mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="1" id="show-signals-check" checked>
                            <label class="form-check-label" for="show-signals-check">Show Signals</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="1" id="show-trades-check" checked>
                            <label class="form-check-label" for="show-trades-check">Show Trades</label>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Update Chart</button>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-9">
        <div class="card">
            <div class="card-header">
                <span id="chart-title">EUR/USD - H1</span>
                <div class="float-end">
                    <button class="btn btn-sm btn-outline-secondary" id="refresh-chart-btn">
                        <i class="bi bi-arrow-clockwise"></i> Refresh
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div id="price-chart" style="height: 500px;">
                    <p>Loading chart data...</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/plotly-latest.min.js') }}"></script>
<script src="{{ url_for('static', filename='js/charts.js') }}"></script>
{% endblock %}
''')
        
        # Create trades template
        trades_template = os.path.join(templates_dir, 'trades.html')
        if not os.path.exists(trades_template):
            with open(trades_template, 'w') as f:
                f.write('''
{% extends "base.html" %}

{% block title %}TradeBOT - Trades{% endblock %}

{% block content %}
<h2>Trade History</h2>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <ul class="nav nav-tabs card-header-tabs" id="trades-tabs">
                    <li class="nav-item">
                        <a class="nav-link active" id="open-tab" data-bs-toggle="tab" href="#open">Open Positions</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="closed-tab" data-bs-toggle="tab" href="#closed">Closed Trades</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="all-tab" data-bs-toggle="tab" href="#all">All Trades</a>
                    </li>
                </ul>
            </div>
            <div class="card-body">
                <div class="tab-content" id="trades-content">
                    <div class="tab-pane fade show active" id="open" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-striped" id="open-trades-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Pair</th>
                                        <th>Type</th>
                                        <th>Open Time</th>
                                        <th>Entry Price</th>
                                        <th>Size</th>
                                        <th>Stop Loss</th>
                                        <th>Take Profit</th>
                                        <th>Current P&L</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td colspan="10" class="text-center">Loading open trades...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="tab-pane fade" id="closed" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-striped" id="closed-trades-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Pair</th>
                                        <th>Type</th>
                                        <th>Open Time</th>
                                        <th>Close Time</th>
                                        <th>Entry Price</th>
                                        <th>Exit Price</th>
                                        <th>Size</th>
                                        <th>P&L</th>
                                        <th>Exit Reason</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td colspan="10" class="text-center">Loading closed trades...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="tab-pane fade" id="all" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-striped" id="all-trades-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Pair</th>
                                        <th>Type</th>
                                        <th>Status</th>
                                        <th>Open Time</th>
                                        <th>Close Time</th>
                                        <th>Entry Price</th>
                                        <th>Exit Price</th>
                                        <th>Size</th>
                                        <th>P&L</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td colspan="10" class="text-center">Loading trades...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">Trade Statistics</div>
            <div class="card-body">
                <div class="row" id="trade-statistics">
                    <p>Loading trade statistics...</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/trades.js') }}"></script>
{% endblock %}
''')
        
        # Create backtest template
        backtest_template = os.path.join(templates_dir, 'backtest.html')
        if not os.path.exists(backtest_template):
            with open(backtest_template, 'w') as f:
                f.write('''
{% extends "base.html" %}

{% block title %}TradeBOT - Backtest{% endblock %}

{% block content %}
<h2>Strategy Backtesting</h2>

<div class="row mt-4">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">Backtest Settings</div>
            <div class="card-body">
                <form id="backtest-form">
                    <div class="mb-3">
                        <label for="start-date" class="form-label">Start Date</label>
                        <input type="date" class="form-control" id="start-date" required>
                    </div>
                    <div class="mb-3">
                        <label for="end-date" class="form-label">End Date</label>
                        <input type="date" class="form-control" id="end-date" required>
                    </div>
                    <div class="mb-3">
                        <label for="timeframe-select" class="form-label">Timeframe</label>
                        <select class="form-select" id="timeframe-select">
                            <option value="M1">1 Minute</option>
                            <option value="M5">5 Minutes</option>
                            <option value="M15">15 Minutes</option>
                            <option value="M30">30 Minutes</option>
                            <option value="H1" selected>1 Hour</option>
                            <option value="H4">4 Hours</option>
                            <option value="D">Daily</option>
                            <option value="W">Weekly</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Currency Pairs</label>
                        <div id="pairs-checkboxes">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" value="EUR_USD" id="eur-usd-check" checked>
                                <label class="form-check-label" for="eur-usd-check">EUR/USD</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" value="GBP_USD" id="gbp-usd-check">
                                <label class="form-check-label" for="gbp-usd-check">GBP/USD</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" value="USD_JPY" id="usd-jpy-check">
                                <label class="form-check-label" for="usd-jpy-check">USD/JPY</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" value="AUD_USD" id="aud-usd-check">
                                <label class="form-check-label" for="aud-usd-check">AUD/USD</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" value="USD_CAD" id="usd-cad-check">
                                <label class="form-check-label" for="usd-cad-check">USD/CAD</label>
                            </div>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label for="initial-balance" class="form-label">Initial Balance</label>
                        <input type="number" class="form-control" id="initial-balance" value="10000" required>
                    </div>
                    <div class="mb-3">
                        <label for="risk-per-trade" class="form-label">Risk Per Trade (%)</label>
                        <input type="number" class="form-control" id="risk-per-trade" value="1" min="0.1" max="10" step="0.1" required>
                    </div>
                    <button type="submit" class="btn btn-primary" id="run-backtest-btn">Run Backtest</button>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">Backtest Results</div>
            <div class="card-body">
                <div id="backtest-results">
                    <p class="text-center">No backtest results available. Run a backtest to see results.</p>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">Equity Curve</div>
            <div class="card-body">
                <div id="equity-chart" style="height: 400px;">
                    <p class="text-center">Run a backtest to see the equity curve.</p>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">Backtest Trades</div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped" id="backtest-trades-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Pair</th>
                                <th>Type</th>
                                <th>Open Time</th>
                                <th>Close Time</th>
                                <th>Entry Price</th>
                                <th>Exit Price</th>
                                <th>Size</th>
                                <th>P&L</th>
                                <th>Exit Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td colspan="10" class="text-center">No backtest trades available.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/chart.min.js') }}"></script>
<script src="{{ url_for('static', filename='js/backtest.js') }}"></script>
{% endblock %}
''')
        
        # Create settings template
        settings_template = os.path.join(templates_dir, 'settings.html')
        if not os.path.exists(settings_template):
            with open(settings_template, 'w') as f:
                f.write('''
{% extends "base.html" %}

{% block title %}TradeBOT - Settings{% endblock %}

{% block content %}
<h2>Bot Settings</h2>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <ul class="nav nav-tabs card-header-tabs" id="settings-tabs">
                    <li class="nav-item">
                        <a class="nav-link active" id="general-tab" data-bs-toggle="tab" href="#general">General</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="pairs-tab" data-bs-toggle="tab" href="#pairs">Currency Pairs</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="indicators-tab" data-bs-toggle="tab" href="#indicators">Indicators</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="risk-tab" data-bs-toggle="tab" href="#risk">Risk Management</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="api-tab" data-bs-toggle="tab" href="#api">API Settings</a>
                    </li>
                </ul>
            </div>
            <div class="card-body">
                <div class="tab-content" id="settings-content">
                    <div class="tab-pane fade show active" id="general" role="tabpanel">
                        <form id="general-settings-form">
                            <div class="mb-3">
                                <label for="bot-name" class="form-label">Bot Name</label>
                                <input type="text" class="form-control" id="bot-name" value="TradeBOT">
                            </div>
                            <div class="mb-3">
                                <label for="trading-mode" class="form-label">Trading Mode</label>
                                <select class="form-select" id="trading-mode">
                                    <option value="paper">Paper Trading</option>
                                    <option value="live">Live Trading</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="update-interval" class="form-label">Update Interval (seconds)</label>
                                <input type="number" class="form-control" id="update-interval" value="60" min="10">
                            </div>
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="enable-notifications">
                                <label class="form-check-label" for="enable-notifications">Enable Notifications</label>
                            </div>
                            <button type="submit" class="btn btn-primary">Save General Settings</button>
                        </form>
                    </div>
                    <div class="tab-pane fade" id="pairs" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-striped" id="pairs-table">
                                <thead>
                                    <tr>
                                        <th>Pair</th>
                                        <th>Enabled</th>
                                        <th>Timeframes</th>
                                        <th>Pip Value</th>
                                        <th>Stop Loss (pips)</th>
                                        <th>Take Profit (pips)</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td colspan="7" class="text-center">Loading currency pairs...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <button class="btn btn-primary mt-3" id="add-pair-btn">Add Currency Pair</button>
                        <button class="btn btn-success mt-3" id="save-pairs-btn">Save All Pairs</button>
                    </div>
                    <div class="tab-pane fade" id="indicators" role="tabpanel">
                        <form id="indicators-settings-form">
                            <h5>Moving Averages</h5>
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <label for="sma-periods" class="form-label">SMA Periods (comma-separated)</label>
                                    <input type="text" class="form-control" id="sma-periods" value="20,50,200">
                                </div>
                                <div class="col-md-4">
                                    <label for="ema-periods" class="form-label">EMA Periods (comma-separated)</label>
                                    <input type="text" class="form-control" id="ema-periods" value="9,21">
                                </div>
                            </div>
                            
                            <h5>Oscillators</h5>
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <label for="rsi-period" class="form-label">RSI Period</label>
                                    <input type="number" class="form-control" id="rsi-period" value="14" min="2">
                                </div>
                                <div class="col-md-4">
                                    <label for="rsi-overbought" class="form-label">RSI Overbought</label>
                                    <input type="number" class="form-control" id="rsi-overbought" value="70" min="50" max="100">
                                </div>
                                <div class="col-md-4">
                                    <label for="rsi-oversold" class="form-label">RSI Oversold</label>
                                    <input type="number" class="form-control" id="rsi-oversold" value="30" min="0" max="50">
                                </div>
                            </div>
                            
                            <h5>Bollinger Bands</h5>
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <label for="bb-period" class="form-label">BB Period</label>
                                    <input type="number" class="form-control" id="bb-period" value="20" min="2">
                                </div>
                                <div class="col-md-4">
                                    <label for="bb-std" class="form-label">BB Standard Deviation</label>
                                    <input type="number" class="form-control" id="bb-std" value="2" min="0.1" step="0.1">
                                </div>
                            </div>
                            
                            <h5>MACD</h5>
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <label for="macd-fast" class="form-label">MACD Fast Period</label>
                                    <input type="number" class="form-control" id="macd-fast" value="12" min="2">
                                </div>
                                <div class="col-md-4">
                                    <label for="macd-slow" class="form-label">MACD Slow Period</label>
                                    <input type="number" class="form-control" id="macd-slow" value="26" min="2">
                                </div>
                                <div class="col-md-4">
                                    <label for="macd-signal" class="form-label">MACD Signal Period</label>
                                    <input type="number" class="form-control" id="macd-signal" value="9" min="2">
                                </div>
                            </div>
                            
                            <button type="submit" class="btn btn-primary">Save Indicator Settings</button>
                        </form>
                    </div>
                    <div class="tab-pane fade" id="risk" role="tabpanel">
                        <form id="risk-settings-form">
                            <div class="mb-3">
                                <label for="risk-per-trade" class="form-label">Risk Per Trade (%)</label>
                                <input type="number" class="form-control" id="risk-per-trade" value="1" min="0.1" max="10" step="0.1">
                            </div>
                            <div class="mb-3">
                                <label for="max-open-trades" class="form-label">Maximum Open Trades</label>
                                <input type="number" class="form-control" id="max-open-trades" value="5" min="1">
                            </div>
                            <div class="mb-3">
                                <label for="max-daily-loss" class="form-label">Maximum Daily Loss (%)</label>
                                <input type="number" class="form-control" id="max-daily-loss" value="5" min="1" max="100">
                            </div>
                            <div class="mb-3">
                                <label for="stop-loss-type" class="form-label">Stop Loss Type</label>
                                <select class="form-select" id="stop-loss-type">
                                    <option value="fixed">Fixed (pips)</option>
                                    <option value="percent">Percentage</option>
                                    <option value="atr" selected>ATR Multiple</option>
                                    <option value="support_resistance">Support/Resistance</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="take-profit-type" class="form-label">Take Profit Type</label>
                                <select class="form-select" id="take-profit-type">
                                    <option value="fixed">Fixed (pips)</option>
                                    <option value="percent">Percentage</option>
                                    <option value="atr" selected>ATR Multiple</option>
                                    <option value="risk_reward">Risk-Reward Ratio</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="atr-period" class="form-label">ATR Period</label>
                                <input type="number" class="form-control" id="atr-period" value="14" min="1">
                            </div>
                            <div class="mb-3">
                                <label for="atr-multiplier-sl" class="form-label">ATR Multiplier (Stop Loss)</label>
                                <input type="number" class="form-control" id="atr-multiplier-sl" value="2" min="0.1" step="0.1">
                            </div>
                            <div class="mb-3">
                                <label for="atr-multiplier-tp" class="form-label">ATR Multiplier (Take Profit)</label>
                                <input type="number" class="form-control" id="atr-multiplier-tp" value="3" min="0.1" step="0.1">
                            </div>
                            <div class="mb-3">
                                <label for="risk-reward-ratio" class="form-label">Risk-Reward Ratio</label>
                                <input type="number" class="form-control" id="risk-reward-ratio" value="2" min="0.1" step="0.1">
                            </div>
                            <button type="submit" class="btn btn-primary">Save Risk Settings</button>
                        </form>
                    </div>
                    <div class="tab-pane fade" id="api" role="tabpanel">
                        <form id="api-settings-form">
                            <h5>Oanda API</h5>
                            <div class="mb-3">
                                <label for="oanda-account-id" class="form-label">Account ID</label>
                                <input type="text" class="form-control" id="oanda-account-id">
                            </div>
                            <div class="mb-3">
                                <label for="oanda-api-key" class="form-label">API Key</label>
                                <input type="password" class="form-control" id="oanda-api-key">
                            </div>
                            <div class="mb-3">
                                <label for="oanda-environment" class="form-label">Environment</label>
                                <select class="form-select" id="oanda-environment">
                                    <option value="practice">Practice</option>
                                    <option value="live">Live</option>
                                </select>
                            </div>
                            
                            <h5 class="mt-4">CCXT Exchange</h5>
                            <div class="mb-3">
                                <label for="ccxt-exchange" class="form-label">Exchange</label>
                                <select class="form-select" id="ccxt-exchange">
                                    <option value="">None</option>
                                    <option value="binance">Binance</option>
                                    <option value="ftx">FTX</option>
                                    <option value="kraken">Kraken</option>
                                    <option value="kucoin">KuCoin</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="ccxt-api-key" class="form-label">API Key</label>
                                <input type="text" class="form-control" id="ccxt-api-key">
                            </div>
                            <div class="mb-3">
                                <label for="ccxt-api-secret" class="form-label">API Secret</label>
                                <input type="password" class="form-control" id="ccxt-api-secret">
                            </div>
                            
                            <button type="submit" class="btn btn-primary">Save API Settings</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/settings.js') }}"></script>
{% endblock %}
''')
        
        # Create basic CSS file
        css_dir = os.path.join(static_dir, 'css')
        os.makedirs(css_dir, exist_ok=True)
        
        style_css = os.path.join(css_dir, 'style.css')
        if not os.path.exists(style_css):
            with open(style_css, 'w') as f:
                f.write('''
/* Main styles for TradeBOT */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f8f9fa;
}

.navbar {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card {
    border-radius: 0.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    margin-bottom: 1.5rem;
}

.card-header {
    background-color: #f8f9fa;
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
    font-weight: 500;
}

.table th {
    font-weight: 500;
    background-color: #f8f9fa;
}

.btn-primary {
    background-color: #0d6efd;
    border-color: #0d6efd;
}

.btn-primary:hover {
    background-color: #0b5ed7;
    border-color: #0a58ca;
}

.footer {
    border-top: 1px solid #e9ecef;
}
''')
        
        # Create JS directory and files
        js_dir = os.path.join(static_dir, 'js')
        os.makedirs(js_dir, exist_ok=True)
        
        # Create app.js
        app_js = os.path.join(js_dir, 'app.js')
        if not os.path.exists(app_js):
            with open(app_js, 'w') as f:
                f.write('''
// Main application JavaScript file

// Socket.io connection
let socket;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.io connection
    initSocketConnection();
    
    // Initialize tooltips and popovers if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
});

function initSocketConnection() {
    try {
        socket = io();
        
        socket.on('connect', function() {
            console.log('Connected to server');
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
        });
        
        socket.on('data_update', function(data) {
            console.log('Data update received:', data);
            // Trigger page-specific update functions if they exist
            if (typeof updateDashboard === 'function') {
                updateDashboard();
            }
            if (typeof updateCharts === 'function') {
                updateCharts();
            }
            if (typeof updateTrades === 'function') {
                updateTrades();
            }
        });
        
        // Subscribe to relevant rooms based on current page
        const currentPage = window.location.pathname.split('/').pop() || 'index';
        socket.emit('subscribe', { room: currentPage });
        
    } catch (error) {
        console.error('Socket.io connection error:', error);
    }
}

// Format date and time
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Format currency
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Format percentage
function formatPercent(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

// Show notification
function showNotification(message, type = 'info') {
    // Check if the notification container exists, if not create it
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '10px';
        container.style.right = '10px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to container
    container.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            container.removeChild(notification);
        }, 150);
    }, 5000);
}
''')        
        # Create dashboard.js
        dashboard_js = os.path.join(js_dir, 'dashboard.js')
        if not os.path.exists(dashboard_js):
            with open(dashboard_js, 'w') as f:
                f.write('''
// Dashboard JavaScript file

document.addEventListener('DOMContentLoaded', function() {
    // Initial data load
    updateDashboard();
    
    // Set up refresh interval (every 60 seconds)
    setInterval(updateDashboard, 60000);
});

function updateDashboard() {
    // Update account information
    updateAccountInfo();
    
    // Update performance chart
    updatePerformanceChart();
    
    // Update open positions table
    updateOpenPositions();
    
    // Update signals table
    updateSignals();
}

function updateAccountInfo() {
    fetch('/api/performance')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error fetching account info:', data.error);
                return;
            }
            
            const accountInfo = data.account || {};
            const accountInfoDiv = document.getElementById('account-info');
            
            if (accountInfoDiv) {
                accountInfoDiv.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Balance:</strong> ${formatCurrency(accountInfo.balance || 0)}</p>
                            <p><strong>Equity:</strong> ${formatCurrency(accountInfo.equity || 0)}</p>
                            <p><strong>Margin Used:</strong> ${formatCurrency(accountInfo.margin_used || 0)}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Open Trades:</strong> ${accountInfo.open_trades || 0}</p>
                            <p><strong>Daily P&L:</strong> <span class="${(accountInfo.daily_pnl || 0) >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(accountInfo.daily_pnl || 0)}</span></p>
                            <p><strong>Last Updated:</strong> ${formatDateTime(data.updated_at || new Date())}</p>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error fetching account info:', error);
        });
}

function updatePerformanceChart() {
    fetch('/api/performance')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error fetching performance data:', data.error);
                return;
            }
            
            const statistics = data.statistics || {};
            const performanceChartDiv = document.getElementById('performance-chart');
            
            if (performanceChartDiv && statistics.equity_curve) {
                // Clear previous chart
                performanceChartDiv.innerHTML = '';
                
                // Create chart using Chart.js
                const ctx = document.createElement('canvas');
                performanceChartDiv.appendChild(ctx);
                
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: statistics.equity_curve.dates || [],
                        datasets: [{
                            label: 'Account Equity',
                            data: statistics.equity_curve.values || [],
                            borderColor: 'rgba(13, 110, 253, 1)',
                            backgroundColor: 'rgba(13, 110, 253, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return formatCurrency(context.raw);
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: {
                                    display: false
                                }
                            },
                            y: {
                                beginAtZero: false,
                                ticks: {
                                    callback: function(value) {
                                        return formatCurrency(value);
                                    }
                                }
                            }
                        }
                    }
                });
            } else if (performanceChartDiv) {
                performanceChartDiv.innerHTML = '<p class="text-center">No performance data available</p>';
            }
        })
        .catch(error => {
            console.error('Error fetching performance data:', error);
        });
}

function updateOpenPositions() {
    fetch('/api/trades?status=open')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.querySelector('#open-positions-table tbody');
            
            if (!tableBody) return;
            
            if (data.error || !Array.isArray(data) || data.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="10" class="text-center">No open positions</td></tr>';
                return;
            }
            
            let html = '';
            
            data.forEach(trade => {
                const pnl = trade.current_pnl || 0;
                const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
                
                html += `
                    <tr>
                        <td>${trade.id || ''}</td>
                        <td>${trade.pair || ''}</td>
                        <td><span class="badge ${trade.type === 'buy' ? 'bg-success' : 'bg-danger'}">${trade.type === 'buy' ? 'BUY' : 'SELL'}</span></td>
                        <td>${formatDateTime(trade.open_time || '')}</td>
                        <td>${trade.entry_price || ''}</td>
                        <td>${trade.size || ''}</td>
                        <td>${trade.stop_loss || ''}</td>
                        <td>${trade.take_profit || ''}</td>
                        <td class="${pnlClass}">${formatCurrency(pnl)}</td>
                        <td>
                            <button class="btn btn-sm btn-danger close-trade-btn" data-trade-id="${trade.id}">Close</button>
                        </td>
                    </tr>
                `;
            });
            
            tableBody.innerHTML = html;
            
            // Add event listeners to close buttons
            document.querySelectorAll('.close-trade-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const tradeId = this.getAttribute('data-trade-id');
                    closeTrade(tradeId);
                });
            });
        })
        .catch(error => {
            console.error('Error fetching open positions:', error);
        });
}

function updateSignals() {
    // Get all enabled pairs
    fetch('/api/pairs')
        .then(response => response.json())
        .then(pairsData => {
            const enabledPairs = Object.keys(pairsData).filter(pair => pairsData[pair].enabled !== false);
            
            if (enabledPairs.length === 0) {
                const tableBody = document.querySelector('#signals-table tbody');
                if (tableBody) {
                    tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No enabled currency pairs</td></tr>';
                }
                return;
            }
            
            // Get signals for each enabled pair
            const signalPromises = enabledPairs.map(pair => {
                return fetch(`/api/signals?pair=${pair}&limit=1`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error || !data.timestamps || data.timestamps.length === 0) {
                            return null;
                        }
                        
                        // Get the latest price for this pair
                        return fetch(`/api/price_data?pair=${pair}&limit=1`)
                            .then(response => response.json())
                            .then(priceData => {
                                const latestPrice = priceData.close ? priceData.close[priceData.close.length - 1] : null;
                                
                                return {
                                    pair: pair,
                                    timestamp: data.timestamps[data.timestamps.length - 1],
                                    signal: data.signal[data.signal.length - 1],
                                    strength: data.strength[data.strength.length - 1],
                                    price: latestPrice
                                };
                            });
                    });
            });
            
            Promise.all(signalPromises)
                .then(signals => {
                    const tableBody = document.querySelector('#signals-table tbody');
                    
                    if (!tableBody) return;
                    
                    // Filter out null signals and sort by timestamp (newest first)
                    const validSignals = signals.filter(signal => signal !== null)
                        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                    
                    if (validSignals.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No recent signals</td></tr>';
                        return;
                    }
                    
                    let html = '';
                    
                    validSignals.forEach(signal => {
                        const signalClass = signal.signal > 0 ? 'bg-success' : (signal.signal < 0 ? 'bg-danger' : 'bg-secondary');
                        const signalText = signal.signal > 0 ? 'BUY' : (signal.signal < 0 ? 'SELL' : 'NEUTRAL');
                        
                        html += `
                            <tr>
                                <td>${formatDateTime(signal.timestamp)}</td>
                                <td>${signal.pair}</td>
                                <td><span class="badge ${signalClass}">${signalText}</span></td>
                                <td>${signal.strength.toFixed(2)}</td>
                                <td>${signal.price !== null ? signal.price : 'N/A'}</td>
                                <td>
                                    <button class="btn btn-sm btn-primary view-chart-btn" data-pair="${signal.pair}">View Chart</button>
                                </td>
                            </tr>
                        `;
                    });
                    
                    tableBody.innerHTML = html;
                    
                    // Add event listeners to view chart buttons
                    document.querySelectorAll('.view-chart-btn').forEach(button => {
                        button.addEventListener('click', function() {
                            const pair = this.getAttribute('data-pair');
                            window.location.href = `/charts?pair=${pair}`;
                        });
                    });
                });
        })
        .catch(error => {
            console.error('Error fetching signals:', error);
        });
}

function closeTrade(tradeId) {
    if (!confirm('Are you sure you want to close this trade?')) {
        return;
    }
    
    // This would typically be a POST request to an API endpoint
    // For now, we'll just show a notification
    showNotification(`Trade ${tradeId} close request sent`, 'info');
    
    // In a real implementation, you would make an API call here
    // fetch('/api/close_trade', {
    //     method: 'POST',
    //     headers: {
    //         'Content-Type': 'application/json'
    //     },
    //     body: JSON.stringify({ trade_id: tradeId })
    // })
    // .then(response => response.json())
    // .then(data => {
    //     if (data.success) {
    //         showNotification('Trade closed successfully', 'success');
    //         updateOpenPositions();
    //     } else {
    //         showNotification(`Error: ${data.error}`, 'danger');
    //     }
    // })
    // .catch(error => {
    //     showNotification(`Error: ${error.message}`, 'danger');
    // });
}
''')        
        # Create charts.js
        charts_js = os.path.join(js_dir, 'charts.js')
        if not os.path.exists(charts_js):
            with open(charts_js, 'w') as f:
                f.write('''
// Charts JavaScript file

let priceChart = null;
let currentPair = 'EUR_USD';
let currentTimeframe = 'H1';
let selectedIndicators = [];
let showSignals = true;
let showTrades = true;

document.addEventListener('DOMContentLoaded', function() {
    // Get URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('pair')) {
        currentPair = urlParams.get('pair');
        document.getElementById('pair-select').value = currentPair;
    }
    if (urlParams.has('timeframe')) {
        currentTimeframe = urlParams.get('timeframe');
        document.getElementById('timeframe-select').value = currentTimeframe;
    }
    
    // Set chart title
    updateChartTitle();
    
    // Initial chart load
    loadChart();
    
    // Set up event listeners
    document.getElementById('chart-settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        updateChartSettings();
        loadChart();
    });
    
    document.getElementById('refresh-chart-btn').addEventListener('click', function() {
        loadChart();
    });
    
    // Set up refresh interval (every 5 minutes)
    setInterval(loadChart, 300000);
});

function updateChartSettings() {
    // Update pair and timeframe
    currentPair = document.getElementById('pair-select').value;
    currentTimeframe = document.getElementById('timeframe-select').value;
    
    // Update indicators
    selectedIndicators = [];
    document.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
        if (checkbox.id !== 'show-signals-check' && checkbox.id !== 'show-trades-check') {
            selectedIndicators.push(checkbox.value);
        }
    });
    
    // Update signals and trades visibility
    showSignals = document.getElementById('show-signals-check').checked;
    showTrades = document.getElementById('show-trades-check').checked;
    
    // Update chart title
    updateChartTitle();
    
    // Update URL parameters
    const url = new URL(window.location);
    url.searchParams.set('pair', currentPair);
    url.searchParams.set('timeframe', currentTimeframe);
    window.history.replaceState({}, '', url);
}

function updateChartTitle() {
    const pairDisplay = currentPair.replace('_', '/');
    document.getElementById('chart-title').textContent = `${pairDisplay} - ${currentTimeframe}`;
}

function loadChart() {
    const chartDiv = document.getElementById('price-chart');
    if (!chartDiv) return;
    
    chartDiv.innerHTML = '<p class="text-center">Loading chart data...</p>';
    
    // Fetch price data
    fetch(`/api/price_data?pair=${currentPair}&timeframe=${currentTimeframe}&limit=200`)
        .then(response => response.json())
        .then(priceData => {
            if (priceData.error) {
                chartDiv.innerHTML = `<p class="text-center text-danger">Error: ${priceData.error}</p>`;
                return;
            }
            
            if (!priceData.timestamps || priceData.timestamps.length === 0) {
                chartDiv.innerHTML = '<p class="text-center">No data available for this pair and timeframe</p>';
                return;
            }
            
            // Prepare data for Plotly
            const ohlc = {
                x: priceData.timestamps,
                open: priceData.open,
                high: priceData.high,
                low: priceData.low,
                close: priceData.close,
                type: 'candlestick',
                name: currentPair,
                increasing: {line: {color: '#26a69a'}},
                decreasing: {line: {color: '#ef5350'}}
            };
            
            const traces = [ohlc];
            
            // Add selected indicators
            for (const indicator of selectedIndicators) {
                if (indicator.includes(',')) {
                    // Handle multi-line indicators like Bollinger Bands
                    const indicatorParts = indicator.split(',');
                    for (const part of indicatorParts) {
                        if (priceData[part]) {
                            traces.push({
                                x: priceData.timestamps,
                                y: priceData[part],
                                type: 'scatter',
                                mode: 'lines',
                                name: part,
                                line: {width: 1}
                            });
                        }
                    }
                } else if (priceData[indicator]) {
                    traces.push({
                        x: priceData.timestamps,
                        y: priceData[indicator],
                        type: 'scatter',
                        mode: 'lines',
                        name: indicator,
                        line: {width: 1.5}
                    });
                }
            }
            
            // Add signals if enabled
            if (showSignals) {
                fetch(`/api/signals?pair=${currentPair}&timeframe=${currentTimeframe}&limit=200`)
                    .then(response => response.json())
                    .then(signalData => {
                        if (!signalData.error && signalData.timestamps && signalData.timestamps.length > 0) {
                            const buySignals = [];
                            const sellSignals = [];
                            
                            for (let i = 0; i < signalData.timestamps.length; i++) {
                                if (signalData.signal[i] > 0) {
                                    buySignals.push({
                                        x: signalData.timestamps[i],
                                        y: priceData.low[priceData.timestamps.indexOf(signalData.timestamps[i])] * 0.9995,
                                        strength: signalData.strength[i]
                                    });
                                } else if (signalData.signal[i] < 0) {
                                    sellSignals.push({
                                        x: signalData.timestamps[i],
                                        y: priceData.high[priceData.timestamps.indexOf(signalData.timestamps[i])] * 1.0005,
                                        strength: signalData.strength[i]
                                    });
                                }
                            }
                            
                            if (buySignals.length > 0) {
                                traces.push({
                                    x: buySignals.map(s => s.x),
                                    y: buySignals.map(s => s.y),
                                    type: 'scatter',
                                    mode: 'markers',
                                    name: 'Buy Signal',
                                    marker: {
                                        symbol: 'triangle-up',
                                        size: buySignals.map(s => Math.min(10 + s.strength * 5, 20)),
                                        color: 'green'
                                    }
                                });
                            }
                            
                            if (sellSignals.length > 0) {
                                traces.push({
                                    x: sellSignals.map(s => s.x),
                                    y: sellSignals.map(s => s.y),
                                    type: 'scatter',
                                    mode: 'markers',
                                    name: 'Sell Signal',
                                    marker: {
                                        symbol: 'triangle-down',
                                        size: sellSignals.map(s => Math.min(10 + s.strength * 5, 20)),
                                        color: 'red'
                                    }
                                });
                            }
                        }
                        
                        // Add trades if enabled
                        if (showTrades) {
                            addTradeMarkers(traces, priceData).then(() => {
                                // Create the chart
                                createPlotlyChart(chartDiv, traces);
                            });
                        } else {
                            // Create the chart without trades
                            createPlotlyChart(chartDiv, traces);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching signals:', error);
                        // Create the chart without signals
                        if (showTrades) {
                            addTradeMarkers(traces, priceData).then(() => {
                                createPlotlyChart(chartDiv, traces);
                            });
                        } else {
                            createPlotlyChart(chartDiv, traces);
                        }
                    });
            } else if (showTrades) {
                // Add trades without signals
                addTradeMarkers(traces, priceData).then(() => {
                    createPlotlyChart(chartDiv, traces);
                });
            } else {
                // Create the chart without signals or trades
                createPlotlyChart(chartDiv, traces);
            }
        })
        .catch(error => {
            console.error('Error fetching price data:', error);
            chartDiv.innerHTML = `<p class="text-center text-danger">Error loading chart data: ${error.message}</p>`;
        });
}

async function addTradeMarkers(traces, priceData) {
    try {
        const response = await fetch(`/api/trades?status=open&pair=${currentPair}`);
        const tradeData = await response.json();
        
        if (!tradeData.error && Array.isArray(tradeData) && tradeData.length > 0) {
            const buyTrades = [];
            const sellTrades = [];
            
            for (const trade of tradeData) {
                // Find the closest timestamp in price data
                const tradeTime = new Date(trade.open_time).getTime();
                let closestIndex = 0;
                let minDiff = Infinity;
                
                for (let i = 0; i < priceData.timestamps.length; i++) {
                    const diff = Math.abs(new Date(priceData.timestamps[i]).getTime() - tradeTime);
                    if (diff < minDiff) {
                        minDiff = diff;
                        closestIndex = i;
                    }
                }
                
                if (trade.type === 'buy') {
                    buyTrades.push({
                        x: priceData.timestamps[closestIndex],
                        y: parseFloat(trade.entry_price),
                        id: trade.id,
                        text: `Buy ${trade.pair} at ${trade.entry_price}`
                    });
                } else if (trade.type === 'sell') {
                    sellTrades.push({
                        x: priceData.timestamps[closestIndex],
                        y: parseFloat(trade.entry_price),
                        id: trade.id,
                        text: `Sell ${trade.pair} at ${trade.entry_price}`
                    });
                }
            }
            
            if (buyTrades.length > 0) {
                traces.push({
                    x: buyTrades.map(t => t.x),
                    y: buyTrades.map(t => t.y),
                    text: buyTrades.map(t => t.text),
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Buy Trade',
                    marker: {
                        symbol: 'circle',
                        size: 10,
                        color: 'rgba(0, 128, 0, 0.7)',
                        line: {width: 2, color: 'green'}
                    }
                });
            }
            
            if (sellTrades.length > 0) {
                traces.push({
                    x: sellTrades.map(t => t.x),
                    y: sellTrades.map(t => t.y),
                    text: sellTrades.map(t => t.text),
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Sell Trade',
                    marker: {
                        symbol: 'circle',
                        size: 10,
                        color: 'rgba(255, 0, 0, 0.7)',
                        line: {width: 2, color: 'red'}
                    }
                });
            }
        }
    } catch (error) {
        console.error('Error fetching trades:', error);
    }
}

function createPlotlyChart(chartDiv, traces) {
    const layout = {
        title: '',
        dragmode: 'zoom',
        showlegend: true,
        legend: {
            orientation: 'h',
            y: 1.1,
            x: 0.5,
            xanchor: 'center'
        },
        margin: {
            l: 50,
            r: 20,
            b: 50,
            t: 20,
            pad: 4
        },
        xaxis: {
            rangeslider: {
                visible: false
            },
            type: 'date'
        },
        yaxis: {
            autorange: true,
            fixedrange: false
        }
    };
    
    const config = {
        responsive: true,
        scrollZoom: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    };
    
    Plotly.newPlot(chartDiv, traces, layout, config);
}
''')