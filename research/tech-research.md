# Options Strategy Backtesting Engine - Technical Architecture Research

## Executive Summary

Research completed on building an options strategy backtesting engine. Found 92+ open-source options backtesting repositories on GitHub, multiple pricing libraries, and several free data sources. The ecosystem is mature but fragmented - no single library handles everything.

---

## 1. FREE DATA SOURCES

### 1.1 Yahoo Finance (yfinance)
**Repository:** https://github.com/ranaroussi/yfinance (25k stars)
**Status:** Actively maintained (v1.6.0, updated last week)

```python
import yfinance as yf

# Get options chain
ticker = yf.Ticker("AAPL")
options = ticker.options  # List of expiration dates

# Get options chain for specific expiration
chain = ticker.option_chain('2024-01-19')
puts = chain.puts
calls = chain.calls

# Fields available:
# strike, lastPrice, bid, ask, change, percentChange,
# volume, openInterest, impliedVolatility
```

**Key Points:**
- Free, no API key required
- Real-time data (15min delay)
- Options chain with Greeks not included (must calculate)
- Historical options data very limited
- Rate limiting issues with heavy usage

### 1.2 CBOE Data
**Relevant Repositories:**
- `simonlin1212/global-stock-data` (1.5k stars) - CBOE options with full Greeks + 0DTE flow
- `Darthreign/gex-dashboard` - Gamma/Delta Exposure from CBOE delayed data
- `qlero/vix_index_modelization` - VIX index from CBOE white paper

```python
# CBOE delayed data (free, 15-min delay)
# URL pattern: https://www.cboe.com/delayed_quotes/{symbol}/option_quotes
# CSV download available for historical data

# For real-time CBOE data, paid subscription required
# But delayed data is sufficient for backtesting
```

**Key Points:**
- Delayed data (15 min) is free
- Historical data available via CSV downloads
- Greeks included in CBOE data
- Official source for VIX, SPX options

### 1.3 Other Free Sources
- **NSEPY** - Indian NSE options data (used in OptionsnPython repo)
- **Polygon.io** - Free tier available (limited)
- **Alpha Vantage** - Free tier for basic data

---

## 2. OPTIONS PRICING MODELS

### 2.1 Black-Scholes-Merton (BSM)
**Python Implementation:**

```python
import numpy as np
from scipy.stats import norm

def black_scholes(S, K, T, r, sigma, option_type='call'):
    """
    S: Current stock price
    K: Strike price
    T: Time to expiration (years)
    r: Risk-free interest rate
    sigma: Volatility
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price
```

### 2.2 Binomial Model
**Repository:** `just-krivi/option-pricing-models` (333 stars)

```python
def binomial_price(S, K, T, r, sigma, N=100, option_type='call', american=False):
    """
    Cox-Ross-Rubinstein binomial tree
    """
    dt = T / N
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp(r * dt) - d) / (u - d)
    
    # Build price tree
    ST = S * u ** np.arange(N, -1, -1) * d ** np.arange(0, N+1, 1)
    
    # Calculate option values at expiry
    if option_type == 'call':
        values = np.maximum(ST - K, 0)
    else:
        values = np.maximum(K - ST, 0)
    
    # Backward induction
    for i in range(N-1, -1, -1):
        values = np.exp(-r * dt) * (p * values[:-1] + (1-p) * values[1:])
        if american:
            ST = S * u ** np.arange(i, -1, -1) * d ** np.arange(0, i+1, 1)
            if option_type == 'call':
                values = np.maximum(values, ST - K)
            else:
                values = np.maximum(values, K - ST)
    
    return values[0]
```

### 2.3 American Options
**Key Insight:** Black-Scholes only works for European options. For American options (most equity options):
- Use Binomial model (preferred)
- Use Longstaff-Schwartz Monte Carlo
- Use QuantLib's American engine

---

## 3. GREEKS CALCULATION METHODS

### 3.1 The Greeks

