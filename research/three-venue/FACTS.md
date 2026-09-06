# Venue Fact Sheet — Polymarket / Hyperliquid / Binance Futures
**Verified 2026-09-06 (UTC)** via live API responses + official docs. Sources cited. Method note: fetched through Cloudflare DoH-resolved IPs (this machine's agent sandbox had broken DNS) — re-verify from a normal network before relying on any single fact. Research only; no orders.

## 1) Polymarket — "Bitcoin Up or Down" 5-minute markets

**Fees — VERIFIED** ([docs.polymarket.com/trading/fees](https://docs.polymarket.com/trading/fees) + live gamma API)
- Crypto category taker fee rate **0.07**, maker **0** ("Makers are never charged fees"), maker rebate = 20% of taker fees.
- Fee formula: `fee = C × 0.07 × p × (1−p)` — peaks **1.75% of notional at p=0.50**, →0 at extremes. **As fraction of cost: 0.07×(1−p)** → 1.05% @ 85¢, 0.70% @ 90¢, 0.35% @ 95¢. Not tiered/dynamic.
- Live 5m market `feeSchedule`: `{rate: 0.07, exponent: 1, takerOnly: true, rebateRate: 0.2}`, `feesEnabled: true`. Fees rounded to 5dp, min 0.00001 USDC.
- Separate taker rebate tiers (Bronze $2k/30d vol = 3% back … 7 tiers).
- Fee history (official changelog): Jan 5 2026 fees on 15m crypto → **Feb 12 2026: 5m markets launched WITH fees** → Mar 6 2026 all crypto. **Implication: no pre-fee book history exists anywhere; the paper phase is the only measurement path.**
- Redemption/winning fee: none documented → treat as none. UNVERIFIED (absence).

- CLOB `GET /prices-history`: params are **`market`, `fidelity`, `startTs`, `endTs`** (`start`/`end`/`interval` → HTTP 400). **Carry-forward caveat:** values are last-trade snapshots sampled ~60s — a flat path means *untraded*, not stable; exclude flat paths from any book-quality inference.
- Gamma closed-event pagination for the 5m series caps out at **2,100 events (~7.3 days)** — older windows are not exposed via `/events?series_id=10684&closed=true` (HTTP 422 past that depth). Poly-side offline evidence is therefore bounded to a rolling week; long-horizon claims rest on the Binance kline study.
**Resolution — VERIFIED** (live market description + [changelog](https://docs.polymarket.com/changelog/predictions) + **live RTDS capture 2026-09-06**)
- Oracle: **Chainlink Data Streams BTC/USD**; since **Aug 17 2026** both open "price-to-beat" and settlement use the **60-second Chainlink TWAP** (spot stream before Aug 7; 30s TWAP Aug 7–17).
- Exact rule (verbatim from live market): resolves **"Up" if end TWAP ≥ start price, else "Down"** → **exact tie = UP wins**.
- **RTDS protocol VERIFIED live:** `wss://ws-live-data.polymarket.com`, subscribe `{"action":"subscribe","subscriptions":[{"topic":"crypto_prices_twap_sixty","type":"update","filters":"{\"symbol\":\"btc/usd\"}"}]}` (raw wire topics ≠ SDK names; app-level "PING" every 5s; E18 fixed-point `full_accuracy_value`; push carries payload-observation timestamp). Gap #3/#4 from first pass closed for the TWAP feed.
- **Basis risk vs backtest:** our backtest uses Binance 1m bar open/close as boundary proxies; the oracle is a Chainlink 60s TWAP. Phase 2 logs the TWAP to measure the flip rate directly.

**Cadence — VERIFIED** (live gamma): series `btc-up-or-down-5m`, recurrence `5m`, new market every 5-min window 24/7, created ~24h ahead. Slug `btc-updown-5m-<window-start-unix>`. Tick 0.01, min size 5 shares.

**API — VERIFIED live**: `gamma-api.polymarket.com` (/markets, /public-search) · `clob.polymarket.com/book?token_id=` · WS `wss://ws-subscriptions-clob.polymarket.com/ws/market`. Rate limits: gamma /markets 300/10s, CLOB /book 1,500/10s, general 9,000/10s, /prices-history 1,000/10s. **Backfill note:** /prices-history gives ~7 months (Feb→now) of 1m price paths per resolved market — a large no-wait dataset for Phase 2.

## 2) Hyperliquid — BTC perp
- Fees **VERIFIED**: base taker **0.045%** / maker 0.015%; tiers by 14-day volume. ([fees gitbook](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees))
- Funding **VERIFIED**: **hourly** at 1/8 of 8h rate; `F = avg premium + clamp(0.01% − premium, ±0.05%)`; cap 4%/h; paid on oracle price. Live BTC: 0.0000125/h → **2-min hold expected funding cost ≈ 0.00004% — dead code confirmed numerically** (model accrual only if a leg crosses an hourly boundary).
- API **VERIFIED live**: POST `api.hyperliquid.xyz/info`; WS `wss://api.hyperliquid.xyz/ws`.

## 3) Binance USDT-M — BTCUSDT perp
- Fees **VERIFIED**: VIP0 **maker 0.0200% / taker 0.0500%**; BNB −10% → 0.0180/0.0450. ([fee page](https://www.binance.com/en/fee/futureFee))
- Funding **VERIFIED live**: 8h interval (00/08/16 UTC), cap ±0.30%/interval; recent avg ≈ +0.0022%/8h → negligible for 2-min holds (crosses boundary ~1/240 of holds).
- API **VERIFIED live**: `fapi.binance.com/fapi/v1/premiumIndex`, `/exchangeInfo`; WS `wss://fstream.binance.com`. Limits: 2,400 weight/min; 300 orders/10s.

## Round-trip cost model for the paper ledger (taker, 2-min hold)
| Venue | Cost of a $1 (notional-cost) round trip | Funding for 2-min hold |
|---|---|---|
| Poly binary @ price p | 0.07×(1−p) of cost (1.05% @ 85¢ … 0.35% @ 95¢) | n/a |
| Hyperliquid perp | 0.09% (2 × 4.5bp) | ~0.00004% expected |
| Binance perp | 0.10% (2 × 5bp) | ~0.00001% expected |

## Open gaps (to close during Phase 2)
1. Poly rate-raise 0.0625→0.07 exact date. 2. Explicit "no redemption fee" confirmation. 3. WS-specific rate limits (Poly, HL). 4. TWAP boundary anchoring (does the 60s TWAP end exactly at HH:MM:00?). 5. HL fee-table extra discount columns. 6. BNB-discount fine print for a fresh paper account.
