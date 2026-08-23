"""
IV Rank / IV Percentile — real calculation.

IV Rank = (current_IV − 52w_low) / (52w_high − 52w_low) × 100

Since free option-chain history isn't available, we use 21-day realized
volatility (annualized) as the IV proxy — the two track closely for index
ETFs and this is a standard approximation when a paid vol-history feed is
unavailable. The series is computed once per day from yfinance daily closes
and cached to data/iv_history.json.
"""
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

CACHE_FILE = Path(__file__).parent.parent / 'data' / 'iv_history.json'


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache['_generated_at'] = datetime.now().isoformat()
    CACHE_FILE.write_text(json.dumps(cache))


def _realized_vol_series(symbol: str, window: int = 21, lookback_days: int = 252) -> list:
    """Annualized rolling realized volatility over the past year."""
    hist = yf.Ticker(symbol).history(period=f'{lookback_days + window}d')['Close']
    rets = hist.pct_change().dropna()
    vol = rets.rolling(window).std() * math.sqrt(252)
    return [round(v * 100, 2) for v in vol.dropna().tolist()]


class IVRankCalculator:
    """Real IV Rank via 52-week realized-vol range."""

    def __init__(self, symbol: str = 'QQQ'):
        self.symbol = symbol.upper()

    def get_iv_metrics(self) -> dict:
        """
        Returns:
            {
              iv_rank: float,        # 0-100 within 52w realized-vol range
              iv_percentile: float,  # % of days below current vol
              current_iv: float,     # current annualized vol (proxy)
              iv_52w_high: float,
              iv_52w_low: float,
              source: 'realized_proxy' | 'cached'
            }
        """
        cache = _load_cache()
        entry = cache.get(self.symbol)
        today = date.today().isoformat()

        # Use today's cache entry if present
        if entry and entry.get('date') == today:
            return {**entry, 'source': 'cached'}

        if not HAS_YFINANCE:
            return {'iv_rank': 30.0, 'iv_percentile': 30.0, 'current_iv': 15.0,
                    'iv_52w_high': 20.0, 'iv_52w_low': 10.0, 'source': 'fallback'}

        try:
            series = _realized_vol_series(self.symbol)
            if len(series) < 30:
                raise ValueError('insufficient history')

            current = series[-1]
            hi = max(series)
            lo = min(series)
            rank = (current - lo) / (hi - lo) * 100 if hi > lo else 50.0
            pctile = sum(1 for v in series if v <= current) / len(series) * 100

            metrics = {
                'date': today,
                'iv_rank': round(rank, 1),
                'iv_percentile': round(pctile, 1),
                'current_iv': round(current, 2),
                'iv_52w_high': round(hi, 2),
                'iv_52w_low': round(lo, 2),
            }
            cache[self.symbol] = metrics
            _save_cache(cache)
            return {**metrics, 'source': 'realized_proxy'}
        except Exception as e:
            # Stale cache beats nothing
            if entry:
                return {**entry, 'source': 'stale_cache'}
            return {'iv_rank': 30.0, 'iv_percentile': 30.0, 'current_iv': 15.0,
                    'iv_52w_high': 20.0, 'iv_52w_low': 10.0, 'source': 'fallback'}


def get_iv_rank(symbol: str = 'QQQ') -> dict:
    """Module-level convenience function."""
    return IVRankCalculator(symbol).get_iv_metrics()
