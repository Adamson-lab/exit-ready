"""HTML report (inline SVG, zero deps) and a Markdown exit plan with Mermaid diagrams."""
from __future__ import annotations

import html
import math
import re

from .catalog import CLASS_LABEL, PHASES

RAG = {"GREEN": "#1a7f37", "AMBER": "#bf8700", "RED": "#d1242f"}


def _col(v):  # 0..100 lock-in colour
    return "#1a7f37" if v < 25 else "#9a6700" if v < 50 else "#bc4c00" if v < 70 else "#d1242f"


def svg_gauge(score, rag, w=260, h=170):
    cx, cy, r = w / 2, h - 30, 100
    def pt(p):
        a = math.pi * (1 - p / 100)
        return cx + r * math.cos(a), cy - r * math.sin(a)
    x0, y0 = pt(0); x1, y1 = pt(score); xe, ye = pt(100)
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">'
            f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {xe:.1f},{ye:.1f}" fill="none" stroke="#e5e7eb" stroke-width="18"/>'
            f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}" fill="none" stroke="{RAG[rag]}" stroke-width="18"/>'
            f'<text x="{cx}" y="{cy-8}" text-anchor="middle" font-size="40" font-weight="700" fill="{RAG[rag]}">{score:.0f}</text>'
            f'<text x="{cx}" y="{cy+16}" text-anchor="middle" font-size="13" fill="#555">Exit Readiness Index · {rag}</text></svg>')


def svg_bars(data: dict, title, w=620, color=_col, unit=""):
    rowh, pad = 24, 150
    h = 40 + rowh * len(data)
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="12">',
         f'<text x="0" y="16" font-weight="700" font-size="13">{html.escape(title)}</text>']
    for i, (k, v) in enumerate(data.items()):
        y = 30 + i * rowh
        bw = (w - pad - 60) * v / 100
        o.append(f'<text x="0" y="{y+14}">{html.escape(k)}</text>')
        o.append(f'<rect x="{pad}" y="{y}" width="{bw:.1f}" height="16" rx="3" fill="{color(v)}"/>')
        o.append(f'<text x="{pad+bw+6:.1f}" y="{y+13}" fill="#333">{v:.0f}{unit}</text>')
    return "".join(o) + "</svg>"


def svg_gantt(name, sc, w=860):
    rows, win = sc["phases"], sc["window_days"]
    xmax = max(win, sc["days"]) * 1.08
    pad, rowh = 250, 30
    h = 70 + rowh * (len(rows) + 1)
    X = lambda d: pad + (w - pad - 20) * d / xmax
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="12">',
         f'<text x="0" y="16" font-weight="700" font-size="13">{name.title()} exit — {sc["days"]} days vs {win}-day window · team {sc["team"]}</text>']
    for i, r in enumerate(rows):
        y = 36 + i * rowh
        c = "#bc4c00" if r["xfer_bound"] else "#0969da"
        o.append(f'<text x="0" y="{y+16}">{r["phase"]}. {html.escape(r["name"][:34])}</text>')
        o.append(f'<rect x="{X(r["start"]):.1f}" y="{y}" width="{max(X(r["dur"])-X(0),2):.1f}" height="20" rx="3" fill="{c}"/>')
    y = 36 + len(rows) * rowh
    o.append(f'<text x="0" y="{y+16}">Parallel run &amp; decommission</text>')
    o.append(f'<rect x="{X(sc["days"]-14):.1f}" y="{y}" width="{X(14)-X(0):.1f}" height="20" rx="3" fill="#6e7781"/>')
    col = "#1a7f37" if sc["feasible"] else "#d1242f"
    o.append(f'<line x1="{X(win):.1f}" x2="{X(win):.1f}" y1="24" y2="{h-14}" stroke="{col}" stroke-width="2" stroke-dasharray="6 4"/>')
    o.append(f'<text x="{X(win):.1f}" y="{h-2}" text-anchor="middle" fill="{col}">deadline {win}d</text>')
    return "".join(o) + "</svg>"