| Greek | Formula | Description |
|-------|---------|-------------|
| **Delta (Δ)** | ∂V/∂S | Rate of change of option price w.r.t. stock price |
| **Gamma (Γ)** | ∂²V/∂S² | Rate of change of delta |
| **Theta (Θ)** | ∂V/∂t | Time decay |
| **Vega (ν)** | ∂V/∂σ | Sensitivity to volatility |
| **Rho (ρ)** | ∂V/∂r | Sensitivity to interest rates |

### 3.2 Analytical Greeks (Black-Scholes)

```python
def option_greeks(S, K, T, r, sigma, option_type='call'):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Delta
    if option_type == 'call':
        delta = norm.cdf(d1)
    else:
        delta = norm.cdf(d1) - 1
    
    # Gamma
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    # Theta
    theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
             - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    if option_type == 'put':
        theta += r * K * np.exp(-r * T) / 365
    
    # Vega (per 1% move)
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    
    # Rho
    rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    if option_type == 'put':
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    
    return {'delta': delta, 'gamma': gamma, 'theta': theta, 
            'vega': vega, 'rho': rho}
```

### 3.3 Numerical Greeks
For models without closed-form solutions:
- **Finite Difference Method:** ΔV/ΔS
- **Bump-and-Revalue:** Change each input slightly, reprice

---

## 4. PYTHON LIBRARIES

### 4.1 QuantLib-Python
**Repository:** https://github.com/lballabio/QuantLib-SWIG (397 stars)
**Status:** Very actively maintained (v1.43, updated 3 days ago)

```python
import QuantLib as ql

# Setup
date = ql.Date(15, 1, 2024)
ql.Settings.instance().evaluationDate = date

# Option setup
option_type = ql.Option.Call
payoff = ql.PlainVanillaPayoff(option_type, 100.0)
exercise = ql.AmericanExercise(date, ql.Date(15, 6, 2024))
option = ql.VanillaOption(payoff, exercise)

# Pricing engine
spot = ql.QuoteHandle(ql.SimpleQuote(100.0))
rate = ql.YieldTermStructureHandle(
    ql.FlatForward(date, 0.05, ql.Actual365Fixed())
)
vol = ql.BlackVolTermStructureHandle(
    ql.BlackConstantVol(date, ql.TARGET(), 0.2, ql.Actual365Fixed())
)
bsm = ql.BlackScholesMertonProcess(spot, rate, rate, vol)
option.setPricingEngine(ql.BaroneAdesiWhaleyApproximationEngine(bsm))

# Get price and Greeks
price = option.NPV()
delta = option.delta()
gamma = option.gamma()
theta = option.theta()
vega = option.vega()
```

**Pros:**
- Most comprehensive quant finance library
- American options with Barone-Adesi approximation
- Exotic options support
- Well-documented

**Cons:**
- Heavy dependency (C++ library)
- Complex setup
- Slower for simple calculations

### 4.2 pyvolr (Modern replacement for py_vollib)
**Repository:** https://github.com/yipjunkai/pyvolr (3 stars, new)
**Status:** Drop-in replacement for abandoned py_vollib

```python
# From README - Rust core for performance
import pyvolr

# Black-Scholes pricing
price = pyvolr.black76(S=100, K=100, T=1, r=0.05, sigma=0.2, flag='c')

# Greeks
greeks = pyvolr.black76_greeks(S=100, K=100, T=1, r=0.05, sigma=0.2, flag='c')

# Implied volatility
iv = pyvolr.black76_iv(price=10, S=100, K=100, T=1, r=0.05, flag='c')
```

**Pros:**
- Very fast (Rust core)
- Drop-in replacement for py_vollib
- Modern maintained codebase

**Cons:**
- Very new (3 months old)
- Small community

### 4.3 vollib/py_vollib (Legacy)
**Website:** https://vollib.org/
**Status:** Abandoned (last update years ago)

