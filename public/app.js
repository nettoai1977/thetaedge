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
