#!/usr/bin/env python3
"""
NZ$500 -> monthly growth projection under Ravish-style defined-risk calendars.
Monte Carlo with REAL micro-account frictions:
  - FX: NZ$500 ~= US$295 @ 0.59
  - Instrument: single XSP calendar (~US$44 debit = 15% of start equity)
  - Moomoo fees: US$0.50/contract x 2 legs x (open+close) = US$2.00/cycle
  - Trade cadence: 2 cycles/month (calendars hold 2-4 weeks)
Outcomes modelled per trade: WIN = +25% of debit (take-profit zone), LOSS = -30% (mental stop).
"""
import random

START_NZD = 500.0
FX = 0.59
start_usd = START_NZD * FX          # ~295
DEBIT_PCT = 0.15                    # calendar debit as fraction of equity
WIN, LOSS = 0.25, -0.30             # P/L as % of debit
FEES = 2.00                         # USD per round-trip cycle
TRADES_PER_MONTH = 2
MONTHS = 24
SIMS = 20_000


def run_months(win_rate, monthly_contrib_nzd=0.0):
    finals, paths = [], []
    for _ in range(SIMS):
        eq = start_usd
        rng = random.Random()
        path = []
        for m in range(MONTHS):
            for _t in range(TRADES_PER_MONTH):
                debit = max(eq * DEBIT_PCT, 20.0)   # XSP min viable ~US$20 debit floor
                pl = debit * (WIN if rng.random() < win_rate else LOSS) - FEES
                eq += pl
                eq = max(eq, 50.0)                  # below this, strategy not executable -> floor
            eq += monthly_contrib_nzd * FX
            path.append(eq)
        finals.append(eq)
        paths.append(path)
    paths.sort()
    finals.sort()

    def pct(p, q):
        return p[int(len(p) * q)]

    print(f"\n=== Win rate {win_rate*100:.0f}% | contrib NZ${monthly_contrib_nzd:.0f}/mo ===")
    print(f"{'Month':>5} | {'p10':>9} | {'median':>9} | {'p90':>9}   (NZ$)")
    for m in [3, 6, 12, 18, 24]:
        row = sorted(p[m - 1] / FX for p in paths)
        lo, mid, hi = pct(row, .10), pct(row, .50), pct(row, .90)
        print(f"{m:>5} | {lo:>9,.0f} | {mid:>9,.0f} | {hi:>9,.0f}")
    med_month1 = (paths[0][0] / FX) if False else None
    # median monthly growth rate over 24m
    med_final = pct(sorted(f / FX for f in finals), .50)
    cagr_m = (med_final / START_NZD) ** (1 / MONTHS) - 1
    print(f"Median implied monthly growth: {cagr_m*100:+.1f}%/mo "
          f"(~US${(med_final-start)*0:.0f}" if False else
          f"Median implied monthly growth: {cagr_m*100:+.1f}%/mo")
    return finals


print(f"Start: NZ${START_NZD:.0f} = US${start_usd:.0f} | XSP calendar ~US$44 debit | "
      f"fees US$2/cycle | {TRADES_PER_MONTH} trades/mo")

print("\n--- SCENARIO A: beginner edge (55% win) ---")
run_months(0.55, 0)
print("\n--- SCENARIO B: proven Ravish-style edge (70% win) ---")
run_months(0.70, 0)
print("\n--- SCENARIO C: proven edge + NZ$150/mo contributions ---")
run_months(0.70, 150)

# Fee-drag illustration
print("\n=== WHY SIZE MATTERS: same edge, different account size (70% win, per month) ===")
for acct_usd in [295, 1000, 5000, 25000]:
    debit = acct_usd * DEBIT_PCT
    ev_gross = TRADES_PER_MONTH * (0.70 * WIN - 0.30 * abs(LOSS)) * debit
    fees = TRADES_PER_MONTH * FEES
    net = ev_gross - fees
    print(f"US${acct_usd:>6,} account: gross EV +US${ev_gross:>6.2f}/mo - fees US${fees:.2f} "
          f"= net +US${net:>7.2f}/mo ({net/acct_usd*100:+.1f}%/mo)")
