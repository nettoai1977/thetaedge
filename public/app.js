// ThetaEdge - Mobile-First App
const VALID_USERNAME = 'netto.ai1977';
const VALID_PASSWORD = '680204';
let payoffChart = null;
let currentStrategy = 'double_calendar';

// ============ Authentication ============
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
        // Haptic feedback
        if (navigator.vibrate) navigator.vibrate(50);
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

// ============ Navigation ============
function showTab(tab) {
    // Hide all tabs
    ['calculator', 'scan', 'calendar', 'backtest', 'tracker', 'vix'].forEach(t => {
        document.getElementById(t + 'Tab').classList.add('hidden');
    });
    
    // Show selected tab
    document.getElementById(tab + 'Tab').classList.remove('hidden');
    
    // Update nav
    document.querySelectorAll('.bottom-nav-item').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById('nav-' + tab).classList.add('active');
    
    // Haptic feedback
    if (navigator.vibrate) navigator.vibrate(10);
    
    // Load data if needed
    if (tab === 'calendar') {
        loadCalendarData();
    } else if (tab === 'scan') {
        loadTickerScan();
    }
}

function selectStrategy(strat) {
    currentStrategy = strat;
    ['dc', 'cc', 'cp'].forEach(s => {
        const btn = document.getElementById('strat-' + s);
        if (strat === 'double_calendar' && s === 'dc') {
            btn.className = 'h-12 rounded-xl text-sm font-medium bg-cyan-500/20 text-cyan-400 border border-cyan-500/50';
        } else if (strat === 'calendar_call' && s === 'cc') {
            btn.className = 'h-12 rounded-xl text-sm font-medium bg-cyan-500/20 text-cyan-400 border border-cyan-500/50';
        } else if (strat === 'calendar_put' && s === 'cp') {
            btn.className = 'h-12 rounded-xl text-sm font-medium bg-cyan-500/20 text-cyan-400 border border-cyan-500/50';
        } else {
            btn.className = 'h-12 rounded-xl text-sm font-medium bg-slate-700/50 text-slate-400 border border-slate-600';
        }
    });
}

// ============ IV Slider ============
const ivSlider = document.getElementById('ivSlider');
const ivDisplay = document.getElementById('ivDisplay');
ivSlider.addEventListener('input', (e) => {
    ivDisplay.textContent = e.target.value + '%';
});

// ============ Black-Scholes Engine ============
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
    return type === 'call' 
        ? S * normalCDF(d1) - K * Math.exp(-r * T) * normalCDF(d2)
        : K * Math.exp(-r * T) * normalCDF(-d2) - S * normalCDF(-d1);
}

// ============ Strategy Calculations ============
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
    
    return {
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

// ============ Calculate Button ============
function calculateStrategy() {
    const S = +document.getElementById('stockPrice').value;
    const putK = +document.getElementById('putStrike').value;
    const callK = +document.getElementById('callStrike').value;
    const shortDays = +document.getElementById('shortDays').value;
    const longDays = +document.getElementById('longDays').value;
    const iv = +document.getElementById('ivSlider').value;
    
    let result;
    if (currentStrategy === 'double_calendar') {
        result = calculateDoubleCalendar(S, putK, callK, shortDays, longDays, iv);
    } else if (currentStrategy === 'calendar_call') {
        result = calculateCalendarSpread(S, callK, shortDays, longDays, iv, 'call');
    } else {
        result = calculateCalendarSpread(S, putK, shortDays, longDays, iv, 'put');
    }
    
    // Update results
    document.getElementById('resultDebit').textContent = '$' + result.netDebit;
    document.getElementById('resultProfit').textContent = '$' + result.maxProfit;
    document.getElementById('resultLoss').textContent = '$' + result.maxLoss;
    document.getElementById('resultRR').textContent = '1:' + (result.maxProfit / result.netDebit).toFixed(1);
    
    // Update legs
    const legsList = document.getElementById('legsList');
    legsList.innerHTML = result.legs.map(l => `
        <div class="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
            <div class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full ${l.qty > 0 ? 'bg-green-400' : 'bg-red-400'}"></span>
                <span class="text-sm text-white">${l.qty > 0 ? 'Buy' : 'Sell'} ${l.type.toUpperCase()}</span>
            </div>
            <span class="text-sm text-slate-400">K=$${l.strike} | $${l.premium}</span>
        </div>
    `).join('');
    
    // Show results
    document.getElementById('resultsSection').classList.remove('hidden');
    
    // Update chart
    updateChart(result.prices, result.payoffs);
    
    // Haptic feedback
    if (navigator.vibrate) navigator.vibrate([10, 50, 10]);
}

// ============ Charts ============
function updateChart(prices, payoffs) {
    const ctx = document.getElementById('payoffChart').getContext('2d');
    if (payoffChart) payoffChart.destroy();
    
    payoffChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: prices,
            datasets: [{
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
            plugins: { legend: { display: false } },
            scales: {
                x: { 
                    display: true,
                    ticks: { color: '#64748B', maxTicksLimit: 5, font: { size: 10 } },
                    grid: { display: false }
                },
                y: { 
                    display: true,
                    ticks: { color: '#64748B', maxTicksLimit: 5, font: { size: 10 } },
                    grid: { color: 'rgba(100, 116, 139, 0.1)' }
                }
            }
        }
    });
}

