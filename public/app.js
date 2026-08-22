// ThetaEdge - Frontend JavaScript
const VALID_USERNAME = 'netto.ai1977';
const VALID_PASSWORD = '680204';
let payoffChart = null;

// Authentication
if (sessionStorage.getItem('authenticated') === 'true') showDashboard();

document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorMsg = document.getElementById('errorMsg');
    
    if (username === VALID_USERNAME && password === VALID_PASSWORD) {
        sessionStorage.setItem('authenticated', 'true');
        sessionStorage.setItem('username', username);
        showDashboard();
    } else {
        errorMsg.textContent = 'Invalid credentials';
        errorMsg.classList.remove('hidden');
        document.getElementById('password').value = '';
    }
});

function showDashboard() {
    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
}

function logout() {
    sessionStorage.removeItem('authenticated');
    sessionStorage.removeItem('username');
    location.reload();
}

function showTab(tab) {
    document.getElementById('calculatorTab').classList.add('hidden');
    document.getElementById('strategiesTab').classList.add('hidden');
    document.getElementById(tab + 'Tab').classList.remove('hidden');
}

// Black-Scholes calculations (client-side)
function normalCDF(x) {
    const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741;
    const a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
    const sign = x < 0 ? -1 : 1;
    x = Math.abs(x) / Math.sqrt(2);
    const t = 1.0 / (1.0 + p * x);
    const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return 0.5 * (1.0 + sign * y);
}

