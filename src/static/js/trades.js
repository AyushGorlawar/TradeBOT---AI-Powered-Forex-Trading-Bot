/**
 * trades.js - Handles trades page functionality for the Forex Trading Bot
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize socket connection
    const socket = io();
    
    // Load initial data
    loadOpenPositions();
    loadTradeHistory();
    
    // Set up event listeners
    setupEventListeners();
    
    // Listen for trade events from server
    socket.on('trade_opened', function(trade) {
        // Refresh open positions
        loadOpenPositions();
        showNotification(`New trade opened: ${trade.pair} ${trade.direction.toUpperCase()}`, 'info');
    });
    
    socket.on('trade_closed', function(trade) {
        // Refresh open positions and trade history
        loadOpenPositions();
        loadTradeHistory();
        
        // Show notification with profit/loss
        const profitLoss = trade.profit_loss;
        const notificationType = profitLoss >= 0 ? 'success' : 'danger';
        const profitLossText = formatCurrency(profitLoss);
        showNotification(`Trade closed: ${trade.pair} ${trade.direction.toUpperCase()} (${profitLossText})`, notificationType);
    });
    
    socket.on('trade_updated', function(trade) {
        // Refresh open positions
        loadOpenPositions();
    });
});

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Filter trade history
    document.getElementById('filter-trades-form').addEventListener('submit', function(e) {
        e.preventDefault();
        loadTradeHistory();
    });
    
    // Pagination for trade history
    document.getElementById('trade-history-pagination').addEventListener('click', function(e) {
        if (e.target.tagName === 'A' && e.target.dataset.page) {
            e.preventDefault();
            const page = parseInt(e.target.dataset.page);
            document.getElementById('current-page').value = page;
            loadTradeHistory();
        }
    });
    
    // Close all trades button
    document.getElementById('close-all-trades-btn').addEventListener('click', function() {
        if (confirm('Are you sure you want to close all open trades?')) {
            closeAllTrades();
        }
    });
    
    // Trade modal events
    const tradeModal = document.getElementById('trade-modal');
    tradeModal.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        const tradeId = button.getAttribute('data-trade-id');
        const tradeType = button.getAttribute('data-trade-type'); // 'open' or 'history'
        
        if (tradeId) {
            loadTradeDetails(tradeId, tradeType);
        }
    });
}

/**
 * Load open positions
 */
function loadOpenPositions() {
    fetch('/api/trades/open')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayOpenPositions(data.trades);
            } else {
                showNotification('Failed to load open positions: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading open positions:', error);
            showNotification('Failed to load open positions. Please try again.', 'error');
        });
}

/**
 * Display open positions
 */
