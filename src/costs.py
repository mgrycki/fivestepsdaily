"""Cost ledger and monthly budget guard. Ported from ShortFactory's cost table.

Every paid call appends one JSON line to data/costs.jsonl, which the workflow commits back,
so the ledger survives ephemeral runners. The guard stops a run BEFORE it spends.
"""
import json
import os
from datetime import datetime, timezone

from . import config

LEDGER = os.path.join(config.ROOT, "data", "costs.jsonl")

# USD list prices at 2026-09. Update when a provider or model changes, or the budget lies.
PRICING = {
    "image":        float(config.opt("IMAGE_COST_USD", "0.08")),      # one 1024px illustration
    "heygen_second": float(config.opt("HEYGEN_COST_PER_SECOND", "0.0333")),  # Video Agent
    "claude_routine": 0.0,                                              # subscription, not API
}


def record(item: str, units: float, run: str = "", note: str = "") -> float:
    usd = round(units * PRICING.get(item, 0.0), 4)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run": run, "item": item, "units": units, "usd": usd, "note": note,
        }) + "\n")
    print(f"[cost] {item}: {units:g} x ${PRICING.get(item, 0):.4f} = ${usd:.4f}")
    return usd


def month_spend() -> float:
    if not os.path.exists(LEDGER):
        return 0.0
    prefix = datetime.now(timezone.utc).strftime("%Y-%m")
    total = 0.0
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("at", "").startswith(prefix):
                total += float(row.get("usd", 0))
    return round(total, 4)


def budget() -> float:
    return float(config.opt("MONTHLY_BUDGET_USD", "15"))


def guard(about_to_spend: float, what: str) -> bool:
    """True if the spend fits under MONTHLY_BUDGET_USD; otherwise print why and return False."""
    spent = month_spend()
    if spent + about_to_spend > budget():
        print(f"[budget] refusing {what}: ${spent:.2f} spent + ${about_to_spend:.2f} "
              f"> ${budget():.2f} monthly cap (MONTHLY_BUDGET_USD)")
        return False
    return True