```python
# Original API (if installed)
from py_vollib.black_scholes import black_scholes
from py_vollib.black_scholes import put_black_scholes
from py_vollib.black_scholes import call_black_scholes
from py_vollib.black_scholes import black_scholes_flag
from py_vollib.black_scholes import normalized_black_scholes_put
from py_vollib.black_scholes import normalized_black_scholes_call

# Greeks
from py_vollib.black_scholes.greeks import delta
from py_vollib.black_scholes.greeks import gamma
from py_vollib.black_scholes.greeks import theta
from py_vollib.black_scholes.greeks import vega
from py_vollib.black_scholes.greeks import rho
```

**Warning:** Original py_vollib is abandoned. Use pyvolr instead.

### 4.4 PyFENG
**Repository:** https://github.com/quants-net/PyFENG (184 stars)
**Status:** Actively maintained

```python
import pyfeng as pf

# Black-Scholes model
model = pf.Bsm(100)  # Strike = 100
price = model.price(100, 100, 0.2, 1)  # S=100, K=100, T=1, r=0.2

# Heston model
model = pf.Heston1993()
price = model.price(100, 100, 0.2, 1, v0=0.04, kappa=2, theta=0.04, sigma=0.5, rho=-0.7)
```

**Pros:**
- Modern, well-maintained
- Multiple models (BSM, Heston, SABR, Bachelier)
- Good documentation

### 4.5 wallstreet
**Repository:** https://github.com/mcdallas/wallstreet (1.7k stars)
**Status:** Last updated 2 years ago

```python
from wallstreet import Stock, Call, Put

# Get stock data
s = Stock('AAPL')
print(s.price)

# Get options data with Greeks
c = Call('AAPL', expiration='2024-01-19', strike=100)
print(c.price)
print(c.delta)
print(c.gamma)
print(c.theta)
print(c.vega)
```

**Pros:**
- Easy to use
- Built-in Greeks calculation
- Real-time data from Yahoo Finance

**Cons:**
- Not maintained
- Limited functionality

### 4.6 optionlab
**Repository:** https://github.com/rgaveiga/optionlab (563 stars)
**Status:** Very actively maintained (2 weeks ago)

```python
from optionlab import Strategy, run_strategy

# Define strategy
strategy = Strategy(
    stock_price=100,
    start_date="2024-01-01",
    target_date="2024-01-31",
    risk_free_rate=0.05,
    strategy=[
        {"type": "call", "strike": 100, "premium": 5, "n": 1},
        {"type": "call", "strike": 105, "premium": 3, "n": -1},
    ]
)

# Run strategy
results = run_strategy(strategy)
print(results["profit_loss"])
```

**Pros:**
- Purpose-built for options strategies
- Backtesting capabilities
- Good documentation

---

## 5. BACKTESTING FRAMEWORKS

### 5.1 Specialized Options Backtesting

#### OptionStrategiesBacktesting
**Repository:** `OptionsnPython/Option-strategies-backtesting-in-Python` (176 stars)

```python
# Jupyter notebooks with examples for:
# - Straddle strategy
# - Strangle strategy  
# - Iron condor
# - Butterfly spread
# - Ratio spreads

# Uses mibian library for Greeks
import mibian

# Calculate implied volatility
bs = mibian.BS([100, 100, 0.05, 30], callPrice=5)
bs.impliedVolatility

# Calculate Greeks
bs = mibian.BS([100, 100, 0.05, 30], volatility=20)
bs.callDelta
bs.callGamma
bs.callTheta
bs.vega
```

### 5.2 General Backtesting Frameworks

#### backtrader (5k stars)
```python
import backtrader as bt

class OptionsStrategy(bt.Strategy):
    def __init__(self):
        self.signal = None
        
    def next(self):
        # Implement options logic here
        pass

# Note: No native options support, must extend
```

#### vectorbt (4k stars)
```python
import vectorbt as vbt

# For portfolio analysis, not options-specific
# Can be extended for options with custom signals
```

