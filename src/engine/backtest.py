"""
ThetaBrain Backtest Validator
=============================
Replays ~12 months of real market data through the SAME decision rules as
theta_brain.ThetaBrain.analyze(), then simulates Ravish-playbook exits:

  - Take profit at +30% of net debit
  - Stop loss at -30% of net debit (mental stop -> evaluated on daily marks)
  - Roll / re-enter if < 7 DTE remaining or short-strike |delta| > 0.40

HONEST MODELING NOTES (free-data limitations):
  - Volatility input = 21d realized vol (annualized), same proxy as iv_rank.py
  - Option prices are Black-Scholes mid estimates (no bid-ask spread modeled)
  - Entries/exits assumed at daily closes; intraday fills not modeled
  - FOMC guard uses published FOMC decision dates; earnings guard is inert
    for index underliers (QQQ has no earnings)
Results are INDICATIVE, not broker-exact.

Two tracks are reported:
  Track A ("signal_edge"): every non-AVOID signal trades exactly 1 contract,
      no compounding -> validates whether the BRAIN'S CALLS have an edge.
  Track B ("portfolio_1k"): $1,000 account, strict risk rules (2%/trade,
      max 5 positions, 15% portfolio heat). Shows what the real account does.
"""

import json
import math
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from src.engine.black_scholes import black_scholes, calculate_greeks

# ---------------------------------------------------------------- constants
ACCOUNT_START = 1000.00
RISK_PER_TRADE_PCT = 2.0
MAX_PORTFOLIO_RISK_PCT = 15.0
MAX_POSITIONS = 5
MAX_CONTRACTS_CAP = 5          # ThetaBrain cap
TP_PCT = 0.30                  # +30% of debit
SL_PCT = 0.30                  # -30% of debit
ROLL_DTE = 7                   # roll if < 7 days left
DELTA_ROLL_THRESHOLD = 0.40
SHORT_DTE = 14                 # Ravish: ~2 weeks short leg
LONG_DTE = 21                  # long leg one week behind
EM_DTE = 30                    # expected move horizon used by ThetaBrain
RISK_FREE = 0.042              # approx T-bill
DIV_YIELD = 0.006              # QQQ dividend yield
TEST_DAYS = 252                # ~12 months of trading days

# Published FOMC decision dates (day 2 of each meeting)
FOMC_DATES = [
    '2025-01-29', '2025-03-19', '2025-05-07', '2025-06-18',
    '2025-07-30', '2025-09-17', '2025-10-29', '2025-12-10',
    '2026-01-28', '2026-03-18', '2026-04-29', '2026-06-17',
    '2026-07-29', '2026-09-16', '2026-10-28', '2026-12-09',
]
FOMC = [datetime.strptime(d, '%Y-%m-%d').date() for d in FOMC_DATES]


def days_to_fomc(d: date):
    """Days until next FOMC decision (None if none within calendar)."""
    future = [f for f in FOMC if f >= d]
    return (future[0] - d).days if future else None


@dataclass
class SimTrade:
    symbol: str
    track: str                 # 'signal_edge' | 'portfolio_1k'
    entry_date: str
    exit_date: str = ''
    strategy: str = ''
    put_strike: float = 0.0
    call_strike: float = 0.0
    contracts: int = 1
    entry_debit: float = 0.0   # per contract
    exit_value: float = 0.0    # per contract
    pnl: float = 0.0           # dollars, all contracts
    ret_on_debit: float = 0.0  # fraction
    result: str = ''           # tp / sl / roll_close / expiry
    reason: str = ''
    rolls: int = 0
    signal: str = ''