def svg_cost(plan, w=620):
    parts = [("egress", "#9a6700"), ("labour", "#0969da"), ("dual_run", "#8250df"), ("contingency", "#6e7781")]
    mx = max(s["cost"]["total"] for s in plan["scenarios"].values()) or 1
    h, pad = 50 + 56 * len(plan["scenarios"]), 80
    o = [f'<svg viewBox="0 0 {w} {h+30}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="12">',
         '<text x="0" y="16" font-weight="700" font-size="13">One-time exit cost (USD)</text>']
    for i, (n, s) in enumerate(plan["scenarios"].items()):
        y, x = 34 + i * 56, pad
        o.append(f'<text x="0" y="{y+16}">{n}</text>')
        for k, c in parts:
            bw = (w - pad - 120) * s["cost"][k] / mx
            o.append(f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="22" fill="{c}"/>')
            x += bw
        o.append(f'<text x="{x+6:.1f}" y="{y+16}">${s["cost"]["total"]:,} ({s["cost"]["pct_of_annual_spend"]}% of annual)</text>')
    lx = pad
    for k, c in parts:
        o.append(f'<rect x="{lx}" y="{h}" width="12" height="12" fill="{c}"/><text x="{lx+16}" y="{h+10}">{k}</text>')
        lx += 110
    return "".join(o) + "</svg>"


def html_report(estate, lock, ready, eri, plan):
    e = html.escape
    hs = "".join(f"<tr><td>{e(h['address'])}</td><td>{h['tier']}</td><td style='color:{_col(h['score'])};font-weight:600'>"
                 f"{h['score']:.0f}</td><td>{e(h['label'])}</td><td>{e(h['target'])}</td></tr>" for h in lock["hotspots"])
    sc_rows = "".join(
        f"<tr><td>{n}</td><td>{e(s['desc'])}</td><td>{s['window_days']}d</td><td>{s['days']}d</td>"
        f"<td style='color:{'#1a7f37' if s['feasible'] else '#d1242f'};font-weight:700'>{'FEASIBLE' if s['feasible'] else 'NOT FEASIBLE'}</td>"
        f"<td>{s['min_team'] if s['min_team'] else 'unreachable'}</td><td>{e(s['bottleneck'])}</td></tr>"
        for n, s in plan["scenarios"].items())
    gaps = "".join(f"<li><b>{g['id']}</b> ({g['score']}/3): {e(g['text'])}</li>" for g in ready["critical_gaps"]) or "<li>None</li>"
    dom = {k: v["pct"] for k, v in ready["domains"].items()}
    gantts = "".join(svg_gantt(n, s) for n, s in plan["scenarios"].items())
    notes = "".join(f"<li>{e(n)}</li>" for n in eri["notes"])
    return f"""<!doctype html><meta charset=utf-8><title>Cloud Exit Assessment — {e(estate.name)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:940px;margin:2rem auto;color:#1f2328;padding:0 1rem}}
table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border-bottom:1px solid #d0d7de;padding:6px 8px;text-align:left}}
.kpi{{display:flex;gap:1.2rem;flex-wrap:wrap;align-items:center}}.k{{background:#f6f8fa;border-radius:8px;padding:.8rem 1.1rem}}
.k b{{display:block;font-size:1.5rem}}svg{{max-width:100%;height:auto}}</style>
<h1>Cloud Exit Assessment — {e(estate.name)}</h1>
<div class=kpi>{svg_gauge(eri['score'], eri['rag'])}
<div class=k><b>{lock['overall']:.0f}/100</b>technical lock-in ({lock['level']})</div>
<div class=k><b>{ready['overall']:.0f}%</b>organisational readiness ({ready['maturity']})</div>
<div class=k><b>{lock['proprietary_spend_pct']:.0f}%</b>of spend on proprietary services</div>
<div class=k><b>{plan['effort_days']:,}</b>person-days to exit</div></div>
<ul>{notes}</ul>
<h2>Exit scenarios</h2><table><tr><th>Scenario</th><th>Trigger</th><th>Window</th><th>Needs</th><th>Verdict</th><th>Min team</th><th>Bottleneck</th></tr>{sc_rows}</table>
{gantts}
<h2>Cost to leave</h2>{svg_cost(plan)}
<h2>Where the lock-in lives</h2>{svg_bars(lock['by_category'], 'Lock-in score by category (higher = harder to leave)')}
<h3>Top hotspots</h3><table><tr><th>Resource</th><th>Tier</th><th>Score</th><th>Class</th><th>Open target</th></tr>{hs}</table>
<h2>Organisational readiness</h2>{svg_bars(dom, 'Readiness by domain (higher = better)', color=lambda v: _col(100 - v), unit='%')}
<h3>Critical gaps (gate questions scored 0–1)</h3><ul>{gaps}</ul>
<p style="color:#6e7781;font-size:12px">Model estimates, not quotes. Validate rates, throughput and contract terms before relying on figures.</p>"""


def _id(s):
    return re.sub(r"\W", "_", s)


def markdown_plan(estate, lock, ready, eri, plan, scenario="stressed"):
    sc = plan["scenarios"][scenario]
    L = [f"# Exit plan — {estate.name} ({scenario})", "",
         f"**ERI {eri['score']} ({eri['rag']})** · lock-in {lock['overall']} ({lock['level']}) · "
         f"{plan['effort_days']:,} person-days · {sc['days']} days with team {sc['team']} vs {sc['window_days']}-day window "
         f"→ **{'FEASIBLE' if sc['feasible'] else 'NOT FEASIBLE'}**", ""]
    if not sc["feasible"]:
        L.append(f"> To meet the window you would need a team of **{sc['min_team'] or 'more than 500 (adding people cannot fix this)'}**. Bottleneck: {sc['bottleneck']}.\n")
    L += ["## Wave plan", "", "```mermaid", "flowchart LR"]
    phases = sorted({i["phase"] for i in plan["items"]})
    for ph in phases:
        L.append(f'  subgraph P{ph}["{ph}. {PHASES[ph]}"]')
        for i in [x for x in plan["items"] if x["phase"] == ph]:
            L.append(f'    {_id(i["address"])}["{i["address"]}<br/>class {i["cls"]}"]')
        L.append("  end")
    for a, b in zip(phases, phases[1:]):
        L.append(f"  P{a} --> P{b}")
    for i in plan["items"]:
        for d in i["deps"]:
            L.append(f"  {_id(d)} -.-> {_id(i['address'])}")
    L += ["```", "", "## Runbook by wave", ""]
    for ph in phases:
        L.append(f"### Wave {ph} — {PHASES[ph]}")
        for i in sorted([x for x in plan["items"] if x["phase"] == ph], key=lambda x: -x["effort"]):
            xf = f", transfer ≈ {i['transfer_days']:.1f}d for {i['data_gb']:,.0f} GB" if i["transfer_days"] else ""
            L.append(f"- [ ] **{i['address']}** ({i['tier']}, class {i['cls']}, ~{i['effort']:.0f} pd{xf})  \n"
                     f"  Target: {i['target']}  \n  Play: {i['playbook']}")
        L.append("")
    L += ["## Exit-test checklist (run annually)", "",
          "- [ ] Restore a tier-1 dataset from the independent backup into the target and checksum it",
          "- [ ] Bring up the foundations wave in the target from IaC only (no console clicks)",
          "- [ ] Prove an identity cutover with a pilot user group",
          "- [ ] Time a DNS cutover with lowered TTLs", "- [ ] Record findings; re-run `exitkit assess` and compare the score", ""]
    return "\n".join(L)