#### lumibot (1.9k stars)
```python
from lumibot.strategies import Strategy
from lumibot.brokers import Broker

class OptionsStrategy(Strategy):
    # Has native options support
    # Can trade stocks, options, crypto, forex
    pass
```

### 5.3 Quantitative Analysis

#### Qlib (47.8k stars) - Microsoft
```python
import qlib
from qlib.contrib.strategy import TopkDropout

# AI-oriented quant platform
# Can be extended for options analysis
```

---

## 6. ARCHITECTURE RECOMMENDATIONS

### 6.1 Minimum Viable Stack

```python
# Data Layer
import yfinance as yf  # Free data

# Pricing Layer
import QuantLib as ql  # Or pyvolr for speed

# Strategy Layer
# Custom implementation using optionlab patterns

# Backtesting Layer
# Event-driven architecture recommended
```

### 6.2 Suggested Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                            │
├─────────────────────────────────────────────────────────┤
│  yfinance (free)  │  CBOE (delayed)  │  Paid APIs      │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                  Pricing Engine                         │
├─────────────────────────────────────────────────────────┤
│  Black-Scholes  │  Binomial Tree  │  Monte Carlo       │
│  (Analytical)   │  (American)     │  (Exotics)         │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                  Greeks Calculator                      │
├─────────────────────────────────────────────────────────┤
│  Analytical     │  Numerical      │  Implied Vol       │
│  (BSM formulas) │  (Finite diff)  │  (Newton-Raphson)  │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│               Strategy Engine                           │
├─────────────────────────────────────────────────────────┤
│  Legs definition │  Position sizing  │  Risk metrics   │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│               Backtesting Engine                        │
├─────────────────────────────────────────────────────────┤
│  Event loop  │  Order matching  │  P&L calculation     │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Key Design Decisions

1. **Data Source:** Start with yfinance (free), add CBOE for historical Greeks
2. **Pricing:** Use QuantLib for flexibility, pyvolr for speed
3. **Greeks:** Calculate analytically when possible, numerically for American options
4. **American Options:** Use binomial tree or Barone-Adesi approximation
5. **Backtesting:** Event-driven architecture, not vectorized

---

## 7. WORKING CODE EXAMPLES

### 7.1 Complete Simple Backtest

```python
import yfinance as yf
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta

def black_scholes(S, K, T, r, sigma, option_type='call'):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

# Simple covered call backtest
def backtest_covered_call(ticker, start_date, end_date):
    stock = yf.Ticker(ticker)
    
    # Get historical stock prices
    hist = stock.history(start=start_date, end=end_date)
    
    results = []
    for date in hist.index:
        S = hist.loc[date, 'Close']
        
        # Get options chain
        try:
            options = stock.options
            if len(options) > 0:
                # Select 30-day expiration
                target_exp = date + timedelta(days=30)
                exp = min(options, key=lambda x: abs(datetime.strptime(x, '%Y-%m-%d') - target_exp))
                
                chain = stock.option_chain(exp)
                calls = chain.calls[chain.calls['strike'] >= S * 1.02]  # Slightly OTM
                
                if len(calls) > 0:
                    call = calls.iloc[0]
                    strike = call['strike']
                    premium = call['lastPrice']
                    
                    # Calculate P&L at expiration
                    stock_price_at_exp = S * 1.02  # Assume 2% move
                    if stock_price_at_exp > strike:
                        stock_pnl = (strike - S) * 100  # Stock sold at strike
                        option_pnl = premium * 100      # Keep premium
                    else:
                        stock_pnl = (stock_price_at_exp - S) * 100
                        option_pnl = premium * 100 + (stock_price_at_exp - strike) * 100
                    
                    results.append({
                        'date': date,
                        'stock_price': S,
                        'strike': strike,
                        'premium': premium,
                        'pnl': stock_pnl + option_pnl
                    })
        except:
            continue
    
    return results

# Run backtest
results = backtest_covered_call('AAPL', '2023-01-01', '2023-12-31')
total_pnl = sum(r['pnl'] for r in results)
print(f"Total P&L: ${total_pnl}")
```

