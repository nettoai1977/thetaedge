"""
Position Sizing Calculator for ThetaEdge
Helps determine how many contracts to trade
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PositionSizeResult:
    """Position sizing result"""
    account_size: float
    risk_per_trade_pct: float
    max_loss_per_trade: float
    contracts: int
    total_risk: float
    risk_remaining: float
    recommendation: str


class PositionSizer:
    """Calculate position size based on risk management rules"""
    
    # Default risk parameters
    DEFAULT_RISK_PCT = 2.0  # 2% max risk per trade
    MAX_PORTFOLIO_RISK = 15.0  # 15% max total portfolio risk
    
    def __init__(self, account_size: float = 10000):
        self.account_size = account_size
    
    def calculate(
        self,
        net_debit: float,
        max_loss_pct: float = 100,
        risk_pct: float = None,
        current_positions: int = 0
    ) -> PositionSizeResult:
        """
        Calculate position size
        
        Parameters:
        -----------
        net_debit : float
            Net debit per spread (e.g., $1.50)
        max_loss_pct : float
            Max loss as % of debit (100% = lose entire debit)
        risk_pct : float
            Risk per trade as % of account
        current_positions : int
            Number of current open positions
        """
        if risk_pct is None:
            risk_pct = self.DEFAULT_RISK_PCT
        
        # Calculate max loss per contract
        max_loss_per_contract = net_debit * (max_loss_pct / 100) * 100  # Options multiplier = 100
        
        # Calculate max dollar risk
        max_dollar_risk = self.account_size * (risk_pct / 100)
        
        # Calculate contracts
        if max_loss_per_contract > 0:
            contracts = int(max_dollar_risk / max_loss_per_contract)
        else:
            contracts = 0
        
        # Cap at reasonable max
        contracts = min(contracts, 10)
        
        # Calculate actual risk
        total_risk = contracts * max_loss_per_contract
        risk_remaining = max_dollar_risk - total_risk
        
        # Generate recommendation
        recommendation = self._get_recommendation(
            contracts, risk_pct, current_positions
        )
        
        return PositionSizeResult(
            account_size=self.account_size,
            risk_per_trade_pct=risk_pct,
            max_loss_per_trade=round(max_dollar_risk, 2),
            contracts=contracts,
            total_risk=round(total_risk, 2),
            risk_remaining=round(risk_remaining, 2),
            recommendation=recommendation
        )
    
    def _get_recommendation(
        self, contracts: int, risk_pct: float, current_positions: int
    ) -> str:
        """Generate position sizing recommendation"""
        if contracts == 0:
            return "Position too large for account size. Consider smaller size."
        
        if risk_pct > 3:
            return "High risk per trade. Consider reducing to 1-2%."
        
        if current_positions >= 5:
            return "Max positions reached. Close existing trades first."
        
        if contracts >= 5:
            return "Large position. Consider splitting into multiple entries."
        
        return "Position size looks good. Ready to trade."
    
    def get_portfolio_risk(
        self, positions: list
    ) -> Dict:
        """Calculate total portfolio risk"""
        total_risk = sum(p.get('max_loss', 0) for p in positions)
        risk_pct = (total_risk / self.account_size * 100) if self.account_size > 0 else 0
        
        return {
            'total_positions': len(positions),
            'total_risk': round(total_risk, 2),
            'risk_pct': round(risk_pct, 2),
            'max_allowed': self.MAX_PORTFOLIO_RISK,
            'remaining_capacity': round(self.MAX_PORTFOLIO_RISK - risk_pct, 2),
            'status': 'safe' if risk_pct < self.MAX_PORTFOLIO_RISK else 'warning'
        }
    
    def calculate_for_double_calendar(
        self,
        short_put_premium: float,
        long_put_premium: float,
        short_call_premium: float,
        long_call_premium: float,
        risk_pct: float = None
    ) -> PositionSizeResult:
        """Calculate position size for double calendar"""
        net_debit = (
            (long_put_premium - short_put_premium) + 
            (long_call_premium - short_call_premium)
        )
        
        # Max loss for double calendar = net debit (typically)
        return self.calculate(
            net_debit=net_debit,
            max_loss_pct=100,
            risk_pct=risk_pct
        )
