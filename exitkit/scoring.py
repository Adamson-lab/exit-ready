"""Technical lock-in score, 0 (fully portable) .. 100 (captive)."""
from __future__ import annotations

import math
from collections import defaultdict

from .catalog import CLASS_LABEL, lookup
from .model import TIER_WEIGHT

CLASS_SCORE = {1: 5, 2: 20, 3: 45, 4: 75, 5: 100}


def coupling_mult(estate, rtype) -> float:
    """+1% effort per code call-site, capped at +100%."""
    return 1 + min(estate.code_calls.get(rtype, 0) / 100, 1.0)


def resource_score(estate, r):
    e, _ = lookup(r.rtype)
    base = CLASS_SCORE[e["class"]]
    score = min(100, base + min(estate.code_calls.get(r.rtype, 0) / 10, 10))
    weight = TIER_WEIGHT.get(r.tier, 2.0) * (1 + min(math.log10(1 + r.data_gb) / 4, 1.0))
    return score, weight, e


def lockin(estate):
    tot_w = tot = 0.0
    by_cat, rows = defaultdict(lambda: [0.0, 0.0]), []
    prop_spend = 0.0
    tier1_prop = 0
    for r in estate.resources:
        s, w, e = resource_score(estate, r)
        tot += s * w
        tot_w += w
        by_cat[e["category"]][0] += s * w
        by_cat[e["category"]][1] += w
        if e["class"] >= 4:
            prop_spend += r.monthly_usd
            tier1_prop += r.tier == "tier1"
        rows.append({"address": r.address, "tier": r.tier, "class": e["class"], "label": CLASS_LABEL[e["class"]],
                     "score": round(s, 1), "weight": round(w, 2), "impact": round(s * w, 1),
                     "target": e["target"], "data_gb": r.data_gb, "catalogued": r.catalogued})
    overall = tot / tot_w if tot_w else 0.0
    rows.sort(key=lambda x: -x["impact"])
    cats = {c: round(v[0] / v[1], 1) for c, v in by_cat.items()}
    spend = estate.monthly_total or 1
    return {
        "overall": round(overall, 1),
        "level": "LOW" if overall < 25 else "MODERATE" if overall < 50 else "HIGH" if overall < 70 else "SEVERE",
        "by_category": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
        "proprietary_spend_pct": round(100 * prop_spend / spend, 1),
        "tier1_proprietary": tier1_prop,
        "providers": sorted({r.provider for r in estate.resources}),
        "hotspots": rows[:10], "all": rows,
        "uncatalogued": [r.address for r in estate.resources if not r.catalogued],
    }