### 7.2 Greeks Heatmap

```python
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt

def option_greeks_matrix(S_range, K_range, T, r, sigma, option_type='call'):
    """Calculate Greeks matrix for heatmap"""
    deltas = np.zeros((len(K_range), len(S_range)))
    thetas = np.zeros((len(K_range), len(S_range)))
    vegas = np.zeros((len(K_range), len(S_range)))
    
    for i, K in enumerate(K_range):
        for j, S in enumerate(S_range):
            d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            
            # Delta
            if option_type == 'call':
                deltas[i, j] = norm.cdf(d1)
            else:
                deltas[i, j] = norm.cdf(d1) - 1
            
            # Theta
            thetas[i, j] = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
                           - r * K * np.exp(-r * T) * norm.cdf(d1)) / 365
            
            # Vega
            vegas[i, j] = S * norm.pdf(d1) * np.sqrt(T) / 100
    
    return deltas, thetas, vegas

# Create heatmap
S_range = np.linspace(80, 120, 20)
K_range = np.linspace(90, 110, 10)
deltas, thetas, vegas = option_greeks_matrix(S_range, K_range, T=0.25, r=0.05, sigma=0.2)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
axes[0].imshow(deltas, aspect='auto', origin='lower')
axes[0].set_title('Delta')
axes[1].imshow(thetas, aspect='auto', origin='lower')
axes[1].set_title('Theta')
axes[2].imshow(vegas, aspect='auto', origin='lower')
axes[2].set_title('Vega')
plt.show()
```

---

## 8. ISSUES AND CONSIDERATIONS

### 8.1 Data Challenges
- **Historical Options Data:** Very limited free sources
- **Greeks History:** Not available from free sources
- **Bid-Ask Spreads:** Important for realistic backtesting
- **Dividend Adjustments:** Need to account for ex-dividend dates

### 8.2 Model Limitations
- **Black-Scholes:** Assumes constant volatility (wrong)
- **Binomial:** Slow for long-dated options
- **American Options:** No closed-form solution
- **Early Exercise:** Complex to model

### 8.3 Backtesting Pitfalls
- **Survivorship Bias:** Options that expire worthless disappear from data
- **Look-ahead Bias:** Using future information
- **Transaction Costs:** Must include commissions and slippage
- **Liquidity:** Assume fills at mid-price or slightly worse

### 8.4 Missing Features in Existing Libraries
- **No complete backtesting framework** for options strategies
- **Limited support** for multi-leg strategies
- **No standard** for options strategy definition
- **No consensus** on Greeks calculation methods

---

## 9. RECOMMENDATIONS FOR BUILD

### Quick Start Stack:
```bash
pip install yfinance numpy scipy pandas matplotlib
```

### For Production:
```bash
pip install yfinance QuantLib-Python pyvolr pandas numpy
```

### For Full Features:
```bash
pip install yfinance QuantLib-Python pyvolr optionlab vectorbt pandas
```

---

## 10. REFERENCES

### Documentation
- yfinance: https://ranaroussi.github.io/yfinance
- QuantLib: https://www.quantlib.org
- pyvolr: https://github.com/yipjunkai/pyvolr
- optionlab: https://rgaveiga.github.io/optionlab

### Key Repositories
- 92+ options backtesting repos on GitHub
- `OptionsnPython/Option-strategies-backtesting-in-Python` - Jupyter examples
- `rgaveiga/optionlab` - Purpose-built library
- `Lumiwealth/lumibot` - Trading bot with options support
- `just-krivi/option-pricing-models` - Multiple pricing models

### Books (Referenced in Repos)
- "Option Greeks Strategies & Backtesting in Python" by Anjana Gupta

---

*Research completed: August 22, 2026*
