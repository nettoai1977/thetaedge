# Three-Venue Momentum Engine — Master Roadmap & Lifecycle Plan
**Strategy family:** BTC momentum-into-close · **Venues:** Polymarket (BTC 5m Up/Down binary) + Hyperliquid (BTC perp) + Binance Futures (BTC perp) · **No spot leg.**
**Date:** 2026-09-06 · **Status:** RESEARCH / PLANNING — nothing built, nothing executed
**Mandate:** research-only, paper-only until Michael explicitly approves anything real.

---

## 0. Ground truth — where we are

| Fact | Evidence | Status |
|---|---|---|
| Momentum follow-through is real & durable | `~/nautilus-lab/poly_premise_results.json`: 900,725 buckets, 2018–2026, follow-through 83.0–86.2% every year; at FV≥0.8: IS-2024 97.39% / OOS-2025 97.19% | **Proven (on Binance 1m bars)** |
| The book leaves that edge open after costs | None. Never measured. | **The open question — the whole project** |
| Edge survives 3-venue cost stack | None | Unproven |
| A robot can run it safely | None | Unproven |

Reference implementation (READ-ONLY, we change nothing): `~/poly-5m/` (Novals83 5m-btc skill).
Backtest source: `~/nautilus-lab/poly_premise_backtest_v2.py`. Data: `~/data-lake/btcusdt_1m/`.

**EV reality check (memorize this):** the 70¢-ask / 85%-true dream is +21¢ per $1 and would imply ~50% full-Kelly sizing — markets don't leave that on 2-minute binaries. Realistic best case at T-120s is ask 85–88¢ vs true 90–92% → **+2–5¢ per $1 after costs**. A thin-but-positive result is SUCCESS. Pre-committing to this band now prevents misreading a working engine as a failure.

**Hypotheses, falsifiably stated**
- **H1** (proven): P(same-direction close | Δ$ move by T-120s) ≈ 85% raw, ≈97% at FV≥0.8.
- **H2** (open): conditional on the signal, at least one venue's executable price sits below FV by more than that venue's cost stack, often enough to matter.
- **H3** (open): the same signal monetizes net-positive on ≥1 of Poly / HL / BNF after fees, spread, funding-if-crossed, and latency.
- **H4** (later): capital, ops, and risk limits can carry it.

---

## 1. Phase plan — correct order, every phase gated

### Phase 0 — Venue fact sheet (parallel, cheap, no code)
One page of verified facts per venue. No assumptions survive into the engine.

| Item | Polymarket | Hyperliquid | Binance Futures |
|---|---|---|---|
| Instrument | BTC 5m Up/Down binary (CLOB) | BTC-USD perp | BTCUSDT perp |
| Taker fee | **VERIFY — fees exist on short-term crypto series; backtest's 1% buffer is an assumption** | VERIFY (~4.5bp?) | VERIFY (VIP0 ~5bp) |
| Funding cycle | n/a (binary, no funding) | hourly? VERIFY | 8h |
| Resolution oracle + tie rule | **VERIFY per market spec (Chainlink data streams on current 5m series?)** | n/a | n/a |
| WS book feed + rate limits | CLOB WS, public, no auth | public WS | public WS |
| Testnet / paper venue | none → paper sim only | testnet exists | testnet exists |
| Access from NZ | OK (US blocked) | OK | OK |

**Deliverable:** `FACTS.md` with sources. Gate: none, but H2 math is meaningless until fees are real numbers.

### Phase 1 — Signal & calibration study (existing data only, no new infra) → **Gate G1**
Extend `poly_premise_backtest_v2.py`. No venue code.
1. **Calibration curve**: realized win rate vs FV bucket (0.60–0.65, …, 0.95–1.00). If realized > model → genuine momentum drift beyond Brownian (alpha even vs competent MMs). If realized < model → model overconfident, and NO book gap matters. **This is the single most informative plot in the project.**
2. **Signal timing**: source Binance aggTrades/tick data; test tick-level trigger vs 1m-bar-close trigger. MMs see ticks; if the book reprices before our 1m-based signal fires, the strategy as designed is structurally late — better to know now.
3. **Both sides**: momentum side (buy the mover) AND fade side (FV says 15%, book still overprices the trailing side). Fade may be the retail-friendly edge (MM inventory skew, fewer bots).
4. Regime robustness: FV normalization only — dollar thresholds ($70–100) are regime-fragile (avg |Δ| ran $7.7 in 2019 → $68.7 in 2025).
5. Tie-rule sensitivity: backtest excluded ties — quantify how much that flatters the win rate.
6. Write **`SIGNAL_SPEC.md`** — the canonical, venue-agnostic signal definition (inputs, timestamps, FV formula, thresholds). Single source of truth; backtest, loggers, paper engine, and robot all consume it. No drift allowed.