function displayOpenPositions(trades) {
    const tableBody = document.getElementById('open-positions-table-body');
    const noTradesMessage = document.getElementById('no-open-trades-message');
    const closeAllBtn = document.getElementById('close-all-trades-btn');
    
    // Clear table
    tableBody.innerHTML = '';
    
    if (trades.length === 0) {
        // Show no trades message
        noTradesMessage.style.display = 'block';
        closeAllBtn.style.display = 'none';
        return;
    }
    
    // Hide no trades message and show close all button
    noTradesMessage.style.display = 'none';
    closeAllBtn.style.display = 'block';
    
    // Add trades to table
    trades.forEach(trade => {
        const row = document.createElement('tr');
        
        // Determine profit/loss class
        const plClass = trade.current_profit_loss >= 0 ? 'text-success' : 'text-danger';
        
        // Format dates
        const openTime = new Date(trade.open_time);
        const formattedOpenTime = formatDateTime(openTime);
        
        // Calculate duration
        const duration = formatDuration(new Date() - openTime);
        
        row.innerHTML = `
            <td>${trade.id}</td>
            <td>${trade.pair}</td>
            <td><span class="badge bg-${trade.direction === 'buy' ? 'success' : 'danger'}">${trade.direction.toUpperCase()}</span></td>
            <td>${trade.size}</td>
            <td>${trade.open_price}</td>
            <td>${trade.current_price}</td>
            <td>${formattedOpenTime}</td>
            <td>${duration}</td>
            <td>${trade.stop_loss || 'N/A'}</td>
            <td>${trade.take_profit || 'N/A'}</td>
            <td class="${plClass}">${formatCurrency(trade.current_profit_loss)}</td>
            <td>
                <button class="btn btn-sm btn-outline-info me-1" data-bs-toggle="modal" data-bs-target="#trade-modal" data-trade-id="${trade.id}" data-trade-type="open">
                    <i class="fas fa-info-circle"></i>
                </button>
                <button class="btn btn-sm btn-outline-primary me-1" onclick="modifyTrade('${trade.id}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="closeTrade('${trade.id}')">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

/**
 * Load trade history
 */
function loadTradeHistory() {
    // Get filter values
    const pair = document.getElementById('filter-pair').value;
    const direction = document.getElementById('filter-direction').value;
    const outcome = document.getElementById('filter-outcome').value;
    const dateFrom = document.getElementById('filter-date-from').value;
    const dateTo = document.getElementById('filter-date-to').value;
    const currentPage = parseInt(document.getElementById('current-page').value) || 1;
    const pageSize = parseInt(document.getElementById('page-size').value) || 10;
    
    // Build query string
    let queryParams = new URLSearchParams();
    if (pair) queryParams.append('pair', pair);
    if (direction) queryParams.append('direction', direction);
    if (outcome) queryParams.append('outcome', outcome);
    if (dateFrom) queryParams.append('date_from', dateFrom);
    if (dateTo) queryParams.append('date_to', dateTo);
    queryParams.append('page', currentPage);
    queryParams.append('page_size', pageSize);
    
    fetch(`/api/trades/history?${queryParams.toString()}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayTradeHistory(data.trades, data.total_trades, currentPage, pageSize);
            } else {
                showNotification('Failed to load trade history: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading trade history:', error);
            showNotification('Failed to load trade history. Please try again.', 'error');
        });
}

/**
 * Display trade history
 */
