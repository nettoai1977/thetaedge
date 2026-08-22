"""
VIX Monitor for ThetaEntry
Tracks VIX and provides entry signals
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import random


@dataclass
class VIXReading:
    """Single VIX reading"""
    timestamp: str
    value: float
    signal: str  # 'buy', 'sell', 'neutral'
    interpretation: str


@dataclass
class VIXAlert:
    """VIX alert configuration"""
    id: str
    name: str
    condition: str  # 'above', 'below', 'between'
    value1: float
    value2: Optional[float]
    enabled: bool
    triggered: bool


class VIXMonitor:
    """VIX monitoring and entry signal system"""
    
    # VIX Interpretation thresholds
    THRESHOLDS = {
        'very_low': 12,
        'low': 15,
        'normal_low': 18,
        'normal_high': 22,
        'high': 25,
        'very_high': 30
    }
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.expanduser("~/.thetaedge")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.readings_file = self.data_dir / "vix_readings.json"
        self.alerts_file = self.data_dir / "vix_alerts.json"
        self.readings: List[VIXReading] = self._load_readings()
        self.alerts: List[VIXAlert] = self._load_alerts()
    
    def _load_readings(self) -> List[VIXReading]:
        """Load VIX readings from file"""
        if self.readings_file.exists():
            with open(self.readings_file, 'r') as f:
                data = json.load(f)
                return [VIXReading(**r) for r in data]
        return []
    
    def _save_readings(self):
        """Save VIX readings to file"""
        with open(self.readings_file, 'w') as f:
            json.dump([asdict(r) for r in self.readings[-1000:]], f, indent=2)
    
    def _load_alerts(self) -> List[VIXAlert]:
        """Load alerts from file"""
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                data = json.load(f)
                return [VIXAlert(**a) for a in data]
        return self._default_alerts()
    
    def _save_alerts(self):
        """Save alerts to file"""
        with open(self.alerts_file, 'w') as f:
            json.dump([asdict(a) for a in self.alerts], f, indent=2)
    
    def _default_alerts(self) -> List[VIXAlert]:
        """Create default alerts"""
        return [
            VIXAlert(
                id="entry_signal",
                name="Entry Signal (VIX < 20)",
                condition="below",
                value1=20,
                value2=None,
                enabled=True,
                triggered=False
            ),
            VIXAlert(
                id="high_volatility",
                name="High Volatility (VIX > 25)",
                condition="above",
                value1=25,
                value2=None,
                enabled=True,
                triggered=False
            ),
            VIXAlert(
                id="optimal_zone",
                name="Optimal Zone (VIX 15-20)",
                condition="between",
                value1=15,
                value2=20,
                enabled=True,
                triggered=False
            )
        ]
    
    def get_current_vix(self) -> float:
        """Get current VIX value (simulated - in production use API)"""
        # Simulated VIX data
        base_vix = 18.5
        variation = random.uniform(-2, 2)
        return round(base_vix + variation, 2)
    
    def record_reading(self, value: float = None) -> VIXReading:
        """Record a VIX reading"""
        if value is None:
            value = self.get_current_vix()
        
        signal = self._interpret_signal(value)
        interpretation = self._interpret_vix(value)
        
        reading = VIXReading(
            timestamp=datetime.now().isoformat(),
            value=value,
            signal=signal,
            interpretation=interpretation
        )
        
        self.readings.append(reading)
        self._save_readings()
        self._check_alerts(value)
        
        return reading
    
    def _interpret_signal(self, vix: float) -> str:
        """Interpret VIX into trading signal"""
        if vix < self.THRESHOLDS['low']:
            return 'buy'  # Good for selling options
        elif vix < self.THRESHOLDS['normal_high']:
            return 'neutral'
        elif vix < self.THRESHOLDS['high']:
            return 'caution'
        else:
            return 'sell'  # Bad for selling options
    
    def _interpret_vix(self, vix: float) -> str:
        """Get human-readable interpretation"""
        if vix < self.THRESHOLDS['very_low']:
            return "Very Low - Excellent for selling premium"
        elif vix < self.THRESHOLDS['low']:
            return "Low - Good for selling premium"
        elif vix < self.THRESHOLDS['normal_low']:
            return "Normal-Low - Acceptable for trades"
        elif vix < self.THRESHOLDS['normal_high']:
            return "Normal - Neutral conditions"
        elif vix < self.THRESHOLDS['high']:
            return "High - Caution, wait for better entry"
        elif vix < self.THRESHOLDS['very_high']:
            return "Very High - Avoid new positions"
        else:
            return "Extreme - Market stress, potential opportunity"
    
    def _check_alerts(self, vix: float):
        """Check if any alerts should trigger"""
        for alert in self.alerts:
            if not alert.enabled:
                continue
            
            triggered = False
            
            if alert.condition == 'above' and vix > alert.value1:
                triggered = True
            elif alert.condition == 'below' and vix < alert.value1:
                triggered = True
            elif alert.condition == 'between' and alert.value1 <= vix <= alert.value2:
                triggered = True
            
            if triggered and not alert.triggered:
                alert.triggered = True
                # In production, send notification here
            elif not triggered:
                alert.triggered = False
        
        self._save_alerts()
    
    def get_readings_history(self, days: int = 30) -> List[VIXReading]:
        """Get VIX readings for last N days"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [r for r in self.readings if r.timestamp >= cutoff]
    
    def get_statistics(self) -> Dict:
        """Get VIX statistics"""
        if not self.readings:
            return {
                'current': 0,
                'avg_7d': 0,
                'avg_30d': 0,
                'min_30d': 0,
                'max_30d': 0,
                'signal': 'neutral',
                'interpretation': 'No data'
            }
        
        recent = self.readings[-100:]  # Last 100 readings
        values = [r.value for r in recent]
        
        # Get readings for different periods
        now = datetime.now()
        last_7d = [r.value for r in self.readings if (now - datetime.fromisoformat(r.timestamp)).days <= 7]
        last_30d = [r.value for r in self.readings if (now - datetime.fromisoformat(r.timestamp)).days <= 30]
        
        return {
            'current': recent[-1].value if recent else 0,
            'avg_7d': round(sum(last_7d) / len(last_7d), 2) if last_7d else 0,
            'avg_30d': round(sum(last_30d) / len(last_30d), 2) if last_30d else 0,
            'min_30d': round(min(last_30d), 2) if last_30d else 0,
            'max_30d': round(max(last_30d), 2) if last_30d else 0,
            'signal': recent[-1].signal if recent else 'neutral',
            'interpretation': recent[-1].interpretation if recent else 'No data',
            'readings_count': len(self.readings)
        }
    
    def get_entry_signal(self) -> Dict:
        """Get current entry signal for Ravish's strategies"""
        current = self.get_current_vix()
        
        if current < self.THRESHOLDS['low']:
            return {
                'signal': 'ENTER',
                'confidence': 'high',
                'message': f'VIX at {current} - Excellent entry for Double Calendar',
                'strategies': ['Double Calendar', 'Time Spread'],
                'color': 'green'
            }
        elif current < self.THRESHOLDS['normal_high']:
            return {
                'signal': 'HOLD',
                'confidence': 'medium',
                'message': f'VIX at {current} - Normal conditions, selective entries',
                'strategies': ['Time Spread'],
                'color': 'yellow'
            }
        else:
            return {
                'signal': 'WAIT',
                'confidence': 'low',
                'message': f'VIX at {current} - High volatility, wait for better entry',
                'strategies': ['Double Diagonal'],
                'color': 'red'
            }
