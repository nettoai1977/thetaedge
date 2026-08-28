# Ravish Put-Selling Strategy — Complete Reference

**Source:** "How I Sell Put Options for Monthly Income (With a 89% Win Rate)" — Options With Ravish  
**Video:** https://youtu.be/kHdZhbQkqxc  
**Documented:** 2026-08-27  
**Verified claims:** $420,000 profit in 1 year, 89% win rate (verified on his platform)

---

## 1. Strategy Overview

### What It Is
Sell cash-secured put options on stocks/ETFs you'd be happy to own. Collect premium upfront. If the stock stays above the strike at expiration, you keep the full premium. If assigned, hold shares and sell covered calls (the "wheel").

### Why It Works (Ravish's Logic)
- You win if the stock goes **up** ✓
- You win if the stock goes **flat** ✓
- You win if the stock goes **down a little** (but stays above strike) ✓
- You only lose if the stock **crashes hard** below your strike minus premium
- You get paid **upfront** when you enter the trade
- No day trading required — minimal screen time

### Key Insight
> "This is kind of like earning a rental income, but when things go against us, we have an option to buy shares, and then we can turn around and sell covered calls against it."

---

## 2. Core Rules & Parameters

| Parameter | Value | Rationale |
|---|---|---|
| **Win rate** | 89% | Verified over $420k in 1 year |
| **Probability of profit** | >70% OTM | Filtered via options chain |
| **DTE (days to expiration)** | 28–60 days | Sweet spot for theta decay vs premium |
| **Minimum return on cash** | ~2%/month | Floor for trade viability |
| **Market cap** | >$1B | Avoids penny stocks, ensures liquidity |
| **Expiration** | Monthly (not weekly) | More time for recovery, fewer gamma events |

---

## 3. Three Ways to Sell Puts

### A. Cash-Secured Puts (Conservative)
- Reserve full cash to buy 100 shares if assigned
- Example: Sell 1 NVDA 200-strike put → need $20,000 cash secured
- Return on capital: ~3.5%/month (if stock stays flat)
- **Safest approach** — you have the cash to cover assignment

### B. Margin-Secured Puts (Moderate)
- Use portfolio margin instead of full cash
- Return on margin: ~20%/month
- Higher returns but **higher risk** — margin calls possible in crashes

### C. Put Spreads (Defined Risk)
- Sell a put at strike A, buy a put at lower strike B
- Example: Sell NVDA 200-strike put, buy 190-strike put
- Max loss = difference between strikes minus premium received
- **Reduces capital requirement significantly**
- Best for smaller accounts or risk-averse traders

---

## 4. Stock Selection Criteria

### Ravish's Screening Process
1. **Stocks/ETFs you'd happily own** — if assigned, you hold and sell covered calls
2. **Long-term uptrend** — look for stocks with established uptrends
3. **Recent pullback** — buy the dip within the uptrend
4. **Market cap >$1B** — ensures liquidity and avoids manipulation
5. **Earnings not imminent** — avoid selling puts right before earnings

### Ideal Setup
- Stock in established uptrend
- Recent pullback of 10-20% from recent highs
- Sitting near a support level
- Implied volatility elevated (higher premiums)

### What to AVOID
- Stocks in downtrends
- Penny stocks or micro-caps
- Stocks with earnings within 2 weeks
- Leveraged ETFs (2x/3x) — "double-edged sword"
- Stocks you wouldn't want to own for 6+ months

---

## 5. Entry Logic

### Step-by-Step Process
1. Identify a stock/ETF you'd own from your watchlist
2. Check the options chain for 28-60 DTE
3. Find a strike with **>70% probability of profit** (OTM)
4. Verify premium is **≥2% of capital** (cash-secured) or acceptable for spread
5. Enter the trade — sell the put (or put spread)

### Example: NVIDIA (from video)
- NVDA trading at $208
- Sell 200-strike put, October 2 expiration (39 DTE)
- Premium received: $677 per contract
- **Downside protection:** 7.3% (stock can drop to $193 and you still profit)
- **If NVDA stays above $200:** Full $677 profit
- **If NVDA drops below $200:** Assigned 100 shares at $200, cost basis reduced to $193.23

### Break-Even Math
```
Break-Even = Strike Price - Premium Received
           = $200 - $6.77 = $193.23

Downside Protection = (Strike - Break-Even) / Spot Price × 100
                    = ($200 - $193.23) / $208 × 100
                    = 3.25%
```

---

## 6. Exit Rules & Management

### Winning Trades (Stock Above Strike at Expiration)
- Option expires worthless → keep full premium
- Or close early at 50-80% of profit for faster capital turnover

### Losing Trades — Rolling Strategy

**When to roll:** When the stock drops below your strike but hasn't hit your break-even yet.

**How to roll:**
1. Buy back the current put (at a loss)
2. Sell a new put at a lower or same strike, further out in time
3. Collect **additional credit** for the roll
4. This **lowers your break-even** and extends the trade

**Ravish's Marvel (MRVL) Example:**
| Step | Action | Premium |
|---|---|---|
| Entry | Sell MRVL 220-strike put, Aug expiry | +$920 |
| Stock drops 42% | Roll to Sep expiry, same/similar strike | +$850 |
| Total credit | $920 + $850 = $1,770 | |
| Exit | Close for $6 debit | -$6 |
| **Net profit** | **$1,170** | Stock still down 14% |