function displayTradeHistory(trades, totalTrades, currentPage, pageSize) {
    const tableBody = document.getElementById('trade-history-table-body');
    const noTradesMessage = document.getElementById('no-trade-history-message');
    const paginationContainer = document.getElementById('trade-history-pagination');
    
    // Clear table
    tableBody.innerHTML = '';
    
    if (trades.length === 0) {
        // Show no trades message
        noTradesMessage.style.display = 'block';
        paginationContainer.style.display = 'none';
        return;
    }
    
    // Hide no trades message
    noTradesMessage.style.display = 'none';
    
    // Add trades to table
    trades.forEach(trade => {
        const row = document.createElement('tr');
        
        // Determine profit/loss class
        const plClass = trade.profit_loss >= 0 ? 'text-success' : 'text-danger';
        
        // Format dates
        const openTime = new Date(trade.open_time);
        const closeTime = new Date(trade.close_time);
        const formattedOpenTime = formatDateTime(openTime);
        const formattedCloseTime = formatDateTime(closeTime);
        
        // Calculate duration
        const duration = formatDuration(closeTime - openTime);
        
        row.innerHTML = `
            <td>${trade.id}</td>
            <td>${trade.pair}</td>
            <td><span class="badge bg-${trade.direction === 'buy' ? 'success' : 'danger'}">${trade.direction.toUpperCase()}</span></td>
            <td>${trade.size}</td>
            <td>${trade.open_price}</td>
            <td>${trade.close_price}</td>
            <td>${formattedOpenTime}</td>
            <td>${formattedCloseTime}</td>
            <td>${duration}</td>
            <td class="${plClass}">${formatCurrency(trade.profit_loss)}</td>
            <td>
                <button class="btn btn-sm btn-outline-info" data-bs-toggle="modal" data-bs-target="#trade-modal" data-trade-id="${trade.id}" data-trade-type="history">
                    <i class="fas fa-info-circle"></i>
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Update pagination
    updatePagination(totalTrades, currentPage, pageSize);
}

/**
 * Update pagination controls
 */
function updatePagination(totalTrades, currentPage, pageSize) {
    const paginationContainer = document.getElementById('trade-history-pagination');
    const totalPages = Math.ceil(totalTrades / pageSize);
    
    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }
    
    paginationContainer.style.display = 'block';
    
    // Generate pagination HTML
    let paginationHtml = `
        <ul class="pagination justify-content-center">
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${currentPage - 1}" aria-label="Previous">
                    <span aria-hidden="true">&laquo;</span>
                </a>
            </li>
    `;
    
    // Determine which page numbers to show
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    // Adjust if we're near the end
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    // Add page numbers
    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>
        `;
    }
    
    paginationHtml += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${currentPage + 1}" aria-label="Next">
                    <span aria-hidden="true">&raquo;</span>
                </a>
            </li>
        </ul>
    `;
    
    paginationContainer.innerHTML = paginationHtml;
}

/**
 * Load trade details for modal
 */
function loadTradeDetails(tradeId, tradeType) {
    const endpoint = tradeType === 'open' ? '/api/trades/open/' : '/api/trades/history/';
    
    fetch(endpoint + tradeId)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayTradeDetails(data.trade, tradeType);
            } else {
                showNotification('Failed to load trade details: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading trade details:', error);
            showNotification('Failed to load trade details. Please try again.', 'error');
        });
}

/**
 * Display trade details in modal
 */
function displayTradeDetails(trade, tradeType) {
    const modalTitle = document.getElementById('trade-modal-title');
    const modalBody = document.getElementById('trade-modal-body');
    const modalFooter = document.getElementById('trade-modal-footer');
    
    // Set modal title
    modalTitle.textContent = `${trade.pair} ${trade.direction.toUpperCase()} Trade Details`;
    
    // Format dates
    const openTime = new Date(trade.open_time);
    const formattedOpenTime = formatDateTime(openTime);
    
    let closeTimeHtml = '';
    let durationHtml = '';
    let profitLossHtml = '';
    
    if (tradeType === 'history') {
        const closeTime = new Date(trade.close_time);
        const formattedCloseTime = formatDateTime(closeTime);
        const duration = formatDuration(closeTime - openTime);
        const plClass = trade.profit_loss >= 0 ? 'text-success' : 'text-danger';
        
        closeTimeHtml = `
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Close Time:</div>
                <div class="col-md-8">${formattedCloseTime}</div>
            </div>
        `;
        
        durationHtml = `
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Duration:</div>
                <div class="col-md-8">${duration}</div>
            </div>
        `;
        
        profitLossHtml = `
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Profit/Loss:</div>
                <div class="col-md-8 ${plClass}">${formatCurrency(trade.profit_loss)}</div>
            </div>
        `;
    } else {
        const duration = formatDuration(new Date() - openTime);
        const plClass = trade.current_profit_loss >= 0 ? 'text-success' : 'text-danger';
        
        durationHtml = `
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Duration:</div>
                <div class="col-md-8">${duration}</div>
            </div>
        `;
        
        profitLossHtml = `
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Current P/L:</div>
                <div class="col-md-8 ${plClass}">${formatCurrency(trade.current_profit_loss)}</div>
            </div>
        `;
    }
    
    // Build modal body HTML
    let modalBodyHtml = `
        <div class="row mb-2">
            <div class="col-md-4 fw-bold">Trade ID:</div>
            <div class="col-md-8">${trade.id}</div>
        </div>
        <div class="row mb-2">
            <div class="col-md-4 fw-bold">Pair:</div>
            <div class="col-md-8">${trade.pair}</div>
        </div>
        <div class="row mb-2">
            <div class="col-md-4 fw-bold">Direction:</div>
            <div class="col-md-8">
                <span class="badge bg-${trade.direction === 'buy' ? 'success' : 'danger'}">${trade.direction.toUpperCase()}</span>
            </div>
        </div>
        <div class="row mb-2">
            <div class="col-md-4 fw-bold">Size:</div>
            <div class="col-md-8">${trade.size}</div>
        </div>
        <div class="row mb-2">
            <div class="col-md-4 fw-bold">Open Price:</div>
            <div class="col-md-8">${trade.open_price}</div>
        </div>
    `;
    
    if (tradeType === 'history') {
        modalBodyHtml += `
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Close Price:</div>
                <div class="col-md-8">${trade.close_price}</div>
            </div>
        `;
    } else {
        modalBodyHtml += `
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Current Price:</div>
                <div class="col-md-8">${trade.current_price}</div>
            </div>
        `;
    }
    
    modalBodyHtml += `
        <div class="row mb-2">
            <div class="col-md-4 fw-bold">Open Time:</div>
            <div class="col-md-8">${formattedOpenTime}</div>
        </div>
        ${closeTimeHtml}
        ${durationHtml}
    `;
    
    if (tradeType === 'open') {
        modalBodyHtml += `
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Stop Loss:</div>
                <div class="col-md-8">${trade.stop_loss || 'N/A'}</div>
            </div>
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Take Profit:</div>
                <div class="col-md-8">${trade.take_profit || 'N/A'}</div>
            </div>
        `;
    }
    
    modalBodyHtml += profitLossHtml;
    
    // Add signal information if available
    if (trade.signal) {
        modalBodyHtml += `
            <hr>
            <h6>Signal Information</h6>
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Signal Type:</div>
                <div class="col-md-8">${trade.signal.type}</div>
            </div>
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Signal Strength:</div>
                <div class="col-md-8">${trade.signal.strength}%</div>
            </div>
            <div class="row mb-2">
                <div class="col-md-4 fw-bold">Indicators:</div>
                <div class="col-md-8">${trade.signal.indicators.join(', ')}</div>
            </div>
        `;
    }
    
    // Set modal body content
    modalBody.innerHTML = modalBodyHtml;
    
    // Set modal footer buttons
    if (tradeType === 'open') {
        modalFooter.innerHTML = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            <button type="button" class="btn btn-primary" onclick="modifyTrade('${trade.id}')" data-bs-dismiss="modal">Modify</button>
            <button type="button" class="btn btn-danger" onclick="closeTrade('${trade.id}')" data-bs-dismiss="modal">Close Trade</button>
        `;
    } else {
        modalFooter.innerHTML = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            <button type="button" class="btn btn-primary" onclick="viewTradeChart('${trade.id}')" data-bs-dismiss="modal">View Chart</button>
        `;
    }
}

/**
 * Close a trade
 */
function closeTrade(tradeId) {
    if (confirm('Are you sure you want to close this trade?')) {
        fetch(`/api/trades/close/${tradeId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Trade closed successfully', 'success');
                // Trade closed event will trigger refresh via socket
            } else {
                showNotification('Failed to close trade: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error closing trade:', error);
            showNotification('Failed to close trade. Please try again.', 'error');
        });
    }
}