// ============ Backtest ============
let equityChart = null;

function runBacktest() {
    const ticker = document.getElementById('btTicker').value;
    const capital = +document.getElementById('btCapital').value;
    const startDate = document.getElementById('btStart').value;
    const endDate = document.getElementById('btEnd').value;
    
    // Generate synthetic data
    const trades = generateBacktestTrades(startDate, endDate, capital);
    const stats = calculateBacktestStats(trades, capital);
    
    const resultsDiv = document.getElementById('btResults');
    resultsDiv.innerHTML = `
        <div class="mobile-card">
            <div class="grid grid-cols-2 gap-3 mb-4">
                <div class="text-center">
                    <p class="text-xs text-slate-400">Trades</p>
                    <p class="text-xl font-bold text-white">${stats.totalTrades}</p>
                </div>
                <div class="text-center">
                    <p class="text-xs text-slate-400">Win Rate</p>
                    <p class="text-xl font-bold text-green-400">${stats.winRate}%</p>
                </div>
                <div class="text-center">
                    <p class="text-xs text-slate-400">Total P&L</p>
                    <p class="text-xl font-bold ${stats.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}">$${stats.totalPnl.toLocaleString()}</p>
                </div>
                <div class="text-center">
                    <p class="text-xs text-slate-400">Sharpe</p>
                    <p class="text-xl font-bold text-cyan-400">${stats.sharpeRatio}</p>
                </div>
            </div>
            <div style="height: 180px;">
                <canvas id="equityChart"></canvas>
            </div>
        </div>
    `;
    
    updateEquityChart(stats.equityCurve);
}

function generateBacktestTrades(startDate, endDate, capital) {
    const trades = [];
    const start = new Date(startDate);
    const end = new Date(endDate);
    const numWeeks = Math.floor((end - start) / (7 * 24 * 60 * 60 * 1000));
    
    let currentPrice = 480;
    for (let i = 0; i < numWeeks; i++) {
        const entryDate = new Date(start.getTime() + i * 7 * 24 * 60 * 60 * 1000);
        const priceChange = (Math.random() - 0.5) * 0.1;
        currentPrice *= (1 + priceChange);
        const isWin = Math.random() < 0.75;
        const pnlPct = isWin ? Math.random() * 30 : -(Math.random() * 30 + 5);
        const tradeAmount = capital * 0.02;
        const pnl = tradeAmount * (pnlPct / 100);
        
        trades.push({ date: entryDate.toISOString().split('T')[0], pnl, isWin });
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
    const returns = trades.map(t => t.pnl / initialCapital);
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
        equityCurve
    };
}

function updateEquityChart(equityCurve) {
    const ctx = document.getElementById('equityChart').getContext('2d');
    if (equityChart) equityChart.destroy();
    
    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: equityCurve.map((_, i) => i),
            datasets: [{
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
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { 
                    display: true,
                    ticks: { color: '#64748B', maxTicksLimit: 4, font: { size: 10 } },
                    grid: { color: 'rgba(100, 116, 139, 0.1)' }
                }
            }
        }
    });
}

// ============ Trade Tracker ============
let trades = [];

