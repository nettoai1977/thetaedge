"""v3: calibration study for the BTC 5m momentum premise.

Clean semantics (fixes v2's muddled entry timing):
  bucket = aligned 5-min interval [B, B+300)
  P(t)  = price at minute-offset t:
          bar with open_time == B      -> open = P(0), close = P(60)
          bar with open_time == B+60k  -> close = P(60*(k+1))
  open reference  = bar(B).open            (approximates the oracle boundary open)
  final reference = bar(B+240).close       (approximates the oracle boundary close)
  signal at offset t in {1,2,3,4} minutes:
      delta_t = P(60t) - P(0)
      side    = sign(delta_t)            (momentum side; delta==0 -> no trade)
      FV_t    = Phi(|delta_t| / (sigma_1m@t * P(60t) * sqrt(4 - t)))   [t_left minutes]
      win     = P(300) > P(0) if side=up else P(300) < P(0)  (ties tracked separately)
  sigma_1m = rolling 60-bar std of 1m log returns, ending at the signal bar
             (known at decision time -> no lookahead)
  Exact-alignment validity: bar(B), bar(B+60), ..., bar(B+240) must all exist
  exactly (no stale-price buckets).

Outputs: calibration curve (FV bins vs realized win rate + Wilson CI),
momentum & fade EV surfaces over ask grids x fee levels, timing sweep (t=1..4),
tie-rate bounds, per-year and recent-window (2024+) stability.
"""
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

PQ = "/Users/michaelnetto/data-lake/btcusdt_1m/btcusdt_1m_combined.parquet"
OUT = Path.home() / "thetaedge/research/three-venue/results/poly_calibration_v3.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

BUCKET = 300
SIG_WIN = 60
SIG_LO, SIG_HI = 1e-5, 0.05   # sane 1m sigma bounds (return space)
FEE_LEVELS = [0.0, 0.02]
ASK_GRID = [0.70, 0.75, 0.80, 0.85, 0.88, 0.90, 0.92]
FV_BINS = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.70), (0.70, 0.80),
           (0.80, 0.90), (0.90, 0.95), (0.95, 1.001)]
Z = 1.959963985  # 95%


def norm_cdf(x):
    # Abramowitz-Stegun 7.1.26, vectorized (max abs err 1.5e-7)
    x = np.asarray(x, dtype=np.float64)
    sign = np.sign(x)
    ax = np.abs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * ax)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    erf = 1.0 - poly * np.exp(-ax * ax)
    return 0.5 * (1.0 + sign * erf)


def wilson(p, n):
    if n == 0:
        return (float("nan"), float("nan"))
    den = 1 + Z * Z / n
    ctr = (p + Z * Z / (2 * n)) / den
    hw = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return (ctr - hw, ctr + hw)