class ThetaBrainBacktester:
    """Replay ThetaBrain decisions on real history."""

    def __init__(self, symbol: str = 'QQQ', lookback_days: int = TEST_DAYS + 320,
                 strike_mode: str = 'em', strike_width: float = None,
                 tp_pct: float = TP_PCT, sl_pct: float = SL_PCT,
                 cost_pct: float = 0.0):
        self.symbol = symbol
        self.lookback_days = lookback_days
        # Sweep parameters
        self.strike_mode = strike_mode      # 'em' (expected move) | 'pts' (fixed pts)
        self.strike_width = strike_width    # points from spot when mode='pts'
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.cost_pct = cost_pct            # round-trip spread haircut on value
        self.df = None             # daily frame w/ indicators
        self.trades: list[SimTrade] = []
        self.daily_log: list[dict] = []
        self.portfolio_equity: dict = {}   # date -> equity (track B)

    # ---------------------------------------------------------- data prep
    def _fetch_close(self, symbol: str, start, end, tries: int = 4) -> 'pd.Series':
        """Fetch closes with retry — yfinance intermittently returns empty."""
        import time
        last_err = None
        for attempt in range(tries):
            try:
                s = yf.Ticker(symbol).history(start=start, end=end)['Close'].dropna()
                if len(s) > 0:
                    return s
                last_err = RuntimeError(f'{symbol}: empty response')
            except Exception as e:               # noqa: BLE001
                last_err = e
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f'yfinance failed for {symbol}: {last_err}')

    def load_data(self):
        end = date.today()
        start = end - timedelta(days=self.lookback_days)
        px = self._fetch_close(self.symbol, start, end)
        import time
        time.sleep(1)
        vix = self._fetch_close('^VIX', start, end)
        time.sleep(1)
        vix3m = self._fetch_close('^VIX3M', start, end)

        df = pd.DataFrame({'spot': self._to_daily(px)})
        df['vix'] = self._to_daily(vix).reindex(df.index).ffill()
        df['vix3m'] = self._to_daily(vix3m).reindex(df.index).ffill()
        df['term_ratio'] = (df['vix'] / df['vix3m']).round(3)

        rets = df['spot'].pct_change()
        rv = rets.rolling(21).std() * math.sqrt(252) * 100     # annualized %
        df['rv21'] = rv

        # IV-rank proxy: rank of current RV21 within trailing 252 obs
        def rank_row(series):
            cur = series.iloc[-1]
            win = series.dropna()
            if len(win) < 60 or cur != cur:
                return np.nan
            lo, hi = win.min(), win.max()
            return (cur - lo) / (hi - lo) * 100 if hi > lo else 50.0
        df['iv_rank'] = rv.rolling(252).apply(rank_row, raw=False)

        self.df = df.dropna(subset=['spot', 'vix', 'rv21']).copy()

    def _to_daily(self, s: 'pd.Series') -> 'pd.Series':
        """Normalize tz-aware index (yfinance returns inconsistent tz) to
        plain calendar dates and aggregate any duplicates."""
        idx = pd.to_datetime(s.index).tz_localize(None).normalize()
        out = pd.Series(s.values, index=idx)
        return out.groupby(level=0).last()

    # ------------------------------------------------------ brain replica
    def brain_decide(self, row, d) -> dict:
        """Mirror theta_brain.analyze() guard chain + strategy/strike/sizing."""
        vix = float(row.vix)
        iv_rank = float(row.iv_rank) if row.iv_rank == row.iv_rank else 30.0
        spot = float(row.spot)
        out = {'signal': 'avoid', 'reason': '', 'strategy': None,
               'put_strike': None, 'call_strike': None}

        if vix > 25.0:
            out['reason'] = f'VIX {vix:.1f} > 25'
            return out
        tr = row.term_ratio
        if tr == tr and tr > 1.0:
            out['reason'] = f'term structure inverted ({tr})'
            return out
        d_fomc = days_to_fomc(d)
        if d_fomc is not None and d_fomc <= 2:
            out['reason'] = f'FOMC in {d_fomc} days'
            return out
        if iv_rank < 20.0:
            out['reason'] = f'IV rank {iv_rank:.0f}% < 20%'
            return out

        if vix < 15:
            out['strategy'] = 'double_calendar'
        elif vix < 20:
            out['strategy'] = 'calendar_call'
        else:
            out['strategy'] = 'double_diagonal'

        iv_decimal = float(row.rv21) / 100.0
        if self.strike_mode == 'pts' and self.strike_width:
            half = self.strike_width
        else:
            half = spot * iv_decimal * math.sqrt(EM_DTE / 365.0)
        out['put_strike'] = round((spot - half) / 5) * 5
        out['call_strike'] = round((spot + half) / 5) * 5
        out['iv_decimal'] = iv_decimal

        if vix < 15 and iv_rank > 50:
            out['signal'] = 'strong_buy'
        elif vix < 20:
            out['signal'] = 'buy'
        else:
            out['signal'] = 'hold'
        return out

    # ----------------------------------------------------------- pricing
    def _opt_px(self, S, K, T, sigma, kind):
        if T <= 0:
            return max(0.0, (S - K) if kind == 'call' else (K - S))
        return black_scholes(S, K, T, RISK_FREE, sigma, kind, DIV_YIELD)

    def position_value(self, S, put_k, call_k, dte_short, dte_long, sigma,
                       strategy):
        """Per-contract value of the structure (long leg - shorts paid)."""
        sT, lT = dte_short / 365.0, dte_long / 365.0
        sig = sigma
        val = 0.0
        if strategy == 'double_calendar':
            # sell put+call @short, buy same strikes @long
            val += self._opt_px(S, put_k, lT, sig, 'put')
            val += self._opt_px(S, call_k, lT, sig, 'call')
            val -= self._opt_px(S, put_k, sT, sig, 'put')
            val -= self._opt_px(S, call_k, sT, sig, 'call')
        elif strategy == 'calendar_call':
            val += self._opt_px(S, call_k, lT, sig, 'call')
            val -= self._opt_px(S, call_k, sT, sig, 'call')
        elif strategy == 'calendar_put':
            val += self._opt_px(S, put_k, lT, sig, 'put')
            val -= self._opt_px(S, put_k, sT, sig, 'put')
        elif strategy == 'double_diagonal':
            # sell put+call @short; buy further-OTM wings @long
            wing_put, wing_call = put_k - 5, call_k + 5
            val += self._opt_px(S, wing_put, lT, sig, 'put')
            val += self._opt_px(S, wing_call, lT, sig, 'call')
            val -= self._opt_px(S, put_k, sT, sig, 'put')
            val -= self._opt_px(S, call_k, sT, sig, 'call')
        return max(val, 0.05)   # floor: spreads never worth less than nickel

    def short_deltas(self, S, put_k, call_k, dte_short, sigma):
        sT = max(dte_short, 0.5) / 365.0
        dp = calculate_greeks(S, put_k, sT, RISK_FREE, sigma, 'put', DIV_YIELD)['delta']
        dc = calculate_greeks(S, call_k, sT, RISK_FREE, sigma, 'call', DIV_YIELD)['delta']
        return abs(dp), abs(dc)

    # ------------------------------------------------------------ engine
    def run(self):
        df = self.df
        idx = df.index
        test_start = idx[-TEST_DAYS] if len(idx) > TEST_DAYS else idx[0]

        # Track A state (independent 1-contract trade per signal)
        a_open = None       # dict with trade bookkeeping
        # Track B state
        b_cash = ACCOUNT_START
        b_positions: list[dict] = []

        for i in range(idx.get_loc(test_start), len(idx)):
            row = df.iloc[i]
            d = idx[i].date()
            S = float(row.spot)
            sigma = float(row.rv21) / 100.0
            dec = self.brain_decide(row, d)

            log = {'date': d.isoformat(), 'spot': round(S, 2),
                   'vix': round(float(row.vix), 2),
                   'iv_rank': round(float(row.iv_rank), 1) if row.iv_rank == row.iv_rank else None,
                   'signal': dec['signal'], 'strategy': dec['strategy'],
                   'reason': dec.get('reason', '')}

            # ---------------- manage OPEN positions first (both tracks)
            def manage(pos, track):
                nonlocal b_cash
                entered = pos['entry_date']
                dte_total_s = pos['dte_short']
                dte_total_l = pos['dte_long']
                days_held = (d - entered).days
                dte_s = dte_total_s - days_held
                dte_l = dte_total_l - days_held
                val = self.position_value(S, pos['put_k'], pos['call_k'],
                                          dte_s, dte_l, sigma, pos['strategy'])
                if self.cost_pct > 0:
                    val *= (1 - self.cost_pct)
                basis = pos['basis']
                ret = val / basis - 1.0
                action, reason = None, ''

                if ret >= self.tp_pct:
                    action, reason = 'tp', f'take profit +{ret*100:.0f}%'
                elif ret <= -self.sl_pct:
                    action, reason = 'sl', f'stop loss {ret*100:.0f}%'
                elif dte_s < ROLL_DTE:
                    action, reason = 'roll_close', f'{dte_s} DTE < {ROLL_DTE}'
                else:
                    dp, dc = self.short_deltas(S, pos['put_k'], pos['call_k'],
                                               dte_s, sigma)
                    if max(dp, dc) > DELTA_ROLL_THRESHOLD:
                        action, reason = 'roll_close', 'short delta > 0.40'

                if dte_s <= 0:      # expiry forced close
                    action, reason = 'expiry', 'expiration'

                if not action:
                    pos['last_val'] = val
                    return None

                pnl_pc = (val - basis)
                t = SimTrade(symbol=self.symbol, track=track,
                             entry_date=entered.isoformat(), exit_date=d.isoformat(),
                             strategy=pos['strategy'], put_strike=pos['put_k'],
                             call_strike=pos['call_k'], contracts=pos['contracts'],
                             entry_debit=round(basis, 2), exit_value=round(val, 2),
                             pnl=round(pnl_pc * pos['contracts'] * 100, 2),
                             ret_on_debit=round(ret, 4), result=action, reason=reason,
                             rolls=pos['rolls'])
                if track == 'portfolio_1k':
                    b_cash += pnl_pc * pos['contracts'] * 100
                return t

            still_open_a, still_open_b = [], []
            if a_open:
                closed = manage(a_open, 'signal_edge')
                if closed:
                    self.trades.append(closed)
                    a_open = None
                else:
                    still_open_a.append(a_open)
            for p in b_positions:
                closed = manage(p, 'portfolio_1k')
                if closed:
                    self.trades.append(closed)
                else:
                    still_open_b.append(p)
            b_positions = still_open_b
            a_open = a_open if (a_open and a_open in still_open_a) else (
                a_open if a_open and not any(t.track == 'signal_edge' for t in []) else a_open)
            if a_open and a_open not in still_open_a:
                a_open = None

            # ---------------- new entries on non-avoid signals
            if dec['signal'] != 'avoid':
                put_k, call_k = dec['put_strike'], dec['call_strike']
                strat = dec['strategy']

                def open_pos(contracts, basis, track):
                    return {'entry_date': d, 'strategy': strat, 'put_k': put_k,
                            'call_k': call_k, 'dte_short': SHORT_DTE,
                            'dte_long': LONG_DTE, 'sigma': sigma,
                            'contracts': contracts, 'basis': basis,
                            'rolls': 0, 'track': track}

                # Track A: always 1 contract on fresh signal
                if a_open is None:
                    basis = self.position_value(S, put_k, call_k, SHORT_DTE,
                                                LONG_DTE, sigma, strat)
                    a_open = open_pos(1, basis, 'signal_edge')

                # Track B: strict sizing
                if len(b_positions) < MAX_POSITIONS:
                    est_debit = self.position_value(S, put_k, call_k, SHORT_DTE,
                                                    LONG_DTE, sigma, strat)
                    heat = sum(p['basis'] * p['contracts'] * 100 for p in b_positions)
                    risk_budget = ACCOUNT_START * RISK_PER_TRADE_PCT / 100.0
                    port_cap = ACCOUNT_START * MAX_PORTFOLIO_RISK_PCT / 100.0
                    n = int(risk_budget / est_debit) if est_debit > 0 else 0
                    while n > 0 and (heat + n * est_debit * 100) > port_cap:
                        n -= 1
                    cash_avail = b_cash - sum(p['basis'] * p['contracts'] * 100
                                              for p in b_positions)
                    while n > 0 and n * est_debit * 100 > cash_avail:
                        n -= 1
                    n = min(n, MAX_CONTRACTS_CAP)
                    if n >= 1:
                        b_positions.append(open_pos(n, est_debit, 'portfolio_1k'))
                        log['b_entry'] = {'contracts': n,
                                          'debit_per': round(est_debit, 2)}

            # equity curve (track B) = cash + open marks
            open_val = 0.0
            for p in b_positions:
                dh = (d - p['entry_date']).days
                v = self.position_value(S, p['put_k'], p['call_k'],
                                        p['dte_short'] - dh, p['dte_long'] - dh,
                                        sigma, p['strategy']) if p['dte_short'] - dh > 0 else 0.0
                open_val += (v - p['basis']) * p['contracts'] * 100
            eq = ACCOUNT_START + sum(t.pnl for t in self.trades
                                     if t.track == 'portfolio_1k') \
                + (b_cash - ACCOUNT_START) + open_val
            self.portfolio_equity[d.isoformat()] = round(eq, 2)
            log['portfolio_eq'] = round(eq, 2)
            self.daily_log.append(log)

        # force-close anything left at final bar
        last_i = len(self.df) - 1
        row = self.df.iloc[last_i]
        d = self.df.index[last_i].date()
        S = float(row.spot); sigma = float(row.rv21) / 100.0

        def force_close(pos, track):
            dh = (d - pos['entry_date']).days
            dte_s = pos['dte_short'] - dh
            val = self.position_value(S, pos['put_k'], pos['call_k'],
                                      max(dte_s, 0), max(dte_s + 7, 0),
                                      sigma, pos['strategy'])
            pnl_pc = (val - pos['basis'])
            self.trades.append(SimTrade(
                symbol=self.symbol, track=track,
                entry_date=pos['entry_date'].isoformat(), exit_date=d.isoformat(),
                strategy=pos['strategy'], put_strike=pos['put_k'],
                call_strike=pos['call_k'], contracts=pos['contracts'],
                entry_debit=round(pos['basis'], 2), exit_value=round(val, 2),
                pnl=round(pnl_pc * pos['contracts'] * 100, 2),
                ret_on_debit=round(pnl_pc / pos['basis'], 4),
                result='eod_close', reason='backtest ended',
                rolls=pos['rolls']))
        if a_open:
            force_close(a_open, 'signal_edge')
        for p in b_positions:
            force_close(p, 'portfolio_1k')

    # ------------------------------------------------------------ report
    def report(self) -> dict:
        def track_stats(track):
            ts = [t for t in self.trades if t.track == track and t.result != 'eod_close']
            if not ts:
                return {'trades': 0}
            wins = [t for t in ts if t.pnl > 0]
            pnl = sum(t.pnl for t in ts)
            rets = [t.ret_on_debit for t in ts]
            return {
                'trades': len(ts),
                'wins': len(wins),
                'win_rate': round(len(wins) / len(ts) * 100, 1),
                'total_pnl': round(pnl, 2),
                'avg_ret_on_debit': round(float(np.mean(rets)) * 100, 1),
                'avg_win': round(float(np.mean([t.pnl for t in wins])), 2) if wins else 0,
                'avg_loss': round(float(np.mean([t.pnl for t in ts if t.pnl <= 0])), 2)
                            if any(t.pnl <= 0 for t in ts) else 0,
                'tp_exits': sum(1 for t in ts if t.result == 'tp'),
                'sl_exits': sum(1 for t in ts if t.result == 'sl'),
                'roll_closes': sum(1 for t in ts if t.result == 'roll_close'),
                'expiries': sum(1 for t in ts if t.result == 'expiry'),
            }

        signals = [l for l in self.daily_log]
        avoids = [l for l in signals if l['signal'] == 'avoid']
        eq = list(self.portfolio_equity.values())

        return {
            'symbol': self.symbol,
            'period_start': self.daily_log[0]['date'] if self.daily_log else '',
            'period_end': self.daily_log[-1]['date'] if self.daily_log else '',
            'modeling_notes': [
                'vol input = 21d realized vol (same proxy as live site)',
                'Black-Scholes mid estimates; no bid-ask spread modeled',
                'entries/exits at daily closes',
                'FOMC guard from published meeting dates; QQQ has no earnings',
                'INDICATIVE results, not broker-exact fills',
            ],
            'signal_counts': {
                'strong_buy': sum(1 for l in signals if l['signal'] == 'strong_buy'),
                'buy': sum(1 for l in signals if l['signal'] == 'buy'),
                'hold': sum(1 for l in signals if l['signal'] == 'hold'),
                'avoid': len(avoids),
            },
            'avoid_reasons': dict(pd.Series([l['reason'] for l in avoids])
                                  .value_counts().head(6)) if avoids else {},
            'track_signal_edge': track_stats('signal_edge'),
            'track_portfolio_1k': {
                **track_stats('portfolio_1k'),
                'account_start': ACCOUNT_START,
                'final_equity': eq[-1] if eq else ACCOUNT_START,
                'return_pct': round((eq[-1] / ACCOUNT_START - 1) * 100, 2) if eq else 0,
                'max_drawdown_pct': round((min(eq) / max(eq[:eq.index(min(eq))] + [max(eq)]) - 1) * 100, 2)
                                     if eq and min(eq) < max(eq) else 0,
            },
            'equity_curve': {k: v for k, v in self.portfolio_equity.items()
                             if k[-2:] in ('01', '08', '15', '22')},  # weekly sample
            'recent_trades': [
                {'track': t.track, 'entry': t.entry_date, 'exit': t.exit_date,
                 'strategy': t.strategy, 'put_k': t.put_strike, 'call_k': t.call_strike,
                 'contracts': t.contracts, 'pnl': t.pnl,
                 'ret_pct': round(t.ret_on_debit * 100, 1), 'result': t.result}
                for t in sorted(self.trades, key=lambda x: x.exit_date)[-10:]
            ],
        }

    def save_trades_csv(self, path='research/ravish/backtest_trades.csv'):
        import csv
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['track', 'entry', 'exit', 'strategy', 'put_k', 'call_k',
                        'contracts', 'debit', 'exit_val', 'pnl', 'ret_pct',
                        'result', 'reason', 'rolls'])
            for t in self.trades:
                w.writerow([t.track, t.entry_date, t.exit_date, t.strategy,
                            t.put_strike, t.call_strike, t.contracts,
                            t.entry_debit, t.exit_value, t.pnl,
                            f"{t.ret_on_debit*100:.1f}", t.result, t.reason, t.rolls])


if __name__ == '__main__':
    bt = ThetaBrainBacktester('QQQ')
    print('Loading data...')
    bt.load_data()
    print(f'Data: {bt.df.index[0].date()} -> {bt.df.index[-1].date()} '
          f'({len(bt.df)} bars)')
    print('Running backtest...')
    bt.run()
    rep = bt.report()
    print(json.dumps(rep, indent=2, default=str))
    bt.save_trades_csv()
    Path('public/data').mkdir(exist_ok=True)
    Path('public/data/backtest.json').write_text(json.dumps(rep, default=str))
    print('Saved research/ravish/backtest_trades.csv + public/data/backtest.json')
