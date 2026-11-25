from __future__ import annotations
from dataclasses import dataclass, field

TIER_WEIGHT = {"tier1": 3.0, "tier2": 2.0, "tier3": 1.0}
TIER_EFFORT = {"tier1": 1.3, "tier2": 1.0, "tier3": 0.8}


@dataclass
class Resource:
    address: str                 # type.name
    rtype: str
    name: str
    provider: str
    tier: str = "tier2"
    data_gb: float = 0.0
    monthly_usd: float = 250.0
    monthly_estimated: bool = True
    deps: list = field(default_factory=list)
    file: str = ""
    catalogued: bool = True


@dataclass
class Estate:
    name: str
    resources: list
    code_calls: dict = field(default_factory=dict)   # rtype -> call-site count
    sdk_files: int = 0
    settings: dict = field(default_factory=dict)

    @property
    def monthly_total(self) -> float:
        return sum(r.monthly_usd for r in self.resources)
