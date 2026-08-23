"""
ThetaBrain - Intelligent Trading Decision Engine
Uses real market data from Yahoo Finance
"""

import math
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
    # New optional inputs (defaulted so existing callers keep working)
    term_structure_ratio: Optional[float] = None   # VIX / VIX3M; >1 = backwardation
    iv_estimate: Optional[float] = None            # decimal ATM IV, e.g. 0.12
    debit_pct_estimate: Optional[float] = None     # calendar debit as % of spot, e.g. 0.012


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
            hist = ticker.history(period='1mo')
            
            price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
            volume = int(hist['Volume'].iloc[-1]) if not hist.empty else 0
            avg_volume = int(hist['Volume'].mean()) if not hist.empty else 0
            
            # Real IV Rank from 52-week realized-vol range (see iv_rank.py)
            iv_metrics = self._get_iv_rank(symbol)
            iv_rank = iv_metrics.get('iv_rank', 30.0)

            # VIX term structure: spot vs 3-month. Backwardation (>1) = stress.
            vix3m = None
            try:
                vix3m_info = yf.Ticker('^VIX3M').info
                vix3m = vix3m_info.get('regularMarketPrice')
            except Exception:
                vix3m = None
            term_ratio = round(vix / vix3m, 3) if vix3m else None

            # Expected move for ~30 DTE (drives strike selection)
            expected_move_30d = price * (iv_metrics.get('current_iv', 15.0) / 100) * math.sqrt(30 / 365)

            # Get earnings
            earnings_date = self._get_earnings_date(symbol)
            
            return {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'avg_volume': avg_volume,
                'vix': vix,
                'vix3m': vix3m,
                'term_structure_ratio': term_ratio,
                'iv_rank': iv_rank,
                'iv_metrics': iv_metrics,
                'expected_move_30d': round(expected_move_30d, 2),
                'earnings_date': earnings_date,
                'has_earnings_soon': self._check_earnings_soon(earnings_date),
                '_data_source': 'live'
            }
        except Exception as e:
            data = self._get_simulated_data()
            data['_data_source'] = 'simulated_fallback'
            data['_fallback_reason'] = str(e)[:120]
            return data
    
    def _get_iv_rank(self, symbol: str, current_price: float = None) -> dict:
        """Real IV Rank via IVRankCalculator (52w realized-vol range proxy)."""
        try:
            from .iv_rank import get_iv_rank
            return get_iv_rank(symbol)
        except Exception:
            return {'iv_rank': 30.0, 'iv_percentile': 30.0, 'current_iv': 15.0,
                    'iv_52w_high': 20.0, 'iv_52w_low': 10.0, 'source': 'fallback'}
    
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
        
        # Step 1: Should trade? (guard chain — any hit = AVOID)
        if inputs.vix_level > self.VIX_HIGH:
            reasoning.append(f"VIX at {inputs.vix_level} - too high")
            return self._create_avoid_output(inputs, reasoning, warnings)
        
        # Term-structure guard: backwardation (spot VIX > 3M VIX) = stress regime
        if getattr(inputs, 'term_structure_ratio', None) is not None and inputs.term_structure_ratio > 1.0:
            reasoning.append(f"VIX term structure inverted ({inputs.term_structure_ratio}) - stress regime")
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

        # Step 2b: Portfolio-level risk enforcement (previously dead constants)
        projected_risk = inputs.current_risk_pct + self.MAX_RISK_PER_TRADE
        if inputs.current_positions >= self.MAX_POSITIONS:
            reasoning.append(f"At max positions ({inputs.current_positions}/{self.MAX_POSITIONS})")
            return self._create_avoid_output(inputs, reasoning, warnings)
        if projected_risk > self.MAX_PORTFOLIO_RISK:
            reasoning.append(f"Portfolio risk would hit {projected_risk:.1f}% (max {self.MAX_PORTFOLIO_RISK}%)")
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
        
        # Step 4: Select strikes — expected-move based, adapts to vol regime
        # EM = S × IV × √(DTE/365); short strikes at ~1.0 EM each side
        iv_decimal = getattr(inputs, 'iv_estimate', None) or (inputs.iv_rank / 100 * 0.5 + 0.10)
        dte = 30
        em = inputs.price * (iv_decimal) * math.sqrt(dte / 365)
        put_strike = round((inputs.price - em) / 5) * 5
        call_strike = round((inputs.price + em) / 5) * 5
        reasoning.append(f"Strikes: Put {put_strike} / Call {call_strike} (±1.0 EM, EM=${em:.0f})")
        
        # Step 5: Position size — from ACTUAL estimated calendar debit
        # Double-calendar debit ≈ 0.5–2% of spot depending on IV; use BS-derived
        # estimate when iv_estimate provided, else 1.2% of spot as mid estimate.
        debit_pct_of_spot = getattr(inputs, 'debit_pct_estimate', None) or 0.012
        est_debit_per_contract = inputs.price * debit_pct_of_spot * 100
        risk_budget = inputs.account_size * (self.MAX_RISK_PER_TRADE / 100)
        contracts = min(int(risk_budget / est_debit_per_contract) if est_debit_per_contract > 0 else 0, 5)
        total_risk = contracts * est_debit_per_contract
        reasoning.append(f"Est. debit ${est_debit_per_contract:.0f}/contract; {contracts} contracts fits ${risk_budget:.0f} risk budget")
        
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
            f"IV Rank {inputs.iv_rank}%",
            f"Strategy: {strategy.replace('_', ' ').title()}",
            f"Strikes: Put {put_strike} / Call {call_strike}",
            f"Contracts: {contracts} (est. ${est_debit_per_contract:.0f} debit each)",
            "Place limit order at mid-price"
        ]
        
        exit_rules = [
            "Take profit at 30% of net debit",   # aligned to Ravish playbook 20-40%
            "Stop loss at 30% (mental)",
            "Roll if < 7 days to expiry",
            "Roll if short strike delta > 0.40"
        ]
        
        return BrainOutput(
            signal=signal,
            signal_strength=strength,
            recommended_strategy=strategy,
            strategy_confidence=confidence,
            suggested_put_strike=put_strike,
            suggested_call_strike=call_strike,
            recommended_contracts=contracts,
            max_risk_dollars=round(total_risk, 2),
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
