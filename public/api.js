// ThetaEdge — Live data layer
// Fetches real market data from the FastAPI backend (/api/*),
// with graceful fallback to the local cache when offline.

const API_BASE = window.API_BASE || '/api';

async function apiGet(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
}

// ---- Live quotes / scan -------------------------------------------------
async function getTickerData() {
    try {
        const tickers = await apiGet('/tickers/scan');
        // Attach recommendation if backend doesn't provide it
        return tickers.map(t => ({
            ...t,
            recommendation: t.recommendation || (t.iv_rank >= 40 && t.volume > 10e6 ? 'buy' : t.has_earnings_soon ? 'avoid' : 'hold')
        }));
    } catch (e) {
        console.warn('Scan API unavailable, using snapshot/cache:', e);
        return getTickerDataFallback();
    }
}

function getTickerDataFallback() {
    // 1) static snapshot baked at deploy time (real data, may be hours old)
    const snapRaw = sessionStorage.getItem('snapshot_tickers');
    if (snapRaw) {
        try {
            const snap = JSON.parse(snapRaw);
            return Array.isArray(snap) ? snap : (snap.tickers || []);
        } catch (_) {}
    }
    // 2) runtime cache from a previous successful fetch
    const cached = localStorage.getItem('thetaedge_tickers');
    if (cached) { try { return JSON.parse(cached); } catch (_) {} }
    return [];
}

function saveTickerCache(tickers) {
    localStorage.setItem('thetaedge_tickers', JSON.stringify(tickers));
}

// ---- Options chain ------------------------------------------------------
async function getOptionsChain(symbol = 'QQQ') {
    try {
        const chain = await apiGet(`/chain/${symbol}`);
        saveChainCache(symbol, chain.options);
        return chain;
    } catch (e) {
        console.warn('Chain API unavailable, using snapshot/cache:', e);
        // 1) static snapshot (QQQ only)
        if (symbol.toUpperCase() === 'QQQ') {
            const snap = sessionStorage.getItem('snapshot_chain_qqq');
            if (snap) { try { return JSON.parse(snap); } catch (_) {} }
        }
        // 2) runtime cache
        const c = localStorage.getItem('thetaedge_chain_' + symbol);
        return c ? JSON.parse(c) : null;
    }
}

function saveChainCache(symbol, chain) {
    localStorage.setItem('thetaedge_chain_' + symbol, JSON.stringify(chain));
}

// ---- VIX -----------------------------------------------------------------
async function getVixData() {
    try {
        const v = await apiGet('/vix');
        // Backend: { current, avg_7d, avg_30d, min_30d, max_30d, signal, interpretation }
        const normalized = {
            current: v.current,
            avg7: v.avg_7d,
            avg30: v.avg_30d,
            min30: v.min_30d,
            max30: v.max_30d,
            signal: v.signal,
            interpretation: v.interpretation
        };
        saveVixCache(normalized);
        return normalized;
    } catch (e) {
        console.warn('VIX API unavailable, using snapshot/cache:', e);
        const snapRaw = sessionStorage.getItem('snapshot_vix');
        if (snapRaw) {
            try {
                const s = JSON.parse(snapRaw);
                // Snapshot uses same shape as API (snake_case) — normalize to camelCase
                const normalized = {
                    current: s.current,
                    avg7: s.avg_7d ?? s.avg7,
                    avg30: s.avg_30d ?? s.avg30,
                    min30: s.min_30d ?? s.min30,
                    max30: s.max_30d ?? s.max30,
                    signal: s.signal,
                    interpretation: s.interpretation
                };
                if (normalized.current != null) return normalized;
            } catch (_) {}
        }
        const v = localStorage.getItem('vix_cache');
        return v ? JSON.parse(v) : null;
    }
}

function saveVixCache(v) {
    localStorage.setItem('vix_cache', JSON.stringify(v));
}