def main():
    t0 = time.time()
    table = pq.read_table(PQ, columns=["open_time", "open", "close"])
    ts_all = np.array(table["open_time"], dtype=np.int64) // 1000
    open_all = np.array(table["open"], dtype=np.float64)
    close_all = np.array(table["close"], dtype=np.float64)
    del table

    # dedupe: keep first occurrence per open_time (matches v2 baseline)
    _, uniq_idx = np.unique(ts_all, return_index=True)
    order = np.sort(uniq_idx)
    ts, op, cl = ts_all[order], open_all[order], close_all[order]
    print(f"deduped {len(ts_all):,} -> {len(ts):,} bars ({time.time()-t0:.0f}s)")

    # rolling 60-bar sigma of 1m log-returns (on close prices)
    rets = np.full(len(cl), np.nan)
    rets[1:] = np.log(cl[1:] / cl[:-1])
    nz = ~np.isnan(rets)
    r = np.where(nz, rets, 0.0)
    c1 = np.cumsum(r)
    c2 = np.cumsum(r * r)
    n = np.arange(len(r))
    w0 = np.maximum(0, n - SIG_WIN + 1)
    cnt = (n - w0 + 1).astype(float)
    mean = (c1 - np.concatenate([[0.0], c1])[w0]) / cnt
    sq = (c2 - np.concatenate([[0.0], c2])[w0]) / cnt
    sigma_1m = np.sqrt(np.maximum(0.0, sq - mean ** 2))
    sigma_1m[:SIG_WIN + 1] = np.nan
    sigma_1m[(sigma_1m < SIG_LO) | (sigma_1m > SIG_HI)] = np.nan

    year_of = np.array([(t // 31536000) for t in ts])  # rough; exact below
    ystarts = {y: int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp()) for y in range(2017, 2028)}
    yend = {y: ystarts.get(y + 1, int(datetime(2027, 1, 1, tzinfo=timezone.utc).timestamp())) for y in ystarts}
    year_of = np.full(len(ts), -1, dtype=np.int64)
    for y in range(2018, 2027):
        year_of[(ts >= ystarts[y]) & (ts < yend[y])] = y

    results = {"method": "v3 clean semantics: bar-open boundary ref, exact-alignment, FV=Phi(|d|/(sig_usd*sqrt(t_left))), rolling-60 sigma",
               "signal_offsets_min": {}, "calibration": {}, "ev_surfaces": {}, "ties": {}, "yearly": {}}

    # one pass per signal offset t (minutes into bucket)
    for t in (1, 2, 3, 4):
        buckets = np.arange(0, ts[-1] + BUCKET, BUCKET, dtype=np.int64)
        # exact alignment: bar(B) open_time == B ; bar(B+60k) ; bar(B+240)
        pB = np.searchsorted(ts, buckets, side="left")
        pB = np.clip(pB, 0, len(ts) - 1)
        okB = ts[pB] == buckets
        sig_bar = buckets + 60 * (t - 1)          # bar whose close = P(60t)
        pS = np.searchsorted(ts, sig_bar, side="left")
        pS = np.clip(pS, 0, len(ts) - 1)
        okS = ts[pS] == sig_bar
        fin_bar = buckets + 240                    # bar whose close = P(300)
        pF = np.searchsorted(ts, fin_bar, side="left")
        pF = np.clip(pF, 0, len(ts) - 1)
        okF = ts[pF] == fin_bar
        # sigma must be known at the signal bar (bar t-1..t window); require sigma at sig bar
        okSig = np.isfinite(sigma_1m[pS])
        valid = okB & okS & okF & okSig & (pS >= pB) & (pF > pS)
        # restrict to 2018+ and full-year coverage
        valid &= (ts[pB] >= ystarts[2018]) & (ts[pF] < yend[2026])

        P0 = op[pB]
        Pt = cl[pS]
        Pf = cl[pF]
        sig_usd = sigma_1m[pS] * Pt
        delta = Pt - P0
        side_up = delta > 0
        tradable = valid & (delta != 0)
        t_left = (5 - t)  # minutes of path left after observing P(60t): P(60t)->P(300)
        with np.errstate(divide="ignore", invalid="ignore"):
            fv = np.where((sig_usd > 0) & tradable,
                          norm_cdf(np.abs(delta) / (sig_usd * math.sqrt(t_left))), np.nan)

        strict_win = np.where(side_up, Pf > P0, Pf < P0)      # ties = loss
        tie = (Pf == P0) & tradable
        up_win_strict = (Pf > P0) & tradable                   # P(up wins | tradable)
        up_any = (Pf >= P0) & tradable                         # up wins ties
        down_any = (Pf <= P0) & tradable                       # down wins ties

        m = tradable & np.isfinite(fv)
        nT = int(m.sum())
        if nT == 0:
            continue
        wr = float(strict_win[m].mean())
        mv = fv[m]
        ties = tie[m]

        results["signal_offsets_min"][f"t{t}"] = {
            "n": nT,
            "momentum_win_pct_tie_lose": round(wr * 100, 3),
            "momentum_win_pct_tie_excl": round(float(strict_win[m & ~tie].mean()) * 100, 3) if (m & ~tie).sum() else None,
            "tie_pct": round(float(ties.mean()) * 100, 3),
            "up_win_pct_if_bought_up_tie_win": round(float(up_any[m].mean()) * 100, 3),
            "down_win_pct_if_bought_down_tie_win": round(float(down_any[m & ~side_up].mean()) * 100, 3) if (m & ~side_up).sum() else None,
            "mean_fv": round(float(np.nanmean(mv)), 4),
            "calibration_gap_pp": round((wr - float(np.nanmean(mv))) * 100, 3),
            "avg_abs_delta_usd": round(float(np.abs(delta[m]).mean()), 1),
        }

        # calibration curve (momentum side)
        cal_rows = []
        for lo, hi in FV_BINS:
            bm = m & (fv >= lo) & (fv < hi)
            nb = int(bm.sum())
            if nb < 50:
                cal_rows.append({"bin": f"{lo:.2f}-{hi:.2f}", "n": nb})
                continue
            wrb = float(strict_win[bm].mean())
            lo95, hi95 = wilson(wrb, nb)
            # breakeven ask under real Poly taker fee (fee=rate*p*(1-p), taker-only):
            # wr/a - 1 - 0.07*(1-a) = 0  ->  0.07a^2 - 1.07a + wr = 0
            disc = 1.07 * 1.07 - 4 * 0.07 * wrb
            be_poly = (1.07 - math.sqrt(max(disc, 0.0))) / 0.14
            cal_rows.append({"bin": f"{lo:.2f}-{hi:.2f}", "n": nb,
                             "mean_fv": round(float(fv[bm].mean()), 4),
                             "realized_wr": round(wrb, 4),
                             "gap_pp": round((wrb - float(fv[bm].mean())) * 100, 2),
                             "wr95": [round(lo95, 4), round(hi95, 4)],
                             "be_ask_poly": round(be_poly, 4),
                             "ev_poly": {f"ask{a}": round(wrb / a - 1 - 0.07 * (1 - a), 4)
                                         for a in (0.85, 0.88, 0.90, 0.92, 0.95)}})
        results["calibration"][f"t{t}"] = cal_rows

        # EV surfaces: momentum side (buy leader at ask) and fade side (buy trailer at ask')
        # realized prob for bought side: momentum wr (ties=loss); fade: 1-wr (ties=loss)
        ev = {}
        for tag, p_win in (("momentum", wr), ("fade", 1.0 - wr)):
            grid = {}
            for ask in ASK_GRID:
                row = {}
                for fee in FEE_LEVELS:
                    evp = p_win / ask - 1 - fee
                    row[f"fee{int(fee*100)}pct"] = round(evp, 4)
                grid[f"ask{ask}"] = row
            ev[tag] = grid
        results["ev_surfaces"][f"t{t}"] = ev

        # yearly + recent-window stability
        yrs = year_of[pB][m]
        winv = strict_win[m]
        fvv = fv[m]
        yearly = {}
        for y in range(2018, 2027):
            ym = yrs == y
            if ym.sum() < 100:
                continue
            yearly[str(y)] = {"n": int(ym.sum()),
                              "wr": round(float(winv[ym].mean()) * 100, 2),
                              "mean_fv": round(float(np.nanmean(fvv[ym])), 4)}
        results["yearly"][f"t{t}"] = yearly
        recent = yrs >= 2024
        if recent.sum() >= 100:
            results.setdefault("recent_2024plus", {})[f"t{t}"] = {
                "n": int(recent.sum()),
                "wr": round(float(winv[recent].mean()) * 100, 2),
                "mean_fv": round(float(np.nanmean(fvv[recent])), 4),
                "gap_pp": round((float(winv[recent].mean()) - float(np.nanmean(fvv[recent]))) * 100, 2),
                "wr95": list(map(lambda v: round(v, 4), wilson(float(winv[recent].mean()), int(recent.sum())))),
            }
        print(f"t={t}min left={4-t}min: n={nT:,} wr={wr*100:.2f}% gap={results['signal_offsets_min'][f't{t}']['calibration_gap_pp']:+.2f}pp ({time.time()-t0:.0f}s)")

    results["runtime_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(results, indent=1))
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
