import argparse
import json
import os
import sys

from . import assess, plan as planmod, report, scoring
from .scanner import load_estate


def analyse(path, answers_path=None, team=None, window=None):
    estate = load_estate(path)
    lock = scoring.lockin(estate)
    ans = json.load(open(answers_path)) if answers_path else (
        json.load(open(os.path.join(path, "answers.json"))) if os.path.exists(os.path.join(path, "answers.json")) else {})
    ready = assess.readiness(ans)
    pl = planmod.build(estate, team, window)
    return estate, lock, ready, assess.eri(lock, ready, pl), pl


def summary(estate, lock, ready, eri, pl):
    print(f"\n{estate.name}: {len(estate.resources)} resources, {', '.join(lock['providers'])}, ${estate.monthly_total:,.0f}/month")
    print(f"  ERI {eri['score']:.0f} [{eri['rag']}]   lock-in {lock['overall']:.0f} ({lock['level']})   readiness {ready['overall']:.0f}% ({ready['maturity']})")
    for n, s in pl["scenarios"].items():
        v = "FEASIBLE" if s["feasible"] else f"NOT FEASIBLE (needs team {s['min_team'] or '>500'})"
        print(f"  {n:<9} {s['days']:>4}d vs {s['window_days']:>3}d window  {v:<34} cost ${s['cost']['total']:>10,}  ({s['cost']['pct_of_annual_spend']}% of annual spend)")
    for n in eri["notes"]:
        print("  note:", n)


def main(argv=None):
    ap = argparse.ArgumentParser("exitkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("assess"); a.add_argument("path"); a.add_argument("--answers"); a.add_argument("--out", default="out")
    a.add_argument("--team", type=int); a.add_argument("--window", type=int)
    c = sub.add_parser("compare"); c.add_argument("before"); c.add_argument("after")
    sub.add_parser("demo")
    sub.add_parser("catalog")
    x = ap.parse_args(argv)

    if x.cmd == "catalog":
        from .catalog import CATALOG, CLASS_LABEL
        for k, v in sorted(CATALOG.items(), key=lambda kv: (kv[1]["provider"], -kv[1]["class"])):
            print(f"{k:<38}{v['provider']:<7}class {v['class']} {CLASS_LABEL[v['class']]:<28}-> {v['target']}")
        return
    if x.cmd == "assess":
        res = analyse(x.path, x.answers, x.team, x.window)
        summary(*res)
        os.makedirs(x.out, exist_ok=True)
        estate, lock, ready, eri, pl = res
        open(os.path.join(x.out, "exit-report.html"), "w", encoding="utf-8").write(report.html_report(*res))
        open(os.path.join(x.out, "exit-plan.md"), "w", encoding="utf-8").write(report.markdown_plan(*res))
        json.dump({"name": estate.name, "eri": eri, "lockin": {k: v for k, v in lock.items() if k != "all"},
                   "readiness": ready, "plan": {n: {k: v for k, v in s.items() if k != "phases"} for n, s in pl["scenarios"].items()}},
                  open(os.path.join(x.out, "results.json"), "w"), indent=1)
        print(f"  wrote {x.out}/exit-report.html, exit-plan.md, results.json")
    elif x.cmd == "compare":
        b, a2 = (json.load(open(p))["eri"]["score"] for p in (x.before, x.after))
        print(f"ERI {b} -> {a2}  ({a2 - b:+.1f})")
    elif x.cmd == "demo":
        for ex in ("northwind-bank", "portable-estate"):
            p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", ex)
            res = analyse(p)
            summary(*res)
            os.makedirs(f"out/{ex}", exist_ok=True)
            open(f"out/{ex}/exit-report.html", "w", encoding="utf-8").write(report.html_report(*res))
            open(f"out/{ex}/exit-plan.md", "w", encoding="utf-8").write(report.markdown_plan(*res))
        print("\nOpen out/northwind-bank/exit-report.html and out/portable-estate/exit-report.html")
