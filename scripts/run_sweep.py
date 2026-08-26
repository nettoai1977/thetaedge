"""
Parameter Sweep + Monte Carlo for ThetaBrain
============================================
1. Grid search: strike mode/width x take-profit x stop-loss
   (54 configurations over the same 12-month replay)
2. Block-bootstrap Monte Carlo on the best config's trades
   (2000 resamples, blocks of 5 to preserve regime clustering)
     - P&L percentile bands, P(strategy has any edge), drawdown dist.

Usage: source .venv/bin/activate && python scripts/run_sweep.py
Output: research/ravish/sweep_results.json + console tables
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.engine.backtest import ThetaBrainBacktester   # noqa: E402


def run_config(df, **kw):
    bt = ThetaBrainBacktester('QQQ', **kw)
    bt.df = df                      # reuse shared data (no refetch)
    bt.run()
    rep = bt.report()
    p1k = rep['track_portfolio_1k']
    edge = rep['track_signal_edge']
    return {
        'params': kw,
        'pnl_1k': p1k.get('total_pnl', 0),
        'win_rate': p1k.get('win_rate', 0),
        'trades': p1k.get('trades', 0),
        'max_dd': p1k.get('max_drawdown_pct', 0),
        'return_pct': p1k.get('return_pct', 0),
        'edge_pnl': edge.get('total_pnl', 0),
        'edge_trades': edge.get('trades', 0),
        'edge_win_rate': edge.get('win_rate', 0),
        '_bt': bt,
    }


def block_bootstrap(trade_pnls, n_iter=2000, block=5, seed=42):
    """Circular block bootstrap of trade P&L sequence."""
    rng = np.random.default_rng(seed)
    x = np.asarray(trade_pnls, dtype=float)
    n = len(x)
    if n == 0:
        return {}
    n_blocks = int(np.ceil(n / block))
    totals = np.empty(n_iter)
    means = np.empty(n_iter)
    for i in range(n_iter):
        starts = rng.integers(0, n, n_blocks)
        sample = np.concatenate([x[(s + np.arange(block)) % n] for s in starts])[:n]
        totals[i] = sample.sum()
        means[i] = sample.mean()
    return {
        'total_pnl_p05': round(float(np.percentile(totals, 5)), 2),
        'total_pnl_p50': round(float(np.percentile(totals, 50)), 2),
        'total_pnl_p95': round(float(np.percentile(totals, 95)), 2),
        'mean_per_trade_p05': round(float(np.percentile(means, 5)), 2),
        'mean_per_trade_p95': round(float(np.percentile(means, 95)), 2),
        'prob_edge_positive': round(float((totals > 0).mean()) * 100, 1),
        'iterations': n_iter,
        'block_size': block,
    }


def main():
    print('Loading shared dataset...')
    base = ThetaBrainBacktester('QQQ')
    base.load_data()
    df = base.df
    print(f'Data: {df.index[0].date()} -> {df.index[-1].date()} ({len(df)} bars)\n')

    # ---------------- grid ----------------
    strike_cfgs = [('pts', 5.0), ('pts', 10.0), ('pts', 15.0), ('pts', 20.0),
                   ('pts', 25.0), ('em', None)]
    tps = [0.20, 0.30, 0.40]
    sls = [0.20, 0.30, 0.40]

    results = []
    total = len(strike_cfgs) * len(tps) * len(sls)
    done = 0
    for (smode, swidth), tp, sl in itertools.product(strike_cfgs, tps, sls):
        r = run_config(df, strike_mode=smode, strike_width=swidth,
                       tp_pct=tp, sl_pct=sl)
        r.pop('_bt')
        results.append(r)
        done += 1
        label = f'{smode}{("+%dpt" % swidth) if swidth else ""}'
        print(f'[{done:02d}/{total}] {label:>8} TP{tp:.0%} SL{sl:.0%} -> '
              f'PnL ${r["pnl_1k"]:>7.2f} | WR {r["win_rate"]}% | '
              f'DD {r["max_dd"]}%')

    # rank by portfolio P&L
    results.sort(key=lambda r: r['pnl_1k'], reverse=True)
    print('\n=== TOP 8 CONFIGURATIONS (by $1k-account P&L) ===')
    for r in results[:8]:
        p = r['params']
        label = f"{p['strike_mode']}" + (f"+{p['strike_width']:.0f}pt" if p['strike_width'] else "")
        print(f"  {label:>8} TP{p['tp_pct']:.0%} SL{p['sl_pct']:.0%} -> "
              f"${r['pnl_1k']:>8.2f} ({r['return_pct']:+.1f}%) WR {r['win_rate']}% DD {r['max_dd']}%")

    # ---------------- Monte Carlo on top config + current default ----------
    print('\n=== MONTE CARLO (block bootstrap, 2000 paths) ===')
    mc_out = {}
    for tag, kw in [('best', results[0]['params']),
                    ('current_default', dict(strike_mode='em', tp_pct=0.30,
                                             sl_pct=0.30))]:
        bt = ThetaBrainBacktester('QQQ', **kw)
        bt.df = df
        bt.run()
        pnls = [t.pnl for t in bt.trades
                if t.track == 'signal_edge' and t.result != 'eod_close']
        rets = [t.ret_on_debit for t in bt.trades
                if t.track == 'signal_edge' and t.result != 'eod_close']
        mc = block_bootstrap(pnls)
        wr_samples = None
        if rets:
            arr = np.asarray(rets)
            mc['avg_ret_on_debit_pct'] = round(float(arr.mean()) * 100, 2)
            mc['trades_in_sample'] = int(len(arr))
        mc_out[tag] = {'config': {k: v for k, v in kw.items()},
                       'raw_trades': len(pnls), 'raw_total_pnl':
                           round(sum(pnls), 2), **mc}
        print(f"  [{tag}] {kw}")
        print(f"    raw: {len(pnls)} trades, ${sum(pnls):.2f}")
        if mc:
            print(f"    bootstrap P&L: p05 ${mc['total_pnl_p05']} | "
                  f"median ${mc['total_pnl_p50']} | p95 ${mc['total_pnl_p95']}")
            print(f"    P(edge > 0): {mc['prob_edge_positive']}%")

    # sensitivity note: how much does cost matter on the best config?
    best_kw = results[0]['params']
    for cpct in (0.03, 0.06):
        r = run_config(df, **{**best_kw, 'cost_pct': cpct})
        r.pop('_bt')
        print(f"  best-config with {cpct:.0%} round-trip cost -> "
              f"PnL ${r['pnl_1k']:.2f} (was ${results[0]['pnl_1k']:.2f})")
        mc_out[f'cost_{int(cpct*100)}pct'] = {'pnl_1k': r['pnl_1k'],
                                              'win_rate': r['win_rate']}

    out = {'top_configs': results[:12], 'all_count': len(results),
           'monte_carlo': mc_out}
    outdir = ROOT / 'research' / 'ravish'
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'sweep_results.json').write_text(json.dumps(out, indent=1, default=str))
    print('\nSaved research/ravish/sweep_results.json')


if __name__ == '__main__':
    main()
