"""
ThetaBrain - Intelligent Trading Decision Engine
Mimics Ravish's decision-making process for options trading
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum


class Signal(Enum):
    """Trading signals"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    WAIT = "wait"
    AVOID = "avoid"
    STRONG_AVOID = "strong_avoid"


class Strategy(Enum):
    """Available strategies"""
    DOUBLE_CALENDAR = "double_calendar"
    CALENDAR_CALL = "calendar_call"
    CALENDAR_PUT = "calendar_put"
    DOUBLE_DIAGONAL = "double_diagonal"
    TIME_SPREAD = "time_spread"


@dataclass
class MarketInputs:
    """Market data inputs for decision engine"""
    # VIX
    vix_level: float
    vix_trend: str  # 'rising', 'falling', 'stable'
    
    # Ticker data
    symbol: str
    price: float
    iv_rank: float
    volume: int
    avg_volume: int
    
    # Calendar
    days_to_fomc: Optional[int]
    days_to_cpi: Optional[int]
    days_to_earnings: Optional[int]
    
    # Position
    current_positions: int
    account_size: float
    current_risk_pct: float


@dataclass
class BrainOutput:
    """ThetaBrain decision output"""
    signal: str
    signal_strength: str  # 'strong', 'moderate', 'weak'
    
    # Strategy recommendation
    recommended_strategy: str
    strategy_confidence: str  # 'high', 'medium', 'low'
    
    # Strike selection
    suggested_put_strike: float
    suggested_call_strike: float
    
    # Position sizing
    recommended_contracts: int
    max_risk_dollars: float
    
    # Entry criteria
    entry_rules: List[str]
    
    # Exit rules
    exit_rules: List[str]
    
    # Risk warnings
    warnings: List[str]
    
    # Reasoning
    reasoning: List[str]


