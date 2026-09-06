# Three-Venue Paper Program — Interim Status
*Generated 2026-09-06 ~13:40 UTC · research-only, zero real orders · gates frozen since collection start*

## Where we are in one paragraph
The 9-year premise (BTC 5m momentum continuation beats the Brownian fair-value model) passed Gate G1 (+2.69pp at t=3, monotonic in time pressure). Phase 2 collection is live in `~/poly-engine/` (4 feeds + REST funding/klines polls). Offline evidence from 2,168 resolved Polymarket 5m windows (~7.3 days — the venue's API cap), measured **leak-free at the spec's t=3 entry point (T−120s)**, shows the market's own trade prices are **approximately fair in the tradable bins** (±2pp), with the residual realized-vs-price gap of **+1–2pp in the high bins — exactly G1's measured edge**. Realized win rate on the FV≥0.80 gated set: **90.6%** (557/615), within G1's 88–97% band. Two rounds of measurement corrections were required to reach this sober picture (entry point, then signal leakage — see register below). Whether the small residual gap survives at the **executable ask** (G2-a/c) is the whole question; the live gates are measuring precisely that.

## Corrections made along the way (full detail in ROADMAP.md decision log)
1. **Entry point** (round 8): analyzers originally sampled books at T−60 — one minute after the market reprices. Corrected to T−120 per frozen spec.
2. **Signal leakage** (round 10): the offline signal had used close(w+180) — one minute of *future* information at the T−120 decision moment, inflating the apparent underpricing to 11–20pp. Canonical v3 semantics restored (P(180) = close of bar ending at w+180; sigma excludes the open signal bar). The sober leak-free picture: market ≈ fair at T−120, residual +1–2pp high-bin gap = G1's edge.
3. **Live sigma source** (round 10): mid-mark returns ran ~2× tight (tick-quantized); live FV now computed from REST-fetched 1m bar closes, sigma provenance stamped per ledger row.
4. **Sigma spec** (round 6): restored rolling-60 one-minute returns after a 60s-mid proxy flattened on quantization.
5. **Parser**: three live-protocol fixes (CLOB batch arrays, dict levels, batched price_change top-of-book preservation); per-asset stamping verified.
6. **G2-d semantics**: per pre-registration (TWAP-vs-Binance boundary flips): **0.00% over n=23+**, accumulating.
7. **Venue fact corrections**: prices-history = 60s last-trade snapshots (carry-forward ⇒ offline EV is an UPPER BOUND); gamma exposes only ~7.3 days of closed 5m events.

## The gates (frozen) and current standing
| Gate | Threshold | Standing |
|---|---|---|
| G2-a | ask ≤ BE−1¢ on ≥10% of signals | 0/14 so far (junk 99¢ asks); verdict needs n≥100 |
| G2-b | median repricing lag >1s after $40 impulses | median **17ms** (n=7) — heading to FAIL; Poly reprices within the impulse |
| G2-c | VWAP@$500 ≤ BE−1¢ on ≥5% | 0/14 so far |
| G2-d | oracle flip <1% | 0.00% (n=25) — PASS so far |

Diagnostics (not gates): ask never ≤BE−1c at ANY point T−120→close in 34/34 windows (day-1 trajectory study) · paper P&L −$0.10/entry (n=9, junk regime) · **premise monitor FLAGGED: t=3 edge −0.70pp on rolling 30d** (first flag; t=4 robustly +0.9–1.2pp; spec unchanged per protocol).

Mechanical verdict tree frozen 2026-09-06 in `poly-engine/reports/G2_VERDICT_FRAME.md`: verdict requires ≥100 gated observations AND ≥20 impulse events, else NO-VERDICT; kill criterion combines the 30d premise edge with G2-a/c.

## Honest risks
- **Offline EV is an upper bound**: trade-print basis, ≤60s staleness undetectable, no spread/queue cost. The live ask-side numbers will be worse — by exactly the amount that decides GO/NO-GO.
- **Continuity**: collection currently runs under harness-managed jobs. **The 30-second launchd install (README) remains the single most valuable manual step** — without it, a machine/session restart truncates the 2–4 week verdict window.
- Perp legs carry no standalone momentum edge (strike-proximity asymmetry, round 2) — they enter Phase 3 as hedges only.

## Daily loop
`~/poly-engine/daily_cycle.sh` (turnkey: klines → backfill top-up → price paths → offline report → live report) · `weekly_scorecard.py` (Wilson CIs vs gates) · reports in `~/poly-engine/reports/`.