**Gate G1 (pass = continue):** calibration slope within [0.95, 1.10] (or drift direction identified and exploitable); a chosen signal timing; both-side EV surfaces computed; SIGNAL_SPEC frozen. **Status: PASSED 2026-09-06 — see G1_REPORT.md.**

### Phase 2 — Microstructure data collection → **Gate G2 — the go/no-go**
**First and only build before validation:** passive loggers, public endpoints, no auth, no orders.
- Poly: L2 book (top 10 levels) on near-expiry 5m markets, WS event timestamps, plus resolution outcomes & oracle boundary prices.
- HL + BNF: book/quote ticks, trade prints, funding rate history.
- Run 2–4 weeks. Everything append-only (jsonl/parquet) — the log IS the dataset.

**Analysis produced from the log:**
- Joint distribution **P(ask, bid, depth, VWAP@$100/$500/$1k | FV)** — this alone answers the 70¢ question.
- **Repricing lag**: cross-correlate Binance trade ticks vs each venue's book reaction. The lag IS the edge's half-life; if median lag < our reaction time, stop here.
- Oracle-basis: resolution feed vs Binance close at the boundary — flip rate on would-be wins.

**Gate G2 (pre-registered, thresholds now settable from G1 + FACTS):** for FV≥0.80 signal observations on the live book:
- **G2-a:** executable ask ≤ BE_poly(realized bin wr) − 1¢ on **≥ 10%** of signal observations;
- **G2-b:** median Poly repricing lag after an impulse > **1 second**;
- **G2-c:** VWAP@$500 fill still ≥ BE − 1¢ on **≥ 5%** of observations;
- **G2-d:** oracle flip rate (Chainlink TWAP vs Binance boundary) < **1%**.
Kill criteria: all four fail → archive H2 with the report, keep the rig for the next hypothesis. No "one more week."
**Backfill accelerant:** Poly `/prices-history` provides ~7 months (Feb 12 2026 → now) of 1m price paths per resolved market — measure the FV-vs-book-price joint distribution at 1m resolution *before* the live loggers finish their first week.

