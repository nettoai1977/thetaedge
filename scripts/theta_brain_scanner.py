#!/usr/bin/env python3
"""
ThetaBrain Automated Scanner - Real Data
Checks market conditions and generates trading signals
"""

import sys
import os
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.expanduser("~/thetaedge"))

from src.engine.theta_brain import ThetaBrain, MarketInputs
from src.engine.vix_monitor import VIXMonitor
from src.engine.ticker_scanner import TickerScanner


def run_scan():
    """Main scan function with real data"""
    brain = ThetaBrain()
    vix_monitor = VIXMonitor()
    scanner = TickerScanner()
    
    # Get real VIX
    vix_data = vix_monitor.get_current_vix()
    vix = vix_data['current']
    vix_signal = vix_data['signal']
    
    # Analyze top tickers
    tickers_to_check = ['QQQ', 'SPY', 'IWM']
    results = []
    
    for symbol in tickers_to_check:
        try:
            # Get live data for each ticker
            live = brain.get_live_data(symbol)
            
            inputs = MarketInputs(
                vix_level=vix,
                vix_trend='stable',
                symbol=symbol,
                price=live['price'],
                iv_rank=live['iv_rank'],
                volume=live['volume'],
                avg_volume=live['avg_volume'],
                days_to_fomc=14,  # Would need calendar integration
                days_to_cpi=7,
                days_to_earnings=14 if live.get('has_earnings_soon') else None,
                current_positions=0,
                account_size=10000,
                current_risk_pct=5.0
            )
            
            analysis = brain.analyze(inputs)
            results.append({
                'symbol': symbol,
                'price': live['price'],
                'iv_rank': live['iv_rank'],
                'analysis': analysis
            })
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
    
    # Find best opportunity
    best = None
    for r in results:
        if r['analysis'].signal in ['strong_buy', 'buy']:
            if best is None or r['analysis'].strategy_confidence == 'high':
                best = r
    
    # Format output
    output = []
    
    # Header
    output.append(f"🧠 *ThetaBrain Scanner*")
    output.append(f"📅 {datetime.now().strftime('%A, %B %d %Y')}")
    output.append("")
    
    # VIX Status
    output.append(f"*VIX:* {vix} ({vix_data['zone']['label']})")
    output.append(f"*Signal:* {vix_signal}")
    output.append("")
    
    # Ticker Analysis
    output.append("*Ticker Analysis:*")
    for r in results:
        emoji = '🟢' if 'buy' in r['analysis'].signal else '🟡' if r['analysis'].signal == 'hold' else '🔴'
        output.append(f"{emoji} {r['symbol']}: ${r['price']:.2f} (IV: {r['iv_rank']:.0f}%)")
    
    output.append("")
    
    # Best Signal
    if best:
        output.append(f"*🎯 Best Opportunity:*")
        output.append(f"Signal: *{best['analysis'].signal.upper()}*")
        output.append(f"Strategy: *{best['analysis'].recommended_strategy.replace('_', ' ').title()}*")
        output.append(f"Confidence: {best['analysis'].strategy_confidence}")
        output.append(f"Strikes: Put {best['analysis'].suggested_put_strike} / Call {best['analysis'].suggested_call_strike}")
        output.append(f"Contracts: {best['analysis'].recommended_contracts}")
    else:
        output.append("*No strong signals at this time*")
    
    return "\n".join(output)


if __name__ == "__main__":
    print(run_scan())
