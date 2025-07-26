/**
 * settings.js - Handles settings page functionality for the Forex Trading Bot
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize socket connection
    const socket = io();
    
    // Load settings from server when page loads
    loadAllSettings();
    
    // Set up form submission handlers
    setupFormHandlers();
    
    // Set up API test buttons
    setupAPITestButtons();
    
    // Set up train model button
    document.getElementById('train-model-btn').addEventListener('click', function() {
        trainModel();
    });
    
    // Listen for settings update events from server
    socket.on('settings_updated', function(data) {
        showNotification('Settings updated successfully', 'success');
        // Reload settings if they were updated from another client
        if (!data.source || data.source !== sessionStorage.getItem('clientId')) {
            loadAllSettings();
        }
    });
});

/**
 * Load all settings from the server
 */
function loadAllSettings() {
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateSettingsForms(data.settings);
            } else {
                showNotification('Failed to load settings: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading settings:', error);
            showNotification('Failed to load settings. Please try again.', 'error');
        });
}

/**
 * Populate all settings forms with data from server
 */
function populateSettingsForms(settings) {
    // Populate general settings
    if (settings.general) {
        document.getElementById('bot-name').value = settings.general.bot_name || 'Forex Trading Bot';
        document.getElementById('log-level').value = settings.general.log_level || 'INFO';
        document.getElementById('data-directory').value = settings.general.data_directory || './data';
        document.getElementById('timezone').value = settings.general.timezone || 'UTC';
        document.getElementById('enable-web-interface').checked = settings.general.enable_web_interface !== false;
        document.getElementById('enable-notifications').checked = settings.general.enable_notifications !== false;
        document.getElementById('web-port').value = settings.general.web_port || 5000;
        document.getElementById('notification-email').value = settings.general.notification_email || '';
    }
    
    // Populate trading settings
    if (settings.trading) {
        document.getElementById('trading-mode').value = settings.trading.mode || 'paper';
        document.getElementById('trading-platform').value = settings.trading.platform || 'oanda';
        document.getElementById('default-lot-size').value = settings.trading.default_lot_size || 0.01;
        document.getElementById('max-open-positions').value = settings.trading.max_open_positions || 10;
        document.getElementById('default-slippage').value = settings.trading.default_slippage || 1;
        document.getElementById('default-spread').value = settings.trading.default_spread || 2;
        document.getElementById('enable-trading').checked = settings.trading.enable_trading !== false;
        document.getElementById('trading-start-time').value = settings.trading.trading_hours?.start || '00:00';
        document.getElementById('trading-end-time').value = settings.trading.trading_hours?.end || '23:59';
        
        // Trading days
        const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
        days.forEach(day => {
            const enabled = settings.trading.trading_days ? settings.trading.trading_days.includes(day.toLowerCase()) : 
                          (day !== 'saturday' && day !== 'sunday');
            document.getElementById(`trading-${day}`).checked = enabled;
        });
    }
    
    // Populate risk management settings
    if (settings.risk) {
        document.getElementById('risk-per-trade').value = settings.risk.risk_per_trade || 1;
        document.getElementById('max-daily-risk').value = settings.risk.max_daily_risk || 5;
        document.getElementById('stop-loss-type').value = settings.risk.stop_loss?.type || 'atr';
        document.getElementById('stop-loss-value').value = settings.risk.stop_loss?.value || 2;
        document.getElementById('take-profit-type').value = settings.risk.take_profit?.type || 'resistance';
        document.getElementById('take-profit-value').value = settings.risk.take_profit?.value || 2;
        document.getElementById('trailing-stop').value = settings.risk.trailing_stop || 0;
        document.getElementById('break-even-pips').value = settings.risk.break_even_pips || 0;
        document.getElementById('max-drawdown').value = settings.risk.max_drawdown || 20;
        document.getElementById('position-sizing').value = settings.risk.position_sizing || 'risk';
    }
    
    // Populate indicators settings
    if (settings.indicators) {
        // Moving averages
        document.getElementById('sma-periods').value = settings.indicators.sma?.periods?.join(',') || '20,50,200';
        document.getElementById('ema-periods').value = settings.indicators.ema?.periods?.join(',') || '9,21,55';
        
        // RSI
        document.getElementById('rsi-period').value = settings.indicators.rsi?.period || 14;
        document.getElementById('rsi-overbought').value = settings.indicators.rsi?.overbought || 70;
        document.getElementById('rsi-oversold').value = settings.indicators.rsi?.oversold || 30;
        
        // Stochastic
        document.getElementById('stoch-k-period').value = settings.indicators.stochastic?.k_period || 14;
        document.getElementById('stoch-d-period').value = settings.indicators.stochastic?.d_period || 3;
        document.getElementById('stoch-slowing').value = settings.indicators.stochastic?.slowing || 3;
        
        // MACD
        document.getElementById('macd-fast').value = settings.indicators.macd?.fast_period || 12;
        document.getElementById('macd-slow').value = settings.indicators.macd?.slow_period || 26;
        document.getElementById('macd-signal').value = settings.indicators.macd?.signal_period || 9;
        
        // Bollinger Bands
        document.getElementById('bb-period').value = settings.indicators.bollinger?.period || 20;
        document.getElementById('bb-std').value = settings.indicators.bollinger?.std_dev || 2;
        
        // Other indicators
        document.getElementById('atr-period').value = settings.indicators.atr?.period || 14;
        document.getElementById('adx-period').value = settings.indicators.adx?.period || 14;
        document.getElementById('adx-threshold').value = settings.indicators.adx?.threshold || 25;
    }
    
    // Populate machine learning settings
    if (settings.ml) {
        document.getElementById('ml-model-type').value = settings.ml.model_type || 'random_forest';
        document.getElementById('prediction-horizon').value = settings.ml.prediction_horizon || 5;
        document.getElementById('training-period').value = settings.ml.training_period || 90;
        document.getElementById('retraining-interval').value = settings.ml.retraining_interval || 7;
        document.getElementById('feature-selection').value = settings.ml.feature_selection || 'rfe';
        document.getElementById('validation-method').value = settings.ml.validation_method || 'cross_val';
        document.getElementById('prediction-threshold').value = settings.ml.prediction_threshold || 0.6;
        document.getElementById('ml-signal-weight').value = settings.ml.signal_weight || 50;
        document.getElementById('enable-ml').checked = settings.ml.enable_ml !== false;
    }
    
    // Populate API credentials (don't populate actual keys for security)
    if (settings.api) {
        // Oanda
        if (settings.api.oanda) {
            // Only show placeholder if API key exists
            if (settings.api.oanda.api_key) {
                document.getElementById('oanda-api-key').value = '••••••••••••••••';
                document.getElementById('oanda-api-key').dataset.hasKey = 'true';
            } else {
                document.getElementById('oanda-api-key').value = '';
                document.getElementById('oanda-api-key').dataset.hasKey = 'false';
            }
            document.getElementById('oanda-account-id').value = settings.api.oanda.account_id || '';
            document.getElementById('oanda-environment').value = settings.api.oanda.environment || 'practice';
        }
        
        // FXCM
        if (settings.api.fxcm) {
            if (settings.api.fxcm.api_key) {
                document.getElementById('fxcm-api-key').value = '••••••••••••••••';
                document.getElementById('fxcm-api-key').dataset.hasKey = 'true';
            } else {
                document.getElementById('fxcm-api-key').value = '';
                document.getElementById('fxcm-api-key').dataset.hasKey = 'false';
            }
            document.getElementById('fxcm-account-id').value = settings.api.fxcm.account_id || '';
            document.getElementById('fxcm-environment').value = settings.api.fxcm.environment || 'demo';
        }
        
        // Alpha Vantage
        if (settings.api.alphavantage) {
            if (settings.api.alphavantage.api_key) {
                document.getElementById('alphavantage-api-key').value = '••••••••••••••••';
                document.getElementById('alphavantage-api-key').dataset.hasKey = 'true';
            } else {
                document.getElementById('alphavantage-api-key').value = '';
                document.getElementById('alphavantage-api-key').dataset.hasKey = 'false';
            }
        }
    }
}

