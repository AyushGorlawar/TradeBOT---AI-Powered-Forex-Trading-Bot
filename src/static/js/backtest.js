/**
 * backtest.js - Handles backtest page functionality for the Forex Trading Bot
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize socket connection
    const socket = io();
    
    // Set default dates (last 3 months)
    setDefaultDates();
    
    // Set up event listeners
    setupEventListeners();
    
    // Listen for backtest events from server
    socket.on('backtest_progress', function(data) {
        updateBacktestProgress(data);
    });
    
    socket.on('backtest_completed', function(data) {
        displayBacktestResults(data);
    });
    
    socket.on('backtest_error', function(data) {
        showBacktestError(data.message);
    });
});

/**
 * Set default dates for backtest (last 3 months)
 */
function setDefaultDates() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 3);
    
    document.getElementById('backtest-start-date').valueAsDate = startDate;
    document.getElementById('backtest-end-date').valueAsDate = endDate;
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Run backtest form submission
    document.getElementById('backtest-form').addEventListener('submit', function(e) {
        e.preventDefault();
        runBacktest();
    });
    
    // Export backtest results
    document.getElementById('export-backtest-btn').addEventListener('click', function() {
        exportBacktestResults();
    });
    
    // Save strategy button
    document.getElementById('save-strategy-btn').addEventListener('click', function() {
        // Show save strategy modal
        const saveStrategyModal = new bootstrap.Modal(document.getElementById('save-strategy-modal'));
        saveStrategyModal.show();
    });
    
    // Save strategy confirmation
    document.getElementById('save-strategy-confirm').addEventListener('click', function() {
        saveStrategy();
    });
    
    // Show only winners checkbox
    document.getElementById('show-only-winners').addEventListener('change', function() {
        filterTradeList();
    });
}

/**
 * Run backtest with current form settings
 */
function runBacktest() {
    // Get form values
    const pairs = Array.from(document.getElementById('backtest-pairs').selectedOptions).map(option => option.value);
    const timeframe = document.getElementById('backtest-timeframe').value;
    const startDate = document.getElementById('backtest-start-date').value;
    const endDate = document.getElementById('backtest-end-date').value;
    const initialBalance = parseFloat(document.getElementById('backtest-initial-balance').value);
    const riskPerTrade = parseFloat(document.getElementById('backtest-risk-per-trade').value);
    
    // Get signal types
    const signalTypes = {
        rsi: document.getElementById('backtest-signal-rsi').checked,
        macd: document.getElementById('backtest-signal-macd').checked,
        bollinger_bands: document.getElementById('backtest-signal-bb').checked,
        moving_averages: document.getElementById('backtest-signal-ma').checked,
        stochastic: document.getElementById('backtest-signal-stoch').checked,
        machine_learning: document.getElementById('backtest-signal-ml').checked
    };
    
    // Get advanced options
    const advancedOptions = {
        include_spread: document.getElementById('backtest-use-spread').checked,
        include_commission: document.getElementById('backtest-use-commission').checked,
        include_swap: document.getElementById('backtest-use-swap').checked
    };
    
    // Validate inputs
    if (pairs.length === 0) {
        showNotification('Please select at least one currency pair', 'warning');
        return;
    }
    
    if (!startDate || !endDate) {
        showNotification('Please select start and end dates', 'warning');
        return;
    }
    
    if (new Date(startDate) >= new Date(endDate)) {
        showNotification('Start date must be before end date', 'warning');
        return;
    }
    
    if (initialBalance <= 0) {
        showNotification('Initial balance must be greater than zero', 'warning');
        return;
    }
    
    if (riskPerTrade <= 0 || riskPerTrade > 10) {
        showNotification('Risk per trade must be between 0.1% and 10%', 'warning');
        return;
    }
    
    // Check if at least one signal type is selected
    if (!Object.values(signalTypes).some(value => value)) {
        showNotification('Please select at least one signal type', 'warning');
        return;
    }
    
    // Prepare backtest parameters
    const backtestParams = {
        pairs: pairs,
        timeframe: timeframe,
        start_date: startDate,
        end_date: endDate,
        initial_balance: initialBalance,
        risk_per_trade: riskPerTrade,
        signal_types: signalTypes,
        advanced_options: advancedOptions
    };
    
    // Show loading state
    document.getElementById('backtest-placeholder').classList.add('d-none');
    document.getElementById('backtest-results').classList.add('d-none');
    document.getElementById('backtest-loading').classList.remove('d-none');
    
    // Disable run button
    document.getElementById('run-backtest-btn').disabled = true;
    
    // Send backtest request to server
    fetch('/api/backtest/run', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(backtestParams)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Backtest started successfully, results will come via socket
            showNotification('Backtest started successfully', 'info');
        } else {
            showBacktestError(data.message);
        }
    })
    .catch(error => {
        console.error('Error starting backtest:', error);
        showBacktestError('Failed to start backtest. Please try again.');
    });
}

