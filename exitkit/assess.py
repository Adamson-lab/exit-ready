"""Organisational readiness questionnaire + combined Exit Readiness Index (ERI)."""
import json
import os

Q = json.load(open(os.path.join(os.path.dirname(__file__), "data", "questionnaire.json")))


def maturity(p):
    return "Initial" if p < 25 else "Developing" if p < 50 else "Defined" if p < 75 else "Tested"


def readiness(answers: dict):
    doms, gaps, unanswered = {}, [], []
    for dom, qs in Q["domains"].items():
        got = 0
        for qid, text, gate in qs:
            if qid not in answers:
                unanswered.append(qid)
            a = int(answers.get(qid, 0))
            if not 0 <= a <= 3:
                raise ValueError(f"{qid}: score must be 0..3")
            got += a
            if gate and a <= 1:
                gaps.append({"id": qid, "text": text, "score": a})
        pct = round(100 * got / (3 * len(qs)), 1)
        doms[dom] = {"pct": pct, "maturity": maturity(pct)}
    overall = round(sum(d["pct"] for d in doms.values()) / len(doms), 1)
    return {"overall": overall, "maturity": maturity(overall), "domains": doms,
            "critical_gaps": gaps, "unanswered": unanswered}


def eri(lock, ready, plan):
    portability = 100 - lock["overall"]
    score = round(0.5 * portability + 0.5 * ready["overall"], 1)
    rag = "GREEN" if score >= 70 else "AMBER" if score >= 45 else "RED"
    why = []
    if not plan["scenarios"]["stressed"]["feasible"] and rag == "GREEN":
        rag = "AMBER"; why.append("stressed exit not feasible in window: capped at AMBER")
    if portability < 30 and rag != "RED":
        rag = "RED"; why.append("portability below 30: forced RED")
    if len(ready["critical_gaps"]) >= 5 and rag == "GREEN":
        rag = "AMBER"; why.append("5+ critical gaps: capped at AMBER")
    return {"score": score, "rag": rag, "portability": round(portability, 1), "readiness": ready["overall"], "notes": why}