/**
 * Close all trades
 */
function closeAllTrades() {
    fetch('/api/trades/close_all', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`${data.closed_count} trades closed successfully`, 'success');
            // Trade closed events will trigger refresh via socket
        } else {
            showNotification('Failed to close trades: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error closing all trades:', error);
        showNotification('Failed to close trades. Please try again.', 'error');
    });
}

/**
 * Modify a trade (stop loss, take profit)
 */
function modifyTrade(tradeId) {
    // Get current trade details
    fetch(`/api/trades/open/${tradeId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showModifyTradeModal(data.trade);
            } else {
                showNotification('Failed to get trade details: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error getting trade details:', error);
            showNotification('Failed to get trade details. Please try again.', 'error');
        });
}

/**
 * Show modify trade modal
 */
function showModifyTradeModal(trade) {
    // Check if modal already exists
    let modifyModal = document.getElementById('modify-trade-modal');
    
    if (!modifyModal) {
        // Create modal if it doesn't exist
        const modalHtml = `
            <div class="modal fade" id="modify-trade-modal" tabindex="-1" aria-labelledby="modify-trade-modal-label" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="modify-trade-modal-label">Modify Trade</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="modify-trade-form">
                                <input type="hidden" id="modify-trade-id">
                                <div class="mb-3">
                                    <label for="modify-stop-loss" class="form-label">Stop Loss</label>
                                    <input type="number" class="form-control" id="modify-stop-loss" step="0.00001">
                                    <div class="form-text">Leave empty to remove stop loss</div>
                                </div>
                                <div class="mb-3">
                                    <label for="modify-take-profit" class="form-label">Take Profit</label>
                                    <input type="number" class="form-control" id="modify-take-profit" step="0.00001">
                                    <div class="form-text">Leave empty to remove take profit</div>
                                </div>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="modify-trailing-stop-enabled">
                                        <label class="form-check-label" for="modify-trailing-stop-enabled">
                                            Enable Trailing Stop
                                        </label>
                                    </div>
                                </div>
                                <div class="mb-3" id="trailing-stop-container" style="display: none;">
                                    <label for="modify-trailing-stop" class="form-label">Trailing Stop (pips)</label>
                                    <input type="number" class="form-control" id="modify-trailing-stop" value="10" min="1" step="1">
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="save-modify-trade-btn">Save Changes</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Append modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        modifyModal = document.getElementById('modify-trade-modal');
        
        // Set up trailing stop checkbox event
        document.getElementById('modify-trailing-stop-enabled').addEventListener('change', function() {
            document.getElementById('trailing-stop-container').style.display = this.checked ? 'block' : 'none';
        });
        
        // Set up save button event
        document.getElementById('save-modify-trade-btn').addEventListener('click', function() {
            saveTradeModifications();
        });
    }
    
    // Set form values
    document.getElementById('modify-trade-id').value = trade.id;
    document.getElementById('modify-stop-loss').value = trade.stop_loss || '';
    document.getElementById('modify-take-profit').value = trade.take_profit || '';
    
    // Set trailing stop values
    const trailingStopEnabled = trade.trailing_stop && trade.trailing_stop > 0;
    document.getElementById('modify-trailing-stop-enabled').checked = trailingStopEnabled;
    document.getElementById('trailing-stop-container').style.display = trailingStopEnabled ? 'block' : 'none';
    document.getElementById('modify-trailing-stop').value = trade.trailing_stop || 10;
    
    // Show modal
    const bsModal = new bootstrap.Modal(modifyModal);
    bsModal.show();
}

