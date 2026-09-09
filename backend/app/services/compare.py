"""Compare two investigations side-by-side: shared entities, unique entities,
shared/different relationships and findings."""
from app.models.entities import Investigation


def compare(left: Investigation, right: Investigation) -> dict:
    l_entities = {e.value.lower(): e for e in left.entities}
    r_entities = {e.value.lower(): e for e in right.entities}

    shared = [v.value for v in (l_entities[k] for k in l_entities.keys()
                                 & r_entities.keys())]
    left_only = [v.value for k, v in l_entities.items() if k not in r_entities]
    right_only = [v.value for k, v in r_entities.items() if k not in l_entities]

    def _sources(inv):
        return sorted({f.source for f in inv.findings})

    def _rel_keys(inv):
        return sorted({f"{r.source_id[:8]}--{r.relation}->{r.target_id[:8]}"
                       for r in inv.relationships})

    l_find = {f.key: f for f in left.findings}
    r_find = {f.key: f for f in right.findings}
    common_keys = l_find.keys() & r_find.keys()
    left_only_find = [k for k in l_find if k not in r_find]
    right_only_find = [k for k in r_find if k not in l_find]

    return {
        "left": {"id": left.id, "raw_input": left.raw_input,
                 "input_type": left.input_type,
                 "created_at": left.created_at,
                 "tags": left.tags or []},
        "right": {"id": right.id, "raw_input": right.raw_input,
                  "input_type": right.input_type,
                  "created_at": right.created_at,
                  "tags": right.tags or []},
        "shared_entities": sorted(shared),
        "left_only_entities": sorted(left_only),
        "right_only_entities": sorted(right_only),
        "shared_sources": sorted(set(_sources(left)) & set(_sources(right))),
        "shared_findings": sorted(common_keys),
        "left_only_findings": sorted(left_only_find),
        "right_only_findings": sorted(right_only_find),
        "shared_relationships": sorted(set(_rel_keys(left)) & set(_rel_keys(right))),
        "left_only_relationships": sorted(set(_rel_keys(left)) - set(_rel_keys(right))),
        "right_only_relationships": sorted(set(_rel_keys(right)) - set(_rel_keys(left))),
    }