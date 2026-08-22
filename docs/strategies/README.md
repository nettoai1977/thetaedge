# Strategies Guide

## Overview

This guide covers the core options selling strategies used in ThetaEdge, inspired by Ravish's systematic approach.

## Strategy Selection Matrix

| Market Condition | Strategy | Entry Criteria |
|------------------|----------|----------------|
| Range-bound, Low IV | Double Calendar | VIX 15-20 |
| Bullish, Low IV | Bull Call Calendar | VIX 15-20, 20-30 delta |
| Bearish, Low IV | Bear Put Calendar | VIX 15-20, 20-30 delta |
| Range-bound, High IV | Double Diagonal | VIX > 20 |

---

## 1. Double Calendar Spread

**The primary strategy — 80% win rate**

### What It Is

Sell near-term options + buy far-term options at the same strikes, collecting theta decay difference as profit.

### Setup

```
Example: SPY at $550

Short Leg (2 weeks out):
- Sell 1x 520 Put
- Sell 1x 580 Call

Long Leg (3 weeks out):
- Buy 1x 520 Put
- Buy 1x 580 Call
```

### Entry Criteria

| Factor | Requirement |
|--------|-------------|
| VIX | 15-20 (low volatility) |
| Market | Range-bound/choppy |
| Ticker | High liquidity (SPX, SPY, QQQ) |
| Strikes | ~10% OTM each side |
| Expiration | Short: 2 weeks, Long: 3 weeks |

### Management

| Rule | Action |
|------|--------|
| Take Profit | 20-40% |
| Stop Loss | 30% (mental only!) |
| Exit Timing | Before short expiration |
| Adjustment | Re-center if price drifts |

### Risk/Reward

- **Max Loss:** ~$346 per contract
- **Max Profit:** ~$249 per contract
- **Breakeven:** Wider range than iron condor

### Why It Works

1. Short-term options decay faster than long-term
2. Positive theta = profit from time passing
3. Positive vega = benefits from IV increase
4. Wide profit zone = high probability

---

## 2. Time Spread (Theta Machine)

**The asymmetric risk/reward play**

### What It Is

Buy a longer-term option, sell a shorter-term option at the same strike. Earn theta daily while waiting for directional move.

### Setup

```
Example: QQQ at $480

Short Leg (1 week out):
- Sell 1x 490 Call

Long Leg (1 month out):
- Buy 1x 490 Call
```

### Entry Criteria

| Factor | Requirement |
|--------|-------------|
| Delta | 20-30 delta |
| Direction | Bullish, Bearish, or Neutral |
| Timeframe | 1-4 weeks |
| IV | Low to moderate |

### Risk/Reward

- **Max Loss:** $162 (net debit)
- **Max Profit:** $618 (300%+)
- **Breakeven:** Near strike price

### Why It Works

1. Short-term theta decays faster
2. Asymmetric risk/reward
3. Can be directional or neutral
4. Low capital requirement

---

## 3. Double Diagonal

**The wide-range play**

### What It Is

Like a double calendar, but with different strikes for puts and calls. Creates a wider profit zone.

### Setup

```
Example: SPY at $550

Short Leg (2 weeks out):
- Sell 1x 510 Put
- Sell 1x 590 Call

Long Leg (3 weeks out):
- Buy 1x 505 Put
- Buy 1x 595 Call
```

### When to Use

- VIX is elevated (>20)
- Expecting IV to decrease
- Want wider profit zone
- Lower Vega risk than double calendar

### Risk/Reward

- **Max Loss:** Limited (net debit)
- **Max Profit:** Near short strikes
- **Breakeven:** Wider than double calendar

---

## Entry Checklist

Before entering any trade:

- [ ] VIX in acceptable range
- [ ] Market is range-bound (not trending)
- [ ] Ticker has high liquidity
- [ ] Strikes are appropriately placed
- [ ] Risk/reward is acceptable
- [ ] No earnings during trade
- [ ] Position size is appropriate

---

## Exit Rules

### Take Profit
- Start scaling out at 20%
- Aggressive scaling at 30-40%
- Hold small runners if desired

### Stop Loss
- **Always mental, never physical**
- Wide bid-ask spreads trigger physical stops prematurely
- Exit manually when 30% loss reached

### Early Exit
- Exit before short expiration
- Avoid gamma risk near expiry
- Re-deploy capital in new trade

---

## Position Sizing

### Rule of Thumb

- **1-5% of account per trade** (conservative)
- **Start with 1 contract** until consistently profitable
- **Scale up gradually** as account grows

### Example with $10,000 account

| Risk Tolerance | Position Size | Max Loss/Trade |
|----------------|---------------|----------------|
| Conservative | 1 contract | $300-500 |
| Moderate | 2 contracts | $600-1000 |
| Aggressive | 3+ contracts | $900-1500 |

---

## Common Mistakes

| Mistake | Solution |
|---------|----------|
| Entering in high IV | Wait for VIX < 20 |
| Using physical stops | Use mental stops only |
| Holding too long | Exit before short expiry |
| Over-sizing | Start with 1 contract |
| Ignoring earnings | Check earnings calendar |
| Chasing returns | Stick to systematic rules |

---

*Last updated: 2026-08-22*
