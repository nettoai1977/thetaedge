"""
ThetaEdge Daily Automation
==========================
One scheduled run = one full day of the paper-trading system:

  1. Fetch live market data (VIX, VIX3M, QQQ, realized-vol IV proxy)
  2. Ask the REAL ThetaBrain.analyze() for today's decision
  3. Persist the signal to public/data/signals.json (web app reads this)
  4. Manage the $1,000 paper portfolio (src/data/paper_portfolio.json):
       - mark open positions to market (Black-Scholes)
       - apply Ravish exits: TP +30% / SL -30% / roll <7 DTE / delta >0.40
       - enter new position when the brain says trade (2%/trade, max 5 pos)
  5. Print a human-readable summary (Hermes cron relays it to Telegram)

Idempotent per day: re-running updates today's entry instead of duplicating.
"""

import json
import math
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.engine.black_scholes import black_scholes, calculate_greeks   # noqa: E402
from src.engine.iv_rank import get_iv_rank                             # noqa: E402
from src.engine.theta_brain import MarketInputs, ThetaBrain            # noqa: E402

SYMBOL = 'QQQ'
ACCOUNT_START = 1000.00
RISK_FREE = 0.042
DIV_YIELD = 0.006
SHORT_DTE = 14      # calendar structure: 14d short leg / 21d long leg
LONG_DTE = 21
TP_PCT = 0.30
SL_PCT = 0.30
ROLL_DTE = 7
DELTA_ROLL = 0.40

SIGNALS_FILE = ROOT / 'public' / 'data' / 'signals.json'
PORTFOLIO_FILE = ROOT / 'src' / 'data' / 'paper_portfolio.json'

# Published FOMC decision dates (shared with backtest)
FOMC_DATES = [
    '2025-01-29', '2025-03-19', '2025-05-07', '2025-06-18',
    '2025-07-30', '2025-09-17', '2025-10-29', '2025-12-10',
    '2026-01-28', '2026-03-18', '2026-04-29', '2026-06-17',
    '2026-07-29', '2026-09-16', '2026-10-28', '2026-12-09',
]
FOMC = [datetime.strptime(x, '%Y-%m-%d').date() for x in FOMC_DATES]


def days_to_fomc(d: date):
    future = [f for f in FOMC if f >= d]
    return (future[0] - d).days if future else None


def _fetch_close(symbol: str, days: int, tries: int = 4):
    """Daily closes with retry + timezone normalization."""
    import yfinance as yf
    import pandas as pd
    end = date.today()
    start = end - timedelta(days=days)
    last_err = None
    for attempt in range(tries):
        try:
            s = yf.Ticker(symbol).history(start=start, end=end)['Close'].dropna()
            if len(s):
                idx = pd.to_datetime(s.index).tz_localize(None).normalize()
                out = pd.Series(s.values, index=idx)
                return out.groupby(level=0).last()
            last_err = RuntimeError('empty response')
        except Exception as e:                                  # noqa: BLE001
            last_err = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'yfinance failed for {symbol}: {last_err}')


def opt_px(S, K, T, sigma, kind):
    if T <= 0:
        return max(0.0, (S - K) if kind == 'call' else (K - S))
    return black_scholes(S, K, T, RISK_FREE, sigma, kind, DIV_YIELD)


def position_value(S, put_k, call_k, dte_s, dte_l, sigma, strategy):
    sT, lT = max(dte_s, 0) / 365.0, max(dte_l, 0) / 365.0
    v = 0.0
    if strategy == 'double_calendar':
        v += opt_px(S, put_k, lT, sigma, 'put') + opt_px(S, call_k, lT, sigma, 'call')
        v -= opt_px(S, put_k, sT, sigma, 'put') + opt_px(S, call_k, sT, sigma, 'call')
    elif strategy == 'calendar_call':
        v += opt_px(S, call_k, lT, sigma, 'call') - opt_px(S, call_k, sT, sigma, 'call')
    elif strategy == 'calendar_put':
        v += opt_px(S, put_k, lT, sigma, 'put') - opt_px(S, put_k, sT, sigma, 'put')
    elif strategy == 'double_diagonal':
        v += opt_px(S, put_k - 5, lT, sigma, 'put') + opt_px(S, call_k + 5, lT, sigma, 'call')
        v -= opt_px(S, put_k, sT, sigma, 'put') + opt_px(S, call_k, sT, sigma, 'call')
    return max(v, 0.05)


def short_deltas(S, put_k, call_k, dte_s, sigma):
    sT = max(dte_s, 0.5) / 365.0
    dp = calculate_greeks(S, put_k, sT, RISK_FREE, sigma, 'put', DIV_YIELD)['delta']
    dc = calculate_greeks(S, call_k, sT, RISK_FREE, sigma, 'call', DIV_YIELD)['delta']
    return abs(dp), abs(dc)


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:                                       # noqa: BLE001
            pass
    return default