// ---- Economic calendar ----------------------------------------------------
// Holidays, NFP (1st Friday) and OPEX (3rd Friday) are computed dynamically
// for any year. FOMC and CPI dates come from official published schedules,
// keyed by year below (update when the Fed/BLS publish new years).
const FOMC_DECISION_DATES = {
    2026: ['2026-01-28', '2026-03-18', '2026-04-29', '2026-06-17',
           '2026-07-29', '2026-09-16', '2026-10-28', '2026-12-09']
};
const CPI_RELEASE_DATES = {
    2026: ['2026-01-13', '2026-02-11', '2026-03-11', '2026-04-10',
           '2026-05-12', '2026-06-10', '2026-07-14', '2026-08-12',
           '2026-09-11', '2026-10-13', '2026-11-10', '2026-12-10']
};

function getHolidayDates(year) {
    return [
        { date: `${year}-01-01`, name: "New Year's Day" },
        { date: thirdMonday(year, 0), name: 'MLK Day' },                    // 3rd Monday Jan
        { date: thirdMonday(year, 1), name: "Presidents' Day" },            // 3rd Monday Feb
        { date: goodFridayOf(year), name: 'Good Friday' },
        { date: lastMondayOfMonth(year, 4), name: 'Memorial Day' },         // last Monday May
        { date: juneteenthObserved(year), name: 'Juneteenth' },
        { date: july4Observed(year), name: 'Independence Day' },
        { date: thirdMonday(year, 8), name: 'Labor Day' },                  // 1st Monday Sep
        { date: fourthThursdayOfMonth(year, 10), name: 'Thanksgiving' },
        { date: christmasObserved(year), name: 'Christmas' }
    ];
}

function getUpcomingEvents() {
    const year = new Date().getFullYear();
    const events = [];
    const fomcDates = FOMC_DECISION_DATES[year] || [];
    const cpiDates = CPI_RELEASE_DATES[year] || [];
    const nfpDates = firstFridaysOfYear(year);
    const opexDates = thirdFridaysOfYear(year);

    fomcDates.forEach(d => events.push({ date: d, type: 'fomc', name: 'FOMC Decision', time: '2:00 PM ET' }));
    cpiDates.forEach(d => events.push({ date: d, type: 'CPI', name: 'CPI Report', time: '8:30 AM ET' }));
    nfpDates.forEach(d => events.push({ date: d, type: 'NFP', name: 'NFP (Jobs Report)', time: '8:30 AM ET' }));
    opexDates.forEach(d => events.push({ date: d, type: 'monthly_opex', name: 'Options Expiration', time: 'Close' }));
    getHolidayDates(year).forEach(h => events.push({ date: h.date, type: 'holiday', name: h.name, time: 'Market Closed' }));

    return events
        .filter(e => new Date(e.date + 'T12:00:00') >= new Date())
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .slice(0, 10);
}

// ---- Weekday / holiday helpers --------------------------------------------
function nthWeekdayOfMonth(year, month, weekday, n) { // month 0-indexed, weekday 0=Sun..6=Sat
    const d = new Date(Date.UTC(year, month, 1));
    let count = 0;
    while (true) {
        if (d.getUTCDay() === weekday && ++count === n) return d.toISOString().split('T')[0];
        d.setUTCDate(d.getUTCDate() + 1);
    }
}
function thirdMonday(year, month) { return nthWeekdayOfMonth(year, month, 1, 3); }
function firstFriday(year, month) { return nthWeekdayOfMonth(year, month, 5, 1); }
function thirdFriday(year, month) { return nthWeekdayOfMonth(year, month, 5, 3); }

function firstFridaysOfYear(year) {
    return Array.from({ length: 12 }, (_, m) => firstFriday(year, m));
}
function thirdFridaysOfYear(year) {
    return Array.from({ length: 12 }, (_, m) => thirdFriday(year, m));
}

function lastMondayOfMonth(year, month) {
    const d = new Date(Date.UTC(year, month + 1, 0));
    while (d.getUTCDay() !== 1) d.setUTCDate(d.getUTCDate() - 1);
    return d.toISOString().split('T')[0];
}

function fourthThursdayOfMonth(year, month) {
    return nthWeekdayOfMonth(year, month, 4, 4);
}

