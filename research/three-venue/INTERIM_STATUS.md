# Three-Venue Paper Program — Interim Status
*Generated 2026-09-06 ~13:40 UTC · research-only, zero real orders · gates frozen since collection start*

## Where we are in one paragraph
The 9-year premise (BTC 5m momentum continuation beats the Brownian fair-value model) passed Gate G1 (+2.69pp at t=3, monotonic in time pressure). Phase 2 collection is live in `~/poly-engine/` (4 feeds: Binance reference, Polymarket CLOB books, Polymarket RTDS Chainlink-TWAP oracle, Hyperliquid). Offline evidence from 2,168 resolved Polymarket 5m windows (~7.3 days — the venue's API cap) shows, at the spec's t=3 entry point (T−120s), the market's own trade prices **systematically underprice momentum continuation by 11–20pp in every price bin**, fully repricing by T−60. Realized win rate on the FV≥0.80 gated set: **97.5%** (713/731) — exactly G1's expectation. Whether that discount is capturable at the **executable ask** is the whole question, and the live G2 gates are now measuring precisely that.

## Corrections made along the way (full detail in ROADMAP.md decision log)
1. **Entry point** (round 8): analyzers originally sampled books at T−60 — one minute after the market reprices. Corrected to T−120 per frozen spec. Round-4's "market is efficient" conclusion retracted as a sampling artifact.
2. **Sigma** (round 6): live σ briefly deviated from spec (60s mid proxy → quantization-flat); restored to rolling-60 one-minute returns.
3. **Parser**: three live-protocol fixes (CLOB batch arrays, dict levels, batched price_change top-of-book preservation); per-asset stamping verified.
4. **G2-d semantics**: implemented per pre-registration (TWAP-vs-Binance boundary flips): **0.00% over n=20+**, accumulating.
5. **Venue fact corrections**: prices-history = 60s last-trade snapshots (carry-forward ⇒ offline EV is an UPPER BOUND); gamma exposes only ~7.3 days of closed 5m events.

## The gates (frozen) and current standing
| Gate | Threshold | Standing |
|---|---|---|
| G2-a | ask ≤ BE−1¢ on ≥10% of signals | 0/11 so far (junk 99¢ asks, quiet Sunday); verdict needs n≥100 |
| G2-b | median repricing lag >1s after $40 impulses | 0 impulses yet (quiet session); semantics fixed to momentum-token reprice after impulse completion |
| G2-c | VWAP@$500 ≤ BE−1¢ on ≥5% | accumulating at T−120 |
| G2-d | oracle flip <1% | 0.00% (n=20+) |

Pre-registered decision rule: after ≥1,000 signal observations per venue, proceed only if the 95% CI lower bound on mean EV/$ is > 0 on at least one venue.

## Honest risks
- **Offline EV is an upper bound**: trade-print basis, ≤60s staleness undetectable, no spread/queue cost. The live ask-side numbers will be worse — by exactly the amount that decides GO/NO-GO.
- **Continuity**: collection currently runs under harness-managed jobs. **The 30-second launchd install (README) remains the single most valuable manual step** — without it, a machine/session restart truncates the 2–4 week verdict window.
- Perp legs carry no standalone momentum edge (strike-proximity asymmetry, round 2) — they enter Phase 3 as hedges only.

## Daily loop
`~/poly-engine/daily_cycle.sh` (turnkey: klines → backfill top-up → price paths → offline report → live report) · `weekly_scorecard.py` (Wilson CIs vs gates) · reports in `~/poly-engine/reports/`.
