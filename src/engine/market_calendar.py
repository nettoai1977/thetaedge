"""
US Market Calendar for ThetaEdge
Tracks market hours, holidays, reports, and important dates
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path
import os


class MarketCalendar:
    """US Market Calendar with NZ time conversion"""
    
    # US Market Hours (Eastern Time)
    MARKET_HOURS = {
        'pre_market': {'start': '04:00', 'end': '09:30', 'label': 'Pre-Market'},
        'regular': {'start': '09:30', 'end': '16:00', 'label': 'Regular Hours'},
        'after_hours': {'start': '16:00', 'end': '20:00', 'label': 'After Hours'}
    }
    
    # Time difference: NZ is ahead of US Eastern
    # NZDT (Oct-Apr) = ET + 18 hours
    # NZST (Apr-Oct) = ET + 16 hours
    # During US DST (Mar-Nov): NZ is 16-17 hours ahead
    # During NZ DST (Sep-Apr): NZ is 18 hours ahead
    
    def __init__(self):
        self.data_dir = Path(os.path.expanduser("~/.thetaedge"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.calendar_file = self.data_dir / "market_calendar.json"
    
    def get_market_status(self, et_time: datetime = None) -> Dict:
        """Get current market status"""
        if et_time is None:
            et_time = datetime.now()  # Should be ET in production
        
        # Convert to NZ time
        nz_time = self._et_to_nz(et_time)
        
        # Determine status
        time_str = et_time.strftime('%H:%M')
        
        if et_time.weekday() >= 5:  # Weekend
            status = 'closed'
            next_open = self._get_next_trading_day(et_time)
        elif time_str < '04:00':
            status = 'closed'
            next_open = et_time.replace(hour=4, minute=0, second=0)
        elif time_str < '09:30':
            status = 'pre_market'
            next_open = et_time.replace(hour=9, minute=30, second=0)
        elif time_str < '16:00':
            status = 'open'
            next_open = et_time.replace(hour=16, minute=0, second=0)
        elif time_str < '20:00':
            status = 'after_hours'
            next_open = et_time.replace(hour=20, minute=0, second=0)
        else:
            status = 'closed'
            next_open = self._get_next_trading_day(et_time)
        
        return {
            'status': status,
            'status_label': status.replace('_', ' ').title(),
            'us_time': et_time.strftime('%I:%M %p ET'),
            'nz_time': nz_time.strftime('%I:%M %p NZST') if nz_time else None,
            'next_event': next_open.strftime('%I:%M %p ET') if next_open else None,
            'is_trading_day': et_time.weekday() < 5,
            'is_holiday': self._is_holiday(et_time)
        }
    
    def _et_to_nz(self, et_time: datetime) -> datetime:
        """Convert Eastern Time to New Zealand Time"""
        # Simplified conversion (in production use pytz)
        # NZ is typically 16-18 hours ahead of ET
        return et_time + timedelta(hours=17)  # Approximate
    
    def _get_next_trading_day(self, current: datetime) -> datetime:
        """Get next trading day"""
        next_day = current + timedelta(days=1)
        while next_day.weekday() >= 5 or self._is_holiday(next_day):
            next_day += timedelta(days=1)
        return next_day.replace(hour=9, minute=30, second=0)
    
    def _is_holiday(self, date: datetime) -> bool:
        """Check if date is a market holiday"""
        holidays = self.get_holidays(date.year)
        date_str = date.strftime('%Y-%m-%d')
        return date_str in [h['date'] for h in holidays]
    
    def get_holidays(self, year: int) -> List[Dict]:
        """Get US market holidays for a year"""
        # 2024-2025 holidays
        holidays_2024 = [
            {'date': '2024-01-01', 'name': "New Year's Day", 'type': 'federal'},
            {'date': '2024-01-15', 'name': "Martin Luther King Jr. Day", 'type': 'federal'},
            {'date': '2024-02-19', 'name': "Presidents' Day", 'type': 'federal'},
            {'date': '2024-03-29', 'name': "Good Friday", 'type': 'exchange'},
            {'date': '2024-05-27', 'name': "Memorial Day", 'type': 'federal'},
            {'date': '2024-06-19', 'name': "Juneteenth", 'type': 'federal'},
            {'date': '2024-07-04', 'name': "Independence Day", 'type': 'federal'},
            {'date': '2024-09-02', 'name': "Labor Day", 'type': 'federal'},
            {'date': '2024-11-28', 'name': "Thanksgiving Day", 'type': 'federal'},
            {'date': '2024-12-25', 'name': "Christmas Day", 'type': 'federal'},
        ]
        
        holidays_2025 = [
            {'date': '2025-01-01', 'name': "New Year's Day", 'type': 'federal'},
            {'date': '2025-01-20', 'name': "Martin Luther King Jr. Day", 'type': 'federal'},
            {'date': '2025-02-17', 'name': "Presidents' Day", 'type': 'federal'},
            {'date': '2025-04-18', 'name': "Good Friday", 'type': 'exchange'},
            {'date': '2025-05-26', 'name': "Memorial Day", 'type': 'federal'},
            {'date': '2025-06-19', 'name': "Juneteenth", 'type': 'federal'},
            {'date': '2025-07-04', 'name': "Independence Day", 'type': 'federal'},
            {'date': '2025-09-01', 'name': "Labor Day", 'type': 'federal'},
            {'date': '2025-11-27', 'name': "Thanksgiving Day", 'type': 'federal'},
            {'date': '2025-12-25', 'name': "Christmas Day", 'type': 'federal'},
        ]
        
        return holidays_2024 if year == 2024 else holidays_2025
    
    def get_fomc_dates(self, year: int) -> List[Dict]:
        """Get FOMC meeting dates"""
        fomc_2024 = [
            {'date': '2024-01-30', 'end': '2024-01-31', 'label': 'FOMC Meeting'},
            {'date': '2024-03-19', 'end': '2024-03-20', 'label': 'FOMC Meeting'},
            {'date': '2024-04-30', 'end': '2024-05-01', 'label': 'FOMC Meeting'},
            {'date': '2024-06-11', 'end': '2024-06-12', 'label': 'FOMC Meeting'},
            {'date': '2024-07-30', 'end': '2024-07-31', 'label': 'FOMC Meeting'},
            {'date': '2024-09-17', 'end': '2024-09-18', 'label': 'FOMC Meeting'},
            {'date': '2024-11-06', 'end': '2024-11-07', 'label': 'FOMC Meeting'},
            {'date': '2024-12-17', 'end': '2024-12-18', 'label': 'FOMC Meeting'},
        ]
        
        fomc_2025 = [
            {'date': '2025-01-28', 'end': '2025-01-29', 'label': 'FOMC Meeting'},
            {'date': '2025-03-18', 'end': '2025-03-19', 'label': 'FOMC Meeting'},
            {'date': '2025-05-06', 'end': '2025-05-07', 'label': 'FOMC Meeting'},
            {'date': '2025-06-17', 'end': '2025-06-18', 'label': 'FOMC Meeting'},
            {'date': '2025-07-29', 'end': '2025-07-30', 'label': 'FOMC Meeting'},
            {'date': '2025-09-16', 'end': '2025-09-17', 'label': 'FOMC Meeting'},
            {'date': '2025-10-28', 'end': '2025-10-29', 'label': 'FOMC Meeting'},
            {'date': '2025-12-16', 'end': '2025-12-17', 'label': 'FOMC Meeting'},
        ]
        
        return fomc_2024 if year == 2024 else fomc_2025
    
    def get_economic_reports(self, year: int) -> List[Dict]:
        """Get key economic report dates (CPI, NFP, GDP)"""
        # These are recurring monthly/quarterly
        reports = []
        
        # CPI - Released monthly, usually Tuesday-Wednesday of second week
        # NFP (Non-Farm Payrolls) - First Friday of each month
        # GDP - Quarterly
        
        months_2024 = {
            'NFP': [
                '2024-01-05', '2024-02-02', '2024-03-08', '2024-04-05',
                '2024-05-03', '2024-06-07', '2024-07-05', '2024-08-02',
                '2024-09-06', '2024-10-04', '2024-11-01', '2024-12-06'
            ],
            'CPI': [
                '2024-01-11', '2024-02-13', '2024-03-12', '2024-04-10',
                '2024-05-15', '2024-06-12', '2024-07-11', '2024-08-14',
                '2024-09-11', '2024-10-10', '2024-11-13', '2024-12-11'
            ]
        }
        
        for report_type, dates in months_2024.items():
            for date in dates:
                reports.append({
                    'date': date,
                    'type': report_type,
                    'name': f'{report_type} Release',
                    'time': '08:30 ET',
                    'importance': 'high' if report_type in ['NFP', 'CPI'] else 'medium'
                })
        
        return reports
    
    def get_options_expiration(self, year: int) -> List[Dict]:
        """Get monthly options expiration dates (3rd Friday)"""
        expirations = []
        
        for month in range(1, 13):
            # Find third Friday
            first_day = datetime(year, month, 1)
            fridays = []
            for day in range(1, 32):
                try:
                    d = datetime(year, month, day)
                    if d.weekday() == 4:  # Friday
                        fridays.append(d)
                except ValueError:
                    break
            
            if len(fridays) >= 3:
                third_friday = fridays[2]
                expirations.append({
                    'date': third_friday.strftime('%Y-%m-%d'),
                    'type': 'monthly_opex',
                    'name': f'Monthly Options Expiration',
                    'importance': 'high'
                })
        
        return expirations
    
    def get_calendar_events(self, month: int, year: int) -> List[Dict]:
        """Get all events for a given month"""
        events = []
        
        # Add holidays
        for holiday in self.get_holidays(year):
            h_date = datetime.strptime(holiday['date'], '%Y-%m-%d')
            if h_date.month == month:
                events.append({
                    'date': holiday['date'],
                    'type': 'holiday',
                    'name': holiday['name'],
                    'importance': 'high',
                    'market_closed': True
                })
        
        # Add FOMC
        for fomc in self.get_fomc_dates(year):
            f_date = datetime.strptime(fomc['date'], '%Y-%m-%d')
            if f_date.month == month:
                events.append({
                    'date': fomc['date'],
                    'type': 'fomc',
                    'name': fomc['label'],
                    'importance': 'high',
                    'market_closed': False
                })
        
        # Add economic reports
        for report in self.get_economic_reports(year):
            r_date = datetime.strptime(report['date'], '%Y-%m-%d')
            if r_date.month == month:
                events.append(report)
        
        # Add options expiration
        for opex in self.get_options_expiration(year):
            o_date = datetime.strptime(opex['date'], '%Y-%m-%d')
            if o_date.month == month:
                events.append(opex)
        
        # Sort by date
        events.sort(key=lambda x: x['date'])
        
        return events
    
    def get_market_hours_nz(self) -> Dict:
        """Get market hours in New Zealand time"""
        return {
            'pre_market': {'start': '21:00', 'end': '02:30 NZST', 'label': 'Pre-Market (NZ)'},
            'regular': {'start': '02:30', 'end': '09:00 NZST', 'label': 'Regular Hours (NZ)'},
            'after_hours': {'start': '09:00', 'end': '13:00 NZST', 'label': 'After Hours (NZ)'},
            'note': 'NZ is 16-18 hours ahead of US Eastern'
        }
    
    def get_upcoming_events(self, days: int = 7) -> List[Dict]:
        """Get events for next N days"""
        today = datetime.now()
        events = []
        
        for i in range(days):
            date = today + timedelta(days=i)
            day_events = self.get_calendar_events(date.month, date.year)
            
            for event in day_events:
                if event['date'] == date.strftime('%Y-%m-%d'):
                    events.append({
                        **event,
                        'day_name': date.strftime('%A'),
                        'days_until': i
                    })
        
        return events
