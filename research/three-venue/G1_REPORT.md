# Gate G1 Review — Signal Calibration & Timing
**Date:** 2026-09-06 · **Script:** `scripts/poly_premise_backtest_v3.py` · **Results:** `results/poly_calibration_v3.json`
**Data:** Binance BTCUSDT 1m bars, 2018-01 → 2026-07, 4,680,079 bars → ~897k valid 5m buckets per offset
**Verdict: G1 = PASS** (drift-identified arm). `SIGNAL_SPEC.md` frozen at v1.0.

## 1. Method (v3 supersedes v2)
Clean semantics: boundary = bar(B).open vs bar(B+240).close (exact alignment enforced); signal price P(60t) known at decision time; σ = rolling-60 1m return std (no lookahead); **FV = Φ(|Δ|/(σ_usd·√(5−t)))**. Fixes vs v2: v2's entry/FV horizon was internally inconsistent (measured effectively 1-min-left follow-through but priced FV at 2 min → inflated FV, understated gap). v3 is the canonical baseline.

## 2. Timing sweep (momentum side, ties = loss)
| Signal at | Time left | n | Win % | Mean FV | Gap (realized − model) |
|---|---|---|---|---|---|
| t=1 | 3 min | 886,343 | 65.47% | 0.648 | **+0.69pp** |
| t=2 | 2 min | 894,731 | 73.19% | 0.713 | **+1.85pp** |
| t=3 | 1 min | 897,252 | 79.96% | 0.773 | **+2.69pp** |
| t=4 | 0 min | 898,412 | 86.94% | 0.841 | **+2.79pp** |

Realized follow-through **exceeds** the Brownian FV model at every timing → persistent momentum drift, monotonic in time pressure. Yearly wr at t=3: 79.3–81.3% every year 2018–2025; 2026 partial 77.4% (gap +0.4pp — drift thinner in 2026; watched, not acted on).

## 3. Calibration curve — t=3 (2 min left), Wilson 95% CIs all tight (n ≥ 15k/bin)
| FV bin | Mean FV | Realized | Gap |
|---|---|---|---|
| 0.50–0.55 | 0.524 | 54.5% | +2.1pp |
| 0.55–0.60 | 0.575 | 61.1% | +3.5pp |
| 0.60–0.70 | 0.650 | 69.8% | +4.8pp |
| 0.70–0.80 | 0.750 | 79.6% | +4.6pp |
| 0.80–0.90 | 0.850 | 88.1% | +3.1pp |
| 0.90–0.95 | 0.925 | 93.4% | +0.8pp |
| 0.95–1.00 | 0.982 | 97.2% | **−1.0pp** |

Model is **underconfident mid-range** (realized beats it by 3–6pp) and **slightly overconfident above 0.95**. Actionable: EV math uses *realized* bin rates, not raw FV; treat FV>0.95 with the realized number.

## 4. The edge map the book must beat (Poly real fees `0.07·p(1−p)`, taker-only)
Breakeven ask (BE) per realized bin; EV per $1 at each ask. **G2 question: does the live book offer asks below BE?**
| FV bin (t=3) | Realized wr | BE ask | EV @85¢ | @88¢ | @90¢ | @92¢ |
|---|---|---|---|---|---|---|
| 0.80–0.90 | 88.1% | **87.4¢** | +2.6¢ | −0.7¢ | −2.8¢ | −4.8¢ |
| 0.90–0.95 | 93.4% | **92.9¢** | +8.8¢ | +5.2¢ | +3.0¢ | +0.9¢ |
| 0.95–1.00 | 97.2% | **97.0¢** | +13.3¢ | +9.6¢ | +7.3¢ | +5.1¢ |

t=4 is uniformly better (~+0.6–1.6pp per bin; BE 0.9836 in the top bin). Fade side: dead unless the trailer asks ≤ ~19.9¢ (BE for 1−wr ≈ 0.20) — monitored only. Perp legs: directional P&L (no binary collapse), measured in the Phase 3 ledger after 9–10bp round-trip cost.

## 5. Standing scoreboard (scoring rubric — every future report graded on these)
| # | Metric | Source | G1 value | Gate |
|---|---|---|---|---|
| 1 | Calibration gap (t=3, FV≥0.80) | backtest | +2.7pp | must stay > 0 on rolling 30d |
| 2 | % signal obs. with ask ≤ BE−1¢ | Phase 2 log | — | ≥ 10% (G2) |
| 3 | Median Poly repricing lag after impulse | Phase 2 log | — | > 1s (G2) |
| 4 | VWAP@$500 vs BE | Phase 2 log | — | ≥ BE−1¢ on ≥5% (G2) |
| 5 | Staleness tax (fill@t+500ms vs @t) | Phase 3 | — | reported; < 50% of gross edge |
| 6 | Oracle flip rate (TWAP vs Binance boundary) | Phase 2 log | 0.00% (n=15, first hours live — accumulating) | < 1% |
| 7 | Ledger EV/$ 95% CI (N≥1,000/venue) | Phase 3 | — | lower bound > 0 (G3) |
| 8 | Realized-vs-predicted wr drift | rolling | 2026: +0.4pp | freeze trades if < −1pp for 14d |

## 6. Honest caveats
1. Backtest boundaries are Binance bar-open/close; the oracle is a **Chainlink 60s TWAP** — flip risk is real and is exactly metric #6. 2. Ties (0.14%) counted as losses everywhere = conservative, and Up-side entries actually win ties under the real rule. 3. Poly 5m books exist only since **Feb 12 2026, with fees from day one** — no pre-fee history exists; the paper phase is the only test of H2. 4. This study contains **zero book data** — nothing here says the edge is capturable; it says the probability model is honest enough to test against the book. 5. 2026 partial-year drift is thinner (+0.4pp) — regime watch.

**Gate decision:** PASS → Phase 2 (book measurement) is justified. SIGNAL_SPEC v1.0 frozen.
