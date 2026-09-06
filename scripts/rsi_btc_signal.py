"""RSI(14) 30/70 reversion signal — BTC module for ThetaEdge.

The validated strategy from the dual-engine battery (NT + VT, 2024 IS + 2025 OOS,
quality-gate GO). Produces a daily signal + paper-position state for BTC:

  LONG (enter)  : RSI14 crosses UP through 30
  CLOSE         : RSI14 crosses UP through 70

State: ~/thetaedge/src/data/rsi_btc_paper.json
Output appended to the daily summary for the Telegram relay.

Paper rules: $1,000 notional per position (matches ThetaEdge account), fees 0.1%/side
(spot), one position at a time. No leverage.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(__file__).parent / "data" / "rsi_btc_paper.json"
PERIOD = 14
ENTRY_LEVEL = 30.0
EXIT_LEVEL = 70.0
POSITION_USD = 1000.0
FEE = 0.001  # spot taker per side

KLINE_URL = ("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d"
             "&limit={limit}")


def fetch_daily_closes(limit=PERIOD + 60):
    url = KLINE_URL.format(limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    rows = json.load(urllib.request.urlopen(req, timeout=30))
    # skip the still-forming last candle; use only closed dailies
    return [{
        "ts": r[0],
        "date": datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
        "close": float(r[4]),
    } for r in rows[:-1]]


def rsi(closes, period=PERIOD):
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas[-period:]]
    losses = [max(-d, 0) for d in deltas[-period:]]
    avg_g = sum(gains) / period
    avg_l = sum(losses) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))


def rsi_series(closes, period=PERIOD):
    out = []
    for i in range(period, len(closes) + 1):
        v = rsi(closes[:i], period)
        if v is not None:
            out.append((closes[i - 1], v))
    return out


def load_state():
    if STATE_FILE.exists():
        return json.load(open(STATE_FILE))
    return {"position": None, "history": []}


def compute_signal():
    state = load_state()
    candles = fetch_daily_closes()
    closes = [c["close"] for c in candles]
    series = rsi_series(closes)
    if len(series) < 2:
        return {"error": "not enough data"}

    prev_close, prev_rsi = series[-2]
    last_candle = candles[-1]
    last_close, last_rsi = series[-1]

    crossed_up_entry = prev_rsi < ENTRY_LEVEL <= last_rsi
    crossed_up_exit = prev_rsi < EXIT_LEVEL <= last_rsi

    pos = state.get("position")
    action = "HOLD"
    pnl = None

    if pos is None and crossed_up_entry:
        action = "ENTER LONG"
        pos = {
            "entry_date": last_candle["date"],
            "entry_price": last_close,
            "usd": POSITION_USD,
            "qty": POSITION_USD / last_close,
            "fees_paid": POSITION_USD * FEE,
        }
    elif pos is not None and crossed_up_exit:
        exit_value = pos["qty"] * last_close
        exit_fee = exit_value * FEE
        pnl = exit_value - exit_fee - pos["usd"] - pos["fees_paid"]
        action = f"CLOSE LONG (PnL {pnl:+.2f} USD)"
        state["history"].append({
            "entry_date": pos["entry_date"], "entry_price": pos["entry_price"],
            "exit_date": last_candle["date"], "exit_price": last_close,
            "pnl_usd": round(pnl, 2),
            "return_pct": round(pnl / pos["usd"] * 100, 2),
        })
        pos = None
    elif pos is not None:
        pnl = pos["qty"] * last_close - pos["usd"] - pos["fees_paid"]
        action = f"HOLD LONG (open PnL {pnl:+.2f} USD)"

    state["position"] = pos
    state["last_computed"] = last_candle["date"]
    state["last_rsi"] = round(last_rsi, 2)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(state, open(STATE_FILE, "w"), indent=1)

    history = state.get("history", [])
    wins = sum(1 for h in history if h["pnl_usd"] > 0)
    return {
        "date": last_candle["date"],
        "rsi14": round(last_rsi, 2),
        "prev_rsi": round(prev_rsi, 2),
        "crossed_up_entry": crossed_up_entry,
        "crossed_up_exit": crossed_up_exit,
        "action": action,
        "open_pnl_usd": round(pnl, 2) if pnl is not None and pos else None,
        "closed_trades": len(history),
        "closed_win_rate": round(wins / len(history) * 100, 1) if history else None,
        "cum_pnl_usd": round(sum(h["pnl_usd"] for h in history), 2),
        "state_file": str(STATE_FILE),
    }


if __name__ == "__main__":
    print(json.dumps(compute_signal(), indent=1))
