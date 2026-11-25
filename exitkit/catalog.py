import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "data", "catalog.json")
CATALOG = json.load(open(_PATH))

# category -> migration phase (0 = first)
PHASES = ["Foundations (network, identity, keys)", "Data platforms (replicate first)",
          "Messaging & streaming", "Compute & applications", "ML & analytics, observability",
          "Edge cutover & decommission"]
CATEGORY_PHASE = {"network": 0, "identity": 0, "keys": 0,
                  "relational": 1, "nosql": 1, "warehouse": 1, "object": 1, "cache": 1,
                  "messaging": 2, "streaming": 2,
                  "vm": 3, "containers": 3, "serverless": 3,
                  "ml": 4, "analytics": 4, "observability": 4, "edge": 5}
DATA_CATEGORIES = {"relational", "nosql", "warehouse", "object", "streaming", "cache"}
CLASS_LABEL = {1: "Lift-and-shift", 2: "Open-standard managed", 3: "Re-platform",
               4: "Re-architect", 5: "Proprietary / no equivalent"}

UNKNOWN = {"provider": "?", "category": "compute-unknown", "class": 4, "effort": 1.0,
           "target": "Unmapped: assess manually", "playbook": "Uncatalogued service: treated as class 4 until assessed."}


def lookup(rtype: str):
    e = CATALOG.get(rtype)
    return (e, True) if e else (UNKNOWN, False)


def phase_of(category: str) -> int:
    return CATEGORY_PHASE.get(category, 3)
