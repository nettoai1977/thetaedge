"""
Local Data Cache for ThetaEdge
Stores historical data locally for offline use and backtesting
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


class DataCache:
    """Local data cache with fallback"""
    
    # Ravish's primary tickers (from research)
    RAVISH_TICKERS = ['SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    
    def __init__(self):
        self.cache_dir = Path(os.path.expanduser("~/.thetaedge/cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.prices_dir = self.cache_dir / "prices"
        self.prices_dir.mkdir(parents=True, exist_ok=True)
        
        self.options_dir = self.cache_dir / "options"
        self.options_dir.mkdir(parents=True, exist_ok=True)
        
        self.vix_file = self.cache_dir / "vix_history.json"
        self.ticker_data_file = self.cache_dir / "ticker_data.json"
    
    def get_price(self, symbol: str, period: str = '1mo') -> Optional[Dict]:
        """Get price data with local fallback"""
        cache_file = self.prices_dir / f"{symbol}_{period}.json"
        
        # Try to get fresh data
        if HAS_YFINANCE:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                
                if not hist.empty:
                    data = {
                        'symbol': symbol,
                        'period': period,
                        'last_updated': datetime.now().isoformat(),
                        'current_price': float(hist['Close'].iloc[-1]),
                        'prices': [
                            {
                                'date': str(date.date()),
                                'open': float(row['Open']),
                                'high': float(row['High']),
                                'low': float(row['Low']),
                                'close': float(row['Close']),
                                'volume': int(row['Volume'])
                            }
                            for date, row in hist.iterrows()
                        ]
                    }
                    
                    # Save to cache
                    with open(cache_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    return data
            except Exception as e:
                print(f"API error for {symbol}: {e}")
        
        # Fallback to cache
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def get_vix_history(self, days: int = 30) -> List[Dict]:
        """Get VIX history with local fallback"""
        cache_file = self.vix_file
        
        # Try fresh data
        if HAS_YFINANCE:
            try:
                vix = yf.Ticker('^VIX')
                hist = vix.history(period=f'{days}d')
                
                if not hist.empty:
                    data = [
                        {
                            'date': str(date.date()),
                            'close': float(row['Close']),
                            'high': float(row['High']),
                            'low': float(row['Low'])
                        }
                        for date, row in hist.iterrows()
                    ]
                    
                    # Save cache
                    with open(cache_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    return data
            except Exception as e:
                print(f"VIX API error: {e}")
        
        # Fallback
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        return []
    
    def get_options_chain(self, symbol: str, expiry: str = None) -> Optional[Dict]:
        """Get options chain with local fallback"""
        cache_file = self.options_dir / f"{symbol}_{expiry or 'latest'}.json"
        
        # Try fresh data
        if HAS_YFINANCE:
            try:
                ticker = yf.Ticker(symbol)
                expirations = ticker.options
                
                if not expirations:
                    return None
                
                if expiry is None:
                    expiry = expirations[0]
                
                chain = ticker.option_chain(expiry)
                
                # Get current price
                hist = ticker.history(period='1d')
                current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 100
                
                data = {
                    'symbol': symbol,
                    'expiry': expiry,
                    'underlying_price': current_price,
                    'last_updated': datetime.now().isoformat(),
                    'calls': chain.calls.to_dict('records'),
                    'puts': chain.puts.to_dict('records'),
                    'expirations': list(expirations)
                }
                
                # Convert any Timestamp objects to strings
                def convert_timestamps(obj):
                    if isinstance(obj, dict):
                        return {k: convert_timestamps(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_timestamps(i) for i in obj]
                    elif hasattr(obj, 'isoformat'):
                        return obj.isoformat()
                    return obj
                
                data = convert_timestamps(data)
                
                # Save cache
                with open(cache_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                return data
            except Exception as e:
                print(f"Options API error for {symbol}: {e}")
        
        # Fallback
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def download_all_ravish_tickers(self, period: str = '1y'):
        """Download historical data for all Ravish tickers"""
        print("Downloading data for Ravish's tickers...")
        
        for symbol in self.RAVISH_TICKERS:
            print(f"  Downloading {symbol}...")
            self.get_price(symbol, period)
            self.get_options_chain(symbol)
        
        # Download VIX
        print("  Downloading VIX...")
        self.get_vix_history(365)
        
        print("Done!")
    
    def get_cache_status(self) -> Dict:
        """Check what's in the cache"""
        status = {
            'prices': [],
            'options': [],
            'vix': False
        }
        
        # Check prices
        for f in self.prices_dir.glob('*.json'):
            symbol = f.stem.split('_')[0]
            status['prices'].append(symbol)
        
        # Check options
        for f in self.options_dir.glob('*.json'):
            symbol = f.stem.split('_')[0]
            status['options'].append(symbol)
        
        # Check VIX
        status['vix'] = self.vix_file.exists()
        
        return status
    
    def get_historical_prices(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """Get historical prices for backtesting"""
        # Try API first
        if HAS_YFINANCE:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date)
                
                if not hist.empty:
                    return [
                        {
                            'date': str(date.date()),
                            'open': float(row['Open']),
                            'high': float(row['High']),
                            'low': float(row['Low']),
                            'close': float(row['Close']),
                            'volume': int(row['Volume'])
                        }
                        for date, row in hist.iterrows()
                    ]
            except Exception as e:
                print(f"Historical API error: {e}")
        
        # Fallback to cached data
        cache_file = self.prices_dir / f"{symbol}_1y.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                data = json.load(f)
                prices = data.get('prices', [])
                # Filter by date range
                return [
                    p for p in prices
                    if start_date <= p['date'] <= end_date
                ]
        
        return []
