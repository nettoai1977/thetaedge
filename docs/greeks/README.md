# Options Greeks Reference

## Overview

The Greeks measure how an option's price changes relative to underlying parameters. Understanding them is essential for systematic options trading.

---

## The Five Greeks

### 1. Delta (Δ) — Price Sensitivity

**What it measures:** How much the option price changes for a $1 move in the underlying.

| Option Type | Delta Range | Interpretation |
|-------------|-------------|----------------|
| Call | 0 to +1 | Positive (price rises with stock) |
| Put | -1 to 0 | Negative (price falls as stock rises) |
| ATM | ±0.50 | At-the-money |
| Deep ITM | ±0.90+ | High delta, behaves like stock |
| Deep OTM | ±0.10- | Low delta, unlikely to profit |

**Delta as Probability:**
- 20 delta = ~20% chance of expiring ITM
- 30 delta = ~30% chance of expiring ITM
- 50 delta = ~50% chance of expiring ITM

**Ravish's Target:** 20-30 delta for entries

**Formula:**
```
Call Delta = N(d1)
Put Delta = N(d1) - 1

Where:
d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
```

---

### 2. Gamma (Γ) — Delta Acceleration

**What it measures:** How much delta changes for a $1 move in the underlying.

| Gamma Level | Implication |
|-------------|-------------|
| High | Delta changes rapidly (risky near expiry) |
| Low | Delta changes slowly (stable) |
| ATM + Near Expiry | Highest gamma |

**Why It Matters:**
- High gamma = unstable position
- Risk increases near expiration
- Gamma risk is why we exit before expiry

**Formula:**
```
Gamma = φ(d1) / (S × σ × √T)

Where φ(d1) = standard normal PDF
```

---

### 3. Theta (Θ) — Time Decay

**What it measures:** How much value the option loses per day (time decay).

| Theta Value | Implication |
|-------------|-------------|
| Large negative | Fast decay (good for sellers) |
| Small negative | Slow decay |
| Positive | Earning time decay (sellers) |

**Theta Decay Curve:**
```
Days to Expiry:  30    21    14    7    1
                 |     |     |     |    |
Theta:          -0.02 -0.03 -0.05 -0.10 -0.25
                 Slow decay → → → Fast decay
```

**Key Insight:**
- Short-term options decay faster than long-term
- This differential is our edge
- Theta accelerates as expiry approaches

**Ravish's Edge:** Earn theta from short-term, pay less theta for long-term

**Formula:**
```
Call Theta = [-(S × φ(d1) × σ) / (2√T) 
              - rKe^(-rT)N(d2) 
              + qSe^(-qT)N(d1)] / 365

Put Theta = [-(S × φ(d1) × σ) / (2√T) 
             + rKe^(-rT)N(-d2) 
             - qSe^(-qT)N(-d1)] / 365
```

---

### 4. Vega (ν) — Volatility Sensitivity

**What it measures:** How much the option price changes for a 1% change in implied volatility (IV).

| Vega Level | Implication |
|------------|-------------|
| High | Sensitive to IV changes |
| Low | Less sensitive to IV changes |
| Long-dated | Higher vega |
| Short-dated | Lower vega |

**Vega and Strategy:**
| Strategy | Vega Position | IV Impact |
|----------|---------------|-----------|
| Double Calendar | Positive Vega | Benefits from IV rise |
| Double Diagonal | Lower Vega | Less IV sensitivity |
| Short Straddle | Negative Vega | Benefits from IV drop |

**Ravish's Rule:**
- Enter when IV is low (VIX < 20)
- Avoid entering when IV is spiking
- Double diagonal if IV might drop

**Formula:**
```
Vega = S × φ(d1) × √T × e^(-qT)

Per 1% move: Vega / 100
```

---

### 5. Rho (ρ) — Interest Rate Sensitivity

**What it measures:** How much the option price changes for a 1% change in interest rates.

| Option Type | Rho |
|-------------|-----|
| Call | Positive (price rises with rates) |
| Put | Negative (price falls as rates rise) |

**Practical Impact:**
- Usually the least important Greek
- Matters more for LEAPS (long-dated options)
- Less relevant for short-term trades

**Formula:**
```
Call Rho = KTe^(-rT)N(d2) / 100
Put Rho = -KTe^(-rT)N(-d2) / 100
```

---

## Greeks Visualization

### Delta Curve
```
Delta
 1.0 |                          ___________
     |                        /
 0.5 |                      /
     |                    /
 0.0 |__________________/___________________
     |                / 
-0.5 |              /
     |            /
-1.0 |___________/
     Low ← Strike → High
```

### Theta Decay
```
Theta (decay rate)
  -0.25 |                         *
        |                       *
  -0.15 |                     *
        |                   *
  -0.05 |              ***
        |        ****
   0.00 |____***____________________________
        30   21   14    7    1  Days to Expiry
```

---

## Greeks in Practice

### Entry Rules
| Greek | Target | Why |
|-------|--------|-----|
| Delta | 20-30 | 20-30% chance ITM |
| Theta | Positive | Earn time decay |
| Vega | Positive (or low) | Benefit from IV rise |

### Exit Rules
| Condition | Action |
|-----------|--------|
| Delta > 50 | Consider adjustment |
| Theta turning negative | Exit position |
| Gamma spiking (near expiry) | Exit before expiry |

---

## Black-Scholes Implementation

### Python Code

```python
import numpy as np
from scipy.stats import norm

def black_scholes(S, K, T, r, sigma, option_type='call'):
    """
    Calculate Black-Scholes option price
    
    Parameters:
    S: Current stock price
    K: Strike price
    T: Time to expiration (years)
    r: Risk-free interest rate
    sigma: Implied volatility
    option_type: 'call' or 'put'
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price

def calculate_greeks(S, K, T, r, sigma, option_type='call'):
    """Calculate all Greeks"""
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Delta
    delta = norm.cdf(d1) if option_type == 'call' else norm.cdf(d1) - 1
    
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

---

## Common Greeks Mistakes

| Mistake | Solution |
|---------|----------|
| Ignoring theta | Always consider time decay |
| Over-looking vega | Check IV before entering |
| Confusing delta with probability | Delta ≈ probability, not exact |
| Ignoring gamma near expiry | Exit before high gamma risk |
| Not tracking net Greeks | Calculate for entire position |

---

*Last updated: 2026-08-22*
