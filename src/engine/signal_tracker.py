"""
Signal Tracker for ThetaEdge
Logs all trading signals for later analysis
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from datetime import datetime
import json
from pathlib import Path
import os


@dataclass
class SignalRecord:
    """Record of a trading signal"""
    id: str
    timestamp: str
    
    # Signal data
    symbol: str
    signal: str  # 'buy', 'sell', 'hold', 'wait', 'avoid'
    signal_strength: str  # 'strong', 'moderate', 'weak'
    strategy: str
    confidence: str  # 'high', 'medium', 'low'
    
    # Market conditions
    vix_level: float
    iv_rank: float
    price_at_signal: float
    
    # Recommendation
    put_strike: float
    call_strike: float
    contracts: int
    max_risk: float
    
    # Outcome (filled later)
    outcome: Optional[str] = None  # 'win', 'loss', 'breakeven', 'pending'
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    
    # Analysis
    notes: str = ""


class SignalTracker:
    """Track and analyze all trading signals"""
    
    def __init__(self):
        self.data_dir = Path(os.path.expanduser("~/.thetaedge"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.signals_file = self.data_dir / "signals.json"
        self.signals: List[SignalRecord] = self._load_signals()
    
    def _load_signals(self) -> List[SignalRecord]:
        """Load signals from file"""
        if self.signals_file.exists():
            with open(self.signals_file, 'r') as f:
                data = json.load(f)
                return [SignalRecord(**s) for s in data]
        return []
    
    def _save_signals(self):
        """Save signals to file"""
        with open(self.signals_file, 'w') as f:
            json.dump([asdict(s) for s in self.signals], f, indent=2)
    
    def log_signal(
        self,
        symbol: str,
        signal: str,
        signal_strength: str,
        strategy: str,
        confidence: str,
        vix_level: float,
        iv_rank: float,
        price_at_signal: float,
        put_strike: float,
        call_strike: float,
        contracts: int,
        max_risk: float,
        notes: str = ""
    ) -> SignalRecord:
        """Log a new trading signal"""
        
        record = SignalRecord(
            id=f"S{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            signal=signal,
            signal_strength=signal_strength,
            strategy=strategy,
            confidence=confidence,
            vix_level=vix_level,
            iv_rank=iv_rank,
            price_at_signal=price_at_signal,
            put_strike=put_strike,
            call_strike=call_strike,
            contracts=contracts,
            max_risk=max_risk,
            notes=notes
        )
        
        self.signals.append(record)
        self._save_signals()
        return record
    
    def update_outcome(
        self,
        signal_id: str,
        outcome: str,
        pnl: float,
        pnl_pct: float,
        exit_date: str,
        exit_price: float
    ) -> bool:
        """Update signal with outcome"""
        for signal in self.signals:
            if signal.id == signal_id:
                signal.outcome = outcome
                signal.pnl = pnl
                signal.pnl_pct = pnl_pct
                signal.exit_date = exit_date
                signal.exit_price = exit_price
                self._save_signals()
                return True
        return False
    
    def get_signals(
        self,
        symbol: str = None,
        signal: str = None,
        limit: int = 50
    ) -> List[SignalRecord]:
        """Get signals with optional filters"""
        filtered = self.signals
        
        if symbol:
            filtered = [s for s in filtered if s.symbol == symbol]
        
        if signal:
            filtered = [s for s in filtered if s.signal == signal]
        
        # Sort by timestamp (newest first)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        
        return filtered[:limit]
    
    def get_performance(self) -> Dict:
        """Calculate overall performance metrics"""
        closed = [s for s in self.signals if s.outcome and s.outcome != 'pending']
        
        if not closed:
            return {
                'total_signals': len(self.signals),
                'closed_trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'total_pnl': 0,
                'profit_factor': 0,
                'max_win': 0,
                'max_loss': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        wins = [s for s in closed if s.outcome == 'win']
        losses = [s for s in closed if s.outcome == 'loss']
        
        total_pnl = sum(s.pnl or 0 for s in closed)
        total_wins = sum(s.pnl or 0 for s in wins)
        total_losses = abs(sum(s.pnl or 0 for s in losses))
        
        return {
            'total_signals': len(self.signals),
            'closed_trades': len(closed),
            'win_rate': len(wins) / len(closed) * 100 if closed else 0,
            'avg_pnl': total_pnl / len(closed) if closed else 0,
            'total_pnl': total_pnl,
            'profit_factor': total_wins / total_losses if total_losses > 0 else 0,
            'max_win': max((s.pnl or 0) for s in wins) if wins else 0,
            'max_loss': min((s.pnl or 0) for s in losses) if losses else 0,
            'avg_win': total_wins / len(wins) if wins else 0,
            'avg_loss': total_losses / len(losses) if losses else 0
        }
    
    def get_signal_accuracy(self) -> Dict:
        """Analyze signal accuracy by type"""
        closed = [s for s in self.signals if s.outcome and s.outcome != 'pending']
        
        by_signal = {}
        for s in closed:
            if s.signal not in by_signal:
                by_signal[s.signal] = {'wins': 0, 'losses': 0, 'total': 0}
            by_signal[s.signal]['total'] += 1
            if s.outcome == 'win':
                by_signal[s.signal]['wins'] += 1
            else:
                by_signal[s.signal]['losses'] += 1
        
        # Calculate win rates
        for sig_type in by_signal:
            total = by_signal[sig_type]['total']
            wins = by_signal[sig_type]['wins']
            by_signal[sig_type]['win_rate'] = wins / total * 100 if total > 0 else 0
        
        return by_signal
    
    def get_strategy_performance(self) -> Dict:
        """Analyze performance by strategy"""
        closed = [s for s in self.signals if s.outcome and s.outcome != 'pending']
        
        by_strategy = {}
        for s in closed:
            if s.strategy not in by_strategy:
                by_strategy[s.strategy] = {'wins': 0, 'losses': 0, 'total': 0, 'pnl': 0}
            by_strategy[s.strategy]['total'] += 1
            by_strategy[s.strategy]['pnl'] += s.pnl or 0
            if s.outcome == 'win':
                by_strategy[s.strategy]['wins'] += 1
            else:
                by_strategy[s.strategy]['losses'] += 1
        
        # Calculate win rates
        for strat in by_strategy:
            total = by_strategy[strat]['total']
            wins = by_strategy[strat]['wins']
            by_strategy[strat]['win_rate'] = wins / total * 100 if total > 0 else 0
        
        return by_strategy
    
    def get_vix_performance(self) -> Dict:
        """Analyze performance by VIX level at signal"""
        closed = [s for s in self.signals if s.outcome and s.outcome != 'pending']
        
        ranges = [
            ('low', 0, 15),
            ('normal', 15, 20),
            ('high', 20, 25),
            ('extreme', 25, 100)
        ]
        
        by_vix = {}
        for label, low, high in ranges:
            signals = [s for s in closed if low <= s.vix_level < high]
            if signals:
                wins = len([s for s in signals if s.outcome == 'win'])
                by_vix[label] = {
                    'count': len(signals),
                    'wins': wins,
                    'win_rate': wins / len(signals) * 100,
                    'avg_pnl': sum(s.pnl or 0 for s in signals) / len(signals)
                }
        
        return by_vix
    
    def get_equity_curve(self) -> List[Dict]:
        """Get equity curve data"""
        closed = [s for s in self.signals if s.outcome and s.outcome != 'pending']
        closed.sort(key=lambda x: x.exit_date or x.timestamp)
        
        curve = []
        equity = 10000  # Starting equity
        
        for s in closed:
            equity += s.pnl or 0
            curve.append({
                'date': s.exit_date or s.timestamp,
                'equity': round(equity, 2),
                'pnl': s.pnl or 0,
                'symbol': s.symbol
            })
        
        return curve
    
    def get_daily_summary(self) -> List[Dict]:
        """Get daily P&L summary"""
        closed = [s for s in self.signals if s.outcome and s.outcome != 'pending']
        
        daily = {}
        for s in closed:
            date = (s.exit_date or s.timestamp)[:10]
            if date not in daily:
                daily[date] = {'date': date, 'pnl': 0, 'trades': 0, 'wins': 0}
            daily[date]['pnl'] += s.pnl or 0
            daily[date]['trades'] += 1
            if s.outcome == 'win':
                daily[date]['wins'] += 1
        
        return sorted(daily.values(), key=lambda x: x['date'])