class ThetaBrain:
    """
    Expert system that mimics Ravish's trading decisions
    
    Decision Flow:
    1. Should I trade? (VIX + Calendar check)
    2. Which ticker? (IV Rank + Liquidity)
    3. Which strategy? (VIX Regime)
    4. Which strikes? (Delta + Premium)
    5. How many? (Position Sizing)
    6. When to exit? (Rules)
    
    Architecture: Guard Chain Pattern
    - Each step is a "guard" that can veto the trade
    - All guards run, veto recorded for audit
    - Single source of truth, no parallel signal paths
    """
    
    # ==================== RULE THRESHOLDS ====================
    
    # VIX Regime thresholds
    VIX_EXCELLENT = 12
    VIX_GOOD = 15
    VIX_NORMAL = 20
    VIX_HIGH = 25
    VIX_EXTREME = 30
    
    # IV Rank thresholds
    IV_RANK_HIGH = 50
    IV_RANK_MEDIUM = 30
    IV_RANK_LOW = 20
    
    # Liquidity thresholds
    MIN_VOLUME = 1000000
    MIN_OPEN_INTEREST = 500
    
    # Risk thresholds
    MAX_RISK_PER_TRADE = 2.0  # %
    MAX_PORTFOLIO_RISK = 15.0  # %
    MAX_POSITIONS = 5
    
    # Exit thresholds
    TAKE_PROFIT_PCT = 50
    STOP_LOSS_PCT = 30
    ROLL_DAYS = 7
    ROLL_DELTA = 0.40
    
    def __init__(self):
        self.decision_log = []
    
    def analyze(self, inputs: MarketInputs) -> BrainOutput:
        """
        Main decision function - The Brain at work
        
        Uses Guard Chain Pattern:
        - Each guard evaluates independently
        - Any guard can veto (return AVOID)
        - All reasons recorded for audit trail
        """
        reasoning = []
        warnings = []
        entry_rules = []
        exit_rules = []
        guards_consulted = []
        
        # ==================== STEP 1: SHOULD TRADE? ====================
        should_trade, step1_reasons = self._should_trade(inputs)
        reasoning.extend(step1_reasons)
        guards_consulted.append(('MARKET_HOURS', should_trade))
        
        if not should_trade:
            return self._create_avoid_output(inputs, reasoning, warnings, guards_consulted)
        
        # ==================== STEP 2: WHICH TICKER? ====================
        ticker_ok, step2_reasons = self._evaluate_ticker(inputs)
        reasoning.extend(step2_reasons)
        guards_consulted.append(('TICKER_QUALITY', ticker_ok))
        
        if not ticker_ok:
            return self._create_avoid_output(inputs, reasoning, warnings, guards_consulted)
        
        # ==================== STEP 3: WHICH STRATEGY? ====================
        strategy, confidence, step3_reasons = self._select_strategy(inputs)
        reasoning.extend(step3_reasons)
        guards_consulted.append(('STRATEGY_SELECT', True))
        
        # ==================== STEP 4: WHICH STRIKES? ====================
        put_strike, call_strike, step4_reasons = self._select_strikes(inputs, strategy)
        reasoning.extend(step4_reasons)
        guards_consulted.append(('STRIKE_SELECT', True))
        
        # ==================== STEP 5: HOW MANY? ====================
        contracts, max_risk, step5_reasons, step5_warnings = self._size_position(inputs)
        reasoning.extend(step5_reasons)
        warnings.extend(step5_warnings)
        guards_consulted.append(('POSITION_SIZE', contracts > 0))
        
        # ==================== STEP 6: ENTRY/EXIT RULES ====================
        entry_rules = self._get_entry_rules(inputs, strategy)
        exit_rules = self._get_exit_rules()
        guards_consulted.append(('RULES_LOADED', True))
        
        # ==================== GENERATE SIGNAL ====================
        signal, strength = self._generate_signal(inputs, strategy, confidence)
        
        # Log decision for audit
        self._log_decision(inputs, signal, guards_consulted)
        
        return BrainOutput(
            signal=signal,
            signal_strength=strength,
            recommended_strategy=strategy,
            strategy_confidence=confidence,
            suggested_put_strike=put_strike,
            suggested_call_strike=call_strike,
            recommended_contracts=contracts,
            max_risk_dollars=max_risk,
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            warnings=warnings,
            reasoning=reasoning
        )
    
    # ==================== STEP 1: SHOULD TRADE? ====================
    
    def _should_trade(self, inputs: MarketInputs) -> Tuple[bool, List[str]]:
        """Determine if market conditions are favorable"""
        reasons = []
        
        # Check VIX level
        if inputs.vix_level > self.VIX_EXTREME:
            reasons.append(f"❌ VIX at {inputs.vix_level} - EXTREME volatility, no trades")
            return False, reasons
        
        if inputs.vix_level > self.VIX_HIGH:
            reasons.append(f"⚠️ VIX at {inputs.vix_level} - HIGH volatility, wait for better entry")
            return False, reasons
        
        if inputs.vix_level < self.VIX_EXCELLENT:
            reasons.append(f"✅ VIX at {inputs.vix_level} - EXCELLENT for selling premium")
        elif inputs.vix_level < self.VIX_GOOD:
            reasons.append(f"✅ VIX at {inputs.vix_level} - GOOD for selling premium")
        elif inputs.vix_level < self.VIX_NORMAL:
            reasons.append(f"✅ VIX at {inputs.vix_level} - NORMAL conditions, acceptable")
        
        # Check FOMC
        if inputs.days_to_fomc is not None and inputs.days_to_fomc <= 2:
            reasons.append(f"⚠️ FOMC in {inputs.days_to_fomc} days - WAIT")
            return False, reasons
        
        # Check CPI
        if inputs.days_to_cpi is not None and inputs.days_to_cpi <= 1:
            reasons.append(f"⚠️ CPI report tomorrow - WAIT")
            return False, reasons
        
        # Check portfolio risk
        if inputs.current_risk_pct > self.MAX_PORTFOLIO_RISK:
            reasons.append(f"⚠️ Portfolio risk at {inputs.current_risk_pct}% - max {self.MAX_PORTFOLIO_RISK}%")
            return False, reasons
        
        if inputs.current_positions >= self.MAX_POSITIONS:
            reasons.append(f"⚠️ {inputs.current_positions} open positions - max {self.MAX_POSITIONS}")
            return False, reasons
        
        reasons.append("✅ Market conditions favorable for trading")
        return True, reasons
    
    # ==================== STEP 2: WHICH TICKER? ====================
    
    def _evaluate_ticker(self, inputs: MarketInputs) -> Tuple[bool, List[str]]:
        """Evaluate if ticker is suitable"""
        reasons = []
        
        # Check IV Rank
        if inputs.iv_rank < self.IV_RANK_LOW:
            reasons.append(f"❌ {inputs.symbol} IV Rank at {inputs.iv_rank}% - too low for selling")
            return False, reasons
        
        if inputs.iv_rank > self.IV_RANK_HIGH:
            reasons.append(f"✅ {inputs.symbol} IV Rank at {inputs.iv_rank}% - HIGH, excellent for selling")
        elif inputs.iv_rank > self.IV_RANK_MEDIUM:
            reasons.append(f"✅ {inputs.symbol} IV Rank at {inputs.iv_rank}% - MEDIUM, acceptable")
        
        # Check volume/liquidity
        if inputs.volume < self.MIN_VOLUME:
            reasons.append(f"⚠️ {inputs.symbol} volume at {inputs.volume:,} - below minimum {self.MIN_VOLUME:,}")
            return False, reasons
        
        volume_ratio = inputs.volume / inputs.avg_volume if inputs.avg_volume > 0 else 1
        if volume_ratio > 1.2:
            reasons.append(f"✅ {inputs.symbol} volume {volume_ratio:.1f}x average - HIGH liquidity")
        
        # Check earnings
        if inputs.days_to_earnings is not None and inputs.days_to_earnings <= 7:
            reasons.append(f"⚠️ {inputs.symbol} earnings in {inputs.days_to_earnings} days - AVOID")
            return False, reasons
        
        reasons.append(f"✅ {inputs.symbol} meets all criteria")
        return True, reasons
    
    # ==================== STEP 3: WHICH STRATEGY? ====================
    
    def _select_strategy(self, inputs: MarketInputs) -> Tuple[str, str, List[str]]:
        """Select best strategy based on VIX regime"""
        reasons = []
        
        if inputs.vix_level < self.VIX_GOOD:
            # Low VIX - Double Calendar
            reasons.append("📊 VIX regime: LOW → Double Calendar (max theta)")
            return Strategy.DOUBLE_CALENDAR.value, 'high', reasons
        
        elif inputs.vix_level < self.VIX_NORMAL:
            # Normal VIX - Calendar Spread
            reasons.append("📊 VIX regime: NORMAL → Calendar Spread")
            return Strategy.CALENDAR_CALL.value, 'medium', reasons
        
        elif inputs.vix_level < self.VIX_HIGH:
            # High VIX - Double Diagonal
            reasons.append("📊 VIX regime: HIGH → Double Diagonal (lower vega)")
            return Strategy.DOUBLE_DIAGONAL.value, 'medium', reasons
        
        else:
            # Very high VIX - Time Spread
            reasons.append("📊 VIX regime: VERY HIGH → Time Spread (defined risk)")
            return Strategy.TIME_SPREAD.value, 'low', reasons
    
    # ==================== STEP 4: WHICH STRIKES? ====================
    
    def _select_strikes(
        self, inputs: MarketInputs, strategy: str
    ) -> Tuple[float, float, List[str]]:
        """Select strike prices"""
        reasons = []
        
        if strategy == Strategy.DOUBLE_CALENDAR.value:
            # 10% OTM each side
            put_strike = round(inputs.price * 0.90 / 5) * 5
            call_strike = round(inputs.price * 1.10 / 5) * 5
            reasons.append(f"🎯 Strikes: Put {put_strike} / Call {call_strike} (10% OTM)")
        
        elif strategy == Strategy.CALENDAR_CALL.value:
            # 20-30 delta (slightly OTM)
            call_strike = round(inputs.price * 1.05 / 5) * 5
            put_strike = call_strike
            reasons.append(f"🎯 Strike: {call_strike} (slightly OTM)")
        
        elif strategy == Strategy.DOUBLE_DIAGONAL.value:
            # Wider strikes for high IV
            put_strike = round(inputs.price * 0.85 / 5) * 5
            call_strike = round(inputs.price * 1.15 / 5) * 5
            reasons.append(f"🎯 Strikes: Put {put_strike} / Call {call_strike} (15% OTM)")
        
        else:
            # Default
            put_strike = round(inputs.price * 0.95 / 5) * 5
            call_strike = round(inputs.price * 1.05 / 5) * 5
            reasons.append(f"🎯 Strikes: {put_strike} / {call_strike}")
        
        return put_strike, call_strike, reasons
    
    # ==================== STEP 5: HOW MANY? ====================
    
    def _size_position(
        self, inputs: MarketInputs
    ) -> Tuple[int, float, List[str], List[str]]:
        """Calculate position size"""
        reasons = []
        warnings = []
        
        # Simplified position sizing
        risk_per_trade = inputs.account_size * (self.MAX_RISK_PER_TRADE / 100)
        max_loss_per_contract = inputs.price * 0.02 * 100  # ~2% of stock price
        
        if max_loss_per_contract > 0:
            contracts = int(risk_per_trade / max_loss_per_contract)
        else:
            contracts = 0
        
        contracts = min(contracts, 5)  # Cap at 5
        total_risk = contracts * max_loss_per_contract
        
        reasons.append(f"📐 Position size: {contracts} contracts")
        reasons.append(f"📐 Max risk: ${total_risk:,.0f} ({self.MAX_RISK_PER_TRADE}% of ${inputs.account_size:,.0f})")
        
        if contracts == 0:
            warnings.append("⚠️ Account too small for this trade")
        
        if inputs.current_positions >= 3:
            warnings.append(f"⚠️ Already {inputs.current_positions} positions open")
        
        return contracts, total_risk, reasons, warnings
    
    # ==================== ENTRY/EXIT RULES ====================
    
    def _get_entry_rules(self, inputs: MarketInputs, strategy: str) -> List[str]:
        """Generate entry rules"""
        rules = [
            f"✓ Enter with VIX at {inputs.vix_level}",
            f"✓ Use {strategy.replace('_', ' ').title()} strategy",
            "✓ Place limit order at mid-price",
            "✓ Fill within 5% of mid or cancel",
            "✓ No market orders",
        ]
        
        if inputs.vix_level < self.VIX_GOOD:
            rules.append("✓ VIX is LOW - good for premium selling")
        
        return rules
    
    def _get_exit_rules(self) -> List[str]:
        """Generate exit rules"""
        return [
            f"✓ Take profit at {self.TAKE_PROFIT_PCT}% of max profit",
            f"✓ Stop loss at {self.STOP_LOSS_PCT}% of debit paid",
            f"✓ Roll if < {self.ROLL_DAYS} days to expiry",
            f"✓ Roll if delta > {self.ROLL_DELTA}",
            "✓ Close before earnings",
            "✓ Close before FOMC if uncertain",
        ]
    
    # ==================== SIGNAL GENERATION ====================
    
    def _generate_signal(
        self, inputs: MarketInputs, strategy: str, confidence: str
    ) -> Tuple[str, str]:
        """Generate final trading signal"""
        
        # Strong buy conditions
        if (inputs.vix_level < self.VIX_GOOD and 
            inputs.iv_rank > self.IV_RANK_HIGH and
            confidence == 'high'):
            return Signal.BUY.value, 'strong'
        
        # Buy conditions
        if inputs.vix_level < self.VIX_NORMAL and confidence != 'low':
            return Signal.BUY.value, 'moderate'
        
        # Hold conditions
        if inputs.vix_level < self.VIX_HIGH:
            return Signal.HOLD.value, 'weak'
        
        # Wait conditions
        return Signal.WAIT.value, 'weak'
    
    # ==================== HELPER METHODS ====================
    
    def _create_avoid_output(
        self, inputs: MarketInputs, reasoning: List[str], warnings: List[str],
        guards_consulted: List[Tuple[str, bool]]
    ) -> BrainOutput:
        """Create output for avoid signal"""
        # Log decision
        self._log_decision(inputs, Signal.AVOID.value, guards_consulted)
        
        return BrainOutput(
            signal=Signal.AVOID.value,
            signal_strength='strong',
            recommended_strategy='none',
            strategy_confidence='none',
            suggested_put_strike=0,
            suggested_call_strike=0,
            recommended_contracts=0,
            max_risk_dollars=0,
            entry_rules=["DO NOT TRADE - See reasoning"],
            exit_rules=[],
            warnings=warnings,
            reasoning=reasoning
        )
    
    def _log_decision(self, inputs: MarketInputs, signal: str, guards: List[Tuple[str, bool]]):
        """Log decision for audit trail"""
        from datetime import datetime
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'symbol': inputs.symbol,
            'vix': inputs.vix_level,
            'iv_rank': inputs.iv_rank,
            'signal': signal,
            'guards': {g[0]: g[1] for g in guards}
        }
        
        self.decision_log.append(log_entry)
        
        # Keep last 100 decisions
        if len(self.decision_log) > 100:
            self.decision_log = self.decision_log[-100:]
    
    def get_decision_log(self) -> List[Dict]:
        """Get audit trail of decisions"""
        return self.decision_log
    
    def get_quick_assessment(self, vix: float, iv_rank: float) -> Dict:
        """Quick assessment without full analysis"""
        if vix < self.VIX_GOOD and iv_rank > self.IV_RANK_HIGH:
            return {'signal': 'BUY', 'strategy': 'Double Calendar', 'confidence': 'high'}
        elif vix < self.VIX_NORMAL and iv_rank > self.IV_RANK_MEDIUM:
            return {'signal': 'BUY', 'strategy': 'Calendar Spread', 'confidence': 'medium'}
        elif vix < self.VIX_HIGH:
            return {'signal': 'HOLD', 'strategy': 'Wait', 'confidence': 'low'}
        else:
            return {'signal': 'AVOID', 'strategy': 'None', 'confidence': 'none'}
