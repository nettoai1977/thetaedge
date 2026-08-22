"""
Options Chain for ThetaEdge
Shows all available strikes and premiums
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import random


@dataclass
class OptionContract:
    """Single option contract"""
    strike: float
    expiry: str
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    mid: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    in_the_money: bool


class OptionsChain:
    """Generate options chain data"""
    
    def __init__(self, symbol: str, current_price: float):
        self.symbol = symbol
        self.current_price = current_price
    
    def get_chain(self, expiry_days: int = 30) -> Dict:
        """Get full options chain"""
        strikes = self._generate_strikes()
        
        calls = []
        puts = []
        
        for strike in strikes:
            call = self._create_option(strike, 'call', expiry_days)
            put = self._create_option(strike, 'put', expiry_days)
            calls.append(asdict(call))
            puts.append(asdict(put))
        
        return {
            'symbol': self.symbol,
            'underlying_price': self.current_price,
            'expiry_days': expiry_days,
            'calls': calls,
            'puts': puts
        }
    
    def _generate_strikes(self) -> List[float]:
        """Generate strike prices around current price"""
        strikes = []
        step = self._get_strike_step()
        
        # Generate strikes from -20% to +20%
        low = self.current_price * 0.8
        high = self.current_price * 1.2
        
        strike = round(low / step) * step
        while strike <= high:
            strikes.append(round(strike, 2))
            strike += step
        
        return strikes
    
    def _get_strike_step(self) -> float:
        """Get strike step based on price"""
        if self.current_price < 50:
            return 1
        elif self.current_price < 200:
            return 5
        elif self.current_price < 500:
            return 5
        else:
            return 10
    
    def _create_option(self, strike: float, option_type: str, days: int) -> OptionContract:
        """Create option contract with simulated data"""
        import math
        
        T = days / 365
        r = 0.05
        sigma = 0.25
        
        # Simplified Black-Scholes approximation
        if option_type == 'call':
            moneyness = (self.current_price - strike) / self.current_price
            delta = max(0.05, min(0.95, 0.5 + moneyness * 2))
        else:
            moneyness = (strike - self.current_price) / self.current_price
            delta = max(-0.95, min(-0.05, -0.5 - moneyness * 2))
        
        # Price approximation
        intrinsic = max(0, (self.current_price - strike) if option_type == 'call' else (strike - self.current_price))
        time_value = self.current_price * sigma * math.sqrt(T) * 0.4
        mid = intrinsic + time_value
        
        bid = round(mid * 0.95, 2)
        ask = round(mid * 1.05, 2)
        mid = round(mid, 2)
        
        # Greeks approximation
        gamma = 0.02 / math.sqrt(T) if T > 0 else 0
        theta = -(mid * 0.05) / 30 if days > 0 else 0
        vega = self.current_price * 0.001 * math.sqrt(T)
        
        in_the_money = (option_type == 'call' and strike < self.current_price) or \
                       (option_type == 'put' and strike > self.current_price)
        
        return OptionContract(
            strike=strike,
            expiry=f"{days}D",
            option_type=option_type,
            bid=bid,
            ask=ask,
            mid=mid,
            last=mid,
            volume=random.randint(100, 10000),
            open_interest=random.randint(500, 50000),
            implied_volatility=round(sigma + random.uniform(-0.05, 0.05), 3),
            delta=round(delta, 3),
            gamma=round(gamma, 4),
            theta=round(theta, 3),
            vega=round(vega, 3),
            in_the_money=in_the_money
        )
    
    def get_atm_options(self, expiry_days: int = 30) -> Dict:
        """Get at-the-money options"""
        chain = self.get_chain(expiry_days)
        
        # Find closest strike to current price
        calls = chain['calls']
        closest = min(calls, key=lambda x: abs(x['strike'] - self.current_price))
        
        return {
            'strike': closest['strike'],
            'call': closest,
            'put': next(p for p in chain['puts'] if p['strike'] == closest['strike'])
        }
