# Options Trading Tool — Complete Build Blueprint

## Executive Summary

Build a professional options trading tool inspired by OptionStrat/Tastytrade, tailored for Ravish's strategies (calendar spreads, double calendars, diagonals). The tool will include:
1. **Strategy Calculator** — Payoff diagrams, Greeks, risk analysis
2. **Backtesting Engine** — Test strategies on historical data
3. **Trade Tracker** — Log and analyze performance
4. **VIX Monitor** — Entry signal alerts

**Target User:** Michael (NZ-based, trading US options via Moomoo, starting with $1,000)

---

## 1. UI/UX Design Standards

### Color Scheme (Industry Standard)
| Element | Color | Hex |
|---------|-------|-----|
| Profit zone | Green | #22C55E |
| Loss zone | Red | #EF4444 |
| Expiration P&L | Blue | #3B82F6 |
| Current value | Gray dashed | #9CA3AF |
| Background (dark) | Near-black | #0F172A |
| Surface | Dark gray | #1E293B |
| Text primary | White | #F8FAFC |
| Accent | Cyan | #06B6D4 |

### Typography
- **Headers:** Inter or SF Pro Display (bold)
- **Body:** Inter or system font
- **Numbers:** JetBrains Mono (monospace for alignment)

### Layout Pattern
```
┌─────────────────────────────────────────────────────────────┐
│  Header: Logo | Strategy Selector | Settings | Dark/Light  │
├─────────────────────────────────────────────────────────────┤
│  Left Panel (40%)           │  Right Panel (60%)           │
│  ┌─────────────────────┐   │  ┌─────────────────────────┐ │
│  │ Strategy Builder     │   │  │ Payoff Diagram          │ │
│  │ - Symbol input       │   │  │ (Interactive chart)     │ │
│  │ - Expiration picker  │   │  │                         │ │
│  │ - Strike selector    │   │  │                         │ │
│  │ - Buy/Sell toggle    │   │  └─────────────────────────┘ │
│  │ - Quantity           │   │  ┌─────────────────────────┐ │
│  │ + Add Leg button     │   │  │ Metrics Panel           │ │
│  │                      │   │  │ Max Profit | Max Loss    │ │
│  │ [Strategy Templates] │   │  │ Breakeven | POP | POM    │ │
│  │ - Calendar Spread    │   │  │ Delta | Theta | Vega     │ │
│  │ - Double Calendar    │   │  │ Risk/Reward Ratio        │ │
│  │ - Diagonal           │   │  └─────────────────────────┘ │
│  │ - Iron Condor        │   │  ┌─────────────────────────┐ │
│  │ - Butterfly          │   │  │ Greeks Chart             │ │
│  │ - Straddle           │   │  │ (Delta/Theta/Vega curves)│ │
│  └─────────────────────┘   │  └─────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Footer: VIX | Market Status | Last Updated | Disclaimer    │
└─────────────────────────────────────────────────────────────┘
```

### Key UX Principles
1. **Real-time updates** — No "calculate" button; recalculate on every input change
2. **Interactive sliders** — Drag current price marker on payoff chart
3. **Strategy templates** — Pre-built shapes for common strategies
4. **Progressive disclosure** — Simple by default, advanced options available
5. **Educational tooltips** — Explain Greeks and metrics on hover
6. **Mobile responsive** — Stack panels vertically on small screens

---

## 2. Technical Architecture

### Recommended Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | React + TypeScript + Tailwind CSS | Fast development, dark mode native, large ecosystem |
| **Charts** | Recharts or D3.js | Recharts for simplicity, D3 for maximum flexibility |
| **Backend** | Python FastAPI | Fast, async, great for calculations |
| **Calculation Engine** | NumPy + SciPy + QuantLib | Industry-standard, accurate |
| **Data Source** | yfinance (free) | No API key, real-time options chains |
| **Database** | SQLite (local) | Simple, portable, no setup |
| **Deployment** | Local web app | Run on localhost, access from browser |

### Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Strategy │  │ Payoff   │  │ Greeks   │  │ Trade    │  │
│  │ Builder  │  │ Chart    │  │ Panel    │  │ Tracker  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │              │        │
│       └──────────────┴──────────────┴──────────────┘        │
│                          │                                   │
│                    REST API calls                            │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────┴──────────────────────┐           │
│  │              API Layer                       │           │
│  └──────────────────────┬──────────────────────┘           │
│                          │                                   │
│  ┌─────────────┐  ┌─────┴─────┐  ┌─────────────┐          │
│  │ Pricing     │  │ Greeks    │  │ Backtesting │          │
│  │ Engine      │  │ Calculator│  │ Engine      │          │
│  │ (Black-     │  │ (NumPy)   │  │ (Custom)    │          │
│  │  Scholes)   │  │           │  │             │          │
│  └──────┬──────┘  └─────┬─────┘  └──────┬──────┘          │
│         │               │               │                   │
│  ┌──────┴───────────────┴───────────────┴──────┐          │
│  │              Data Layer                      │          │
│  │  yfinance (options chains)                   │          │
│  │  SQLite (trade logs)                         │          │
│  │  Cache (Redis/file)                          │          │
│  └─────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Core Calculation Engine

