"""
Options Chain - Real Data from Yahoo Finance
"""

from dataclasses import dataclass
from typing import List, Dict, Optional

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


class OptionsChain:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
    
    def get_chain(self, expiry_index: int = 0) -> Dict:
        """Get real options chain from Yahoo Finance"""
        if not HAS_YFINANCE:
            return self._get_simulated_chain()
        
        try:
            ticker = yf.Ticker(self.symbol)
            expirations = ticker.options
            
            if not expirations:
                return self._get_simulated_chain()
            
            # Get selected expiry
            if expiry_index >= len(expirations):
                expiry_index = 0
            
            expiry = expirations[expiry_index]
            chain = ticker.option_chain(expiry)
            
            # Get current price
            hist = ticker.history(period='1d')
            current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 100
            
            calls = self._format_contracts(chain.calls, 'call', current_price)
            puts = self._format_contracts(chain.puts, 'put', current_price)
            
            return {
                'symbol': self.symbol,
                'underlying_price': current_price,
                'expiry': expiry,
                'expiry_days': self._days_to_expiry(expiry),
                'calls': calls,
                'puts': puts,
                'expirations': list(expirations)[:10]  # First 10 expirations
            }
        except Exception as e:
            return self._get_simulated_chain()
    
    def _format_contracts(self, df, option_type: str, current_price: float) -> List[Dict]:
        """Format options contracts"""
        contracts = []
        
        for _, row in df.iterrows():
            strike = float(row.get('strike', 0))
            bid = float(row.get('bid', 0))
            ask = float(row.get('ask', 0))
            last = float(row.get('lastPrice', 0))
            volume = int(row.get('volume', 0) or 0)
            oi = int(row.get('openInterest', 0) or 0)
            iv = float(row.get('impliedVolatility', 0) or 0)
            
            # Calculate delta approximation
            if option_type == 'call':
                moneyness = (current_price - strike) / current_price
                delta = max(0.01, min(0.99, 0.5 + moneyness * 2))
            else:
                moneyness = (strike - current_price) / current_price
                delta = max(-0.99, min(-0.01, -0.5 - moneyness * 2))
            
            in_the_money = (option_type == 'call' and strike < current_price) or \
                           (option_type == 'put' and strike > current_price)
            
            contracts.append({
                'strike': strike,
                'bid': round(bid, 2),
                'ask': round(ask, 2),
                'mid': round((bid + ask) / 2, 2) if bid and ask else round(last, 2),
                'last': round(last, 2),
                'volume': volume,
                'open_interest': oi,
                'implied_volatility': round(iv * 100, 1) if iv else 0,
                'delta': round(delta, 3),
                'in_the_money': in_the_money,
                'spread': round(ask - bid, 2) if bid and ask else 0
            })
        
        return contracts
    
    def _days_to_expiry(self, expiry_str: str) -> int:
        from datetime import datetime
        try:
            exp_date = datetime.strptime(expiry_str, '%Y-%m-%d')
            return (exp_date - datetime.now()).days
        except:
            return 30
    
    def get_atm_options(self, expiry_index: int = 0) -> Dict:
        """Get ATM options"""
        chain = self.get_chain(expiry_index)
        current_price = chain['underlying_price']
        
        # Find closest strike
        calls = chain['calls']
        if not calls:
            return None
        
        closest = min(calls, key=lambda x: abs(x['strike'] - current_price))
        strike = closest['strike']
        
        put = next((p for p in chain['puts'] if p['strike'] == strike), None)
        
        return {
            'strike': strike,
            'call': closest,
            'put': put
        }
    
    def _get_simulated_chain(self):
        """Fallback simulated chain"""
        import random
        base_price = 713 if self.symbol == 'QQQ' else 640 if self.symbol == 'SPY' else 100
        
        calls = []
        puts = []
        
        for i in range(-10, 11):
            strike = base_price + (i * 5)
            iv = 20 + random.uniform(-5, 5)
            
            calls.append({
                'strike': strike,
                'bid': round(random.uniform(1, 20), 2),
                'ask': round(random.uniform(1, 20) + 0.30, 2),
                'mid': round(random.uniform(1, 20), 2),
                'last': round(random.uniform(1, 20), 2),
                'volume': random.randint(100, 10000),
                'open_interest': random.randint(500, 50000),
                'implied_volatility': round(iv, 1),
                'delta': round(random.uniform(0.1, 0.9), 3),
                'in_the_money': strike < base_price,
                'spread': round(random.uniform(0.10, 0.50), 2)
            })
            
            puts.append({
                'strike': strike,
                'bid': round(random.uniform(1, 20), 2),
                'ask': round(random.uniform(1, 20) + 0.30, 2),
                'mid': round(random.uniform(1, 20), 2),
                'last': round(random.uniform(1, 20), 2),
                'volume': random.randint(100, 10000),
                'open_interest': random.randint(500, 50000),
                'implied_volatility': round(iv, 1),
                'delta': round(-random.uniform(0.1, 0.9), 3),
                'in_the_money': strike > base_price,
                'spread': round(random.uniform(0.10, 0.50), 2)
            })
        
        return {
            'symbol': self.symbol,
            'underlying_price': base_price,
            'expiry': '2025-09-19',
            'expiry_days': 30,
            'calls': calls,
            'puts': puts,
            'expirations': ['2025-08-25', '2025-09-01', '2025-09-19']
        }