/**
 * Set up form submission handlers for all settings forms
 */
function setupFormHandlers() {
    // General settings form
    document.getElementById('general-settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const settings = {
            bot_name: document.getElementById('bot-name').value,
            log_level: document.getElementById('log-level').value,
            data_directory: document.getElementById('data-directory').value,
            timezone: document.getElementById('timezone').value,
            enable_web_interface: document.getElementById('enable-web-interface').checked,
            enable_notifications: document.getElementById('enable-notifications').checked,
            web_port: parseInt(document.getElementById('web-port').value),
            notification_email: document.getElementById('notification-email').value
        };
        saveSettings('general', settings);
    });
    
    // Trading settings form
    document.getElementById('trading-settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get trading days
        const tradingDays = [];
        ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].forEach(day => {
            if (document.getElementById(`trading-${day}`).checked) {
                tradingDays.push(day.toLowerCase());
            }
        });
        
        const settings = {
            mode: document.getElementById('trading-mode').value,
            platform: document.getElementById('trading-platform').value,
            default_lot_size: parseFloat(document.getElementById('default-lot-size').value),
            max_open_positions: parseInt(document.getElementById('max-open-positions').value),
            default_slippage: parseFloat(document.getElementById('default-slippage').value),
            default_spread: parseFloat(document.getElementById('default-spread').value),
            enable_trading: document.getElementById('enable-trading').checked,
            trading_hours: {
                start: document.getElementById('trading-start-time').value,
                end: document.getElementById('trading-end-time').value
            },
            trading_days: tradingDays
        };
        saveSettings('trading', settings);
    });
    
    // Risk management settings form
    document.getElementById('risk-settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const settings = {
            risk_per_trade: parseFloat(document.getElementById('risk-per-trade').value),
            max_daily_risk: parseFloat(document.getElementById('max-daily-risk').value),
            stop_loss: {
                type: document.getElementById('stop-loss-type').value,
                value: parseFloat(document.getElementById('stop-loss-value').value)
            },
            take_profit: {
                type: document.getElementById('take-profit-type').value,
                value: parseFloat(document.getElementById('take-profit-value').value)
            },
            trailing_stop: parseFloat(document.getElementById('trailing-stop').value),
            break_even_pips: parseFloat(document.getElementById('break-even-pips').value),
            max_drawdown: parseFloat(document.getElementById('max-drawdown').value),
            position_sizing: document.getElementById('position-sizing').value
        };
        saveSettings('risk', settings);
    });
    
    // Indicators settings form
    document.getElementById('indicators-settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Parse comma-separated periods into arrays
        const smaPeriods = document.getElementById('sma-periods').value.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
        const emaPeriods = document.getElementById('ema-periods').value.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
        
        const settings = {
            sma: {
                periods: smaPeriods
            },
            ema: {
                periods: emaPeriods
            },
            rsi: {
                period: parseInt(document.getElementById('rsi-period').value),
                overbought: parseInt(document.getElementById('rsi-overbought').value),
                oversold: parseInt(document.getElementById('rsi-oversold').value)
            },
            stochastic: {
                k_period: parseInt(document.getElementById('stoch-k-period').value),
                d_period: parseInt(document.getElementById('stoch-d-period').value),
                slowing: parseInt(document.getElementById('stoch-slowing').value)
            },
            macd: {
                fast_period: parseInt(document.getElementById('macd-fast').value),
                slow_period: parseInt(document.getElementById('macd-slow').value),
                signal_period: parseInt(document.getElementById('macd-signal').value)
            },
            bollinger: {
                period: parseInt(document.getElementById('bb-period').value),
                std_dev: parseFloat(document.getElementById('bb-std').value)
            },
            atr: {
                period: parseInt(document.getElementById('atr-period').value)
            },
            adx: {
                period: parseInt(document.getElementById('adx-period').value),
                threshold: parseInt(document.getElementById('adx-threshold').value)
            }
        };
        saveSettings('indicators', settings);
    });
    
    // Machine learning settings form
    document.getElementById('ml-settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const settings = {
            model_type: document.getElementById('ml-model-type').value,
            prediction_horizon: parseInt(document.getElementById('prediction-horizon').value),
            training_period: parseInt(document.getElementById('training-period').value),
            retraining_interval: parseInt(document.getElementById('retraining-interval').value),
            feature_selection: document.getElementById('feature-selection').value,
            validation_method: document.getElementById('validation-method').value,
            prediction_threshold: parseFloat(document.getElementById('prediction-threshold').value),
            signal_weight: parseInt(document.getElementById('ml-signal-weight').value),
            enable_ml: document.getElementById('enable-ml').checked
        };
        saveSettings('ml', settings);
    });
    
    // API credentials settings form
    document.getElementById('api-settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Only send API keys if they've been changed (not placeholders)
        const settings = {
            oanda: {
                account_id: document.getElementById('oanda-account-id').value,
                environment: document.getElementById('oanda-environment').value
            },
            fxcm: {
                account_id: document.getElementById('fxcm-account-id').value,
                environment: document.getElementById('fxcm-environment').value
            },
            alphavantage: {}
        };
        
        // Only include API keys if they're not the placeholder
        const oandaApiKey = document.getElementById('oanda-api-key').value;
        if (oandaApiKey && oandaApiKey !== '••••••••••••••••') {
            settings.oanda.api_key = oandaApiKey;
        }
        
        const fxcmApiKey = document.getElementById('fxcm-api-key').value;
        if (fxcmApiKey && fxcmApiKey !== '••••••••••••••••') {
            settings.fxcm.api_key = fxcmApiKey;
        }
        
        const alphavantageApiKey = document.getElementById('alphavantage-api-key').value;
        if (alphavantageApiKey && alphavantageApiKey !== '••••••••••••••••') {
            settings.alphavantage.api_key = alphavantageApiKey;
        }
        
        saveSettings('api', settings);
    });
}