### Black-Scholes Implementation
```python
import numpy as np
from scipy.stats import norm

def black_scholes(S, K, T, r, sigma, option_type='call'):
    """
    S: Current stock price
    K: Strike price
    T: Time to expiration (years)
    r: Risk-free interest rate
    sigma: Volatility (IV)
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price

def calculate_greeks(S, K, T, r, sigma, option_type='call'):
    """Calculate all Greeks for an option"""
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Delta
    if option_type == 'call':
        delta = norm.cdf(d1)
    else:
        delta = norm.cdf(d1) - 1
    
    # Gamma (same for calls and puts)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    # Theta (per day)
    theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
             - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    if option_type == 'put':
        theta += r * K * np.exp(-r * T) / 365
    
    # Vega (per 1% move)
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    
    # Rho (per 1% move)
    rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    if option_type == 'put':
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    
    return {
        'delta': round(delta, 4),
        'gamma': round(gamma, 4),
        'theta': round(theta, 4),
        'vega': round(vega, 4),
        'rho': round(rho, 4)
    }
```

### Payoff Calculator
```python
def calculate_payoff(positions, underlying_prices):
    """
    positions: list of dicts with keys:
        - type: 'call' or 'put'
        - strike: float
        - premium: float
        - quantity: int (positive = long, negative = short)
        - expiration: str (YYYY-MM-DD)
    
    underlying_prices: array of prices to calculate P&L for
    
    Returns: array of P&L values
    """
    payoffs = np.zeros_like(underlying_prices)
    
    for pos in positions:
        if pos['type'] == 'call':
            option_payoff = np.maximum(underlying_prices - pos['strike'], 0)
        else:  # put
            option_payoff = np.maximum(pos['strike'] - underlying_prices, 0)
        
        # For long positions: payoff - premium
        # For short positions: premium - payoff
        if pos['quantity'] > 0:  # Long
            payoffs += pos['quantity'] * (option_payoff - pos['premium'])
        else:  # Short
            payoffs += abs(pos['quantity']) * (pos['premium'] - option_payoff)
    
    return payoffs
```

### Calendar Spread Specific
```python
def calendar_spread(S, K_call, short_exp, long_exp, r, sigma_short, sigma_long):
    """
    Calculate calendar spread P&L
    
    S: Current stock price
    K_call: Strike price (same for both)
    short_exp: Short leg expiration (days)
    long_exp: Long leg expiration (days)
    r: Risk-free rate
    sigma_short: IV for short leg
    sigma_long: IV for long leg
    """
    T_short = short_exp / 365
    T_long = long_exp / 365
    
    # Price the two options
    short_price = black_scholes(S, K_call, T_short, r, sigma_short, 'call')
    long_price = black_scholes(S, K_call, T_long, r, sigma_long, 'call')
    
    # Net debit (cost to enter)
    net_debit = long_price - short_price
    
    # Greeks
    short_greeks = calculate_greeks(S, K_call, T_short, r, sigma_short, 'call')
    long_greeks = calculate_greeks(S, K_call, T_long, r, sigma_long, 'call')
    
    # Net Greeks
    net_greeks = {
        'delta': long_greeks['delta'] - short_greeks['delta'],
        'gamma': long_greeks['gamma'] - short_greeks['gamma'],
        'theta': long_greeks['theta'] - short_greeks['theta'],
        'vega': long_greeks['vega'] - short_greeks['vega'],
    }
    
    return {
        'net_debit': net_debit,
        'max_profit': None,  # Depends on price at short expiration
        'max_loss': net_debit,
        'net_greeks': net_greeks,
        'short_price': short_price,
        'long_price': long_price
    }
```

---

## 4. Data Sources

### Primary: Yahoo Finance (yfinance)
```python
import yfinance as yf

# Get options chain
ticker = yf.Ticker("QQQ")
options_dates = ticker.options  # List of expiration dates

# Get chain for specific date
chain = ticker.option_chain('2026-09-19')
calls = chain.calls  # DataFrame with strike, bid, ask, IV, volume, OI
puts = chain.puts

# Fields available:
# strike, lastPrice, bid, ask, change, percentChange,
# volume, openInterest, impliedVolatility
```