function normalPDF(x) {
    return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

function blackScholes(S, K, T, r, sigma, type = 'call') {
    if (T <= 0) return type === 'call' ? Math.max(S - K, 0) : Math.max(K - S, 0);
    const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
    const d2 = d1 - sigma * Math.sqrt(T);
    if (type === 'call') {
        return S * normalCDF(d1) - K * Math.exp(-r * T) * normalCDF(d2);
    } else {
        return K * Math.exp(-r * T) * normalCDF(-d2) - S * normalCDF(-d1);
    }
}

function calculateGreeks(S, K, T, r, sigma, type = 'call') {
    if (T <= 0) return { delta: 0, gamma: 0, theta: 0, vega: 0 };
    const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
    const d2 = d1 - sigma * Math.sqrt(T);
    const delta = type === 'call' ? normalCDF(d1) : normalCDF(d1) - 1;
    const gamma = normalPDF(d1) / (S * sigma * Math.sqrt(T));
    const theta = (-(S * normalPDF(d1) * sigma) / (2 * Math.sqrt(T)) - r * K * Math.exp(-r * T) * (type === 'call' ? normalCDF(d2) : normalCDF(-d2))) / 365;
    const vega = S * normalPDF(d1) * Math.sqrt(T) / 100;
    return { delta: +delta.toFixed(4), gamma: +gamma.toFixed(4), theta: +theta.toFixed(4), vega: +vega.toFixed(4) };
}

// Strategy calculations
function calculateDoubleCalendar(S, putK, callK, shortDays, longDays, iv) {
    const r = 0.05, sigma = iv / 100;
    const Tshort = shortDays / 365, Tlong = longDays / 365;
    
    const shortPut = blackScholes(S, putK, Tshort, r, sigma, 'put');
    const longPut = blackScholes(S, putK, Tlong, r, sigma, 'put');
    const shortCall = blackScholes(S, callK, Tshort, r, sigma, 'call');
    const longCall = blackScholes(S, callK, Tlong, r, sigma, 'call');
    
    const netDebit = (longPut - shortPut) + (longCall - shortCall);
    
    const prices = [], payoffs = [];
    for (let p = S * 0.7; p <= S * 1.3; p += S * 0.01) {
        const shortPutPay = Math.max(putK - p, 0);
        const longPutPay = blackScholes(p, putK, Tlong - Tshort > 0 ? Tlong - Tshort : 0.001, r, sigma, 'put');
        const shortCallPay = Math.max(p - callK, 0);
        const longCallPay = blackScholes(p, callK, Tlong - Tshort > 0 ? Tlong - Tshort : 0.001, r, sigma, 'call');
        const pnl = (longPutPay - shortPutPay) + (longCallPay - shortCallPay) - netDebit;
        prices.push(+p.toFixed(2));
        payoffs.push(+pnl.toFixed(2));
    }
    
    const netGreeks = {
        ...calculateGreeks(S, putK, Tlong, r, sigma, 'put'),
        ...calculateGreeks(S, callK, Tlong, r, sigma, 'call')
    };
    
    return {
        name: 'Double Calendar',
        netDebit: +netDebit.toFixed(2),
        maxProfit: Math.max(...payoffs).toFixed(2),
        maxLoss: netDebit.toFixed(2),
        legs: [
            { type: 'put', strike: putK, qty: -1, premium: shortPut.toFixed(2), days: shortDays },
            { type: 'put', strike: putK, qty: 1, premium: longPut.toFixed(2), days: longDays },
            { type: 'call', strike: callK, qty: -1, premium: shortCall.toFixed(2), days: shortDays },
            { type: 'call', strike: callK, qty: 1, premium: longCall.toFixed(2), days: longDays }
        ],
        prices, payoffs
    };
}

function calculateCalendarSpread(S, K, shortDays, longDays, iv, type = 'call') {
    const r = 0.05, sigma = iv / 100;
    const Tshort = shortDays / 365, Tlong = longDays / 365;
    
    const shortPrice = blackScholes(S, K, Tshort, r, sigma, type);
    const longPrice = blackScholes(S, K, Tlong, r, sigma, type);
    const netDebit = longPrice - shortPrice;
    
    const prices = [], payoffs = [];
    for (let p = S * 0.7; p <= S * 1.3; p += S * 0.01) {
        const shortPay = type === 'call' ? Math.max(p - K, 0) : Math.max(K - p, 0);
        const longPay = blackScholes(p, K, Tlong - Tshort > 0 ? Tlong - Tshort : 0.001, r, sigma, type);
        const pnl = longPay - shortPay - netDebit;
        prices.push(+p.toFixed(2));
        payoffs.push(+pnl.toFixed(2));
    }
    
    return {
        name: `Calendar ${type.toUpperCase()}`,
        netDebit: +netDebit.toFixed(2),
        maxProfit: Math.max(...payoffs).toFixed(2),
        maxLoss: netDebit.toFixed(2),
        legs: [
            { type, strike: K, qty: -1, premium: shortPrice.toFixed(2), days: shortDays },
            { type, strike: K, qty: 1, premium: longPrice.toFixed(2), days: longDays }
        ],
        prices, payoffs
    };
}

// Main calculation function
function calculateStrategy() {
    const S = +document.getElementById('stockPrice').value;
    const putK = +document.getElementById('putStrike').value;
    const callK = +document.getElementById('callStrike').value;
    const shortDays = +document.getElementById('shortDays').value;
    const longDays = +document.getElementById('longDays').value;
    const iv = +document.getElementById('iv').value;
    const strategy = document.getElementById('strategyType').value;
    
    let result;
    if (strategy === 'double_calendar') {
        result = calculateDoubleCalendar(S, putK, callK, shortDays, longDays, iv);
    } else if (strategy === 'calendar_call') {
        result = calculateCalendarSpread(S, callK, shortDays, longDays, iv, 'call');
    } else {
        result = calculateCalendarSpread(S, putK, shortDays, longDays, iv, 'put');
    }
    
    // Display results
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `
        <div class="grid grid-cols-2 gap-4 mb-4">
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Net Debit</p>
                <p class="text-white font-semibold">$${result.netDebit}</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Max Profit</p>
                <p class="text-green-400 font-semibold">$${result.maxProfit}</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Max Loss</p>
                <p class="text-red-400 font-semibold">$${result.maxLoss}</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Risk/Reward</p>
                <p class="text-cyan-400 font-semibold">1:${(result.maxProfit / result.netDebit).toFixed(1)}</p>
            </div>
        </div>
        <h4 class="text-sm font-semibold text-white mb-2">Position Legs</h4>
        <div class="space-y-2">
            ${result.legs.map(l => `
                <div class="bg-slate-900/50 rounded-lg p-2 flex justify-between text-sm">
                    <span class="text-slate-400">${l.qty > 0 ? 'Buy' : 'Sell'} ${l.type.toUpperCase()}</span>
                    <span class="text-white">K=$${l.strike} | $${l.premium} | ${l.days}D</span>
                </div>
            `).join('')}
        </div>
    `;
    
    // Update chart
    updateChart(result.prices, result.payoffs, S);
}

function updateChart(prices, payoffs, currentPrice) {
    const ctx = document.getElementById('payoffChart').getContext('2d');
    if (payoffChart) payoffChart.destroy();
    
    const profitColors = payoffs.map(v => v >= 0 ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)');
    
    payoffChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: prices,
            datasets: [{
                label: 'P&L',
                data: payoffs,
                borderColor: payoffs.map(v => v >= 0 ? '#22C55E' : '#EF4444'),
                backgroundColor: 'transparent',
                pointRadius: 0,
                borderWidth: 2,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => `Price: $${items[0].label}`,
                        label: (item) => `P&L: $${item.raw.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Stock Price', color: '#94A3B8' },
                    ticks: { color: '#94A3B8', maxTicksLimit: 10 },
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                },
                y: {
                    title: { display: true, text: 'Profit/Loss ($)', color: '#94A3B8' },
                    ticks: { color: '#94A3B8' },
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                }
            }
        }
    });
}

// Backtesting functions
let equityChart = null;

function runBacktest() {
    const ticker = document.getElementById('btTicker').value;
    const capital = +document.getElementById('btCapital').value;
    const startDate = document.getElementById('btStart').value;
    const endDate = document.getElementById('btEnd').value;
    const iv = +document.getElementById('btIV').value / 100;
    const tp = +document.getElementById('btTP').value / 100;
    
    // Generate synthetic backtest data
    const trades = generateBacktestTrades(ticker, startDate, endDate, capital, iv, tp);
    const stats = calculateBacktestStats(trades, capital);
    
    // Display results
    const resultsDiv = document.getElementById('btResults');
    resultsDiv.innerHTML = `
        <div class="grid grid-cols-2 gap-4 mb-4">
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Total Trades</p>
                <p class="text-white font-semibold">${stats.totalTrades}</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Win Rate</p>
                <p class="text-green-400 font-semibold">${stats.winRate}%</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Total P&L</p>
                <p class="${stats.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'} font-semibold">$${stats.totalPnl.toLocaleString()}</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Profit Factor</p>
                <p class="text-cyan-400 font-semibold">${stats.profitFactor}</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Avg Win</p>
                <p class="text-green-400 font-semibold">$${stats.avgWin.toLocaleString()}</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Avg Loss</p>
                <p class="text-red-400 font-semibold">$${stats.avgLoss.toLocaleString()}</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Max Drawdown</p>
                <p class="text-yellow-400 font-semibold">${stats.maxDrawdown}%</p>
            </div>
            <div class="bg-slate-900/50 rounded-lg p-3">
                <p class="text-slate-400 text-xs">Sharpe Ratio</p>
                <p class="text-cyan-400 font-semibold">${stats.sharpeRatio}</p>
            </div>
        </div>
    `;
    
    // Update equity curve chart
    updateEquityChart(stats.equityCurve);
}

function generateBacktestTrades(ticker, startDate, endDate, capital, iv, takeProfit) {
    const trades = [];
    const start = new Date(startDate);
    const end = new Date(endDate);
    const numWeeks = Math.floor((end - start) / (7 * 24 * 60 * 60 * 1000));
    
    let currentPrice = 480; // Starting price for QQQ
    
    for (let i = 0; i < numWeeks; i++) {
        const entryDate = new Date(start.getTime() + i * 7 * 24 * 60 * 60 * 1000);
        
        // Random price movement
        const priceChange = (Math.random() - 0.5) * 0.1;
        currentPrice *= (1 + priceChange);
        
        // Random trade outcome
        const isWin = Math.random() < 0.75; // 75% win rate
        const pnlPct = isWin ? 
            Math.random() * takeProfit * 100 : 
            -(Math.random() * 30 + 5);
        
        const tradeAmount = capital * 0.02; // 2% risk per trade
        const pnl = tradeAmount * (pnlPct / 100);
        
        trades.push({
            date: entryDate.toISOString().split('T')[0],
            price: currentPrice,
            pnl: pnl,
            pnlPct: pnlPct,
            isWin: isWin
        });
    }
    
    return trades;
}

function calculateBacktestStats(trades, initialCapital) {
    let equity = initialCapital;
    let peak = initialCapital;
    let maxDrawdown = 0;
    const equityCurve = [initialCapital];
    
    const wins = trades.filter(t => t.isWin);
    const losses = trades.filter(t => !t.isWin);
    
    let totalPnl = 0;
    trades.forEach(t => {
        equity += t.pnl;
        totalPnl += t.pnl;
        equityCurve.push(equity);
        
        if (equity > peak) peak = equity;
        const dd = ((peak - equity) / peak) * 100;
        if (dd > maxDrawdown) maxDrawdown = dd;
    });
    
    const avgWin = wins.length > 0 ? wins.reduce((a, b) => a + b.pnl, 0) / wins.length : 0;
    const avgLoss = losses.length > 0 ? Math.abs(losses.reduce((a, b) => a + b.pnl, 0) / losses.length) : 0;
    const profitFactor = avgLoss > 0 ? (avgWin * wins.length) / (avgLoss * losses.length) : 999;
    
    // Sharpe ratio approximation
    const returns = trades.map(t => t.pnlPct / 100);
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const stdReturn = Math.sqrt(returns.reduce((a, b) => a + Math.pow(b - avgReturn, 2), 0) / returns.length);
    const sharpeRatio = stdReturn > 0 ? (avgReturn / stdReturn) * Math.sqrt(52) : 0;
    
    return {
        totalTrades: trades.length,
        winRate: ((wins.length / trades.length) * 100).toFixed(1),
        totalPnl: Math.round(totalPnl),
        avgWin: Math.round(avgWin),
        avgLoss: Math.round(avgLoss),
        maxDrawdown: maxDrawdown.toFixed(1),
        profitFactor: profitFactor.toFixed(2),
        sharpeRatio: sharpeRatio.toFixed(2),
        equityCurve: equityCurve
    };
}

function updateEquityChart(equityCurve) {
    const ctx = document.getElementById('equityChart').getContext('2d');
    if (equityChart) equityChart.destroy();
    
    const labels = equityCurve.map((_, i) => `Trade ${i}`);
    
    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Equity',
                data: equityCurve,
                borderColor: '#06B6D4',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                fill: true,
                pointRadius: 0,
                borderWidth: 2,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (item) => `Equity: $${item.raw.toLocaleString()}`
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Trades', color: '#94A3B8' },
                    ticks: { color: '#94A3B8', maxTicksLimit: 10 },
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                },
                y: {
                    title: { display: true, text: 'Equity ($)', color: '#94A3B8' },
                    ticks: { color: '#94A3B8' },
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                }
            }
        }
    });
}

// Trade Tracker functions
let trades = [];

function addTrade() {
    const ticker = document.getElementById('tradeTicker').value;
    const strategy = document.getElementById('tradeStrategy').value;
    const debit = +document.getElementById('tradeDebit').value;
    const contracts = +document.getElementById('tradeContracts').value;
    
    if (!debit || debit <= 0) {
        alert('Please enter a valid net debit');
        return;
    }
    
    const trade = {
        id: 'T' + Date.now(),
        entry_date: new Date().toISOString(),
        ticker: ticker,
        strategy: strategy,
        net_debit: debit,
        contracts: contracts,
        status: 'open',
        pnl: null,
        pnl_pct: null
    };
    
    trades.push(trade);
    saveTrades();
    updateTrackerUI();
    
    // Clear form
    document.getElementById('tradeDebit').value = '';
    document.getElementById('tradeContracts').value = '1';
}

function closeTrade(tradeId, exitPrice) {
    const trade = trades.find(t => t.id === tradeId);
    if (trade) {
        trade.status = 'closed';
        trade.exit_date = new Date().toISOString();
        trade.exit_price = exitPrice;
        trade.pnl = (exitPrice - trade.net_debit) * trade.contracts * 100;
        trade.pnl_pct = ((exitPrice - trade.net_debit) / trade.net_debit) * 100;
        
        saveTrades();
        updateTrackerUI();
    }
}

function deleteTrade(tradeId) {
    trades = trades.filter(t => t.id !== tradeId);
    saveTrades();
    updateTrackerUI();
}

function saveTrades() {
    localStorage.setItem('thetaedge_trades', JSON.stringify(trades));
}

function loadTrades() {
    const saved = localStorage.getItem('thetaedge_trades');
    if (saved) {
        trades = JSON.parse(saved);
    }
    updateTrackerUI();
}

function updateTrackerUI() {
    const openTrades = trades.filter(t => t.status === 'open');
    const closedTrades = trades.filter(t => t.status === 'closed');
    
    // Update summary
    document.getElementById('totalTrades').textContent = trades.length;
    document.getElementById('openPositions').textContent = openTrades.length;
    
    if (closedTrades.length > 0) {
        const wins = closedTrades.filter(t => t.pnl > 0).length;
        const winRate = ((wins / closedTrades.length) * 100).toFixed(1);
        const totalPnl = closedTrades.reduce((a, b) => a + (b.pnl || 0), 0);
        
        document.getElementById('winRate').textContent = winRate + '%';
        document.getElementById('totalPnl').textContent = '$' + Math.round(totalPnl).toLocaleString();
    }
    
    // Render open trades
    const openDiv = document.getElementById('openTrades');
    if (openTrades.length === 0) {
        openDiv.innerHTML = '<p class="text-slate-400 text-center">No open trades</p>';
    } else {
        openDiv.innerHTML = openTrades.map(t => `
            <div class="bg-slate-900/50 rounded-lg p-4 flex justify-between items-center">
                <div>
                    <span class="text-white font-semibold">${t.ticker}</span>
                    <span class="text-slate-400 ml-2">${t.strategy}</span>
                    <span class="text-cyan-400 ml-2">$${t.net_debit} x${t.contracts}</span>
                </div>
                <div class="flex space-x-2">
                    <input type="number" id="exit_${t.id}" placeholder="Exit price" class="w-24 px-2 py-1 bg-slate-800 border border-slate-600 rounded text-white text-sm">
                    <button onclick="closeTrade('${t.id}', +document.getElementById('exit_${t.id}').value)" class="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-sm">Close</button>
                    <button onclick="deleteTrade('${t.id}')" class="px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-sm">Delete</button>
                </div>
            </div>
        `).join('');
    }
    
    // Render closed trades
    const historyDiv = document.getElementById('tradeHistory');
    if (closedTrades.length === 0) {
        historyDiv.innerHTML = '<p class="text-slate-400 text-center">No closed trades</p>';
    } else {
        historyDiv.innerHTML = closedTrades.map(t => `
            <div class="bg-slate-900/50 rounded-lg p-4 flex justify-between items-center">
                <div>
                    <span class="text-white font-semibold">${t.ticker}</span>
                    <span class="text-slate-400 ml-2">${t.strategy}</span>
                    <span class="text-slate-400 ml-2">$${t.net_debit} → $${t.exit_price}</span>
                </div>
                <div class="text-right">
                    <span class="${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'} font-semibold">
                        ${t.pnl >= 0 ? '+' : ''}$${Math.round(t.pnl)} (${t.pnl_pct >= 0 ? '+' : ''}${t.pnl_pct.toFixed(1)}%)
                    </span>
                </div>
            </div>
        `).join('');
    }
}

// Initialize tracker on load
loadTrades();

// VIX Monitor functions
let vixChart = null;

function updateVIXMonitor() {
    // Simulated VIX data
    const currentVIX = 18.5 + (Math.random() - 0.5) * 4;
    const avg7d = 17.8;
    const avg30d = 19.2;
    const min30d = 14.5;
    const max30d = 24.8;
    
    // Update display
    document.getElementById('vixValue').textContent = currentVIX.toFixed(1);
    document.getElementById('vixAvg7d').textContent = avg7d.toFixed(1);
    document.getElementById('vixAvg30d').textContent = avg30d.toFixed(1);
    document.getElementById('vixMin30d').textContent = min30d.toFixed(1);
    document.getElementById('vixMax30d').textContent = max30d.toFixed(1);
    
    // Determine signal
    let signal, signalColor, interpretation;
    if (currentVIX < 15) {
        signal = 'ENTER';
        signalColor = 'text-green-400';
        interpretation = 'Low - Good for selling premium';
    } else if (currentVIX < 20) {
        signal = 'HOLD';
        signalColor = 'text-yellow-400';
        interpretation = 'Normal - Acceptable conditions';
    } else if (currentVIX < 25) {
        signal = 'CAUTION';
        signalColor = 'text-orange-400';
        interpretation = 'High - Wait for better entry';
    } else {
        signal = 'WAIT';
        signalColor = 'text-red-400';
        interpretation = 'Very High - Avoid new positions';
    }
    
    document.getElementById('vixInterpretation').textContent = interpretation;
    document.getElementById('vixSignal').innerHTML = `
        <p class="text-slate-400 text-sm">Signal</p>
        <p class="text-2xl font-bold ${signalColor}">${signal}</p>
    `;
    
    // Update entry signal card
    const entrySignal = document.getElementById('entrySignal');
    const signalStrategies = document.getElementById('signalStrategies');
    
    if (currentVIX < 15) {
        entrySignal.innerHTML = `
            <div class="w-4 h-4 rounded-full bg-green-400"></div>
            <span class="text-white font-semibold">ENTER</span>
            <span class="text-green-400">- Excellent entry for Double Calendar</span>
        `;
        signalStrategies.innerHTML = 'Recommended: <span class="text-green-400">Double Calendar</span>, <span class="text-green-400">Time Spread</span>';
    } else if (currentVIX < 20) {
        entrySignal.innerHTML = `
            <div class="w-4 h-4 rounded-full bg-yellow-400"></div>
            <span class="text-white font-semibold">HOLD</span>
            <span class="text-yellow-400">- Normal conditions, selective entries</span>
        `;
        signalStrategies.innerHTML = 'Recommended: <span class="text-yellow-400">Time Spread</span>';
    } else {
        entrySignal.innerHTML = `
            <div class="w-4 h-4 rounded-full bg-red-400"></div>
            <span class="text-white font-semibold">WAIT</span>
            <span class="text-red-400">- High volatility, wait for better entry</span>
        `;
        signalStrategies.innerHTML = 'Consider: <span class="text-orange-400">Double Diagonal</span> (lower Vega risk)';
    }
    
    // Update VIX chart
    updateVIXChart();
}

function updateVIXChart() {
    const ctx = document.getElementById('vixChart').getContext('2d');
    if (vixChart) vixChart.destroy();
    
    // Generate synthetic VIX history
    const labels = [];
    const data = [];
    const now = new Date();
    
    for (let i = 29; i >= 0; i--) {
        const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        data.push(18 + Math.random() * 6 - 3);
    }
    
    vixChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'VIX',
                data: data,
                borderColor: '#F59E0B',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                fill: true,
                pointRadius: 0,
                borderWidth: 2,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (item) => `VIX: ${item.raw.toFixed(1)}`
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#94A3B8', maxTicksLimit: 10 },
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                },
                y: {
                    title: { display: true, text: 'VIX', color: '#94A3B8' },
                    ticks: { color: '#94A3B8' },
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                }
            }
        }
    });
}

// Initialize VIX monitor
updateVIXMonitor();
