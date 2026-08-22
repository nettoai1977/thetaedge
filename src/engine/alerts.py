"""
Alert System for ThetaEdge
Price and IV alerts
"""

from dataclasses import dataclass, asdict
from typing import List, Optional
import json
from pathlib import Path
import os


@dataclass
class Alert:
    """Trading alert"""
    id: str
    symbol: str
    alert_type: str  # 'price_above', 'price_below', 'iv_above', 'iv_below'
    threshold: float
    current_value: float
    triggered: bool
    created_at: str
    notes: str


class AlertSystem:
    """Manage trading alerts"""
    
    def __init__(self):
        self.data_dir = Path(os.path.expanduser("~/.thetaedge"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_file = self.data_dir / "alerts.json"
        self.alerts: List[Alert] = self._load_alerts()
    
    def _load_alerts(self) -> List[Alert]:
        """Load alerts from file"""
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                data = json.load(f)
                return [Alert(**a) for a in data]
        return []
    
    def _save_alerts(self):
        """Save alerts to file"""
        with open(self.alerts_file, 'w') as f:
            json.dump([asdict(a) for a in self.alerts], f, indent=2)
    
    def add_alert(
        self,
        symbol: str,
        alert_type: str,
        threshold: float,
        notes: str = ""
    ) -> Alert:
        """Add new alert"""
        from datetime import datetime
        
        alert = Alert(
            id=f"A{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol=symbol.upper(),
            alert_type=alert_type,
            threshold=threshold,
            current_value=0,
            triggered=False,
            created_at=datetime.now().isoformat(),
            notes=notes
        )
        
        self.alerts.append(alert)
        self._save_alerts()
        return alert
    
    def check_alerts(self, symbol: str, price: float, iv: float = None) -> List[Alert]:
        """Check if any alerts should trigger"""
        triggered = []
        
        for alert in self.alerts:
            if alert.symbol != symbol or alert.triggered:
                continue
            
            should_trigger = False
            
            if alert.alert_type == 'price_above' and price >= alert.threshold:
                should_trigger = True
            elif alert.alert_type == 'price_below' and price <= alert.threshold:
                should_trigger = True
            elif alert.alert_type == 'iv_above' and iv and iv >= alert.threshold:
                should_trigger = True
            elif alert.alert_type == 'iv_below' and iv and iv <= alert.threshold:
                should_trigger = True
            
            if should_trigger:
                alert.triggered = True
                alert.current_value = price if 'price' in alert.alert_type else iv
                triggered.append(alert)
        
        if triggered:
            self._save_alerts()
        
        return triggered
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all non-triggered alerts"""
        return [a for a in self.alerts if not a.triggered]
    
    def get_triggered_alerts(self) -> List[Alert]:
        """Get all triggered alerts"""
        return [a for a in self.alerts if a.triggered]
    
    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert"""
        for i, alert in enumerate(self.alerts):
            if alert.id == alert_id:
                self.alerts.pop(i)
                self._save_alerts()
                return True
        return False
    
    def clear_triggered(self):
        """Clear all triggered alerts"""
        self.alerts = [a for a in self.alerts if not a.triggered]
        self._save_alerts()