function addTrade() {
    const ticker = document.getElementById('tradeTicker').value;
    const debit = +document.getElementById('tradeDebit').value;
    if (!debit || debit <= 0) return;
    
    trades.push({
        id: 'T' + Date.now(),
        ticker,
        strategy: 'Double Calendar',
        net_debit: debit,
        status: 'open',
        entry_date: new Date().toISOString()
    });
    
    saveTrades();
    updateTrackerUI();
    document.getElementById('tradeDebit').value = '';
    if (navigator.vibrate) navigator.vibrate(10);
}

function closeTrade(tradeId, exitPrice) {
    const trade = trades.find(t => t.id === tradeId);
    if (trade) {
        trade.status = 'closed';
        trade.exit_price = exitPrice;
        trade.pnl = (exitPrice - trade.net_debit) * 100;
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
    if (saved) trades = JSON.parse(saved);
    updateTrackerUI();
}

function updateTrackerUI() {
    const openTrades = trades.filter(t => t.status === 'open');
    const closedTrades = trades.filter(t => t.status === 'closed');
    
    document.getElementById('totalTrades').textContent = trades.length;
    document.getElementById('openPositions').textContent = openTrades.length;
    
    if (closedTrades.length > 0) {
        const wins = closedTrades.filter(t => t.pnl > 0).length;
        document.getElementById('winRate').textContent = ((wins / closedTrades.length) * 100).toFixed(1) + '%';
        const totalPnl = closedTrades.reduce((a, b) => a + (b.pnl || 0), 0);
        document.getElementById('totalPnl').textContent = '$' + Math.round(totalPnl).toLocaleString();
    }
    
    document.getElementById('openTrades').innerHTML = openTrades.length === 0 
        ? '<p class="text-slate-400 text-sm text-center">No open trades</p>'
        : openTrades.map(t => `
            <div class="flex items-center justify-between py-3 border-b border-slate-700/50">
                <div>
                    <span class="text-white font-medium">${t.ticker}</span>
                    <span class="text-cyan-400 ml-2">$${t.net_debit}</span>
                </div>
                <div class="flex items-center space-x-2">
                    <input type="number" id="exit_${t.id}" placeholder="Exit" class="w-20 h-8 bg-slate-900/50 border border-slate-600 rounded text-white text-sm px-2">
                    <button onclick="closeTrade('${t.id}', +document.getElementById('exit_${t.id}').value)" class="h-8 px-3 bg-green-600 rounded text-sm text-white">Close</button>
                </div>
            </div>
        `).join('');
    
    document.getElementById('tradeHistory').innerHTML = closedTrades.length === 0
        ? '<p class="text-slate-400 text-sm text-center">No closed trades</p>'
        : closedTrades.map(t => `
            <div class="flex items-center justify-between py-3 border-b border-slate-700/50">
                <span class="text-white">${t.ticker}</span>
                <span class="${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'} font-medium">
                    ${t.pnl >= 0 ? '+' : ''}$${Math.round(t.pnl)}
                </span>
            </div>
        `).join('');
}

// ============ VIX Monitor ============
let vixChart = null;

function updateVIXMonitor() {
    const currentVIX = 18.5 + (Math.random() - 0.5) * 4;
    document.getElementById('vixValue').textContent = currentVIX.toFixed(1);
    document.getElementById('vixAvg7d').textContent = '17.8';
    document.getElementById('vixAvg30d').textContent = '19.2';
    document.getElementById('vixMin30d').textContent = '14.5';
    document.getElementById('vixMax30d').textContent = '24.8';
    
    let signal, color, interpretation;
    if (currentVIX < 15) {
        signal = 'ENTER'; color = 'text-green-400'; interpretation = 'Excellent for selling';
    } else if (currentVIX < 20) {
        signal = 'HOLD'; color = 'text-yellow-400'; interpretation = 'Acceptable conditions';
    } else if (currentVIX < 25) {
        signal = 'CAUTION'; color = 'text-orange-400'; interpretation = 'Wait for better entry';
    } else {
        signal = 'WAIT'; color = 'text-red-400'; interpretation = 'Avoid new positions';
    }
    
    document.getElementById('vixInterpretation').textContent = interpretation;
    document.getElementById('entrySignal').innerHTML = `
        <div class="w-3 h-3 rounded-full ${currentVIX < 15 ? 'bg-green-400' : currentVIX < 20 ? 'bg-yellow-400' : 'bg-red-400'}"></div>
        <span class="text-lg font-semibold ${color}">${signal}</span>
    `;
}

// ============ Position Sizing ============
function calculatePosition() {
    const accountSize = +document.getElementById('accountSize').value;
    const riskPct = +document.getElementById('riskPct').value;
    
    // Get current net debit from results
    const debitText = document.getElementById('resultDebit').textContent;
    const netDebit = parseFloat(debitText.replace('$', '')) || 0;
    
    if (netDebit <= 0) {
        alert('Please calculate a strategy first');
        return;
    }
    
    // Calculate position size
    const maxLoss = netDebit * 100; // Options multiplier
    const maxDollarRisk = accountSize * (riskPct / 100);
    const contracts = Math.floor(maxDollarRisk / maxLoss);
    const totalRisk = contracts * maxLoss;
    
    // Display results
    document.getElementById('posContracts').textContent = Math.min(contracts, 10);
    document.getElementById('posRisk').textContent = '$' + totalRisk.toLocaleString();
    
    let recommendation = '';
    if (contracts === 0) {
        recommendation = 'Position too large for account size';
    } else if (contracts >= 5) {
        recommendation = 'Large position - consider splitting entries';
    } else {
        recommendation = 'Position size looks good ✓';
    }
    document.getElementById('posRecommendation').textContent = recommendation;
    
    document.getElementById('positionResult').classList.remove('hidden');
    
    // Haptic feedback
    if (navigator.vibrate) navigator.vibrate(10);
}

// ============ Ticker Scanner ============
function loadTickerScan() {
    const tickers = getTickerData();
    
    // Best tickers (recommended)
    const bestDiv = document.getElementById('bestTickers');
    const bestTickers = tickers.filter(t => t.recommendation === 'buy').slice(0, 5);
    
    if (bestTickers.length === 0) {
        bestDiv.innerHTML = '<p class="text-slate-400 text-sm text-center">No tickers meet criteria</p>';
    } else {
        bestDiv.innerHTML = bestTickers.map(t => `
            <div class="flex items-center justify-between py-3 border-b border-slate-700/50 last:border-0">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                        <span class="text-cyan-400 font-bold text-sm">${t.symbol}</span>
                    </div>
                    <div>
                        <p class="text-white font-medium">${t.name}</p>
                        <p class="text-xs text-slate-400">${t.sector}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-white font-semibold">$${t.price}</p>
                    <p class="text-xs ${t.change_pct >= 0 ? 'text-green-400' : 'text-red-400'}">
                        ${t.change_pct >= 0 ? '+' : ''}${t.change_pct}%
                    </p>
                </div>
            </div>
        `).join('');
    }
    
    // All tickers
    const allDiv = document.getElementById('allTickers');
    allDiv.innerHTML = tickers.map(t => `
        <div class="flex items-center justify-between py-3 border-b border-slate-700/50 last:border-0">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-lg ${t.recommendation === 'buy' ? 'bg-green-500/20' : t.recommendation === 'avoid' ? 'bg-red-500/20' : 'bg-yellow-500/20'} flex items-center justify-center">
                    <span class="${t.recommendation === 'buy' ? 'text-green-400' : t.recommendation === 'avoid' ? 'text-red-400' : 'text-yellow-400'} font-bold text-sm">${t.symbol}</span>
                </div>
                <div>
                    <p class="text-white font-medium">${t.name}</p>
                    <p class="text-xs text-slate-400">IV: ${t.iv_rank}% | Vol: ${(t.volume/1000000).toFixed(1)}M</p>
                </div>
            </div>
            <div class="text-right">
                <p class="text-white font-semibold">$${t.price}</p>
                <span class="text-xs px-2 py-1 rounded ${t.recommendation === 'buy' ? 'bg-green-500/20 text-green-400' : t.recommendation === 'avoid' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}">
                    ${t.recommendation.toUpperCase()}
                </span>
            </div>
        </div>
    `).join('');
}

function getTickerData() {
    // Simulated ticker data
    const tickers = [
        { symbol: 'QQQ', name: 'Invesco QQQ Trust', price: 482.50, change_pct: 0.85, volume: 35000000, iv_rank: 45, sector: 'Technology', recommendation: 'buy' },
        { symbol: 'SPY', name: 'SPDR S&P 500 ETF', price: 551.20, change_pct: 0.42, volume: 55000000, iv_rank: 38, sector: 'Broad Market', recommendation: 'buy' },
        { symbol: 'IWM', name: 'iShares Russell 2000', price: 218.75, change_pct: -0.32, volume: 25000000, iv_rank: 52, sector: 'Small Cap', recommendation: 'buy' },
        { symbol: 'AAPL', name: 'Apple Inc', price: 195.80, change_pct: 1.25, volume: 45000000, iv_rank: 35, sector: 'Technology', recommendation: 'hold' },
        { symbol: 'MSFT', name: 'Microsoft Corp', price: 418.90, change_pct: 0.68, volume: 22000000, iv_rank: 32, sector: 'Technology', recommendation: 'hold' },
        { symbol: 'NVDA', name: 'NVIDIA Corp', price: 122.40, change_pct: 2.15, volume: 65000000, iv_rank: 58, sector: 'Technology', recommendation: 'buy' },
        { symbol: 'TSLA', name: 'Tesla Inc', price: 248.50, change_pct: -1.85, volume: 75000000, iv_rank: 65, sector: 'Consumer', recommendation: 'avoid' },
        { symbol: 'GOOGL', name: 'Alphabet Inc', price: 176.20, change_pct: 0.92, volume: 28000000, iv_rank: 40, sector: 'Technology', recommendation: 'buy' },
        { symbol: 'AMD', name: 'AMD Inc', price: 158.30, change_pct: 1.45, volume: 42000000, iv_rank: 55, sector: 'Technology', recommendation: 'buy' },
        { symbol: 'META', name: 'Meta Platforms', price: 502.10, change_pct: 0.78, volume: 18000000, iv_rank: 42, sector: 'Technology', recommendation: 'hold' },
    ];
    
    return tickers;
}
function loadCalendarData() {
    // Get current time
    const now = new Date();
    const usTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const nzTime = new Date(now.toLocaleString('en-US', { timeZone: 'Pacific/Auckland' }));
    
    // Determine market status
    const hours = usTime.getHours();
    const minutes = usTime.getMinutes();
    const timeNum = hours * 60 + minutes;
    const isWeekday = usTime.getDay() > 0 && usTime.getDay() < 6;
    
    let status, statusColor;
    if (!isWeekday) {
        status = 'Closed (Weekend)';
        statusColor = 'text-red-400';
    } else if (timeNum < 240) { // 4:00 AM ET
        status = 'Closed';
        statusColor = 'text-red-400';
    } else if (timeNum < 570) { // 9:30 AM ET
        status = 'Pre-Market';
        statusColor = 'text-yellow-400';
    } else if (timeNum < 960) { // 4:00 PM ET
        status = 'Open';
        statusColor = 'text-green-400';
    } else if (timeNum < 1200) { // 8:00 PM ET
        status = 'After Hours';
        statusColor = 'text-orange-400';
    } else {
        status = 'Closed';
        statusColor = 'text-red-400';
    }
    
    document.getElementById('marketStatus').textContent = status;
    document.getElementById('marketStatus').className = `text-xl font-bold ${statusColor}`;
    document.getElementById('usTime').textContent = usTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'America/New_York' }) + ' ET';
    document.getElementById('nzTime').textContent = nzTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Pacific/Auckland' }) + ' NZST';
    
    // Load upcoming events
    loadUpcomingEvents();
}

