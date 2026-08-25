#!/usr/bin/env python3
"""
Moomoo OpenD <-> ThetaEdge account sync.

Pulls live/paper account state from a running OpenD gateway (Moomoo's API
gateway) and writes a ThetaEdge-compatible JSON snapshot plus an append-only
trade ledger suitable for IRD record-keeping.

SAFETY BY DESIGN:
  - READ-ONLY. This script never places, modifies or cancels orders.
  - Defaults to SIMULATE (paper) environment. Use --env real only when you
    deliberately want to mirror your funded account.

PREREQUISITES (one-time):
  1. Moomoo account with API access enabled (in-app questionnaire).
  2. OpenD gateway installed + running on this machine:
        https://openapi.moomoo.com/moomoo-api-doc/en/quick/opend-base.html
     (Java 8+ required; ~500MB RAM. Login with your moomoo ID on first run.)
  3. Python SDK:
        uv pip install futu-api        (recommended, PEP 668-safe)
     or: pip install --user futu-api   (if you have pip)

USAGE:
  python3 scripts/moomoo_sync.py                 # paper account, default port
  python3 scripts/moomoo_sync.py --env real      # live account (read-only!)
  python3 scripts/moomoo_sync.py --port 11111    # custom OpenD port
  python3 scripts/moomoo_sync.py --check         # diagnose setup only

OUTPUTS:
  public/data/account_snapshot.json   -> picked up by ThetaEdge UI
  ~/thetaedge-ledger.jsonl            -> append-only fill log (IRD records)
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
SNAPSHOT_PATH = REPO / 'public' / 'data' / 'account_snapshot.json'
LEDGER_PATH = Path.home() / 'thetaedge-ledger.jsonl'


def check_setup():
    """Diagnose environment without needing OpenD running."""
    print("ThetaEdge <- OpenD sync: setup check")
    print("-" * 50)

    try:
        import futu  # noqa: F401
        print(f"[OK] futu-api SDK installed (v{getattr(futu, '__version__', '?')})")
    except ImportError:
        print("[!!] futu-api SDK NOT installed.")
        print("     Fix:  uv pip install futu-api")
        return False

    try:
        import socket
        s = socket.create_connection(("127.0.0.1", ARGS.port), timeout=2)
        s.close()
        print(f"[OK] OpenD gateway reachable on 127.0.0.1:{ARGS.port}")
    except OSError:
        print(f"[!!] OpenD gateway NOT reachable on 127.0.0.1:{ARGS.port}")
        print("     Start OpenD first (see module docstring).")
        return False

    print("\nAll good. Run without --check to pull your account snapshot.")
    return True


def pull_account(host: str, port: int, env: str) -> dict:
    """Connect to OpenD and pull full account state. Raises on failure."""
    from futu import OpenSecTradeContext, TrdEnv, TrdMarket, SecurityFirm

    trd_env = TrdEnv.REAL if env == "real" else TrdEnv.SIMULATE
    ctx = OpenSecTradeContext(
        filter_trdmarket=TrdMarket.US,
        host=host,
        port=port,
        security_firm=SecurityFirm.MOOMOOINC,  # NZ/AU clients trade under MOOMOOINC entity
    )
    try:
        acc_list, _ = ctx.get_acc_list()
        if acc_list.empty:
            raise RuntimeError("No trading accounts visible to OpenD login.")

        # Pick first account matching requested env
        row = acc_list[acc_list["trd_env"] == ("REAL" if env == "real" else "SIMULATE")]
        if row.empty:
            raise RuntimeError(f"No {env} account found. Accounts seen:\n{acc_list}")
        acc_id = int(row.iloc[0]["acc_id"])

        assets, _ = ctx.accinfo_query(acc_id=acc_id, trd_env=trd_env)
        positions, _ = ctx.position_list_query(acc_id=acc_id, trd_env=trd_env)
        orders, _ = ctx.order_list_query(acc_id=acc_id, trd_env=trd_env)

        now = datetime.now(timezone.utc).isoformat()
        snapshot = {
            "_generated_at": now,
            "source": f"moomoo-opend@{host}:{port}",
            "env": env,
            "acc_id": acc_id,
            "assets": assets.to_dict(orient="records")[0] if not assets.empty else {},
            "positions": positions.to_dict(orient="records"),
            "open_orders": orders.to_dict(orient="records"),
        }
        fills = _extract_fills(ctx, acc_id, trd_env)
        return {"snapshot": snapshot, "fills": fills}
    finally:
        ctx.close()


def _extract_fills(ctx, acc_id, trd_env):
    """Today's executed fills -> ledger records."""
    try:
        deals, _ = ctx.deal_list_query(acc_id=acc_id, trd_env=trd_env)
        records = []
        for _, d in deals.iterrows():
            records.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "code": d.get("code"),
                "name": d.get("stock_name"),
                "side": d.get("trd_side"),
                "qty": float(d.get("qty", 0)),
                "price": float(d.get("dealt_price", 0) or d.get("filled_price", 0) or 0),
                "fee": float(d.get("fee_amount", 0) or 0),
                "order_id": str(d.get("order_id", "")),
                "env": trd_env.name if hasattr(trd_env, "name") else str(trd_env),
            })
        return records
    except Exception as e:  # fills are nice-to-have; don't fail the sync
        print(f"  (fill extraction skipped: {e})")
        return []


def write_outputs(result: dict) -> None:
    snap = result["snapshot"]
    SNAPSHOT_PATH.parent.mkdir(exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snap, default=str, indent=2))
    print(f"  wrote {SNAPSHOT_PATH}")

    if result["fills"]:
        with LEDGER_PATH.open("a") as f:
            for r in result["fills"]:
                f.write(json.dumps(r, default=str) + "\n")
        print(f"  appended {len(result['fills'])} fill(s) to {LEDGER_PATH}")

    # Human-readable one-liner
    a = snap.get("assets", {})
    keys = ["total_assets", "cash", "market_val", "unrealized_pl"]
    summary = ", ".join(f"{k}={a[k]}" for k in keys if k in a)
    print(f"  [{snap['env'].upper()}] acc {snap['acc_id']}: {summary or 'no asset fields returned'}")


def main():
    global ARGS
    parser = argparse.ArgumentParser(description="Moomoo OpenD -> ThetaEdge sync (read-only)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    parser.add_argument("--env", choices=["simulate", "real"], default="simulate")
    parser.add_argument("--check", action="store_true", help="diagnose setup only")
    ARGS = parser.parse_args()

    print("=" * 60)
    print("ThetaEdge <- Moomoo OpenD account sync")
    print("=" * 60)

    if ARGS.check:
        sys.exit(0 if check_setup() else 1)

    try:
        result = pull_account(ARGS.host, ARGS.port, ARGS.env)
    except ImportError:
        print("[!!] futu-api SDK missing. Fix:  uv pip install futu-api")
        sys.exit(1)
    except Exception as e:
        print(f"[!!] Sync failed: {e}")
        print("     Is OpenD running and logged in? Try: python3 scripts/moomoo_sync.py --check")
        sys.exit(1)

    write_outputs(result)
    print("Done.")


if __name__ == "__main__":
    main()
