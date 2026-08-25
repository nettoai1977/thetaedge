"""Runner: executes the ThetaBrain validation study end-to-end.
Usage: .venv/bin/python scripts/run_backtest.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.backtest import ThetaBrainBacktester  # noqa: E402


def main():
    bt = ThetaBrainBacktester('QQQ')
    print('Loading market data...')
    bt.load_data()
    print(f'Data: {bt.df.index[0].date()} -> {bt.df.index[-1].date()} '
          f'({len(bt.df)} bars)')
    print('Replaying decisions...')
    bt.run()
    rep = bt.report()
    print(json.dumps(rep, indent=2, default=str))
    bt.save_trades_csv()
    outdir = Path(__file__).parent.parent / 'public' / 'data'
    outdir.mkdir(exist_ok=True)
    (outdir / 'backtest.json').write_text(json.dumps(rep, default=str))
    print('Saved research/ravish/backtest_trades.csv + public/data/backtest.json')


if __name__ == '__main__':
    main()
