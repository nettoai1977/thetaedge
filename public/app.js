// ThetaEdge - Mobile-First App
// Auth uses SHA-256 hash comparison — the password itself never appears in source.
// To change the password: run in a browser console
//   await sha256('yourNewPassword')
// and replace AUTH_PASSWORD_HASH below with the result.
const CONFIG = {
    USERNAME: 'netto.ai1977',
    AUTH_PASSWORD_HASH: 'c45fb0b04ce5a031c3d129f3efd65f24a129338190617d15e4deaa59b0acd3b5'
};
const PASSWORD_HASH = CONFIG.AUTH_PASSWORD_HASH;
let payoffChart = null;
let currentStrategy = 'double_calendar';

// SHA-256 helper
async function sha256(text) {
    const data = new TextEncoder().encode(text);
    const buf = await crypto.subtle.digest('SHA-256', data);
    return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

// ============ Authentication ============
if (sessionStorage.getItem('authenticated') === 'true') showDashboard();

document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorMsg = document.getElementById('errorMsg');

    const passHash = await sha256(password);
    if (username === CONFIG.USERNAME && passHash === PASSWORD_HASH) {
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
    ['calculator', 'scan', 'tools', 'calendar', 'backtest', 'tracker', 'signals', 'vix'].forEach(t => {
        document.getElementById(t + 'Tab').classList.add('hidden');
    });
    
    // Show selected tab
    document.getElementById(tab + 'Tab').classList.remove('hidden');
    
    // Update nav (guard: calendar/backtest tabs are reached via other views and have no nav item)
    document.querySelectorAll('.bottom-nav-item').forEach(btn => {
        btn.classList.remove('active');
    });
    const navBtn = document.getElementById('nav-' + tab);
    if (navBtn) navBtn.classList.add('active');
    
    // Haptic feedback
    if (navigator.vibrate) navigator.vibrate(10);
    
    // Load data if needed
    if (tab === 'calendar') {
        loadCalendarData();
    } else if (tab === 'scan') {
        loadTickerScan();
    } else if (tab === 'tools') {
        loadOptionsChain();
    } else if (tab === 'signals') {
        loadSignalHistory();
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
    
    // Update real win-rate badge (from YOUR closed trades)
    const badge = document.getElementById('probabilityBadge');
    const badgeText = document.getElementById('winRateBadgeText');
    if (badge && badgeText) {
        if (closedTrades.length > 0) {
            const wins = closedTrades.filter(t => (t.pnl || 0) > 0).length;
            const rate = Math.round(wins / closedTrades.length * 100);
            badgeText.textContent = `${rate}% Win Rate (${wins}/${closedTrades.length} trades)`;
            badge.classList.remove('hidden');
            badge.classList.toggle('probability-high', rate >= 60);
            badge.classList.toggle('probability-medium', rate >= 40 && rate < 60);
            badge.classList.toggle('probability-low', rate < 40);
        } else {
            badge.classList.add('hidden');
        }
    }
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
// Real VIX logic (updateVIXMonitor + renderVixChart) lives in api.js,
// loaded before this file — its globals are directly callable here.

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
        recommendation = `0 contracts — need $${maxLoss.toLocaleString()} per contract but risk budget is only $${Math.round(maxDollarRisk).toLocaleString()}. Increase account size, raise risk %, or trade a cheaper spread.`;
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

// ============ ThetaBrain ============
// Single source of truth: this decision spec mirrors src/engine/theta_brain.py
// exactly (guard chain → strategy select → EM strikes → debit sizing).
const BRAIN = {
    VIX_EXCELLENT: 12, VIX_GOOD: 15, VIX_NORMAL: 20, VIX_HIGH: 25,
    IV_RANK_HIGH: 50, IV_RANK_MEDIUM: 30,
    MAX_RISK_PER_TRADE: 2.0,   // % of account
    MAX_PORTFOLIO_RISK: 15.0,  // %
    MAX_POSITIONS: 5
};

async function runThetaBrain() {
    // Prefill from live data when fields are untouched
    const vixEl = document.getElementById('brainVix');
    const priceEl = document.getElementById('brainPrice');
    if (window.getVixData && (+vixEl.value === 18)) { // default sentinel value
        try {
            const v = await window.getVixData();
            if (v && v.current) vixEl.value = v.current.toFixed(1);
        } catch (e) { console.warn('Live VIX prefill failed:', e); }
    }
    if (priceEl.value === '482') { // default sentinel value
        try {
            const scan = await window.getTickerData();
            const qqq = (scan || []).find(t => t.symbol === document.getElementById('brainSymbol').value.toUpperCase());
            if (qqq) priceEl.value = qqq.price;
        } catch (e) { console.warn('Live price prefill failed:', e); }
    }

    const vix = +vixEl.value;
    const ivRank = +document.getElementById('brainIvRank').value;
    const symbol = document.getElementById('brainSymbol').value.toUpperCase();
    const price = +document.getElementById('brainPrice').value;
    const fomcDays = +document.getElementById('brainFomc').value;
    const account = +document.getElementById('brainAccount').value;

    // ---- Guard chain (mirrors theta_brain.analyze Step 1/2) ----
    let signal, strength, strategy, confidence, reasoning = [], warnings = [];
    let blocked = false;

    if (vix > BRAIN.VIX_HIGH) {
        blocked = true; reasoning.push(`VIX ${vix} too high (> ${BRAIN.VIX_HIGH})`);
    } else if (fomcDays > 0 && fomcDays <= 2) {
        blocked = true; reasoning.push(`FOMC in ${fomcDays} days`);
    } else if (ivRank < 20) {
        blocked = true; reasoning.push(`IV Rank too low (${ivRank}% < 20%)`);
    }

    if (blocked) {
        signal = '🔴 AVOID'; strength = 'strong'; strategy = 'None'; confidence = 'NONE';
        warnings.push(...reasoning.map(r => 'Blocked: ' + r));
    } else {
        // ---- Strategy selection (Step 3) ----
        if (vix < BRAIN.VIX_GOOD) {
            strategy = 'Double Calendar'; confidence = 'HIGH';
            reasoning.push(`VIX LOW (${vix}) - Double Calendar`);
        } else if (vix < BRAIN.VIX_NORMAL) {
            strategy = 'Calendar Call'; confidence = 'MEDIUM';
            reasoning.push(`VIX NORMAL (${vix}) - Calendar Spread`);
        } else {
            strategy = 'Double Diagonal'; confidence = 'LOW';
            reasoning.push(`VIX HIGH (${vix}) - Double Diagonal`);
        }

        // ---- Strikes: expected-move based (Step 4) ----
        const ivDecimal = ivRank / 100 * 0.5 + 0.10; // rank→IV proxy (matches engine)
        const em = price * ivDecimal * Math.sqrt(30 / 365);
        const putStrike = Math.round((price - em) / 5) * 5;
        const callStrike = Math.round((price + em) / 5) * 5;
        reasoning.push(`Strikes P${putStrike}/C${callStrike} (±1.0 EM ≈ $${Math.round(em)})`);

        // ---- Position size from est. calendar debit (Step 5) ----
        const debitPct = 0.012; // mid estimate; real chain debit wired via API when live
        const estDebit = price * debitPct * 100;
        const riskBudget = account * (BRAIN.MAX_RISK_PER_TRADE / 100);
        var contracts = Math.min(Math.floor(riskBudget / estDebit), BRAIN.MAX_POSITIONS);
        var totalRisk = contracts * estDebit;
        reasoning.push(`Est. debit $${estDebit.toFixed(0)}/contract → ${contracts} contracts fits $${riskBudget.toFixed(0)} budget`);

        // ---- Signal ----
        if (vix < BRAIN.VIX_GOOD && ivRank > BRAIN.IV_RANK_HIGH) {
            signal = '🟢 STRONG BUY'; strength = 'strong';
        } else if (vix < BRAIN.VIX_NORMAL) {
            signal = '🟢 BUY'; strength = 'moderate';
        } else {
            signal = '🟡 HOLD'; strength = 'weak';
        }

        // Update strike/risk UI (only in non-blocked path)
        document.getElementById('brainPutStrike').textContent = `$${putStrike}`;
        document.getElementById('brainCallStrike').textContent = `$${callStrike}`;
        document.getElementById('brainContracts').textContent = contracts;
        document.getElementById('brainRisk').textContent = `$${totalRisk.toLocaleString()}`;
    }

    const signalColor = blocked ? 'text-red-400' : signal.includes('STRONG') ? 'text-green-400' : signal.includes('BUY') ? 'text-green-400' : 'text-yellow-400';

    // Update UI
    document.getElementById('brainSignal').textContent = signal;
    document.getElementById('brainSignal').className = `text-lg font-bold ${signalColor}`;
    document.getElementById('brainStrategy').textContent = strategy;
    document.getElementById('brainConfidence').textContent = `Confidence: ${confidence}`;

    // Entry rules / reasoning
    const entryRules = blocked ? reasoning : [
        `✓ VIX at ${vix} - ${vix < 15 ? 'Good' : vix < 20 ? 'Acceptable' : 'Caution'}`,
        `✓ IV Rank ${ivRank}%`,
        `✓ Use ${strategy} strategy`,
        ...reasoning.slice(1),
        '✓ Place limit order at mid-price',
    ];

    document.getElementById('brainEntryRules').innerHTML =
        entryRules.map(r => `<p class="text-xs ${blocked ? 'text-red-400' : 'text-green-400'}">${blocked ? '✗ ' : ''}${r}</p>`).join('');

    // Exit rules (aligned to Ravish playbook)
    const exitRules = [
        'Take profit at 30% of net debit',
        'Stop loss at 30% (mental)',
        'Roll if < 7 days to expiry',
        'Roll if short strike delta > 0.40'
    ];
    const exitEl = document.getElementById('brainExitRules');
    if (exitEl) exitEl.innerHTML = exitRules.map(r =>
        `<p class="text-xs text-cyan-400">→ ${r}</p>`).join('');

    // Warnings
    if (warnings.length > 0) {
        document.getElementById('brainWarnings').classList.remove('hidden');
        document.getElementById('brainWarningList').innerHTML = warnings.map(w =>
            `<p class="text-xs text-red-400">⚠️ ${w}</p>`
        ).join('');
    } else {
        document.getElementById('brainWarnings').classList.add('hidden');
    }
    
    document.getElementById('brainOutput').classList.remove('hidden');
    
    // Log every analysis to signal history (feeds win-rate badge over time)
    try {
        const signals = JSON.parse(localStorage.getItem('thetaedge_signals') || '[]');
        signals.unshift({
            symbol, signal: blocked ? 'avoid' : (signal.includes('STRONG') ? 'strong_buy' : signal.includes('BUY') ? 'buy' : 'hold'),
            strategy: blocked ? null : strategy,
            vix, iv_rank: ivRank, price,
            timestamp: new Date().toISOString()
        });
        localStorage.setItem('thetaedge_signals', JSON.stringify(signals.slice(0, 50)));
    } catch (e) { console.warn('Signal log failed:', e); }

    if (navigator.vibrate) navigator.vibrate([10, 50, 10]);
}

// ============ Tools Tab Functions ============

// Options Chain
function loadOptionsChain() {
    window.getOptionsChain('QQQ').then(chain => {
        const container = document.getElementById('optionsChain');
        if (!chain || !chain.options || !chain.options.length) {
            container.innerHTML =
                '<p class="text-slate-400 text-sm text-center py-4">No chain data available</p>';
            return;
        }
        const rows = chain.options;
        const spot = chain.spot;
        // ATM = strike closest to spot (precomputed in snapshot, else compute)
        const atmStrike = chain.atm_strike ||
            (spot ? rows.reduce((best, o) =>
                Math.abs(o.strike - spot) < Math.abs(best.strike - spot) ? o : best
            ).strike : null);
        container.innerHTML = rows.map(o => `
            <div class="grid grid-cols-4 gap-2 text-xs py-1 ${o.strike === atmStrike ? 'bg-cyan-500/10 rounded px-1' : ''}">
                <span class="text-white ${o.strike === atmStrike ? 'font-semibold' : ''}">${o.strike}</span>
                <span class="text-right text-green-400">${o.bid != null ? (+o.bid).toFixed(2) : '—'}</span>
                <span class="text-right text-red-400">${o.ask != null ? (+o.ask).toFixed(2) : '—'}</span>
                <span class="text-right text-slate-400">${o.iv != null ? (+o.iv).toFixed(1) + '%' : '—'}</span>
            </div>
        `).join('');
    });
}

// Roll Advisor
function checkRoll() {
    const days = +document.getElementById('rollDays').value;
    const delta = +document.getElementById('rollDelta').value;
    const pnl = +document.getElementById('rollPnl').value;
    
    let urgency, color, reason, notes;
    
    if (days <= 7) {
        urgency = '⚠️ ROLL NOW';
        color = 'text-red-400';
        reason = `Only ${days} days to expiry - high gamma risk`;
        notes = 'Consider rolling to next month expiry';
    } else if (Math.abs(delta) > 0.40) {
        urgency = '⚠️ ROLL SOON';
        color = 'text-orange-400';
        reason = `Delta at ${delta.toFixed(2)} - getting too directional`;
        notes = 'Consider rolling to different strikes';
    } else if (pnl >= 50) {
        urgency = '✅ TAKE PROFIT';
        color = 'text-green-400';
        reason = `At ${pnl}% profit - consider closing`;
        notes = 'Good opportunity to realize gains';
    } else if (pnl <= -30) {
        urgency = '🛑 CUT LOSS';
        color = 'text-red-400';
        reason = `At ${pnl}% loss - review strategy`;
        notes = 'Consider closing and reassessing';
    } else {
        urgency = '✅ HOLD';
        color = 'text-green-400';
        reason = 'Position is healthy';
        notes = `${days} days to expiry, delta at ${delta.toFixed(2)}`;
    }
    
    document.getElementById('rollUrgency').textContent = urgency;
    document.getElementById('rollUrgency').className = `text-sm font-semibold mb-1 ${color}`;
    document.getElementById('rollReason').textContent = reason;
    document.getElementById('rollNotes').textContent = notes;
    document.getElementById('rollResult').classList.remove('hidden');
    
    if (navigator.vibrate) navigator.vibrate(10);
}

// Alerts
let alerts = [];

function showAddAlert() {
    const symbol = prompt('Enter symbol (e.g., QQQ):');
    if (!symbol) return;
    
    const type = prompt('Alert type:\n1. Price Above\n2. Price Below\n\nEnter 1 or 2:');
    if (!type) return;
    
    const threshold = parseFloat(prompt('Enter price threshold:'));
    if (isNaN(threshold)) return;
    
    alerts.push({
        id: Date.now(),
        symbol: symbol.toUpperCase(),
        type: type === '1' ? 'price_above' : 'price_below',
        threshold: threshold,
        triggered: false
    });
    
    updateAlertsList();
    if (navigator.vibrate) navigator.vibrate(10);
}

function updateAlertsList() {
    const container = document.getElementById('alertsList');
    
    if (alerts.length === 0) {
        container.innerHTML = '<p class="text-slate-400 text-sm text-center">No alerts set</p>';
        return;
    }
    
    container.innerHTML = alerts.map(a => `
        <div class="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
            <div class="flex items-center space-x-2">
                <div class="w-2 h-2 rounded-full ${a.triggered ? 'bg-green-400' : 'bg-yellow-400'}"></div>
                <span class="text-sm text-white">${a.symbol}</span>
                <span class="text-xs text-slate-400">${a.type === 'price_above' ? '↑' : '↓'} $${a.threshold}</span>
            </div>
            <button onclick="deleteAlert(${a.id})" class="text-xs text-red-400">✕</button>
        </div>
    `).join('');
}

function deleteAlert(id) {
    alerts = alerts.filter(a => a.id !== id);
    updateAlertsList();
}

// Initialize tools
loadOptionsChain();

// ============ Signal Tracker ============
function loadSignalHistory() {
    const signals = getSignalData();
    
    // Calculate performance
    const closed = signals.filter(s => s.outcome);
    const wins = closed.filter(s => s.outcome === 'win');
    const totalPnl = closed.reduce((sum, s) => sum + (s.pnl || 0), 0);
    const winRate = closed.length > 0 ? (wins.length / closed.length * 100).toFixed(0) : 0;
    
    document.getElementById('signalWinRate').textContent = winRate + '%';
    document.getElementById('signalTotalPnl').textContent = '$' + totalPnl.toLocaleString();
    document.getElementById('signalProfitFactor').textContent = '1.5';
    
    // Display signals
    const container = document.getElementById('signalList');
    
    if (signals.length === 0) {
        container.innerHTML = '<p class="text-slate-400 text-sm text-center">No signals logged yet</p>';
        return;
    }
    
    container.innerHTML = signals.slice(0, 10).map(s => {
        const signalColors = {
            'strong_buy': 'text-green-400',
            'buy': 'text-green-400',
            'hold': 'text-yellow-400',
            'wait': 'text-orange-400',
            'avoid': 'text-red-400'
        };
        
        const signalEmoji = {
            'strong_buy': '🟢🟢',
            'buy': '🟢',
            'hold': '🟡',
            'wait': '🟠',
            'avoid': '🔴'
        };
        
        return `
            <div class="py-3 border-b border-slate-700/50 last:border-0">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-2">
                        <span>${signalEmoji[s.signal] || '⚪'}</span>
                        <span class="text-white font-semibold">${s.symbol}</span>
                        <span class="text-xs ${signalColors[s.signal]}">${s.signal.toUpperCase()}</span>
                    </div>
                    <span class="text-xs text-slate-400">${s.strategy}</span>
                </div>
                <div class="flex items-center justify-between mt-1">
                    <span class="text-xs text-slate-400">VIX: ${s.vix} | IV: ${s.iv_rank}%</span>
                    <span class="text-xs ${s.pnl >= 0 ? 'text-green-400' : 'text-red-400'}">${s.pnl ? '$' + s.pnl : 'Pending'}</span>
                </div>
            </div>
        `;
    }).join('');
}

function getSignalData() {
    // Signal history persisted locally; seeded empty until real signals are logged.
    const saved = localStorage.getItem('thetaedge_signals');
    if (saved) { try { return JSON.parse(saved); } catch (_) {} }
    return [];
}

function saveSignalData(signals) {
    localStorage.setItem('thetaedge_signals', JSON.stringify(signals));
}

function showTrackerView(view) {
    if (view === 'signals') {
        showTab('signals');
    } else {
        showTab('tracker');
    }
}
function loadTickerScan() {
    window.getTickerData().then(tickers => {
        if (!tickers || !tickers.length) {
            document.getElementById('bestTickers').innerHTML =
                '<p class="text-slate-400 text-sm text-center py-4">No scan data — API offline and no cache</p>';
            document.getElementById('allTickers').innerHTML =
                '<p class="text-slate-400 text-sm text-center py-4">No tickers available</p>';
            return;
        }
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
    });
}

// Live scan comes from api.js (window.getTickerData); nothing local.
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
    document.getElementById('nzTime').textContent = nzTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Pacific/Auckland' }) + ' NZ';
    
    // Market hours in NZ time — computed dynamically (handles US + NZ DST automatically)
    renderMarketHoursNZ();
    
    // Load upcoming events
    loadUpcomingEvents();
}

// Convert a US Eastern wall-clock time to the equivalent Pacific/Auckland time string.
// Uses iterative Intl conversion so ET↔UTC offset is correct across US DST changes,
// then formats the resolved instant in Pacific/Auckland (NZ DST handled by Intl).
function etToNZ(etHours, etMinutes, usDate) {
    const y = usDate.getFullYear(), mo = usDate.getMonth();
    const targetAsUTC = Date.UTC(y, mo, usDate.getDate(), etHours, etMinutes, 0);
    const fmt = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    // Iterate: adjust guess until its NY wall-clock equals the requested wall-clock
    let guess = targetAsUTC;
    for (let i = 0; i < 3; i++) {
        const parts = Object.fromEntries(fmt.formatToParts(new Date(guess)).map(p => [p.type, p.value]));
        const nyAsUTC = Date.UTC(+parts.year, +parts.month - 1, +parts.day, (+parts.hour) % 24, +parts.minute, +parts.second);
        guess += (targetAsUTC - nyAsUTC);
    }
    const nzFmt = new Intl.DateTimeFormat('en-NZ', { timeZone: 'Pacific/Auckland', hour: 'numeric', minute: '2-digit', hour12: true });
    return nzFmt.format(new Date(guess));
}

function renderMarketHoursNZ() {
    const container = document.getElementById('marketHoursNZ');
    if (!container) return;
    try {
        // Use "today" in New York as the reference date (handles DST on both sides)
        const nowNY = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
        const sessions = [
            { label: 'Pre-Market', start: [4, 0], end: [9, 30] },
            { label: 'Regular Hours', start: [9, 30], end: [16, 0] },
            { label: 'After Hours', start: [16, 0], end: [20, 0] }
        ];
        container.innerHTML = sessions.map(s => {
            const nzStart = etToNZ(s.start[0], s.start[1], nowNY);
            const nzEnd = etToNZ(s.end[0], s.end[1], nowNY);
            return `
                <div class="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
                    <span class="text-sm text-slate-400">${s.label}</span>
                    <span class="text-sm text-white">${nzStart} – ${nzEnd}</span>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.warn('Market-hours render failed:', e);
    }
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
    // Real calendar from api.js — dynamic holidays + current-year FOMC/CPI schedules.
    const year = new Date().getFullYear();
    const events = [];
    const fomcDates = FOMC_DECISION_DATES[year] || [];
    const cpiDates = CPI_RELEASE_DATES[year] || [];

    fomcDates.forEach(d => events.push({ date: d, type: 'fomc', name: 'FOMC Decision', time: '2:00 PM ET' }));
    cpiDates.forEach(d => events.push({ date: d, type: 'CPI', name: 'CPI Report', time: '8:30 AM ET' }));
    firstFridaysOfYear(year).forEach(d => events.push({ date: d, type: 'NFP', name: 'NFP (Jobs Report)', time: '8:30 AM ET' }));
    thirdFridaysOfYear(year).forEach(d => events.push({ date: d, type: 'monthly_opex', name: 'Options Expiration', time: 'Close' }));
    getHolidayDates(year).forEach(h => events.push({ date: h.date, type: 'holiday', name: h.name, time: 'Market Closed' }));

    const now = new Date();
    return events
        .filter(e => new Date(e.date + 'T12:00:00') >= now)
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .slice(0, 10);
}

function updateVIXChart() {
    // Real VIX chart rendering lives in api.js (renderVixChart with live history).
    if (window.renderVixChart) window.renderVixChart([], []); // no-op guard
}

// ============ Initialize ============
loadTrades();
// VIX monitor init handled by api.js DOMContentLoaded (after snapshots load)