/**
 * Save settings to the server
 */
function saveSettings(section, settings) {
    // Generate a client ID if not already set
    if (!sessionStorage.getItem('clientId')) {
        sessionStorage.setItem('clientId', 'client_' + Math.random().toString(36).substr(2, 9));
    }
    
    fetch('/api/settings/' + section, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            settings: settings,
            source: sessionStorage.getItem('clientId')
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Settings saved successfully', 'success');
        } else {
            showNotification('Failed to save settings: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving settings:', error);
        showNotification('Failed to save settings. Please try again.', 'error');
    });
}

/**
 * Set up API test buttons
 */
function setupAPITestButtons() {
    // Oanda API test
    document.getElementById('test-oanda-btn').addEventListener('click', function() {
        testApiConnection('oanda');
    });
    
    // FXCM API test
    document.getElementById('test-fxcm-btn').addEventListener('click', function() {
        testApiConnection('fxcm');
    });
    
    // Alpha Vantage API test
    document.getElementById('test-alphavantage-btn').addEventListener('click', function() {
        testApiConnection('alphavantage');
    });
}

/**
 * Test API connection
 */
function testApiConnection(api) {
    // Show loading state
    const button = document.getElementById(`test-${api}-btn`);
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Testing...';
    button.disabled = true;
    
    // Get API credentials
    let credentials = {};
    
    if (api === 'oanda') {
        const apiKey = document.getElementById('oanda-api-key').value;
        if (apiKey === '••••••••••••••••' && document.getElementById('oanda-api-key').dataset.hasKey === 'true') {
            // Use existing key
            credentials.use_existing_key = true;
        } else if (apiKey && apiKey !== '••••••••••••••••') {
            credentials.api_key = apiKey;
        } else {
            showNotification('Please enter an API key', 'warning');
            button.innerHTML = originalText;
            button.disabled = false;
            return;
        }
        credentials.account_id = document.getElementById('oanda-account-id').value;
        credentials.environment = document.getElementById('oanda-environment').value;
    } else if (api === 'fxcm') {
        const apiKey = document.getElementById('fxcm-api-key').value;
        if (apiKey === '••••••••••••••••' && document.getElementById('fxcm-api-key').dataset.hasKey === 'true') {
            credentials.use_existing_key = true;
        } else if (apiKey && apiKey !== '••••••••••••••••') {
            credentials.api_key = apiKey;
        } else {
            showNotification('Please enter an API key', 'warning');
            button.innerHTML = originalText;
            button.disabled = false;
            return;
        }
        credentials.account_id = document.getElementById('fxcm-account-id').value;
        credentials.environment = document.getElementById('fxcm-environment').value;
    } else if (api === 'alphavantage') {
        const apiKey = document.getElementById('alphavantage-api-key').value;
        if (apiKey === '••••••••••••••••' && document.getElementById('alphavantage-api-key').dataset.hasKey === 'true') {
            credentials.use_existing_key = true;
        } else if (apiKey && apiKey !== '••••••••••••••••') {
            credentials.api_key = apiKey;
        } else {
            showNotification('Please enter an API key', 'warning');
            button.innerHTML = originalText;
            button.disabled = false;
            return;
        }
    }
    
    // Test API connection
    fetch('/api/test_connection/' + api, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(credentials)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`${api.toUpperCase()} API connection successful`, 'success');
        } else {
            showNotification(`${api.toUpperCase()} API connection failed: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error(`Error testing ${api} API:`, error);
        showNotification(`${api.toUpperCase()} API connection failed. Please try again.`, 'error');
    })
    .finally(() => {
        // Restore button state
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

/**
 * Train machine learning model
 */
function trainModel() {
    // Show loading state
    const button = document.getElementById('train-model-btn');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Training...';
    button.disabled = true;
    
    // Get ML settings
    const settings = {
        model_type: document.getElementById('ml-model-type').value,
        prediction_horizon: parseInt(document.getElementById('prediction-horizon').value),
        training_period: parseInt(document.getElementById('training-period').value),
        feature_selection: document.getElementById('feature-selection').value,
        validation_method: document.getElementById('validation-method').value,
        prediction_threshold: parseFloat(document.getElementById('prediction-threshold').value)
    };
    
    // Train model
    fetch('/api/train_model', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Model training started. This may take some time.', 'info');
            // Listen for training completion event
            const socket = io();
            socket.on('model_training_complete', function(result) {
                if (result.success) {
                    showNotification(`Model training completed successfully. Accuracy: ${result.accuracy.toFixed(2)}%`, 'success');
                } else {
                    showNotification(`Model training failed: ${result.message}`, 'error');
                }
                // Restore button state
                button.innerHTML = originalText;
                button.disabled = false;
            });
        } else {
            showNotification(`Failed to start model training: ${data.message}`, 'error');
            // Restore button state
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error training model:', error);
        showNotification('Failed to train model. Please try again.', 'error');
        // Restore button state
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

/**
 * Show notification
 */
function showNotification(message, type) {
    // Check if notification container exists, if not create it
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'warning' ? 'warning' : type === 'info' ? 'info' : 'danger'}`;
    notification.role = 'alert';
    notification.ariaLive = 'assertive';
    notification.ariaAtomic = 'true';
    notification.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    container.appendChild(notification);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(notification, {
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Remove notification after it's hidden
    notification.addEventListener('hidden.bs.toast', function() {
        notification.remove();
    });
}