function loadUpcomingEvents() {
    const events = getUpcomingEvents();
    const container = document.getElementById('upcomingEvents');
    const count = document.getElementById('eventCount');
    
    count.textContent = `${events.length} events`;
    
    container.innerHTML = events.slice(0, 8).map(event => {
        const date = new Date(event.date);
        const isToday = date.toDateString() === new Date().toDateString();
        const isTomorrow = date.toDateString() === new Date(Date.now() + 86400000).toDateString();
        
        let dateLabel = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        if (isToday) dateLabel = 'Today';
        if (isTomorrow) dateLabel = 'Tomorrow';
        
        const typeColors = {
            'holiday': 'bg-red-500',
            'fomc': 'bg-blue-500',
            'NFP': 'bg-green-500',
            'CPI': 'bg-red-500',
            'monthly_opex': 'bg-purple-500'
        };
        
        return `
            <div class="flex items-center space-x-3 py-2 border-b border-slate-700/50 last:border-0">
                <div class="w-2 h-2 rounded-full ${typeColors[event.type] || 'bg-slate-400'}"></div>
                <div class="flex-1">
                    <p class="text-sm text-white">${event.name}</p>
                    <p class="text-xs text-slate-400">${event.time || 'All Day'}</p>
                </div>
                <span class="text-xs ${isToday ? 'text-cyan-400 font-semibold' : 'text-slate-400'}">${dateLabel}</span>
            </div>
        `;
    }).join('');
}

