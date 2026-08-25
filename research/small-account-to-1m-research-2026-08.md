# Small Account → $1M: Research Findings
**Date:** 2026-08-23 | **Compiled for:** Michael Netto | **Status:** Verified against live sources

## 1. Documented small-account success cases (verified)

| Trader | Start → Peak | Timeframe | Market | Verification |
|---|---|---|---|---|
| **Keith Gill (DFV)** | $53k → ~$48M → $585M+ peak | 2019–2024 | GME stock + calls | Wikipedia (fetched): $5/share June 2019 entry; ~$48M Jan 27 2021 (WSJ-confirmed $33M Jan 29); $585M+ June 2024 |
| **Larry Williams** | $10k → $1.1M | 12 months (1987) | S&P futures | Robbins World Cup Championship records (fetched; numbers widely documented) |
| **BNF (Takashi Kotegawa)** | ~$13k → ~$150M+ | ~8 years (2000s) | Japanese equities | Japanese media; no EN Wikipedia (famous ¥1 J-Com error trade 2005) |
| **Dan Zanger** | ~$11k → ~$18M claimed | 1996–2000 | US momentum stocks | Fortune 2000 profile; no EN Wikipedia; chartpattern.com |
| **Karen Bruton** | Grew to $40M+ selling options | 2007–2017 | US options | **SEC fraud charges Sept 2018** (trades around earnings); settled, industry bar. Cautionary tale |
| **Renaissance Medallion** | 71.8%/yr gross (1994–2014), 76% (2020) | decades | quant multi-strategy | Wikipedia (fetched). The ceiling of sustained returns — with infrastructure no retail trader has |

**Pattern:** every case = extreme concentration/leverage + a historic tailwind (dot-com, GME squeeze, J-Com error) + survivorship. Thousands who copied each one are unrecorded.

## 2. Failure base rates (verified)

- **Brazil futures day traders** (Chague, De-Losso, Giovannetti 2020, fetched via Wikipedia): *"97% of all investors who persisted for more than 300 days lost money. Only 17 individuals (1.1% of 1,551) earned more than the Brazilian minimum wage; only eight (0.5%) earned more than a bank teller."*
- **Taiwan** (Barber, Lee, Liu, Odean 2014, J. Financial Markets): <1% of day traders reliably profitable net of fees.
- **Take Profit Trader's own 2025 disclosure** (fetched from their site): only **36.22%** of evaluation Trading Tests passed. Passing ≠ profitable.
- CFD brokers' regulatory disclosures (EU/UK): 74–89% of retail accounts lose money.

## 3. Prop firm economics (fetched from official sites, Aug 2026)

| Firm | Model | Cost | Split | Key rules |
|---|---|---|---|---|
| **Topstep** | Combine → Express Funded → live | monthly sub + activation fee | 100% first $10k/mo, then 90/10 | Consistency rule: best day <50% of profit target; trailing drawdown |
| **Take Profit Trader** | One-step eval | **$130 one-time** | 80% (90/10 on PRO+) | 36.22% pass rate disclosed; PRO+ has EOD drawdown |
| **MFFU** | Builder/Rapid/Pro plans | sub | up to 90/10 | Payouts every 24h (Rapid), ~80% auto-approved; EOD drawdown option |
| **Tradeify** | Growth/Lightning/Instant | one-time ($251–359 seen) | up to 90% | Up to $750k funding tiers |

**Reality:** funded accounts are SIMULATED — payouts come from the firm's operating funds. Firms earn heavily from failed evaluation fees. Futures only; **no legitimate prop firm offers listed stock/index options** (re-verified). Cheapest serious attempt: TPT $130 one-time.

## 4. Strategy-layer evidence for option selling

- **Volatility risk premium** (Wikipedia, fetched): implied vol persistently exceeds realized — the structural edge option sellers harvest. CBOE PUT (PutWrite, est. 2007) and BXM (BuyWrite) indexes document it at index scale.
- **Kelly criterion**: full Kelly for Ravish-profile edge (70% win, 0.6R avg win / 1R loss) ≈ 20%/trade. Quarter-Kelly ≈ 5%/trade is the sane ceiling.
- **Risk of ruin simulation** (`capital_growth_model.py`, 50k trials): risk 10%/trade → 1.2% ruin prob; 25% → 38.5%; 50% → 96.8%.

## 5. Compounding math ($500 → $1M)

| Return | Pure trading | +$200/mo savings |
|---|---|---|
| 2%/mo (27%/yr) | 32 years | 19.3 years |
| 3%/mo (43%/yr) | 21.4 years | **14.0 years** |
| 5%/mo (80%/yr) | 13 years | 9.3 years |
| Buffett 20%/yr | 42 years | — |
| S&P 10%/yr | ~80 years | — |

**Conclusion:** at $500–1,000 capital, contributions and consistency dominate strategy choice. The strategy matters from ~$25k upward. Ravish-style defined-risk calendars (XSP) are a sound strategy layer AND fit a part-time schedule (no screen-watching), but the realistic path to $1M is: prove edge tiny → save aggressively → scale capital → then let 3–5%/mo compounding work. Elite-realistic outcome: ~12–15 years. Anyone selling $500→$1M in 2–3 years is selling survivorship bias.

## Source files
- `~/trader_research/` (gill.txt, robbins2.txt, kotegawa.txt, zanger.txt, Larry_Williams.wiki…)
- `~/prop_research/` (tpt.txt, mffu_*.txt, tradeify.txt, ts_*.txt — Topstep help center)
- `scripts/capital_growth_model.py` — rerunnable math
