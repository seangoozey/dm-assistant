"""Independent extraction-contribution model; never canonical relationships."""
from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field


class Contribution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: str
    target: str
    relation: str
    description: str
    evidence_id: str
    revision: str
    state: str
    authority: str
    visibility: str
    attribution: str
    negated: bool
    time_scope: str
    strength: float = Field(ge=0, le=1, allow_inf_nan=False)


def aggregate(contributions):
    groups = defaultdict(dict)
    for c in contributions:
        key = (c.source, c.target, c.relation, c.state, c.authority, c.negated, c.time_scope,
               c.visibility, c.attribution)
        # Overlap/copies sharing original evidence cannot multiply support.
        identity = (c.evidence_id, c.revision)
        previous = groups[key].get(identity)
        if previous is None or (c.strength, c.description) < (previous.strength, previous.description):
            groups[key][identity] = c
    return [{"source": key[0], "target": key[1], "relation": key[2],
             "state": key[3], "authority": key[4], "negated": key[5], "time_scope": key[6],
             "visibility": key[7], "attribution": key[8],
             "strength": sum(c.strength for c in items.values()) / len(items),
             "support_count": len(items),
             "contributions": [items[k].model_dump() for k in sorted(items)]}
            for key, items in sorted(groups.items())]
