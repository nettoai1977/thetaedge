#!/usr/bin/env python3
"""
ThetaBrain Automated Scanner
Checks market conditions and generates trading signals
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.expanduser("~/thetaedge"))

from src.engine.theta_brain import ThetaBrain, MarketInputs
from src.engine.vix_monitor import VIXMonitor
from src.engine.market_calendar import MarketCalendar


def get_market_data():
    """Get current market data"""
    # In production, use yfinance or API
    # For now, use simulated data
    import random
    
    return {
        'vix': 14.5 + random.uniform(-2, 2),
        'vix_trend': random.choice(['rising', 'falling', 'stable']),
        'qqq_price': 482 + random.uniform(-5, 5),
        'qqq_iv_rank': 45 + random.uniform(-10, 10),
        'qqq_volume': 35000000,
        'spy_price': 551 + random.uniform(-5, 5),
        'spy_iv_rank': 38 + random.uniform(-10, 10),
        'iwm_price': 218 + random.uniform(-3, 3),
        'iwm_iv_rank': 52 + random.uniform(-10, 10),
    }


def check_calendar_events():
    """Check upcoming calendar events"""
    cal = MarketCalendar()
    events = cal.get_upcoming_events(7)
    
    fomc_days = None
    cpi_days = None
    earnings_days = None
    
    for event in events:
        if event['type'] == 'fomc':
            fomc_days = event.get('days_until', 14)
        elif event['type'] == 'CPI':
            cpi_days = event.get('days_until', 14)
    
    return {
        'fomc_days': fomc_days,
        'cpi_days': cpi_days,
        'earnings_days': earnings_days,
        'events': events[:3]  # Next 3 events
    }


def analyze_ticker(brain, ticker_data, calendar_data, account_size=10000):
    """Analyze a single ticker"""
    inputs = MarketInputs(
        vix_level=ticker_data['vix'],
        vix_trend=ticker_data['vix_trend'],
        symbol=ticker_data['symbol'],
        price=ticker_data['price'],
        iv_rank=ticker_data['iv_rank'],
        volume=ticker_data['volume'],
        avg_volume=15000000,
        days_to_fomc=calendar_data['fomc_days'],
        days_to_cpi=calendar_data['cpi_days'],
        days_to_earnings=calendar_data['earnings_days'],
        current_positions=0,
        account_size=account_size,
        current_risk_pct=5.0
    )
    
    return brain.analyze(inputs)


def format_alert(ticker, analysis):
    """Format analysis as alert message"""
    signal_emoji = {
        'strong_buy': '🟢🟢',
        'buy': '🟢',
        'hold': '🟡',
        'wait': '🟠',
        'avoid': '🔴',
        'strong_avoid': '🔴🔴'
    }
    
    strategy_display = analysis.recommended_strategy.replace('_', ' ').title()
    
    msg = f"""
🧠 *ThetaBrain Signal*

{signal_emoji.get(analysis.signal, '⚪')} *{analysis.signal.upper()}* ({analysis.signal_strength})

*{ticker['symbol']}* - ${ticker['price']:.2f}
Strategy: *{strategy_display}*
Confidence: {analysis.strategy_confidence}

*Strikes:*
Put: ${analysis.suggested_put_strike}
Call: ${analysis.suggested_call_strike}

*Position:*
Contracts: {analysis.recommended_contracts}
Max Risk: ${analysis.max_risk_dollars:,.0f}

*Entry Rules:*
"""
    
    for rule in analysis.entry_rules[:3]:
        msg += f"{rule}\n"
    
    if analysis.warnings:
        msg += "\n⚠️ *Warnings:*\n"
        for w in analysis.warnings:
            msg += f"{w}\n"
    
    return msg.strip()


def format_morning_brief(data, calendar_data):
    """Format morning brief"""
    events_text = ""
    for event in calendar_data.get('events', []):
        events_text += f"• {event['name']}\n"
    
    msg = f"""
🌅 *ThetaBrain Morning Brief*

*Market Status:* Open
*VIX:* {data['vix']:.1f} ({data['vix_trend']})
*Date:* {datetime.now().strftime('%A, %B %d')}

*Top Opportunities:*
• QQQ IV Rank: {data['qqq_iv_rank']:.0f}%
• SPY IV Rank: {data['spy_iv_rank']:.0f}%
• IWM IV Rank: {data['iwm_iv_rank']:.0f}%

*Upcoming Events:*
{events_text if events_text else 'No major events this week'}

*Recommendation:* Reply SCAN for analysis
"""
    return msg.strip()


def run_scan():
    """Main scan function"""
    brain = ThetaBrain()
    data = get_market_data()
    calendar = check_calendar_events()
    
    # Analyze top tickers
    tickers = [
        {'symbol': 'QQQ', 'price': data['qqq_price'], 'iv_rank': data['qqq_iv_rank'], 'volume': data['qqq_volume'], 'vix': data['vix'], 'vix_trend': data['vix_trend']},
        {'symbol': 'SPY', 'price': data['spy_price'], 'iv_rank': data['spy_iv_rank'], 'volume': 55000000, 'vix': data['vix'], 'vix_trend': data['vix_trend']},
        {'symbol': 'IWM', 'price': data['iwm_price'], 'iv_rank': data['iwm_iv_rank'], 'volume': 25000000, 'vix': data['vix'], 'vix_trend': data['vix_trend']},
    ]
    
    results = []
    for ticker in tickers:
        analysis = analyze_ticker(brain, ticker, calendar)
        results.append({
            'ticker': ticker,
            'analysis': analysis
        })
    
    # Find best opportunity
    best = None
    for r in results:
        if r['analysis'].signal in ['strong_buy', 'buy']:
            if best is None or r['analysis'].strategy_confidence == 'high':
                best = r
    
    # Format output
    output = []
    
    # Morning brief
    output.append(format_morning_brief(data, calendar))
    
    # Best signal
    if best:
        output.append("\n" + format_alert(best['ticker'], best['analysis']))
    
    # All signals summary
    output.append("\n📊 *All Signals:*")
    for r in results:
        signal = r['analysis'].signal.upper()
        emoji = '🟢' if 'buy' in signal else '🟡' if signal == 'HOLD' else '🔴'
        output.append(f"{emoji} {r['ticker']['symbol']}: {signal} ({r['analysis'].recommended_strategy.replace('_', ' ').title()})")
    
    return "\n".join(output)


if __name__ == "__main__":
    print(run_scan())