### VIX Data
```python
import yfinance as yf

# Get VIX
vix = yf.Ticker("^VIX")
vix_data = vix.history(period="1d")
current_vix = vix_data['Close'].iloc[-1]

# VIX Interpretation:
# < 15: Low volatility (good for selling options)
# 15-20: Normal (neutral)
# 20-30: High (caution)
# > 30: Very high (opportunity for buyers)
```

### Limitations & Workarounds
| Limitation | Workaround |
|------------|------------|
| yfinance may break | Cache data locally, fallback to manual entry |
| No real-time Greeks | Calculate using Black-Scholes |
| 15-min delay | Acceptable for backtesting and planning |
| Rate limiting | Batch requests, cache aggressively |

---

## 5. Backtesting Engine

### Strategy: Double Calendar Backtest
```python
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
            
            # Simulate trade exit (at short expiration or profit target)
            exit_trade = self._exit_trade(trade, data, i)
            
            self.trades.append(exit_trade)
        
        return self._calculate_results()
    
    def _enter_trade(self, entry_date, price, put_strike, call_strike):
        """Enter a double calendar spread"""
        # Get options data (simplified - use actual data in production)
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
        
        # Simplified - calculate based on price movement
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
```

---

## 6. Implementation Plan

### Phase 1: MVP (Week 1-2)
**Goal:** Working strategy calculator with payoff diagrams

| Task | Est. Time | Priority |
|------|-----------|----------|
| Set up React + Tailwind project | 2 hours | High |
| Implement Black-Scholes engine (Python) | 4 hours | High |
| Build FastAPI backend | 3 hours | High |
| Create strategy builder UI | 8 hours | High |
| Implement payoff chart (Recharts) | 6 hours | High |
| Add Greeks display | 4 hours | High |
| Strategy templates (Calendar, Double Calendar, Diagonal) | 6 hours | Medium |
| VIX display | 2 hours | Low |

### Phase 2: Enhanced Features (Week 3-4)
**Goal:** Backtesting and trade tracking

| Task | Est. Time | Priority |
|------|-----------|----------|
| Historical data fetching (yfinance) | 4 hours | High |
| Backtesting engine | 12 hours | High |
| Trade logging (SQLite) | 4 hours | Medium |
| Performance dashboard | 8 hours | Medium |
| VIX monitoring cron job | 2 hours | Low |

### Phase 3: Polish (Week 5-6)
**Goal:** Production-ready tool

| Task | Est. Time | Priority |
|------|-----------|----------|
| Mobile responsive design | 6 hours | Medium |
| Dark/light theme toggle | 2 hours | Low |
| Educational tooltips | 4 hours | Low |
| Performance optimization | 4 hours | Medium |
| Error handling & edge cases | 4 hours | High |

---

## 7. Open Source References

| Project | Language | Stars | Use For |
|---------|----------|-------|---------|
| [OptionLab](https://github.com/rgaveiga/optionlab) | Python | 563 | Strategy evaluation, Greeks |
| [btc_options](https://github.com/riba2534/btc_options) | React/TS | 10 | UI patterns, Recharts |
| [optionmatrix](https://github.com/AnthonyBradford/optionmatrix) | C++ | 249 | Pricing models reference |
| [yfinance](https://github.com/ranaroussi/yfinance) | Python | 25k | Free options data |
| [QuantLib](https://github.com/lballabio/QuantLib-SWIG) | Python | 397 | Professional pricing |

---

## 8. Key Formulas Reference

### Payoff at Expiration
```
Long Call:  max(S - K, 0) - Premium
Long Put:   max(K - S, 0) - Premium
Short Call: Premium - max(S - K, 0)
Short Put:  Premium - max(K - S, 0)
```

### Breakeven Points
```
Long Call:  K + Premium Paid
Long Put:   K - Premium Paid
Short Call: K + Premium Received
Short Put:  Premium Received - K
```

### Multi-Leg P&L
```
Total P&L = Σ (position_size_i × payoff_i(S))
```

### Probability of Profit (Approximation)
```
POP ≈ N(d2) for long calls
POP ≈ N(-d2) for long puts
Where d2 = [ln(S/K) + (r - σ²/2)T] / (σ√T)
```

---

## 9. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Calculation accuracy | Within 1% of OptionStrat | Compare outputs |
| Chart rendering speed | < 100ms | Performance profiling |
| User can build calendar spread | < 2 minutes | User testing |
| Backtest 1 year of data | < 30 seconds | Timing |
| Mobile responsive | Works on iPhone SE | Device testing |

---

*Blueprint created: 2026-08-22*
*Research sources: OptionStrat, OptionsProfitCalculator, ThinkorSwim, Tastytrade, GitHub repos*
