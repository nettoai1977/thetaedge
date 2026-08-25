#!/usr/bin/env python3
"""
ThetaEdge Capital Growth Model
Mathematical reality-check: growing $500-1000 toward $1M via options strategies.
Covers: compounding timelines, risk of ruin, Kelly sizing, contribution hybrids.
"""

import math

# ---------------------------------------------------------------
# 1. Pure compounding timelines: what CAGR gets you to $1M?
# ---------------------------------------------------------------
def months_to_target(start, target, monthly_return):
    """Months of compounding at fixed monthly return."""
    if start <= 0 or monthly_return <= -1:
        return float('inf')
    n = math.log(target / start) / math.log(1 + monthly_return)
    return n

def fmt_months(m):
    if m == float('inf') or m is None:
        return "never"
    y = int(m // 12); mm = int(round(m % 12))
    if mm == 12:  # rounding overflow fix
        y += 1; mm = 0
    return f"{y}y {mm}m"

START = 500.0
TARGET = 1_000_000.0

print("=" * 74)
print("1. PURE COMPOUNDING: $500 -> $1,000,000 (no new contributions)")
print("=" * 74)
print(f"{'Monthly':>8} | {'CAGR equiv':>10} | {'Time to $1M':>12} | {'Realism check'}")
print("-" * 74)
scenarios = [
    (0.02,  "excellent hedge-fund level"),
    (0.03,  "elite retail / small fund"),
    (0.04,  "top-tier retail (rare, sustainable for some)"),
    (0.05,  "world-class (Medallion-ish net)"),
    (0.075, "legendary sustained (BNF/Zanger territory)"),
    (0.10,  "essentially unsustainable long-run"),
]
for mr, note in scenarios:
    cagr = (1 + mr) ** 12 - 1
    t = months_to_target(START, TARGET, mr)
    print(f"{mr*100:>7.1f}% | {cagr*100:>9.0f}% | {fmt_months(t):>12} | {note}")

print()
def ann_to_monthly(cagr):
    """Convert annual return (e.g. 0.10 = +10%/yr) to equivalent monthly return."""
    return (1 + cagr) ** (1 / 12) - 1

print("Reference points ($500 -> $1M):")
print(f"  S&P 500 long-run:            ~10%/yr  -> {fmt_months(months_to_target(START, TARGET, ann_to_monthly(0.10)))}")
print(f"  Renaissance Medallion (net): ~39%/yr  -> {fmt_months(months_to_target(START, TARGET, ann_to_monthly(0.39)))}")
print(f"  Warren Buffett lifetime:     ~20%/yr  -> {fmt_months(months_to_target(START, TARGET, ann_to_monthly(0.20)))}")

# ---------------------------------------------------------------
# 2. Hybrid: trading returns + monthly income contributions
#    (Michael can add $100-200/mo from Uber surplus)
# ---------------------------------------------------------------
def simulate(start, monthly_contrib, monthly_return, target, max_months=1200):
    v = start; m = 0
    while v < target and m < max_months:
        v = v * (1 + monthly_return) + monthly_contrib
        m += 1
    return (m, v) if v >= target else (None, v)

print()
print("=" * 74)
print("2. HYBRID MODEL: $500 start + monthly savings added (the realistic path)")
print("=" * 74)
for contrib in [100, 200]:
    print(f"\n  Contributing ${contrib}/month from income on top of trading returns:")
    print(f"  {'Return/mo':>9} | {'Time to $1M':>12} | {'Total from pocket':>17}")
    print("  " + "-" * 55)
    for mr in [0.02, 0.03, 0.05]:
        m, _ = simulate(START, contrib, mr, TARGET)
        total_in = START + contrib * m if m else None
        print(f"  {mr*100:>8.0f}% | {fmt_months(m) if m else 'never(<100y)':>12} | "
              f"{'$' + format(int(total_in), ',') if total_in else '-':>17}")

# ---------------------------------------------------------------
# 3. Risk of ruin & position sizing (Kelly)
# ---------------------------------------------------------------
print()
print("=" * 74)
print("3. RISK OF RUIN vs POSITION SIZE")
print("=" * 74)
# Model: each trade risks f of account; win rate p, win/loss sizes b (in R multiples)
# Risk of ruin approximation for repeated betting (Gambler's ruin w/ edge):
def risk_of_ruin(p, win_mult, loss_frac_per_trade, trials=200_000, seed=42):
    import random
    rng = random.Random(seed)
    ruined = 0
    for _ in range(trials // 4):  # fewer sims for speed
        equity = 1.0
        ruined_flag = False
        for step in range(400):
            bet = equity * loss_frac_per_trade
            if rng.random() < p:
                equity += bet * win_mult
            else:
                equity -= bet
            if equity < 0.25:  # effectively ruined (75% drawdown)
                ruined_flag = True
                break
        if ruined_flag:
            ruined += 1
    return ruined / (trials // 4)

print("Assumes Ravish-style profile: 70% win rate, avg win 0.6R, avg loss 1R")
print("(positive expectancy EV = 0.7*0.6 - 0.3*1.0 = +0.12R per trade)")
p, wm = 0.70, 0.6
ev = p * wm - (1 - p) * 1.0
kelly = (p * wm - (1 - p)) / wm   # full Kelly fraction for this payoff structure
print(f"Full Kelly optimal risk fraction ≈ {kelly*100:.0f}% per trade (never used raw)\n")
print(f"{'Risk/trade':>10} | {'P(hitting -75% dd)':>18} | comment")
print("-" * 60)
for frac in [0.05, 0.10, 0.15, 0.25, 0.35, 0.50]:
    ror = risk_of_ruin(p, wm, frac)
    comment = ("sane" if frac <= 0.10 else
               "aggressive" if frac <= 0.20 else
               "gambling" if frac <= 0.30 else "account killer")
    print(f"{frac*100:>9.0f}% | {ror*100:>17.1f}% | {comment}")

# ---------------------------------------------------------------
# 4. The honest comparison table: paths to $1M
# ---------------------------------------------------------------
print()
print("=" * 74)
print("4. PATHS TO $1M FROM WHERE MICHAEL STANDS (honest ranking)")
print("=" * 74)
rows = [
    ("Trading $500 @ 3%/mo compounded", "~24 years", "Requires elite consistency; one bad year resets clock"),
    ("Trade + save $200/mo @ 3%/mo", "~13-14 years", "Compounding does most late work; savings de-risk early"),
    ("Uber surplus invested passively", "$200/mo @ 8%/yr = ~30y to ~$300k", "No path to $1M alone, but zero-skill floor"),
    ("Prop futures route", "$165/mo fees; pass rate <10%", "Buys access to size, not skill; costs compound too"),
    ("Ravish-style at scale ($50k+ acct)", "3-5% monthly plausible", "The real bottleneck is CAPITAL, not strategy"),
]
for a, b, c in rows:
    print(f"  • {a}\n      {b} | {c}")

print()
print("=" * 74)
print("KEY INSIGHT")
print("=" * 74)
print("""At $500-1000 capital, even WORLD-CLASS 40%/yr returns yield $700/yr.
Strategy choice barely matters at this size -- CONTRIBUTIONS and SKILL-BUILDING dominate.
The sequence that works:
  Phase 1 (now): prove edge paper/live-tiny, add income monthly
  Phase 2: grow capital base to $25-50k (savings + modest trading CAGR)
  Phase 3: THEN strategy leverage matters: 3%/mo on $50k = $18k/yr
  Phase 4: $250k+ accounts make 2%/mo = $60k+/yr -- $1M becomes a decade-scale goal,
           not a fantasy.
Anyone promising $500->$1M in 2-3 years is selling survivorship bias.""")