def main():
    today = date.today().isoformat()

    # ---------- 1. market data ----------
    px = _fetch_close(SYMBOL, 400)
    vix_s = _fetch_close('^VIX', 400)
    time.sleep(1)
    vix3m_s = _fetch_close('^VIX3M', 400)

    spot = float(px.iloc[-1])
    vix = float(vix_s.iloc[-1])
    vix3m = float(vix3m_s.iloc[-1])
    term_ratio = round(vix / vix3m, 3) if vix3m else None
    vix_trend = 'falling' if vix < float(vix_s.iloc[-6]) else \
                'rising' if vix > float(vix_s.iloc[-6]) else 'flat'

    rets = px.pct_change()
    import numpy as np
    rv21 = float(rets.rolling(21).std().iloc[-1] * math.sqrt(252) * 100)
    window = (rets.rolling(21).std() * math.sqrt(252) * 100).dropna().iloc[-252:]
    lo, hi = float(window.min()), float(window.max())
    iv_rank = round((rv21 - lo) / (hi - lo) * 100, 1) if hi > lo else 50.0

    volume = int(abs(float(px.iloc[-1] - px.iloc[-2]) * 1e6))     # proxy only
    avg_volume = volume                                            # not used by guards

    print(f'Market: {SYMBOL} ${spot:.2f} | VIX {vix:.1f} ({vix_trend}) | '
          f'term {term_ratio} | RV21 {rv21:.1f}% | IV-rank {iv_rank:.0f}%')

    # ---------- 2. ThetaBrain decision ----------
    iv_metrics = {'iv_rank': iv_rank, 'current_iv': rv21}
    em30 = spot * (rv21 / 100) * math.sqrt(30 / 365)
    debit_est = position_value(spot, round((spot - em30) / 5) * 5,
                               round((spot + em30) / 5) * 5, SHORT_DTE, LONG_DTE,
                               rv21 / 100, 'double_calendar')

    pf = load_json(PORTFOLIO_FILE, {})
    positions = pf.get('positions', [])
    risk_used = sum(p['basis'] * p['contracts'] * 100 for p in positions)

    brain = ThetaBrain()
    inputs = MarketInputs(
        vix_level=vix, vix_trend=vix_trend, symbol=SYMBOL, price=spot,
        iv_rank=iv_rank, volume=volume, avg_volume=avg_volume,
        days_to_fomc=days_to_fomc(date.today()), days_to_cpi=None,
        days_to_earnings=None, current_positions=len(positions),
        account_size=ACCOUNT_START,
        current_risk_pct=risk_used / ACCOUNT_START * 100,
        term_structure_ratio=term_ratio,
        iv_estimate=rv21 / 100,
        debit_pct_estimate=debit_est / spot,
    )
    out = brain.analyze(inputs)

    sig_record = {
        'date': today,
        'signal': out.signal,
        'strategy': out.recommended_strategy if out.signal != 'avoid' else None,
        'put_strike': out.suggested_put_strike or None,
        'call_strike': out.suggested_call_strike or None,
        'contracts': out.recommended_contracts,
        'spot': round(spot, 2),
        'vix': round(vix, 2),
        'iv_rank': iv_rank,
        'reasoning': out.reasoning[:3],
    }
    print(f"THETABRAIN: {out.signal.upper()}"
          + (f" -> {out.recommended_strategy}" if out.signal != 'avoid' else
             f" ({'; '.join(out.reasoning)})"))

    # ---------- 3. persist signal ----------
    signals = load_json(SIGNALS_FILE, [])
    signals = [s for s in signals if s.get('date') != today]
    signals.insert(0, sig_record)
    SIGNALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SIGNALS_FILE.write_text(json.dumps(signals[:180], indent=1))

    # ---------- 4. portfolio management ----------
    pf.setdefault('account_start', ACCOUNT_START)
    cash = pf.get('cash', ACCOUNT_START)
    closed = pf.get('closed_trades', [])

    def mark_pos(p):
        dh = (date.today() - datetime.strptime(p['entry_date'], '%Y-%m-%d').date()).days
        p['dte_short'] = SHORT_DTE - dh
        p['dte_long'] = LONG_DTE - dh
        p['value'] = position_value(p['spot'], p['put_k'], p['call_k'],
                                    p['dte_short'], p['dte_long'], p['sigma'],
                                    p['strategy'])
        return p

    still_open = []
    for p in positions:
        mark_pos(p)
        basis = p['basis']
        val = p['value']
        ret = val / basis - 1
        action, reason = None, ''
        if ret >= TP_PCT:
            action, reason = 'tp', f'+{ret*100:.0f}% take profit'
        elif ret <= -SL_PCT:
            action, reason = 'sl', f'{ret*100:.0f}% stop loss'
        elif p['dte_short'] < ROLL_DTE:
            action, reason = 'roll_close', f"{p['dte_short']} DTE"
        else:
            dp, dc = short_deltas(p['spot'], p['put_k'], p['call_k'],
                                  p['dte_short'], p['sigma'])
            if max(dp, dc) > DELTA_ROLL:
                action, reason = 'roll_close', 'delta breach'
        if p['dte_short'] <= 0:
            action, reason = 'expiry', 'expiration'

        if action:
            pnl_pc = val - basis
            pnl = pnl_pc * p['contracts'] * 100
            cash += pnl
            closed.append({**{k: p[k] for k in
                              ('strategy', 'put_k', 'call_k', 'contracts',
                               'basis', 'entry_date')},
                           'exit_date': today, 'exit_value': round(val, 2),
                           'pnl': round(pnl, 2), 'result': action,
                           'reason': reason})
            print(f'  CLOSE {p["strategy"]} x{p["contracts"]}: '
                  f'{action} {reason} -> P&L ${pnl:+.2f}')
        else:
            still_open.append(p)
            print(f'  HOLD  {p["strategy"]} x{p["contracts"]} '
                  f'(ret {ret*100:+.0f}%, {p["dte_short"]} DTE)')

    # New entry?
    entered = False
    if out.signal != 'avoid' and len(still_open) < 5:
        strat = out.recommended_strategy
        put_k, call_k = out.suggested_put_strike, out.suggested_call_strike
        est_debit = position_value(spot, put_k, call_k, SHORT_DTE, LONG_DTE,
                                   rv21 / 100, strat)
        heat = sum(p['basis'] * p['contracts'] * 100 for p in still_open)
        n = int(ACCOUNT_START * 0.02 / est_debit) if est_debit > 0 else 0
        while n > 0 and heat + n * est_debit * 100 > ACCOUNT_START * 0.15:
            n -= 1
        avail = cash - sum(p['basis'] * p['contracts'] * 100 for p in still_open)
        while n > 0 and n * est_debit * 100 > avail:
            n -= 1
        n = min(n, 5)
        if n >= 1:
            still_open.append({'entry_date': today, 'strategy': strat,
                               'spot': round(spot, 2), 'put_k': put_k,
                               'call_k': call_k, 'sigma': rv21 / 100,
                               'contracts': n, 'basis': round(est_debit, 2),
                               'dte_short': SHORT_DTE, 'dte_long': LONG_DTE,
                               'value': round(est_debit, 2)})
            entered = True
            print(f'  ENTER {strat} x{n} @ ${est_debit:.2f}/ct '
                  f'(P{put_k}/C{call_k})')
        else:
            print('  NO ENTRY: sizing rules allow 0 contracts '
                  '(budget < debit)')
    elif out.signal == 'avoid':
        print('  NO ENTRY: avoid signal')

    # Equity snapshot
    open_val = sum((p['value'] - p['basis']) * p['contracts'] * 100
                   for p in still_open)
    total_pnl = sum(t['pnl'] for t in closed)
    equity = ACCOUNT_START + total_pnl + open_val

    eq_hist = pf.get('equity_history', {})
    eq_hist[today] = round(equity, 2)
    pf.update(cash=round(cash, 2), positions=[
        {k: p[k] for k in ('entry_date', 'strategy', 'spot', 'put_k',
                           'call_k', 'sigma', 'contracts', 'basis')} |
        {'dte_short': p['dte_short'], 'value': round(p['value'], 2)}
        for p in still_open],
        closed_trades=closed[-200:], equity_history=dict(
            sorted(eq_hist.items())[-400:]), updated=datetime.now().isoformat())
    PORTFOLIO_FILE.write_text(json.dumps(pf, indent=1))

    wins = [t for t in closed if t['pnl'] > 0]

    # Public snapshot for the static web app
    pub = {
        'updated': datetime.now().isoformat(),
        'account_start': ACCOUNT_START,
        'equity': round(equity, 2),
        'return_pct': round((equity / ACCOUNT_START - 1) * 100, 2),
        'closed_count': len(closed),
        'win_rate': round(len(wins) / len(closed) * 100, 0) if closed else None,
        'open_positions': [
            {'entry_date': p['entry_date'], 'strategy': p['strategy'],
             'contracts': p['contracts'], 'basis': p['basis'],
             'value': round(p['value'], 2),
             'ret_pct': round((p['value'] / p['basis'] - 1) * 100, 1)}
            for p in still_open],
        'recent_closed': [
            {k: t[k] for k in ('exit_date', 'strategy', 'contracts',
                               'pnl', 'result', 'reason')}
            for t in sorted(closed, key=lambda x: x['exit_date'])[-10:]],
    }
    (ROOT / 'public' / 'data' / 'portfolio.json').write_text(
        json.dumps(pub, indent=1))

    print(f'\nPORTFOLIO: equity ${equity:.2f} '
          f'({(equity / ACCOUNT_START - 1) * 100:+.1f}% all-time) | '
          f'closed {len(closed)} trades, {len(wins)} wins '
          f'({len(wins) / len(closed) * 100:.0f}% win rate)' if closed else
          f'\nPORTFOLIO: equity ${equity:.2f} | no closed trades yet')
    print(f'Done. Signal saved to signals.json, portfolio updated.')


if __name__ == '__main__':
    main()
