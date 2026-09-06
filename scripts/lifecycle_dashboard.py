#!/usr/bin/env python3
"""Generate the Strategy Lifecycle Dashboard (Kanban-style HTML).

Reads state from ~/nautilus-lab/state/ + ~/thetaedge/scripts/data/rsi_btc_paper.json
and writes ~/thetaedge/public/lifecycle.html (served by the ThetaEdge app).

Kanban columns = lifecycle stages:
  ARCHIVE (dead) | GENERATED | BACKTESTED | GATED | INCUBATION | DEPLOYMENT-READY
Cards show: name, description, metrics, failure analysis, regime, dates.
Header shows: funnel survival rates, RSI paper signal state, costs model, dates.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

STATE = Path.home() / "nautilus-lab" / "state"
RSI_STATE = Path.home() / "thetaedge" / "scripts" / "data" / "rsi_btc_paper.json"
OUT = Path.home() / "thetaedge" / "public" / "lifecycle.html"

STAGE_COLUMNS = [
    ("archive", "🗄️ ARCHIVE (dead)", "#7f1d1d"),
    ("generated", "💡 GENERATED", "#1e3a8a"),
    ("backtested", "🔬 BACKTESTED", "#1e40af"),
    ("gated_pass", "✅ GATED", "#065f46"),
    ("incubating", "🧪 INCUBATION", "#92400e"),
    ("deployment_ready", "🚀 DEPLOYMENT-READY", "#064e3b"),
]

STAGE_ALIASES = {
    "archived": "archive",
    "gated_fail": "archive", "mc_fail": "archive", "incubation_fail": "archive",
    "gated_pass": "gated_pass", "mc_pass": "gated_pass",
    "incubation_pass": "deployment_ready", "deployed": "deployment_ready",
}


def load(name):
    p = STATE / name
    if p.exists():
        return json.load(open(p))
    return {}


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def card(slug, rec):
    stage = rec.get("stage", "?")
    metrics = rec.get("metrics") or {}
    metric_bits = []
    for k in ["return_pct", "total_return", "trades", "trade_count", "sharpe", "profit_factor", "max_drawdown"]:
        v = metrics.get(k)
        if v is not None:
            label = k.replace("_", " ")
            if isinstance(v, float):
                metric_bits.append(f"<span class='chip'>{label}: {v:+.2f}</span>" if "return" in k or "pct" in k
                                   else f"<span class='chip'>{label}: {v}</span>")
    fa = rec.get("failure_analysis")
    fa_html = f"<div class='fail'>❌ {esc(fa)}</div>" if fa else ""
    regime = f"<div class='regime'>regime: {esc(rec.get('regime'))}</div>" if rec.get("regime") else ""
    desc = esc(rec.get("strategy_description") or rec.get("description") or "")[:220]
    upd = rec.get("updated", "")
    return f"""
    <div class="card" data-stage="{stage}">
      <div class="card-title">{esc(slug)}</div>
      <div class="card-desc">{desc}</div>
      <div class="chips">{''.join(metric_bits)}</div>
      {fa_html}{regime}
      <div class="date">updated {esc(str(upd)[:10])}</div>
    </div>"""


def main():
    funnel = load("funnel.json")
    archive = load("archive.json")
    incub = load("incubation.json")
    swans = load("black_swans.json")
    rsi = {}
    if RSI_STATE.exists():
        rsi = json.load(open(RSI_STATE))

    columns = {sid: [] for sid, _, _ in STAGE_COLUMNS}
    # merge archive.json entries into funnel view
    merged = dict(funnel)
    for slug, rec in archive.items():
        if slug not in merged:
            merged[slug] = {**rec, "stage": "archived"}
    # incubation pool overrides
    for slug, p in (incub.get("pool") or {}).items():
        status = "deployment_ready" if p.get("status") == "deployment_ready" else "incubating"
        merged[slug] = {**merged.get(slug, {}), "stage": status,
                        "strategy_description": merged.get(slug, {}).get("strategy_description", ""),
                        "updated": p.get("enrolled", "")}

    for slug, rec in merged.items():
        stage = rec.get("stage", "generated")
        stage = STAGE_ALIASES.get(stage, stage)
        if stage in columns:
            columns[stage].append(card(slug, rec))

    col_html = ""
    for sid, title, color in STAGE_COLUMNS:
        cards = "\n".join(columns[sid]) or "<div class='empty'>—</div>"
        count = len(columns[sid])
        col_html += f"""
        <div class="column">
          <div class="col-header" style="border-top-color:{color}">{title} <span class="count">{count}</span></div>
          {cards}
        </div>"""

    # funnel rates
    counts = {s: len(columns[s]) for s, _, _ in STAGE_COLUMNS}
    gen = max(counts.get("generated", 0), 1)
    gated = counts.get("gated_pass", 0)
    inc = counts.get("incubating", 0) + counts.get("deployment_ready", 0)
    dep = counts.get("deployment_ready", 0)

    # RSI signal state
    pos = rsi.get("position")
    rsi_html = f"""
    <div class="stat"><b>RSI(14) BTC paper</b><br>
      last computed: {rsi.get('last_computed','—')} | RSI: {rsi.get('last_rsi','—')}<br>
      position: {'LONG ' + str(pos.get('usd')) + ' USD @ ' + str(pos.get('entry_price')) if pos else 'FLAT'}<br>
      closed trades: {len(rsi.get('history', []))} | cum PnL: ${sum(h['pnl_usd'] for h in rsi.get('history', [])):.2f}
    </div>"""

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Strategy Lifecycle — ThetaEdge</title>
<style>
  body {{ background:#0b0e14; color:#d1d4dc; font-family:-apple-system,sans-serif; margin:0; padding:16px; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .sub {{ color:#787b86; font-size:12px; margin-bottom:12px; }}
  .stats {{ display:flex; gap:12px; margin-bottom:14px; flex-wrap:wrap; }}
  .stat {{ background:#131722; border:1px solid #2a2e39; border-radius:4px; padding:10px 14px; font-size:12px; }}
  .board {{ display:flex; gap:10px; align-items:flex-start; overflow-x:auto; }}
  .column {{ min-width:230px; width:230px; background:#131722; border-radius:4px; padding:8px; }}
  .col-header {{ font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.4px;
                 border-top:3px solid #2a2e39; padding:4px 0 8px; }}
  .count {{ background:#2a2e39; border-radius:8px; padding:1px 7px; font-size:11px; }}
  .card {{ background:#1e222d; border:1px solid #2a2e39; border-radius:4px; padding:8px; margin-bottom:8px; font-size:11px; }}
  .card-title {{ font-weight:700; color:#fff; font-size:12px; margin-bottom:3px; }}
  .card-desc {{ color:#787b86; margin-bottom:5px; }}
  .chip {{ display:inline-block; background:#2a2e39; border-radius:3px; padding:1px 5px; margin:1px 2px 1px 0; font-size:10px; }}
  .fail {{ color:#f23645; margin-top:4px; }}
  .regime {{ color:#f5b942; margin-top:3px; }}
  .date {{ color:#4a4e59; margin-top:4px; font-size:10px; }}
  .empty {{ color:#4a4e59; font-size:11px; padding:6px; }}
</style></head><body>
<h1>🐋 Strategy Lifecycle — Kanban</h1>
<div class="sub">generated {now} · dual-engine validation (NautilusTrader + Vibe-Trading) · black-swan battery (9 windows) · costs: taker fees + funding + margin</div>
<div class="stats">
  <div class="stat"><b>Funnel</b><br>generated {gen} → gated {gated} → incubating {inc} → ready {dep}<br>
    survival: {round(gated / gen * 100, 1)}% → {round(inc / gen * 100, 1)}%</div>
  {rsi_html}
  <div class="stat"><b>Black-swan battery</b><br>{len(swans)} windows: COVID, LUNA, FTX, Celsius,<br>Bybit hack, Iran strike, carry unwind,<br>Binance FUD, tariff shock</div>
  <div class="stat"><b>Cost model</b><br>futures taker 0.05%/side<br>spot 0.1%/side · funding 0.01%/8h<br>(0.05%/8h crash premium)</div>
</div>
<div class="board">{col_html}</div>
</body></html>"""

    OUT.write_text(html)
    print(f"dashboard written: {OUT} ({len(html):,} bytes)")
    print(f"stages: {counts}")


if __name__ == "__main__":
    main()