function goodFridayOf(year) {
    // Meeus/Jones/Butcher Easter computus → Good Friday = Easter − 2 days
    const a = year % 19;
    const b = Math.floor(year / 100), c = year % 100;
    const d = Math.floor(b / 4), e = b % 4;
    const f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4), k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const month = Math.floor((h + l - 7 * m + 114) / 31);
    const day = ((h + l - 7 * m + 114) % 31) + 1;
    const easter = new Date(Date.UTC(year, month - 1, day));
    easter.setUTCDate(easter.getUTCDate() - 2);
    return easter.toISOString().split('T')[0];
}

function observed(dateStr) { // weekends roll to next Monday
    const d = new Date(dateStr + 'T00:00:00Z');
    if (d.getUTCDay() === 6) d.setUTCDate(d.getUTCDate() + 2);      // Sat → Mon
    else if (d.getUTCDay() === 0) d.setUTCDate(d.getUTCDate() + 1); // Sun → Mon
    return d.toISOString().split('T')[0];
}
function juneteenthObserved(year) { return observed(`${year}-06-19`); }
function july4Observed(year) { return observed(`${year}-07-04`); }
function christmasObserved(year) { return observed(`${year}-12-25`); }

// ---- VIX monitor with real history ----------------------------------------
let vixChart = null;

async function updateVIXMonitor() {
    const v = await getVixData();
    if (!v) {
        console.warn('No VIX data available (API down, no cache)');
        return;
    }
    document.getElementById('vixValue').textContent = v.current.toFixed(1);
    document.getElementById('vixAvg7d').textContent = v.avg7.toFixed(1);
    document.getElementById('vixAvg30d').textContent = v.avg30.toFixed(1);
    document.getElementById('vixMin30d').textContent = v.min30.toFixed(1);
    document.getElementById('vixMax30d').textContent = v.max30.toFixed(1);

    let signal, color, interpretation;
    if (v.current < 15) {
        signal = 'ENTER'; color = 'text-green-400'; interpretation = 'Excellent for selling';
    } else if (v.current < 20) {
        signal = 'HOLD'; color = 'text-yellow-400'; interpretation = 'Acceptable conditions';
    } else if (v.current < 25) {
        signal = 'CAUTION'; color = 'text-orange-400'; interpretation = 'Wait for better entry';
    } else {
        signal = 'WAIT'; color = 'text-red-400'; interpretation = 'Avoid new positions';
    }

    document.getElementById('vixInterpretation').textContent = interpretation;
    document.getElementById('entrySignal').innerHTML = `
        <div class="w-3 h-3 rounded-full ${v.current < 15 ? 'bg-green-400' : v.current < 20 ? 'bg-yellow-400' : 'bg-red-400'}"></div>
        <span class="text-lg font-semibold ${color}">${signal}</span>
    `;

    // Chart from real 30-day history
    try {
        const hist = await apiGet('/vix/history?days=30');
        // Backend returns list of readings: [{ date, value, ... }]
        renderVixChart(hist.map(r => r.date || r.timestamp), hist.map(r => r.value ?? r.vix));
    } catch (e) {
        // Snapshot history from deploy-time bake
        const snapRaw = sessionStorage.getItem('snapshot_vix');
        if (snapRaw) {
            try {
                const snap = JSON.parse(snapRaw);
                if (snap.history) renderVixChart(snap.history.dates, snap.history.values);
            } catch (_) {}
        } else {
            console.warn('VIX history unavailable:', e);
        }
    }
}

function renderVixChart(labels, data) {
    const ctx = document.getElementById('vixChart')?.getContext('2d');
    if (!ctx || !data || !data.length) return;
    if (vixChart) vixChart.destroy();

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

// ---- Wire-up ---------------------------------------------------------------
async function loadSnapshots() {
    // Static snapshots baked at deploy time — first-run fallback when no backend.
    const names = { snapshot_tickers: 'tickers', snapshot_vix: 'vix', snapshot_chain_qqq: 'chain_qqq' };
    for (const [key, file] of Object.entries(names)) {
        try {
            const res = await fetch(`data/${file}.json`);
            if (res.ok) sessionStorage.setItem(key, JSON.stringify(await res.json()));
        } catch (_) { /* offline, ignore */ }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadSnapshots();
    updateVIXMonitor();
});
