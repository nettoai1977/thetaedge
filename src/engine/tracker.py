"""
Trade Tracker for ThetaEdge
Logs and analyzes options trades
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Trade:
    """Single trade record"""
    id: str
    entry_date: str
    exit_date: Optional[str]
    ticker: str
    strategy: str
    direction: str  # 'bullish', 'bearish', 'neutral'
    status: str  # 'open', 'closed', 'expired'
    
    # Position details
    legs: List[Dict]
    net_debit: float
    contracts: int
    
    # Exit details
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    exit_reason: Optional[str]  # 'take_profit', 'stop_loss', 'expiry', 'manual'
    
    # Metadata
    notes: str
    tags: List[str]
    created_at: str
    updated_at: str


class TradeTracker:
    """Trade logging and portfolio tracking"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.expanduser("~/.thetaedge")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / "trades.json"
        self.trades: List[Trade] = self._load_trades()
    
    def _load_trades(self) -> List[Trade]:
        """Load trades from file"""
        if self.trades_file.exists():
            with open(self.trades_file, 'r') as f:
                data = json.load(f)
                return [Trade(**t) for t in data]
        return []
    
    def _save_trades(self):
        """Save trades to file"""
        with open(self.trades_file, 'w') as f:
            json.dump([asdict(t) for t in self.trades], f, indent=2)
    
    def _generate_id(self) -> str:
        """Generate unique trade ID"""
        return f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{len(self.trades):04d}"
    
    def add_trade(
        self,
        ticker: str,
        strategy: str,
        direction: str,
        legs: List[Dict],
        net_debit: float,
        contracts: int = 1,
        notes: str = "",
        tags: List[str] = None
    ) -> Trade:
        """Add a new trade"""
        now = datetime.now().isoformat()
        
        trade = Trade(
            id=self._generate_id(),
            entry_date=now,
            exit_date=None,
            ticker=ticker,
            strategy=strategy,
            direction=direction,
            status='open',
            legs=legs,
            net_debit=net_debit,
            contracts=contracts,
            exit_price=None,
            pnl=None,
            pnl_pct=None,
            exit_reason=None,
            notes=notes,
            tags=tags or [],
            created_at=now,
            updated_at=now
        )
        
        self.trades.append(trade)
        self._save_trades()
        return trade
    
    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = 'manual',
        notes: str = ""
    ) -> Trade:
        """Close an open trade"""
        for trade in self.trades:
            if trade.id == trade_id and trade.status == 'open':
                trade.exit_date = datetime.now().isoformat()
                trade.status = 'closed'
                trade.exit_price = exit_price
                trade.exit_reason = exit_reason
                trade.updated_at = datetime.now().isoformat()
                
                # Calculate P&L
                if notes:
                    trade.notes = f"{trade.notes}\n{notes}" if trade.notes else notes
                
                # P&L calculation (simplified)
                trade.pnl = round((exit_price - trade.net_debit) * trade.contracts * 100, 2)
                trade.pnl_pct = round(((exit_price - trade.net_debit) / trade.net_debit) * 100, 2)
                
                self._save_trades()
                return trade
        
        raise ValueError(f"Trade {trade_id} not found or already closed")
    
    def get_open_trades(self) -> List[Trade]:
        """Get all open trades"""
        return [t for t in self.trades if t.status == 'open']
    
    def get_closed_trades(self) -> List[Trade]:
        """Get all closed trades"""
        return [t for t in self.trades if t.status == 'closed']
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get a specific trade"""
        for trade in self.trades:
            if trade.id == trade_id:
                return trade
        return None
    
    def delete_trade(self, trade_id: str) -> bool:
        """Delete a trade"""
        for i, trade in enumerate(self.trades):
            if trade.id == trade_id:
                self.trades.pop(i)
                self._save_trades()
                return True
        return False
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        closed = self.get_closed_trades()
        open_trades = self.get_open_trades()
        
        if not closed:
            return {
                'total_trades': 0,
                'closed_trades': 0,
                'open_trades': len(open_trades),
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'best_trade': None,
                'worst_trade': None,
                'profit_factor': 0
            }
        
        pnls = [t.pnl for t in closed if t.pnl is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_pnl = sum(pnls)
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        profit_factor = abs(sum(wins) / sum(losses)) if losses else 999
        
        # Find best and worst trades
        best_trade = max(closed, key=lambda t: t.pnl or 0) if closed else None
        worst_trade = min(closed, key=lambda t: t.pnl or 0) if closed else None
        
        return {
            'total_trades': len(self.trades),
            'closed_trades': len(closed),
            'open_trades': len(open_trades),
            'win_rate': round(len(wins) / len(closed) * 100, 1) if closed else 0,
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(total_pnl / len(closed), 2) if closed else 0,
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'best_trade': {
                'id': best_trade.id,
                'pnl': best_trade.pnl,
                'ticker': best_trade.ticker
            } if best_trade else None,
            'worst_trade': {
                'id': worst_trade.id,
                'pnl': worst_trade.pnl,
                'ticker': worst_trade.ticker
            } if worst_trade else None,
            'profit_factor': round(profit_factor, 2)
        }
    
    def get_strategy_breakdown(self) -> Dict:
        """Get performance breakdown by strategy"""
        closed = self.get_closed_trades()
        breakdown = {}
        
        for trade in closed:
            strategy = trade.strategy
            if strategy not in breakdown:
                breakdown[strategy] = {
                    'trades': 0,
                    'wins': 0,
                    'total_pnl': 0,
                    'pnls': []
                }
            
            breakdown[strategy]['trades'] += 1
            if trade.pnl and trade.pnl > 0:
                breakdown[strategy]['wins'] += 1
            breakdown[strategy]['total_pnl'] += trade.pnl or 0
            breakdown[strategy]['pnls'].append(trade.pnl or 0)
        
        # Calculate stats
        for strategy in breakdown:
            data = breakdown[strategy]
            data['win_rate'] = round(data['wins'] / data['trades'] * 100, 1) if data['trades'] > 0 else 0
            data['avg_pnl'] = round(data['total_pnl'] / data['trades'], 2) if data['trades'] > 0 else 0
            data['total_pnl'] = round(data['total_pnl'], 2)
            del data['pnls']  # Remove raw data
        
        return breakdown
