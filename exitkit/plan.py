"""Migration waves, schedule and exit-cost model."""
from __future__ import annotations

from collections import defaultdict

from .catalog import CATEGORY_PHASE, DATA_CATEGORIES, PHASES, lookup
from .model import TIER_EFFORT
from .scoring import coupling_mult

BASE_DAYS = {1: 2, 2: 5, 3: 15, 4: 40, 5: 90}
EGRESS_PER_GB = {"aws": 0.09, "azure": 0.087, "gcp": 0.12}

DEFAULTS = {
    "day_rate_usd": 900, "gbps": 5, "link_utilisation": 0.5, "verify_days": 3, "test_overhead": 0.5,
    "phase_overlap": 0.3, "parallel_run_days": 14, "target_cost_factor": 0.9,
    "egress_waived": False,
    "scenarios": {
        "stressed": {"window_days": 90, "team": 60, "min_phase_days": 10, "surge_premium": 1.5, "contingency": 0.35,
                     "desc": "Provider failure / sanction / regulator order"},
        "planned": {"window_days": 540, "team": 15, "min_phase_days": 21, "surge_premium": 1.0, "contingency": 0.20,
                    "desc": "Orderly, non-stressed exit"},
    },
}


def settings(estate):
    s = {**DEFAULTS, **estate.settings}
    sc = {k: {**v, **estate.settings.get("scenarios", {}).get(k, {})} for k, v in DEFAULTS["scenarios"].items()}
    s["scenarios"] = sc
    return s


def work_items(estate, cfg):
    items = []
    for r in estate.resources:
        e, _ = lookup(r.rtype)
        days = (BASE_DAYS[e["class"]] * e["effort"] * coupling_mult(estate, r.rtype)
                * TIER_EFFORT.get(r.tier, 1.0) * (1 + cfg["test_overhead"]))
        transfer = 0.0
        if e["category"] in DATA_CATEGORIES and r.data_gb:
            transfer = r.data_gb * 8 / (cfg["gbps"] * 86400 * cfg["link_utilisation"]) + cfg["verify_days"]
        items.append({"address": r.address, "phase": CATEGORY_PHASE.get(e["category"], 3), "effort": days,
                      "transfer_days": transfer, "target": e["target"], "playbook": e["playbook"],
                      "tier": r.tier, "cls": e["class"], "provider": r.provider, "data_gb": r.data_gb,
                      "deps": r.deps})
    return items


def eff_capacity(team):
    return max(team, 1) ** 0.85          # Brooks's-law style diminishing returns


def schedule(items, team, cfg, min_phase=14):
    cap = eff_capacity(team)
    per = defaultdict(list)
    for it in items:
        per[it["phase"]].append(it)
    t, rows = 0.0, []
    for ph in range(len(PHASES)):
        its = per.get(ph, [])
        if not its:
            continue
        eng = sum(i["effort"] for i in its) / cap
        xfer = sum(i["transfer_days"] for i in its)          # one shared link
        floor = min_phase if any(i["tier"] == "tier1" for i in its) else min_phase / 3  # change control & sign-off
        dur = max(eng, xfer, floor)
        rows.append({"phase": ph, "name": PHASES[ph], "start": t, "dur": dur, "effort": sum(i["effort"] for i in its),
                     "n": len(its), "xfer_bound": xfer > eng})
        t += dur * (1 - cfg["phase_overlap"])
    end = max((r["start"] + r["dur"] for r in rows), default=0) + cfg["parallel_run_days"]
    return rows, end


def min_team(items, window, cfg, min_phase, limit=500):
    for team in range(1, limit + 1):
        if schedule(items, team, cfg, min_phase)[1] <= window:
            return team
    return None


def cost(estate, items, cfg, sc, total_days):
    egress = 0.0 if cfg["egress_waived"] else sum(i["data_gb"] * EGRESS_PER_GB.get(i["provider"], 0.09) for i in items)
    effort = sum(i["effort"] for i in items)
    labour = effort * cfg["day_rate_usd"] * sc["surge_premium"]
    months = total_days / 30
    dual = estate.monthly_total * cfg["target_cost_factor"] * (0.5 * months + cfg["parallel_run_days"] / 30)
    sub = egress + labour + dual
    cont = sub * sc["contingency"]
    annual = estate.monthly_total * 12 or 1
    return {"egress": round(egress), "labour": round(labour), "dual_run": round(dual),
            "contingency": round(cont), "total": round(sub + cont), "pct_of_annual_spend": round(100 * (sub + cont) / annual, 1)}


def build(estate, team=None, window=None):
    cfg = settings(estate)
    items = work_items(estate, cfg)
    out = {"effort_days": round(sum(i["effort"] for i in items)), "scenarios": {}, "items": items, "cfg": cfg}
    for name, sc in cfg["scenarios"].items():
        sc = dict(sc)
        if name == "stressed":
            sc["team"], sc["window_days"] = team or sc["team"], window or sc["window_days"]
        rows, total = schedule(items, sc["team"], cfg, sc["min_phase_days"])
        mt = min_team(items, sc["window_days"], cfg, sc["min_phase_days"])
        out["scenarios"][name] = {
            **sc, "days": round(total), "phases": rows, "feasible": total <= sc["window_days"],
            "min_team": mt, "cost": cost(estate, items, cfg, sc, total),
            "bottleneck": "data transfer" if any(r["xfer_bound"] for r in rows) else "engineering effort"}
    return out