### Phase 3 — Three-venue paper engine (gated on G2) → **Gate G3**
Same SIGNAL_SPEC, three fill simulators, one ledger.
- **Fill honesty rules:** decision at signal time t → fill at the book as of **t+500ms** (log t, t+500ms, t+1500ms fills; the difference is the measured staleness tax). Depth-aware VWAP for fixed notionals. Never fill against the snapshot seen at decision time.
- **Ledger:** per-venue fee schedules from FACTS.md; funding accrued **only if a hold crosses a funding timestamp** (2-minute holds cross one ~1/240 of the time — log funding rates, don't model accrual for sub-minute legs; that's dead code); oracle-basis adjustments.
- **Accounting variants:** hold-to-resolution (clean EV measurement) vs exit-before-close (the skill's variant, extra spread cost) — tracked separately.
- **Risk accounting:** the three venues run the SAME signal → **one correlated bet executed three times, not three bets**. Size on the combo; net-direction cap across venues.
- **Pre-registered decision rule:** after N≥1,000 signal observations per venue: mean EV/$ with 95% CI; proceed only if CI lower bound > 0 on ≥1 venue. Snapshot-fill vs delayed-fill EV gap reported side by side.

**Gate G3 pass = the robot gets designed.** Fail = archive with honest funnel entry (matches `~/nautilus-lab/PAPER_TRADING_PLAN.md` culture: every attempt recorded, failures included).

### Phase 4 — Dry-run & probe execution (gated on G3 + Michael's explicit approval)
- Binance testnet + HL testnet end-to-end harness; Poly stays simulated (no testnet).
- Optional micro-size live probes ONLY with written approval + hard caps (per-trade, daily loss, max notional, kill switch, quote-staleness guard — reuse the poly-5m checklist patterns).
- Standing default: paper.

### Phase 5 — Robot system design & build (gated on G3)
Only now architect the real system: execution adapters per venue, unified risk manager (combo-level sizing, daily loss, kill switch), monitoring/alerting into the existing ThetaEdge 10am cron + Telegram summary, ops runbook, capital allocation, failure modes (WS disconnect, oracle dispute, exchange maintenance windows, funding spikes). New repo, our own — `poly-5m` stays read-only.

---

## 2. What we deliberately do NOT build (yet)
Queue-position modeling · spot leg · funding accrual for sub-minute holds · market-making · cross-venue arb logic (Poly↔perp basis trading) · anything requiring API keys before G3. Each is a scoped follow-up if its gate passes.

## 3. Calendar (working estimate)
| When | Work |
|---|---|
| Week 1 | Phase 0 fact sheet + Phase 1 analysis (existing data) → G1 review |
| Weeks 2–5 | Phase 2 loggers live + collection → G2 review (THE decision) |
| Weeks 6–10 | Phase 3 paper engine, N≥1,000 signals accumulated → G3 review |
| Weeks 11+ | Only if G3 passed: Phase 4/5 |

## 4. Decision log (append-only)
- **2026-09-06** — Backtest v2 premise check: GO (conditional). Verdict: the market tendency is real and durable (9y); the unproven part is whether Polymarket's CLOB leaves the 70¢-vs-85% gap open — that is exactly what the paper engine with live books must measure. Scope set: **3 venues (Polymarket, Hyperliquid, Binance Futures), same strategy, no spot.** Funding rates scoped: model accrual only when a leg holds across a funding timestamp. poly-5m repo stays read-only. Nothing built; roadmap only.
- **2026-09-06 — G1 = PASS** (`G1_REPORT.md`). v3 calibration study (~897k buckets/offset, 2018–2026): momentum drift is real — realized beats the Brownian FV model at every timing (t=3: +2.69pp; monotonic in time pressure; 2024+ confirmed). Calibration curve: underconfident 0.60–0.95, slightly overconfident ≥0.95. Poly fee schedule verified (`0.07·p(1−p)` taker-only) → per-bin breakeven asks computed (top bin: 97.0¢ at t=3). Tie rule verified: **Up wins exact ties**. 5m markets launched Feb 12 2026 with fees from day one → no pre-fee book history exists; paper phase is the only test of H2. Funding for 2-min holds confirmed numerically negligible (HL ~4e-5%, BNF ~1e-5%). SIGNAL_SPEC frozen v1.0. Next: Phase 2 loggers (gated on Michael's OK for the build + cron install).
- **2026-09-06 — Phase 2 BUILD APPROVED & DEPLOYED** (`~/poly-engine/`). Four collectors live (Binance fstream, Poly CLOB books, Poly RTDS oracle probe, Hyperliquid), supervisor + heartbeats + daily rotation, DoH DNS fallback for the agent sandbox. Parser fixtures ALL PASS after three live-protocol fixes (CLOB batches first message as a JSON array; WS book levels are dicts not pairs; RTDS rejects SDK topics + sends empty keepalive frames). **RTDS protocol VERIFIED via live production capture** (wire topics `crypto_prices_twap_sixty` etc., 5s PING, E18 values). Backfill rewritten around gamma `series_id=10684&closed=true` (slug endpoint hides resolved markets). **Blocked-from-sandbox note:** `launchctl`/`crontab` are not installable from the agent sandbox → permanent continuity needs Michael to run the 2-command launchd install in `~/poly-engine/README.md`.
- **2026-09-06 (goal round 2) — First offline G2 evidence (30d backfill → actually ~7.3d: gamma paginates out at 2,100 closed events; series exposes only ~7 days → Poly-side offline evidence is bounded to a rolling week).** N=676 BTC-signal windows, 246 with real market prices (flat/untraded paths excluded — prices-history carries last trade forward at ~60s, so flat paths are fiction; e.g. the 09-02 03:15 window: both tokens pinned 0.505/0.495 for 8 min with zero trades). Findings: **(1) Offline G2-a analog: 17.2% of gated windows EV>0 at the market's own T-60 last-trade price (5/29, mean EV +$0.012/$)** — above the 10% gate but n small and last-trade ≠ executable ask; live ask-based G2 remains decisive. (2) **G1 transfer: gated realized wr 25/29 = 86.2%** (G1 expects 88–97%) — direction edge confirms on fee-era Poly windows. (3) Calibration at T-60: high bins fair-to-conservative (0.80–0.90: 33/33; 0.95+: 58/59), mid 0.70–0.80 overpriced (60% vs 75% fair, n=25). (4) **Perp legs (HL/BNF, t=3, net 9–10bp): gross mean +0.002% ≈ ZERO even gated → the momentum edge does NOT transfer to a 2-min perp hold.** Explanation: the binary edge is strike-proximity asymmetry (fixed strike = window open; already-accumulated Δ vs remaining time), not forward drift — a perp entered at t=3 is a fresh random walk with no strike. Consequence: the 3-venue "same strategy" design is reframed — perp leg = hedge/delta-management role or needs its own intrabar signal; Poly binary remains the only leg with a measured edge. (5) Feasibility confirmed: hist_full fetcher (`startTs`/`endTs` — old `start`/`end` params 400'd, all main-run histories lost and now re-fetched properly). Next rounds: finish hist_full, event-cluster dedupe, live G2 accumulation continues.
- **2026-09-06 (goal round 1) — Standing loop initialized.** Analyzer v1 deployed (`~/poly-engine/analyze.py`): joins Poly books × Binance reference × backfill outcomes, scores against frozen G2 gates, writes `reports/g2_<date>.md`. First warm-up observation (N=1): post-impulse ask 99¢ vs BE 96.99¢ → gate rejected (edge −3¢) — gate logic verified live. **Measurement note:** from the DSH sandbox IP, Binance fstream pushes only bookTicker at full rate (aggTrade/markPrice silent) → v1 uses top-of-book mid as price reference; re-check aggTrade under launchd runtime and prefer trades there. Momentum side now resolves the correct token via market_meta outcomes mapping. Canonical clean data series starts 11:26:20Z 2026-09-06; G2 verdict on schedule at 2–4 weeks of accumulation.
- **2026-09-06 (goal rounds 3-4) — Offline evidence completed on full price paths (1,535 histories, 612 priced windows; staleness caveat: prices-history samples ~60s so ≤60s carry-forward is undetectable — market-price EV is an upper bound; live book data remains authoritative).** Findings: **(1) The market's own T-60 last-trade prices are near-perfectly calibrated** — every bin within ~1–2pp of fair (0.80–0.90 → 86.6% vs 85%; 0.90–0.95 → 91.7% vs 92.5%; 0.95+ → 98.8% vs 97.5%; N=477). The earlier "underpricing" hint (N=78) was small-sample noise. **(2) G2-a offline analog: 23.4% of gated windows EV>0 (18/77, gate ≥10%) BUT median EV −$0.076 vs mean +$0.885** — outlier-driven; the typical gated window is NOT attractive at its own last-trade price; the opportunity concentrates in cheap-ask windows (0.71–0.79 rows). Momentum-side wr 65/77 = 84.4% vs G1 88–97% expectation (n small; tie-rule + bin mix plausibly explain ~3pp). **(3) Event clusters: 70 events / 77 gated windows (1.1/event) — signals are singletons, no cluster double-counting.** (4) Live pipeline: batched price_change rows now carry per-asset ids (76% of Poly data was previously unstamped); G2-d implemented per pre-registration (TWAP-vs-Binance basis flips): 0.00% at n=12, growing. Live G2 accumulation continues; next: daily reports, G2-b during NY volatility, weekly scorecard.
- **2026-09-06 (goal round 8) — COURSE CORRECTION: entry-point implementation error found and fixed; the central question re-opens.** New timing analysis (`reports/timing_efficiency.md`, N=1,985 priced windows): at **T−120 (the spec's t=3 entry), Poly's own last-trade prices systematically underprice momentum by 11–20pp in EVERY bin** (0.70–0.80 → 90.0% realized vs 75% fair; 0.80–0.90 → 96.3% vs 85%), while at **T−60 calibration is near-perfect** (±1–2pp) — the market fully reprices in the final minute. Analyzer v0 sampled books at w+240 (T−60) — measuring the edge one minute AFTER it disappears; the round-4 'market near-perfectly calibrated' conclusion was an artifact of that wrong sample point and is hereby CORRECTED. Fixed: both analyzers now observe at w+180 per the frozen spec's primary offset (delta, sigma, book, BE−1c all at t=3); old ledger archived as `g2_ledger_v0_t60.jsonl` (not comparable — mixed semantics). Offline at the correct entry: **731 gated windows, EV>0 share 60.6%, median EV +$0.025, realized gated wr 97.5%** (713/731, matches G1 88–97%). Caveats unchanged: last-trade basis = UPPER BOUND; ≤60s staleness undetectable; the live ASK-based G2-a/c at T−120 is now the decisive measurement (live n=11 gated so far, all asks 99¢ junk — 0/11 below BE, as expected in quiet hours). Also fixed: G2-b semantics (impulse completion → first momentum-token book change, not any-update cadence), and the batched price_change parser now preserves per-asset top-of-book state (price/best_bid/best_ask were being dropped — 23k/h stamped rows verified). Perp-leg conclusion unaffected (entries were already at t=3).

---

*Every number in the funnel is honest because every attempt — including failures — is recorded. That's the whole point.*