function getUpcomingEvents() {
    const now = new Date();
    const events = [];
    
    // 2025 FOMC dates
    const fomcDates = [
        '2025-01-28', '2025-03-18', '2025-05-06', '2025-06-17',
        '2025-07-29', '2025-09-16', '2025-10-28', '2025-12-16'
    ];
    
    // CPI dates (2nd week of each month)
    const cpiDates = [
        '2025-01-15', '2025-02-12', '2025-03-12', '2025-04-10',
        '2025-05-13', '2025-06-11', '2025-07-15', '2025-08-12',
        '2025-09-10', '2025-10-14', '2025-11-12', '2025-12-10'
    ];
    
    // NFP dates (1st Friday of each month)
    const nfpDates = [
        '2025-01-10', '2025-02-07', '2025-03-07', '2025-04-04',
        '2025-05-02', '2025-06-06', '2025-07-03', '2025-08-01',
        '2025-09-05', '2025-10-03', '2025-11-07', '2025-12-05'
    ];
    
    // Options expiration (3rd Friday)
    const opexDates = [
        '2025-01-17', '2025-02-21', '2025-03-21', '2025-04-18',
        '2025-05-16', '2025-06-20', '2025-07-18', '2025-08-15',
        '2025-09-19', '2025-10-17', '2025-11-21', '2025-12-19'
    ];
    
    // Holidays
    const holidays = [
        { date: '2025-01-01', name: "New Year's Day" },
        { date: '2025-01-20', name: "MLK Day" },
        { date: '2025-02-17', name: "Presidents' Day" },
        { date: '2025-04-18', name: "Good Friday" },
        { date: '2025-05-26', name: "Memorial Day" },
        { date: '2025-06-19', name: "Juneteenth" },
        { date: '2025-07-04', name: "Independence Day" },
        { date: '2025-09-01', name: "Labor Day" },
        { date: '2025-11-27', name: "Thanksgiving" },
        { date: '2025-12-25', name: "Christmas" }
    ];
    
    // Add all events
    fomcDates.forEach(d => events.push({ date: d, type: 'fomc', name: 'FOMC Meeting', time: '2:00 PM ET' }));
    cpiDates.forEach(d => events.push({ date: d, type: 'CPI', name: 'CPI Report', time: '8:30 AM ET' }));
    nfpDates.forEach(d => events.push({ date: d, type: 'NFP', name: 'NFP (Jobs Report)', time: '8:30 AM ET' }));
    opexDates.forEach(d => events.push({ date: d, type: 'monthly_opex', name: 'Options Expiration', time: 'Close' }));
    holidays.forEach(h => events.push({ ...h, type: 'holiday', name: h.name, time: 'Market Closed' }));
    
    // Filter to future events and sort
    const futureEvents = events
        .filter(e => new Date(e.date) >= now)
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .slice(0, 10);
    
    return futureEvents;
}

function updateVIXChart() {
    const ctx = document.getElementById('vixChart')?.getContext('2d');
    if (!ctx) return;
    if (vixChart) vixChart.destroy();
    
    const labels = [], data = [];
    for (let i = 29; i >= 0; i--) {
        const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        data.push(18 + Math.random() * 6 - 3);
    }
    
    vixChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                data,
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
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: {
                    ticks: { color: '#64748B', font: { size: 10 } },
                    grid: { color: 'rgba(100, 116, 139, 0.1)' }
                }
            }
        }
    });
}

// ============ Initialize ============
loadTrades();
updateVIXMonitor();
