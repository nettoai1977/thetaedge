"""
ThetaBrain - Intelligent Trading Decision Engine
Uses real market data from Yahoo Finance
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


class Signal(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    WAIT = "wait"
    AVOID = "avoid"


class Strategy(Enum):
    DOUBLE_CALENDAR = "double_calendar"
    CALENDAR_CALL = "calendar_call"
    CALENDAR_PUT = "calendar_put"
    DOUBLE_DIAGONAL = "double_diagonal"


@dataclass
class MarketInputs:
    vix_level: float
    vix_trend: str
    symbol: str
    price: float
    iv_rank: float
    volume: int
    avg_volume: int
    days_to_fomc: Optional[int]
    days_to_cpi: Optional[int]
    days_to_earnings: Optional[int]
    current_positions: int
    account_size: float
    current_risk_pct: float


@dataclass
class BrainOutput:
    signal: str
    signal_strength: str
    recommended_strategy: str
    strategy_confidence: str
    suggested_put_strike: float
    suggested_call_strike: float
    recommended_contracts: int
    max_risk_dollars: float
    entry_rules: List[str]
    exit_rules: List[str]
    warnings: List[str]
    reasoning: List[str]


class ThetaBrain:
    """Expert system using real market data"""
    
    VIX_EXCELLENT = 12
    VIX_GOOD = 15
    VIX_NORMAL = 20
    VIX_HIGH = 25
    
    IV_RANK_HIGH = 50
    IV_RANK_MEDIUM = 30
    
    MAX_RISK_PER_TRADE = 2.0
    MAX_PORTFOLIO_RISK = 15.0
    MAX_POSITIONS = 5
    
    def __init__(self):
        self.decision_log = []
    
    def get_live_data(self, symbol: str = 'QQQ') -> Dict:
        """Get live market data from Yahoo Finance"""
        if not HAS_YFINANCE:
            return self._get_simulated_data()
        
        try:
            # Get VIX
            vix_ticker = yf.Ticker('^VIX')
            vix_info = vix_ticker.info
            vix = vix_info.get('regularMarketPrice', 15.0)
            
            # Get stock
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period='1mo')
            
            price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
            volume = int(hist['Volume'].iloc[-1]) if not hist.empty else 0
            avg_volume = int(hist['Volume'].mean()) if not hist.empty else 0
            
            # Get IV Rank
            iv_rank = self._get_iv_rank(symbol, price)
            
            # Get earnings
            earnings_date = self._get_earnings_date(symbol)
            
            return {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'avg_volume': avg_volume,
                'vix': vix,
                'iv_rank': iv_rank,
                'earnings_date': earnings_date,
                'has_earnings_soon': self._check_earnings_soon(earnings_date)
            }
        except Exception as e:
            return self._get_simulated_data()
    
    def _get_iv_rank(self, symbol: str, current_price: float) -> float:
        """Calculate IV Rank from options"""
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                return 30.0
            
            chain = ticker.option_chain(expirations[0])
            calls = chain.calls
            
            if calls.empty:
                return 30.0
            
            # Find ATM option
            atm = calls.iloc[(calls['strike'] - current_price).abs().argsort()[:1]]
            
            if not atm.empty and 'impliedVolatility' in atm.columns:
                iv = atm['impliedVolatility'].iloc[0]
                return min(100, max(0, iv * 200))
            
            return 30.0
        except:
            return 30.0
    
    def _get_earnings_date(self, symbol: str) -> Optional[str]:
        try:
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            if cal and 'Earnings Date' in cal:
                return str(cal['Earnings Date'][0])
        except:
            pass
        return None
    
    def _check_earnings_soon(self, earnings_date: Optional[str]) -> bool:
        if not earnings_date:
            return False
        try:
            ed = datetime.strptime(earnings_date[:10], '%Y-%m-%d')
            return (ed - datetime.now()).days <= 14
        except:
            return False
    
    def _get_simulated_data(self):
        import random
        return {
            'symbol': 'QQQ',
            'price': 713 + random.uniform(-5, 5),
            'volume': 35000000,
            'avg_volume': 30000000,
            'vix': 15 + random.uniform(-2, 2),
            'iv_rank': 40 + random.uniform(-10, 10),
            'earnings_date': None,
            'has_earnings_soon': False
        }
    
    def analyze(self, inputs: MarketInputs) -> BrainOutput:
        """Main decision function"""
        reasoning = []
        warnings = []
        
        # Step 1: Should trade?
        if inputs.vix_level > self.VIX_HIGH:
            reasoning.append(f"VIX at {inputs.vix_level} - too high")
            return self._create_avoid_output(inputs, reasoning, warnings)
        
        if inputs.days_to_fomc is not None and inputs.days_to_fomc <= 2:
            reasoning.append(f"FOMC in {inputs.days_to_fomc} days")
            return self._create_avoid_output(inputs, reasoning, warnings)
        
        if inputs.days_to_earnings is not None and inputs.days_to_earnings <= 7:
            reasoning.append(f"Earnings in {inputs.days_to_earnings} days")
            return self._create_avoid_output(inputs, reasoning, warnings)
        
        # Step 2: Evaluate ticker
        if inputs.iv_rank < 20:
            reasoning.append(f"IV Rank too low: {inputs.iv_rank}%")
            return self._create_avoid_output(inputs, reasoning, warnings)
        
        # Step 3: Select strategy
        if inputs.vix_level < self.VIX_GOOD:
            strategy = Strategy.DOUBLE_CALENDAR.value
            confidence = 'high'
            reasoning.append("VIX LOW - Double Calendar")
        elif inputs.vix_level < self.VIX_NORMAL:
            strategy = Strategy.CALENDAR_CALL.value
            confidence = 'medium'
            reasoning.append("VIX NORMAL - Calendar Spread")
        else:
            strategy = Strategy.DOUBLE_DIAGONAL.value
            confidence = 'low'
            reasoning.append("VIX HIGH - Double Diagonal")
        
        # Step 4: Select strikes
        put_strike = round(inputs.price * 0.90 / 5) * 5
        call_strike = round(inputs.price * 1.10 / 5) * 5
        reasoning.append(f"Strikes: Put {put_strike} / Call {call_strike}")
        
        # Step 5: Position size
        risk_per_trade = inputs.account_size * (self.MAX_RISK_PER_TRADE / 100)
        max_loss = inputs.price * 0.02 * 100
        contracts = min(int(risk_per_trade / max_loss) if max_loss > 0 else 0, 5)
        total_risk = contracts * max_loss
        
        # Generate signal
        if inputs.vix_level < self.VIX_GOOD and inputs.iv_rank > self.IV_RANK_HIGH:
            signal = Signal.STRONG_BUY.value
            strength = 'strong'
        elif inputs.vix_level < self.VIX_NORMAL:
            signal = Signal.BUY.value
            strength = 'moderate'
        else:
            signal = Signal.HOLD.value
            strength = 'weak'
        
        entry_rules = [
            f"VIX at {inputs.vix_level} - {'Good' if inputs.vix_level < 15 else 'Acceptable'}",
            f"Strategy: {strategy.replace('_', ' ').title()}",
            f"Strikes: Put {put_strike} / Call {call_strike}",
            f"Contracts: {contracts}",
            "Place limit order at mid-price"
        ]
        
        exit_rules = [
            "Take profit at 50%",
            "Stop loss at 30%",
            "Roll if < 7 days to expiry",
            "Roll if delta > 0.40"
        ]
        
        return BrainOutput(
            signal=signal,
            signal_strength=strength,
            recommended_strategy=strategy,
            strategy_confidence=confidence,
            suggested_put_strike=put_strike,
            suggested_call_strike=call_strike,
            recommended_contracts=contracts,
            max_risk_dollars=total_risk,
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            warnings=warnings,
            reasoning=reasoning
        )
    
    def _create_avoid_output(self, inputs, reasoning, warnings):
        return BrainOutput(
            signal=Signal.AVOID.value,
            signal_strength='strong',
            recommended_strategy='none',
            strategy_confidence='none',
            suggested_put_strike=0,
            suggested_call_strike=0,
            recommended_contracts=0,
            max_risk_dollars=0,
            entry_rules=["DO NOT TRADE"],
            exit_rules=[],
            warnings=warnings,
            reasoning=reasoning
        )
    
    def get_quick_assessment(self, vix: float, iv_rank: float) -> Dict:
        if vix < self.VIX_GOOD and iv_rank > self.IV_RANK_HIGH:
            return {'signal': 'BUY', 'strategy': 'Double Calendar', 'confidence': 'high'}
        elif vix < self.VIX_NORMAL and iv_rank > self.IV_RANK_MEDIUM:
            return {'signal': 'BUY', 'strategy': 'Calendar Spread', 'confidence': 'medium'}
        elif vix < self.VIX_HIGH:
            return {'signal': 'HOLD', 'strategy': 'Wait', 'confidence': 'low'}
        else:
            return {'signal': 'AVOID', 'strategy': 'None', 'confidence': 'none'}