/**
 * Update backtest progress
 */
function updateBacktestProgress(data) {
    const loadingElement = document.getElementById('backtest-loading');
    const progressPercentage = Math.round(data.progress * 100);
    
    // Update loading message
    loadingElement.innerHTML = `
        <div class="progress mb-3" style="height: 25px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                role="progressbar" 
                style="width: ${progressPercentage}%" 
                aria-valuenow="${progressPercentage}" 
                aria-valuemin="0" 
                aria-valuemax="100">
                ${progressPercentage}%
            </div>
        </div>
        <p class="mt-3">${data.message || 'Running backtest...'}</p>
    `;
}

/**
 * Display backtest results
 */
function displayBacktestResults(data) {
    // Hide loading, show results
    document.getElementById('backtest-loading').classList.add('d-none');
    document.getElementById('backtest-results').classList.remove('d-none');
    
    // Enable run button
    document.getElementById('run-backtest-btn').disabled = false;
    
    // Enable export and save buttons
    document.getElementById('export-backtest-btn').disabled = false;
    document.getElementById('save-strategy-btn').disabled = false;
    
    // Store backtest results in global variable for later use
    window.backtestResults = data;
    
    // Display performance metrics
    displayPerformanceMetrics(data.performance);
    
    // Display equity curve
    displayEquityCurve(data.equity_history);
    
    // Display trade distribution
    displayTradeDistribution(data.performance);
    
    // Display trade list
    displayTradeList(data.trades);
    
    // Show success notification
    showNotification('Backtest completed successfully', 'success');
}

/**
 * Display performance metrics
 */
function displayPerformanceMetrics(performance) {
    // Update performance metrics
    document.getElementById('backtest-total-return').textContent = formatPercentage(performance.return_pct);
    document.getElementById('backtest-net-profit').textContent = formatCurrency(performance.total_pnl);
    document.getElementById('backtest-win-rate').textContent = formatPercentage(performance.win_rate);
    document.getElementById('backtest-profit-factor').textContent = performance.profit_factor.toFixed(2);
    document.getElementById('backtest-max-drawdown').textContent = formatPercentage(performance.max_drawdown_pct);
    document.getElementById('backtest-sharpe-ratio').textContent = performance.sharpe_ratio.toFixed(2);
    document.getElementById('backtest-total-trades').textContent = performance.total_trades;
    document.getElementById('backtest-avg-trade').textContent = formatCurrency(performance.average_trade);
}

/**
 * Display equity curve
 */
function displayEquityCurve(equityHistory) {
    const ctx = document.getElementById('backtest-equity-curve').getContext('2d');
    
    // Prepare data for chart
    const labels = equityHistory.map(item => new Date(item.timestamp));
    const equityData = equityHistory.map(item => item.equity);
    
    // Destroy existing chart if it exists
    if (window.equityCurveChart) {
        window.equityCurveChart.destroy();
    }
    
    // Create new chart
    window.equityCurveChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Account Equity',
                data: equityData,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderWidth: 2,
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Equity'
                    },
                    beginAtZero: false
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Equity: ' + formatCurrency(context.raw);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Display trade distribution
 */