/**
 * Save trade modifications
 */
function saveTradeModifications() {
    const tradeId = document.getElementById('modify-trade-id').value;
    const stopLoss = document.getElementById('modify-stop-loss').value;
    const takeProfit = document.getElementById('modify-take-profit').value;
    const trailingStopEnabled = document.getElementById('modify-trailing-stop-enabled').checked;
    const trailingStop = trailingStopEnabled ? parseInt(document.getElementById('modify-trailing-stop').value) : 0;
    
    const modifications = {
        stop_loss: stopLoss === '' ? null : parseFloat(stopLoss),
        take_profit: takeProfit === '' ? null : parseFloat(takeProfit),
        trailing_stop: trailingStop
    };
    
    fetch(`/api/trades/modify/${tradeId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(modifications)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Trade modified successfully', 'success');
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('modify-trade-modal')).hide();
            // Refresh open positions
            loadOpenPositions();
        } else {
            showNotification('Failed to modify trade: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error modifying trade:', error);
        showNotification('Failed to modify trade. Please try again.', 'error');
    });
}

/**
 * View trade chart
 */
function viewTradeChart(tradeId) {
    // Redirect to charts page with trade highlighted
    window.location.href = `/charts?highlight_trade=${tradeId}`;
}

/**
 * Format date and time
 */
function formatDateTime(date) {
    return new Date(date).toLocaleString();
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
        return `${days}d ${hours % 24}h ${minutes % 60}m`;
    } else if (hours > 0) {
        return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    } else {
        return `${seconds}s`;
    }
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
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