"""
Roll Advisor for ThetaEdge
Helps decide when and how to roll positions
"""

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timedelta


@dataclass
class RollRecommendation:
    """Roll recommendation"""
    should_roll: bool
    urgency: str  # 'immediate', 'soon', 'optional', 'no'
    reason: str
    new_strike: Optional[float]
    new_expiry: Optional[str]
    estimated_cost: Optional[float]
    notes: str


class RollAdvisor:
    """Advise on when to roll options positions"""
    
    # Roll triggers
    TRIGGERS = {
        'days_to_expiry': 7,  # Roll when < 7 days to expiry
        'delta_threshold': 0.40,  # Roll if delta exceeds this
        'profit_target': 0.50,  # Roll if at 50% profit
        'loss_threshold': 0.30,  # Roll if at 30% loss
    }
    
    def __init__(self):
        self.current_date = datetime.now()
    
    def analyze(
        self,
        entry_date: str,
        expiry_date: str,
        strike: float,
        current_price: float,
        current_delta: float,
        pnl_pct: float,
        option_type: str = 'call'
    ) -> RollRecommendation:
        """Analyze if position should be rolled"""
        
        # Calculate days to expiry
        exp_date = datetime.strptime(expiry_date, '%Y-%m-%d')
        days_to_expiry = (exp_date - self.current_date).days
        
        # Check each trigger
        if days_to_expiry <= self.TRIGGERS['days_to_expiry']:
            return self._recommend_roll(
                urgency='immediate',
                reason=f'Only {days_to_expiry} days to expiry',
                strike=strike,
                current_price=current_price,
                option_type=option_type
            )
        
        if abs(current_delta) > self.TRIGGERS['delta_threshold']:
            return self._recommend_roll(
                urgency='soon',
                reason=f'Delta at {current_delta:.2f} - getting too directional',
                strike=strike,
                current_price=current_price,
                option_type=option_type
            )
        
        if pnl_pct >= self.TRIGGERS['profit_target'] * 100:
            return RollRecommendation(
                should_roll=True,
                urgency='optional',
                reason=f'At {pnl_pct:.0f}% profit - consider taking profits',
                new_strike=None,
                new_expiry=None,
                estimated_cost=None,
                notes='Good opportunity to close or roll to new strikes'
            )
        
        if pnl_pct <= -self.TRIGGERS['loss_threshold'] * 100:
            return RollRecommendation(
                should_roll=True,
                urgency='soon',
                reason=f'At {pnl_pct:.0f}% loss - consider cutting losses',
                new_strike=None,
                new_expiry=None,
                estimated_cost=None,
                notes='Review strategy and consider closing'
            )
        
        # No roll needed
        return RollRecommendation(
            should_roll=False,
            urgency='no',
            reason='Position is healthy',
            new_strike=None,
            new_expiry=None,
            estimated_cost=None,
            notes=f'{days_to_expiry} days to expiry, delta at {current_delta:.2f}'
        )
    
    def _recommend_roll(
        self,
        urgency: str,
        reason: str,
        strike: float,
        current_price: float,
        option_type: str
    ) -> RollRecommendation:
        """Generate roll recommendation"""
        
        # Suggest new strike based on current price
        if option_type == 'call':
            # Roll up and out
            new_strike = round(current_price * 1.05 / 5) * 5
        else:
            # Roll down and out
            new_strike = round(current_price * 0.95 / 5) * 5
        
        return RollRecommendation(
            should_roll=True,
            urgency=urgency,
            reason=reason,
            new_strike=new_strike,
            new_expiry='Next month',
            estimated_cost=0.50,
            notes=f'Consider rolling to {new_strike} strike, next month expiry'
        )
    
    def get_roll_checklist(self) -> list:
        """Get checklist before rolling"""
        return [
            'Check current P&L',
            'Verify new strikes have good liquidity',
            'Confirm roll improves position',
            'Check for upcoming earnings/events',
            'Verify spread is not too wide',
            'Confirm you still want exposure',
            'Calculate net cost/credit of roll'
        ]
