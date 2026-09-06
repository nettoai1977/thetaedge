# SIGNAL_SPEC — BTC 5-minute Momentum Premise
**Version 1.0 · FROZEN 2026-09-06 (Gate G1)** · Applies to all three venues. Venue adapters map this spec onto instruments; nothing may drift without a version bump + decision-log entry + re-validation on data NOT used to derive the change.

## 1. Time base & buckets
- UTC. Bucket = aligned 5-min window `[HH:M{0,5}:00, +5:00)`. One bucket = one Poly 5m market (`btc-updown-5m-<window-start-unix>`).
- Decision offsets **t ∈ {2, 3, 4}** minutes into the bucket (time left = 3/2/1 min). Primary: **t=3** (largest measured calibration gap with exit time remaining). t=1 is analysis-only.

## 2. Reference price R(t)
- **Backtest (validated):** Binance BTCUSDT 1m bars — P(0) = bar(B).open; P(60t) = bar(B+60(t−1)).close; P(300) = bar(B+240).close.
- **Live:** same quantities sampled from the Binance perp last-trade stream, snapshotted at the exact offset seconds (t=120/180/240) and at bucket open (t=0). The Chainlink 60s TWAP (`wss://ws-live-data.polymarket.com`, topic `prices.crypto.chainlink.twap`) is logged in parallel as the *oracle* reference for resolution parity — it is NOT the signal input in v1.0.

## 3. Signal
- `Δ_t = P(60t) − P(0)`; `side = sign(Δ_t)` (momentum side). `Δ_t = 0` → no trade.
- `σ_1m` = rolling std of the last 60 one-minute log-returns of R, computed at the decision timestamp (no lookahead). Sane bounds [1e-5, 5e-2]; outside → no trade.

## 4. Fair value (FV)
- `FV_t = Φ( |Δ_t| / (σ_1m × P(60t) × √(5−t)) )` — Brownian bridge over the minutes remaining.
- Validated calibration (4.68M bars, 2018–2026, ~897k buckets/offset): realized ≥ model everywhere meaningful —
  t=2: +1.85pp · t=3: +2.69pp · t=4: +2.79pp; 2024+ windows confirm (+1.26/+2.08/+2.39pp). Bins 0.70–0.95 show the largest drift; ≥0.95 the model is slightly optimistic (−0.3 to −1.0pp) — the book, not the drift, carries entries there.

## 5. Trade filter (frozen)
- Trade only when **FV ≥ 0.80** at a tradable offset. Poly: buy momentum side, hold to resolution (tie rule: **Up wins ties** → Down-side entries book the 0.14% tie rate as a loss). Perp legs: same direction, enter at signal, close at T−5s (or hold to boundary in the hold-to-resolution ledger variant — variant must be recorded per ledger entry).

## 6. Cost model (from FACTS.md, 2026-09-06)
- Poly taker: `0.07 × p × (1−p)` → breakeven ask per bin (t=3, realized): FV .70–.80 → 79.6¢; .80–.90 → 88.1¢; .90–.95 → 93.3¢; .95–1.0 → 97.2¢.
- HL perp round trip 0.09%; Binance 0.10%; funding for 2-min holds ≈ 0 (model only when a hold crosses an hourly/8h boundary).

## 7. Frozen parameters (change = new version)
| Param | Value |
|---|---|
| σ window | 60 × 1m returns |
| Offsets traded | t ∈ {2,3,4}; primary t=3 |
| FV threshold | 0.80 |
| FV form | Φ(|Δ|/(σ_usd·√t_left)) |
| Tie accounting | loss (conservative); oracle reality: Up wins ties |
| Boundaries | bucket open bar-open ↔ bar(B+240).close |
| σ sane bounds | [1e-5, 5e-2] |
