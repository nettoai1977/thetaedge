"""
Generate static market-data snapshots for the deployed web app.
Firebase Hosting is static-only — this script bakes real yfinance data
into public/data/*.json at deploy time so the frontend always has
recent real data even without a live backend.

Usage:  python3 scripts/snapshot_data.py   (run before `firebase deploy`)
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PUBLIC_DATA = Path(__file__).parent.parent / 'public' / 'data'
PUBLIC_DATA.mkdir(exist_ok=True)


def write(name, payload):
    out = PUBLIC_DATA / f'{name}.json'
    payload['_generated_at'] = datetime.now().isoformat()
    out.write_text(json.dumps(payload, default=str))
    print(f'  wrote {out.name} ({len(str(payload))} bytes)')


def main():
    print('Generating market-data snapshots...')

    # ---- Ticker scan snapshot ----
    try:
        from src.engine.data_cache import DataCache
        cache = DataCache()
        tickers = []
        for symbol in DataCache.RAVISH_TICKERS:
            try:
                info = cache.get_price(symbol, period='5d')
                if not info or not info.get('prices'):
                    continue
                prices = info['prices']
                last = prices[-1]
                prev = prices[-2] if len(prices) > 1 else last
                change_pct = round((last['close'] - prev['close']) / prev['close'] * 100, 2)
                avg_vol = sum(p['volume'] for p in prices[-30:]) / min(len(prices), 30)
                # Simple recommendation heuristic (same rules as ticker_scanner)
                iv_rank = estimate_iv_rank(symbol, cache)
                rec = recommend(iv_rank, change_pct, last['volume'], avg_vol)
                tickers.append({
                    'symbol': symbol,
                    'name': symbol,
                    'price': round(last['close'], 2),
                    'change_pct': change_pct,
                    'volume': int(last['volume'] or avg_vol),
                    'iv_rank': iv_rank,
                    'sector': '',
                    'recommendation': rec,
                })
            except Exception as e:
                print(f'  skip {symbol}: {e}')
        if tickers:
            write('tickers', {'tickers': tickers})
    except Exception as e:
        print(f'  ticker snapshot failed: {e}')

    # ---- VIX snapshot ----
    try:
        import yfinance as yf
        vix = yf.Ticker('^VIX')
        hist = vix.history(period='3mo')
        if not hist.empty:
            closes = hist['Close'].tolist()
            current = closes[-1]
            write('vix', {
                'current': round(current, 2),
                'avg_7d': round(sum(closes[-7:]) / len(closes[-7:]), 2),
                'avg_30d': round(sum(closes[-30:]) / len(closes[-30:]), 2),
                'min_30d': round(min(closes[-30:]), 2),
                'max_30d': round(max(closes[-30:]), 2),
                'history': {
                    'dates': [d.strftime('%m/%d') for d in hist.index[-30:]],
                    'values': [round(v, 2) for v in closes[-30:]],
                },
            })
    except Exception as e:
        print(f'  VIX snapshot failed: {e}')

    # ---- Options chain snapshot (QQQ ATM ±10 strikes) ----
    try:
        from src.engine.options_chain import OptionsChain
        chain = OptionsChain('QQQ').get_chain(0)
        calls = {c['strike']: c for c in chain['calls']}
        puts = {p['strike']: p for p in chain['puts']}
        strikes = sorted(set(calls) | set(puts))
        rows = []
        for s in strikes:
            c = calls.get(s, {})
            p = puts.get(s, {})
            iv = c.get('implied_volatility') or p.get('implied_volatility')
            rows.append({'strike': s, 'bid': c.get('bid', p.get('bid')),
                         'ask': c.get('ask', p.get('ask')), 'iv': iv})
        spot = chain['underlying_price']
        atm = min(rows, key=lambda r: abs(r['strike'] - spot))['strike']
        write('chain_qqq', {
            'symbol': 'QQQ', 'spot': spot, 'expiry': chain['expiry'],
            'atm_strike': atm,
            'options': [r for r in rows if abs(r['strike'] - spot) <= 50],
            'expirations': chain['expirations'],
        })
    except Exception as e:
        print(f'  chain snapshot failed: {e}')

    print('Done.')


def estimate_iv_rank(symbol, cache):
    """Rough IV-rank proxy from realized vol percentile over 1y."""
    try:
        import yfinance as yf
        hist = yf.Ticker(symbol).history(period='1y')['Close']
        rets = hist.pct_change().dropna()
        realized = rets.rolling(21).std().dropna() * (252 ** 0.5) * 100
        cur = realized.iloc[-1]
        return round((cur - realized.min()) / max(realized.max() - realized.min(), 0.01) * 100)
    except Exception:
        return 40


def recommend(iv_rank, change_pct, volume, avg_volume):
    if volume and avg_volume and volume < avg_volume * 0.5:
        return 'hold'
    if iv_rank >= 45:
        return 'buy'
    if iv_rank <= 20:
        return 'avoid'
    return 'hold'


if __name__ == '__main__':
    main()