function displayTradeDistribution(performance) {
    const ctx = document.getElementById('backtest-trade-distribution').getContext('2d');
    
    // Prepare data for chart
    const data = {
        labels: ['Winning Trades', 'Losing Trades', 'Break-Even Trades'],
        datasets: [{
            data: [
                performance.winning_trades,
                performance.losing_trades,
                performance.break_even_trades
            ],
            backgroundColor: [
                'rgba(75, 192, 192, 0.7)',
                'rgba(255, 99, 132, 0.7)',
                'rgba(255, 206, 86, 0.7)'
            ],
            borderColor: [
                'rgba(75, 192, 192, 1)',
                'rgba(255, 99, 132, 1)',
                'rgba(255, 206, 86, 1)'
            ],
            borderWidth: 1
        }]
    };
    
    // Destroy existing chart if it exists
    if (window.tradeDistributionChart) {
        window.tradeDistributionChart.destroy();
    }
    
    // Create new chart
    window.tradeDistributionChart = new Chart(ctx, {
        type: 'pie',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Display trade list
 */
function displayTradeList(trades) {
    const tableBody = document.getElementById('backtest-trades-table');
    
    // Store trades in global variable for filtering
    window.backtestTrades = trades;
    
    // Filter and display trades
    filterTradeList();
}

/**
 * Filter trade list based on show only winners checkbox
 */
function filterTradeList() {
    const tableBody = document.getElementById('backtest-trades-table');
    const showOnlyWinners = document.getElementById('show-only-winners').checked;
    
    // Get trades from global variable
    let trades = window.backtestTrades || [];
    
    // Filter trades if needed
    if (showOnlyWinners) {
        trades = trades.filter(trade => trade.profit_loss > 0);
    }
    
    // Clear table
    tableBody.innerHTML = '';
    
    if (trades.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="10" class="text-center">No trades to display</td>`;
        tableBody.appendChild(row);
        return;
    }
    
    // Add trades to table
    trades.forEach((trade, index) => {
        const row = document.createElement('tr');
        
        // Determine profit/loss class
        const plClass = trade.profit_loss >= 0 ? 'text-success' : 'text-danger';
        
        // Format dates
        const openTime = new Date(trade.open_time);
        const closeTime = new Date(trade.close_time);
        const formattedOpenTime = formatDateTime(openTime);
        const formattedCloseTime = formatDateTime(closeTime);
        
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${trade.pair}</td>
            <td><span class="badge bg-${trade.direction === 'buy' ? 'success' : 'danger'}">${trade.direction.toUpperCase()}</span></td>
            <td>${formattedOpenTime}</td>
            <td>${formattedCloseTime}</td>
            <td>${trade.open_price}</td>
            <td>${trade.close_price}</td>
            <td class="${plClass}">${formatCurrency(trade.profit_loss)}</td>
            <td>${trade.signal_type || 'N/A'}</td>
            <td>
                <button class="btn btn-sm btn-outline-info" onclick="viewTradeDetails(${index})">
                    <i class="fas fa-info-circle"></i>
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

/**
 * View trade details
 */
function viewTradeDetails(tradeIndex) {
    // Get trade from global variable
    const trade = window.backtestTrades[tradeIndex];
    
    // Create modal for trade details
    const modalHtml = `
        <div class="modal fade" id="trade-details-modal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Trade Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <table class="table table-sm">
                                    <tr>
                                        <th>Pair:</th>
                                        <td>${trade.pair}</td>
                                    </tr>
                                    <tr>
                                        <th>Direction:</th>
                                        <td><span class="badge bg-${trade.direction === 'buy' ? 'success' : 'danger'}">${trade.direction.toUpperCase()}</span></td>
                                    </tr>
                                    <tr>
                                        <th>Size:</th>
                                        <td>${trade.size}</td>
                                    </tr>
                                    <tr>
                                        <th>Open Time:</th>
                                        <td>${formatDateTime(new Date(trade.open_time))}</td>
                                    </tr>
                                    <tr>
                                        <th>Close Time:</th>
                                        <td>${formatDateTime(new Date(trade.close_time))}</td>
                                    </tr>
                                    <tr>
                                        <th>Duration:</th>
                                        <td>${formatDuration(new Date(trade.close_time) - new Date(trade.open_time))}</td>
                                    </tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <table class="table table-sm">
                                    <tr>
                                        <th>Entry Price:</th>
                                        <td>${trade.open_price}</td>
                                    </tr>
                                    <tr>
                                        <th>Exit Price:</th>
                                        <td>${trade.close_price}</td>
                                    </tr>
                                    <tr>
                                        <th>Stop Loss:</th>
                                        <td>${trade.stop_loss || 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <th>Take Profit:</th>
                                        <td>${trade.take_profit || 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <th>P/L:</th>
                                        <td class="${trade.profit_loss >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(trade.profit_loss)}</td>
                                    </tr>
                                    <tr>
                                        <th>Exit Reason:</th>
                                        <td>${trade.exit_reason || 'N/A'}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                        
                        <div class="row mt-3">
                            <div class="col-md-12">
                                <h6>Signal Information</h6>
                                <table class="table table-sm">
                                    <tr>
                                        <th>Signal Type:</th>
                                        <td>${trade.signal_type || 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <th>Signal Strength:</th>
                                        <td>${trade.signal_strength ? trade.signal_strength + '%' : 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <th>Indicators:</th>
                                        <td>${trade.indicators ? trade.indicators.join(', ') : 'N/A'}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="viewTradeChart('${trade.pair}', '${trade.open_time}', '${trade.close_time}')" data-bs-dismiss="modal">View Chart</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if it exists
    const existingModal = document.getElementById('trade-details-modal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to document
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('trade-details-modal'));
    modal.show();
}

/**
 * View trade chart
 */
function viewTradeChart(pair, openTime, closeTime) {
    // Redirect to charts page with trade parameters
    window.location.href = `/charts?pair=${pair}&from=${openTime}&to=${closeTime}&highlight=true`;
}

/**
 * Export backtest results
 */
function exportBacktestResults() {
    // Get backtest results from global variable
    const results = window.backtestResults;
    
    if (!results) {
        showNotification('No backtest results to export', 'warning');
        return;
    }
    
    // Prepare data for export
    const exportData = {
        backtest_config: {
            pairs: results.config.pairs,
            timeframe: results.config.timeframe,
            start_date: results.config.start_date,
            end_date: results.config.end_date,
            initial_balance: results.config.initial_balance,
            risk_per_trade: results.config.risk_per_trade
        },
        performance: results.performance,
        trades: results.trades
    };
    
    // Convert to JSON string
    const jsonString = JSON.stringify(exportData, null, 2);
    
    // Create blob and download link
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    // Create download link
    const a = document.createElement('a');
    a.href = url;
    a.download = `backtest_results_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 0);
}

/**
 * Save strategy
 */
function saveStrategy() {
    // Get form values
    const strategyName = document.getElementById('strategy-name').value;
    const strategyDescription = document.getElementById('strategy-description').value;
    const strategyActive = document.getElementById('strategy-active').checked;
    
    // Validate inputs
    if (!strategyName) {
        showNotification('Please enter a strategy name', 'warning');
        return;
    }
    
    // Get backtest results from global variable
    const results = window.backtestResults;
    
    if (!results) {
        showNotification('No backtest results to save', 'warning');
        return;
    }
    
    // Prepare strategy data
    const strategyData = {
        name: strategyName,
        description: strategyDescription,
        active: strategyActive,
        config: results.config,
        performance: results.performance
    };
    
    // Send save request to server
    fetch('/api/strategies/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(strategyData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('save-strategy-modal'));
            modal.hide();
            
            // Show success notification
            showNotification('Strategy saved successfully', 'success');
            
            // Reset form
            document.getElementById('strategy-name').value = '';
            document.getElementById('strategy-description').value = '';
            document.getElementById('strategy-active').checked = false;
        } else {
            showNotification('Failed to save strategy: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving strategy:', error);
        showNotification('Failed to save strategy. Please try again.', 'error');
    });
}

/**
 * Show backtest error
 */
function showBacktestError(message) {
    // Hide loading, show placeholder
    document.getElementById('backtest-loading').classList.add('d-none');
    document.getElementById('backtest-results').classList.add('d-none');
    document.getElementById('backtest-placeholder').classList.remove('d-none');
    
    // Enable run button
    document.getElementById('run-backtest-btn').disabled = false;
    
    // Show error notification
    showNotification('Backtest error: ' + message, 'error');
}

/**
 * Format currency value
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

/**
 * Format percentage value
 */
function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

/**
 * Format date and time
 */
function formatDateTime(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

/**
 * Format duration
 */
function formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
        return `${days}d ${hours % 24}h`;
    } else if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    } else {
        return `${seconds}s`;
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Map type to Bootstrap alert class
    const alertClass = {
        'info': 'alert-info',
        'success': 'alert-success',
        'warning': 'alert-warning',
        'error': 'alert-danger'
    }[type] || 'alert-info';
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show notification`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to notifications container (create if it doesn't exist)
    let container = document.getElementById('notifications-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notifications-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1050';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 150);
    }, 5000);
}