**Without the roll:** Would have made $795 (stock at $218 on original expiry).  
**With the roll:** Made $1,170 (more profit from additional credit).

### Assignment → Wheel Strategy
1. Get assigned 100 shares at strike price
2. Hold shares (you wanted to own them anyway)
3. Sell covered calls against the shares
4. Collect call premium → reduces cost basis further
5. Repeat until shares called away or sold

---

## 7. Greeks & Math Behind the Strategy

### Why Selling Puts Has Edge
- **Theta (time decay):** Works in your favor — option loses value each day
- **Vega:** Selling premium when IV is elevated = collecting more premium
- **Delta:** Selling OTM puts = negative delta exposure (bearish risk), but probability is on your side
- **Gamma:** Lower risk with more DTE (28-60 days)

### Probability vs Premium Trade-Off
```
Higher strike (closer to ATM) → More premium → Lower probability of profit
Lower strike (further OTM)    → Less premium → Higher probability of profit

Sweet spot: 70-80% probability of profit
```

### Return on Capital Calculation
```
Cash-Secured:   Return = Premium / (Strike × 100) × 100
Put Spread:     Return = Premium / Max Loss × 100
Margin:         Return = Premium / Margin Requirement × 100
```

---

## 8. How This Complements Our Calendar Strategy

### Strategy Comparison

| Aspect | Calendar Spreads | Put Selling |
|---|---|---|
| **Direction** | Neutral (range-bound) | Slightly bullish / neutral |
| **Best VIX environment** | Low (15-20) | Elevated (20-30) |
| **Max profit** | Limited (debit spread) | Premium received |
| **Max loss** | Debit paid | Strike - premium (or spread width) |
| **Assignment risk** | Low | High (that's the point) |
| **Capital required** | Low (debit) | High (cash-secured) or low (spreads) |
| **Time decay** | Short leg decays faster | Full premium decays |
| **Win rate** | ~50-60% | ~89% (Ravish's claim) |

### Complementary Timing
- **VIX < 15:** Calendars work best (low IV, range-bound)
- **VIX 15-20:** Both strategies viable
- **VIX 20-25:** Put selling may be better (higher premiums, more cushion)
- **VIX > 25:** AVOID for calendars; put selling only on very strong stocks

### Potential Integration into ThetaBrain
```
Signal Logic Enhancement:
- If VIX < 15 AND IV rank > 50% → Calendar call (current logic)
- If VIX 15-20 AND IV rank > 30% → Calendar call OR put selling
- If VIX 20-25 → Put selling (cash-secured or spread)
- If VIX > 25 → AVOID (too risky for either strategy)
```

---

## 9. Risk Management Rules

### Ravish's Risk Rules
1. **Never sell puts on stocks you don't want to own** — assignment is not a failure
2. **Always have a plan for assignment** — wheel strategy ready
3. **Roll before expiration** — don't let assignment happen if avoidable
4. **Keep position sizes manageable** — don't over-leverage
5. **Diversify across sectors** — don't concentrate in one stock

### Position Sizing
- Ravish uses 1 contract on expensive stocks (NVDA at $200+)
- 10-50 contracts on cheaper stocks (under $50)
- Scale based on capital available and risk tolerance

### When to Cut Losses (Don't Roll)
- Stock fundamental story has changed (fraud, bankruptcy risk)
- Roll would require too much additional capital
- Better opportunity elsewhere (capital is stuck in bad trade)
- Stock has dropped >50% from entry (reassess thesis entirely)

---

## 10. Implementation Notes for ThetaEdge

### Phase 1: Paper Trading (Current)
- ✅ Calendar spreads running on QQQ
- ⏳ Add put-selling as secondary strategy
- ⏳ Track both strategies side-by-side

### Phase 2: Strategy Selection
- Build a "strategy selector" in ThetaBrain
- VIX-based routing: calendars vs puts vs AVOID
- Backtest put-selling on QQQ with same 12-month dataset

### Phase 3: Wheel Integration
- If put gets assigned → auto-switch to covered calls
- Track wheel trades separately in portfolio
- Measure full-cycle returns (put → assignment → call → exit)

### Technical Requirements
- Need options chain data (IV, Greeks, strike probabilities)
- Moomoo OpenAPI can provide this when live
- Backtest engine needs put-selling logic added

---

## 11. Key Takeaways

1. **Selling puts is a business, not a bet** — you're the house, not the gambler
2. **Win rate comes from strike selection** — 70%+ probability of profit
3. **Rolling is your superpower** — turns losers into winners
4. **Assignment is not failure** — it's part of the wheel strategy
5. **Premium is rent** — you're the landlord collecting monthly income
6. **The math works** — theta decay is on your side every single day

---

## Appendix: Glossary

| Term | Definition |
|---|---|
| **Cash-secured put** | Selling a put with enough cash reserved to buy 100 shares |
| **Wheel strategy** | Sell put → get assigned → sell covered call → repeat |
| **Rolling** | Closing current position and opening new one further in time |
| **Break-even** | Strike price minus premium received |
| **Probability of profit** | Option's delta as proxy for probability of expiring OTM |
| **Assignment** | Being obligated to buy 100 shares at the strike price |
| **Premium** | Income received from selling the option |
| **DTE** | Days to expiration |
| **OTM** | Out of the money (stock price above put strike) |
| **IV** | Implied volatility — higher IV = higher premiums |
