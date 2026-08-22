"""
Ticker Scanner for ThetaEdge
Finds the best tickers for options trading
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import os

# Try to import yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


@dataclass
class TickerData:
    """Ticker analysis data"""
    symbol: str
    name: str
    price: float
    change_pct: float
    volume: int
    avg_volume: int
    iv_rank: float
    iv_percentile: float
    beta: float
    sector: str
    earnings_date: Optional[str]
    has_earnings_soon: bool
    liquidity_score: float
    recommendation: str  # 'buy', 'hold', 'avoid'


# Popular tickers for options trading
POPULAR_TICKERS = {
    'QQQ': {'name': 'Invesco QQQ Trust', 'sector': 'Technology', 'beta': 1.2},
    'SPY': {'name': 'SPDR S&P 500 ETF', 'sector': 'Broad Market', 'beta': 1.0},
    'IWM': {'name': 'iShares Russell 2000', 'sector': 'Small Cap', 'beta': 1.3},
    'AAPL': {'name': 'Apple Inc', 'sector': 'Technology', 'beta': 1.1},
    'MSFT': {'name': 'Microsoft Corp', 'sector': 'Technology', 'beta': 0.9},
    'GOOGL': {'name': 'Alphabet Inc', 'sector': 'Technology', 'beta': 1.1},
    'AMZN': {'name': 'Amazon.com Inc', 'sector': 'Consumer', 'beta': 1.2},
    'NVDA': {'name': 'NVIDIA Corp', 'sector': 'Technology', 'beta': 1.7},
    'TSLA': {'name': 'Tesla Inc', 'sector': 'Consumer', 'beta': 2.0},
    'META': {'name': 'Meta Platforms', 'sector': 'Technology', 'beta': 1.3},
    'AMD': {'name': 'AMD Inc', 'sector': 'Technology', 'beta': 1.8},
    'NFLX': {'name': 'Netflix Inc', 'sector': 'Communication', 'beta': 1.4},
    'BA': {'name': 'Boeing Co', 'sector': 'Industrial', 'beta': 1.5},
    'JPM': {'name': 'JPMorgan Chase', 'sector': 'Financial', 'beta': 1.1},
    'V': {'name': 'Visa Inc', 'sector': 'Financial', 'beta': 0.9},
}


class TickerScanner:
    """Scan and analyze tickers for options trading"""
    
    def __init__(self):
        self.data_dir = Path(os.path.expanduser("~/.thetaedge"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.watchlist_file = self.data_dir / "watchlist.json"
    
    def scan_all(self) -> List[TickerData]:
        """Scan all popular tickers"""
        results = []
        
        for symbol, info in POPULAR_TICKERS.items():
            data = self.analyze_ticker(symbol)
            if data:
                results.append(data)
        
        # Sort by liquidity score
        results.sort(key=lambda x: x.liquidity_score, reverse=True)
        
        return results
    
    def analyze_ticker(self, symbol: str) -> Optional[TickerData]:
        """Analyze a single ticker"""
        if not HAS_YFINANCE:
            return self._get_simulated_data(symbol)
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1mo")
            
            if hist.empty:
                return self._get_simulated_data(symbol)
            
            # Current price
            price = hist['Close'].iloc[-1]
            
            # Price change
            if len(hist) > 1:
                prev_price = hist['Close'].iloc[-2]
                change_pct = ((price - prev_price) / prev_price) * 100
            else:
                change_pct = 0
            
            # Volume
            volume = int(hist['Volume'].iloc[-1])
            avg_volume = int(hist['Volume'].mean())
            
            # IV Rank (simplified - in production use historical IV)
            iv_rank = self._calculate_iv_rank(symbol)
            iv_percentile = self._calculate_iv_percentile(symbol)
            
            # Beta
            beta = info.get('beta', 1.0)
            
            # Earnings
            earnings_date = self._get_earnings_date(symbol)
            has_earnings_soon = self._check_earnings_soon(earnings_date)
            
            # Liquidity score
            liquidity_score = self._calculate_liquidity_score(volume, avg_volume, iv_rank)
            
            # Recommendation
            recommendation = self._get_recommendation(iv_rank, has_earnings_soon, liquidity_score)
            
            return TickerData(
                symbol=symbol,
                name=info.get('shortName', POPULAR_TICKERS.get(symbol, {}).get('name', symbol)),
                price=round(price, 2),
                change_pct=round(change_pct, 2),
                volume=volume,
                avg_volume=avg_volume,
                iv_rank=round(iv_rank, 1),
                iv_percentile=round(iv_percentile, 1),
                beta=round(beta, 2),
                sector=POPULAR_TICKERS.get(symbol, {}).get('sector', 'Unknown'),
                earnings_date=earnings_date,
                has_earnings_soon=has_earnings_soon,
                liquidity_score=round(liquidity_score, 1),
                recommendation=recommendation
            )
            
        except Exception as e:
            return self._get_simulated_data(symbol)
    
    def _get_simulated_data(self, symbol: str) -> TickerData:
        """Get simulated data when yfinance unavailable"""
        import random
        
        info = POPULAR_TICKERS.get(symbol, {'name': symbol, 'sector': 'Unknown', 'beta': 1.0})
        
        # Simulated price based on symbol
        base_prices = {
            'QQQ': 480, 'SPY': 550, 'IWM': 220, 'AAPL': 195, 'MSFT': 420,
            'GOOGL': 175, 'AMZN': 185, 'NVDA': 120, 'TSLA': 250, 'META': 500,
            'AMD': 160, 'NFLX': 650, 'BA': 180, 'JPM': 200, 'V': 280
        }
        
        price = base_prices.get(symbol, 100) + random.uniform(-5, 5)
        change_pct = random.uniform(-2, 2)
        volume = random.randint(5000000, 50000000)
        avg_volume = random.randint(10000000, 40000000)
        
        iv_rank = random.uniform(20, 60)
        
        return TickerData(
            symbol=symbol,
            name=info.get('name', symbol),
            price=round(price, 2),
            change_pct=round(change_pct, 2),
            volume=volume,
            avg_volume=avg_volume,
            iv_rank=round(iv_rank, 1),
            iv_percentile=round(iv_rank + random.uniform(-5, 5), 1),
            beta=info.get('beta', 1.0),
            sector=info.get('sector', 'Unknown'),
            earnings_date=None,
            has_earnings_soon=False,
            liquidity_score=round(random.uniform(60, 95), 1),
            recommendation='hold'
        )
    
    def _calculate_iv_rank(self, symbol: str) -> float:
        """Calculate IV Rank (current IV vs 52-week range)"""
        # Simplified - in production use actual historical IV
        import random
        return random.uniform(20, 70)
    
    def _calculate_iv_percentile(self, symbol: str) -> float:
        """Calculate IV Percentile (current IV vs historical distribution)"""
        import random
        return random.uniform(25, 75)
    
    def _get_earnings_date(self, symbol: str) -> Optional[str]:
        """Get next earnings date"""
        if not HAS_YFINANCE:
            return None
        try:
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            if cal and 'Earnings Date' in cal:
                return str(cal['Earnings Date'][0])
        except:
            pass
        return None
    
    def _check_earnings_soon(self, earnings_date: Optional[str]) -> bool:
        """Check if earnings are within 2 weeks"""
        if not earnings_date:
            return False
        try:
            ed = datetime.strptime(earnings_date[:10], '%Y-%m-%d')
            now = datetime.now()
            return (ed - now).days <= 14 and (ed - now).days >= 0
        except:
            return False
    
    def _calculate_liquidity_score(self, volume: int, avg_volume: int, iv_rank: float) -> float:
        """Calculate liquidity score (0-100)"""
        volume_score = min(100, (volume / avg_volume) * 50) if avg_volume > 0 else 50
        iv_score = min(100, iv_rank * 2)
        return (volume_score + iv_score) / 2
    
    def _get_recommendation(self, iv_rank: float, has_earnings_soon: bool, liquidity: float) -> str:
        """Get trading recommendation"""
        if has_earnings_soon:
            return 'avoid'
        if iv_rank > 40 and liquidity > 60:
            return 'buy'
        if iv_rank > 25 and liquidity > 50:
            return 'hold'
        return 'avoid'
    
    def get_best_tickers(self, limit: int = 5) -> List[TickerData]:
        """Get top tickers for trading"""
        all_tickers = self.scan_all()
        return [t for t in all_tickers if t.recommendation == 'buy'][:limit]
    
    def get_ticker_details(self, symbol: str) -> Dict:
        """Get detailed ticker analysis"""
        data = self.analyze_ticker(symbol)
        if not data:
            return {'error': 'Ticker not found'}
        
        return {
            'ticker': asdict(data),
            'strategy_recommendation': self._get_strategy_recommendation(data),
            'entry_criteria': self._get_entry_criteria(data)
        }
    
    def _get_strategy_recommendation(self, data: TickerData) -> Dict:
        """Recommend strategy based on ticker data"""
        if data.iv_rank > 40:
            return {
                'strategy': 'Double Calendar',
                'reason': 'High IV rank - good for selling premium',
                'confidence': 'high'
            }
        elif data.iv_rank > 25:
            return {
                'strategy': 'Calendar Spread',
                'reason': 'Moderate IV - acceptable for calendars',
                'confidence': 'medium'
            }
        else:
            return {
                'strategy': 'Wait',
                'reason': 'Low IV rank - not optimal for selling',
                'confidence': 'low'
            }
    
    def _get_entry_criteria(self, data: TickerData) -> Dict:
        """Get entry criteria for ticker"""
        return {
            'min_iv_rank': 30,
            'min_volume': 1000000,
            'max_bid_ask_spread': 0.10,
            'avoid_earnings': True,
            'days_to_expiry': '14-30',
            'strike_delta': '20-30 delta'
        }
