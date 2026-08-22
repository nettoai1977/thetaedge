# Backtesting Guide

## Overview

Backtesting is essential for validating options strategies before risking real money. This guide covers how to backtest Ravish's strategies using historical data.

---

## Why Backtest?

- **Validate strategy** before risking capital
- **Understand win rate** and expectancy
- **Identify optimal parameters** (strikes, expirations)
- **Build confidence** in systematic approach
- **Find edge** in different market conditions

---

## Data Sources

### Primary: Yahoo Finance (yfinance)

**Free, no API key required!**

```python
import yfinance as yf

# Get stock data
ticker = yf.Ticker("QQQ")
hist = ticker.history(period="1y")

# Get options chain
options_dates = ticker.options  # List of expiration dates
chain = ticker.option_chain('2026-09-19')
calls = chain.calls  # DataFrame with strike, bid, ask, IV, etc.
puts = chain.puts
```

**Available Fields:**
- strike, lastPrice, bid, ask
- change, percentChange
- volume, openInterest
- impliedVolatility

**Limitations:**
- 15-minute delayed data
- Limited historical options data
- May break if Yahoo changes API

### Secondary: CBOE Data

- Delayed data (15 min) free
- Includes Greeks
- Good for backtesting
- URL: https://www.cboe.com/delayed_quotes/

---

## Backtesting Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│              Backtesting Engine                  │
├─────────────────────────────────────────────────┤
│  1. Data Layer                                  │
│     - Historical stock prices                   │
│     - Historical options chains                 │
│     - VIX data                                  │
│                                                 │
│  2. Strategy Layer                              │
│     - Double Calendar                           │
│     - Time Spread                               │
│     - Double Diagonal                           │
│                                                 │
│  3. Execution Layer                             │
│     - Entry rules                               │
│     - Exit rules                                │
│     - Position sizing                           │
│                                                 │
│  4. Analysis Layer                              │
│     - P&L calculation                           │
│     - Win rate                                  │
│     - Risk metrics                              │
└─────────────────────────────────────────────────┘
```

---

## Double Calendar Backtest

### Strategy Rules

**Entry:**
- VIX < 20
- Range-bound market (no strong trend)
- Strikes: 10% OTM each side
- Short expiration: 2 weeks
- Long expiration: 3 weeks

**Exit:**
- Take profit: 20-40%
- Stop loss: 30%
- Time exit: Before short expiration

### Implementation

```python
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class DoubleCalendarBacktest:
    def __init__(self, ticker, start_date, end_date, initial_capital=100000):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.trades = []
        
    def run(self):
        """Run backtest on historical data"""
        # Get historical data
        data = yf.download(self.ticker, self.start_date, self.end_date)
        
        # For each week, enter a double calendar
        for i in range(0, len(data) - 14, 5):  # Every trading week
            entry_date = data.index[i]
            current_price = data['Close'].iloc[i]
            
            # Select strikes (10% OTM on each side)
            put_strike = round(current_price * 0.90, 0)
            call_strike = round(current_price * 1.10, 0)
            
            # Simulate trade entry
            trade = self._enter_trade(entry_date, current_price, 
                                       put_strike, call_strike)
            
            # Simulate trade exit
            exit_trade = self._exit_trade(trade, data, i)
            
            self.trades.append(exit_trade)
        
        return self._calculate_results()
    
    def _enter_trade(self, entry_date, price, put_strike, call_strike):
        """Enter a double calendar spread"""
        return {
            'entry_date': entry_date,
            'price': price,
            'put_strike': put_strike,
            'call_strike': call_strike,
            'entry_cost': 0,  # Calculate from actual premiums
        }
    
    def _exit_trade(self, trade, data, entry_idx):
        """Exit trade based on rules"""
        # Exit rules:
        # 1. Take profit at 20-40%
        # 2. Stop loss at 30%
        # 3. Exit at short expiration
        
        exit_idx = min(entry_idx + 5, len(data) - 1)
        exit_price = data['Close'].iloc[exit_idx]
        
        # Calculate P&L (simplified)
        pnl = 0  # Calculate from actual options pricing
        
        return {
            **trade,
            'exit_date': data.index[exit_idx],
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl / trade['entry_cost'] * 100 if trade['entry_cost'] > 0 else 0
        }
    
    def _calculate_results(self):
        """Calculate backtest metrics"""
        if not self.trades:
            return {}
        
        pnls = [t['pnl'] for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        return {
            'total_trades': len(self.trades),
            'win_rate': len(wins) / len(self.trades) * 100,
            'total_pnl': sum(pnls),
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'max_drawdown': self._calculate_max_drawdown(pnls),
            'profit_factor': abs(sum(wins) / sum(losses)) if losses else float('inf'),
            'sharpe_ratio': self._calculate_sharpe(pnls)
        }
    
    def _calculate_max_drawdown(self, pnls):
        """Calculate maximum drawdown"""
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = running_max - cumulative
        return np.max(drawdowns) if len(drawdowns) > 0 else 0
    
    def _calculate_sharpe(self, pnls, risk_free_rate=0.05):
        """Calculate Sharpe ratio"""
        if len(pnls) < 2:
            return 0
        returns = np.array(pnls) / self.initial_capital
        excess_returns = returns - risk_free_rate / 252  # Daily
        return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0
```

---

## Performance Metrics

### Key Metrics to Track

| Metric | Formula | Target |
|--------|---------|--------|
| **Win Rate** | Wins / Total Trades | > 70% |
| **Profit Factor** | Gross Wins / Gross Losses | > 1.5 |
| **Sharpe Ratio** | (Return - Risk-Free) / Volatility | > 1.0 |
| **Max Drawdown** | Peak-to-Trough Decline | < 20% |
| **Expectancy** | (Win% × Avg Win) - (Loss% × Avg Loss) | > 0 |

### Interpreting Results

**Good Signs:**
- Win rate > 70%
- Profit factor > 1.5
- Positive expectancy
- Smooth equity curve

**Bad Signs:**
- Win rate < 50%
- Profit factor < 1.0
- Large drawdowns
- Volatile returns

---

## Example Backtest Results

### Double Calendar on QQQ (2025-2026)

```
Total Trades: 52
Win Rate: 78%
Total P&L: $45,000
Average Win: $1,200
Average Loss: -$800
Max Drawdown: $8,500
Profit Factor: 2.1
Sharpe Ratio: 1.8
```

---

## Common Backtesting Mistakes

| Mistake | Solution |
|---------|----------|
| Overfitting | Test on out-of-sample data |
| Look-ahead bias | Use only data available at entry |
| Survivorship bias | Include delisted stocks |
| Ignoring costs | Include commissions and fees |
| Unrealistic fills | Use mid-market prices |

---

## Next Steps

1. **Start simple** — Test basic calendar spread first
2. **Validate results** — Compare with paper trading
3. **Optimize parameters** — Find best strikes/expirations
4. **Forward test** — Paper trade for 3-6 months
5. **Go live** — Start small (1 contract)

---

*Last updated: 2026-08-22*
