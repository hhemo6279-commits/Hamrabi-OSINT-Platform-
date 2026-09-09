"""Evidence-based confidence engine.

Confidence is computed from a deterministic rule set, not a random
model guess:

- 0 sources  -> confidence 0.0  (no evidence)
- 1 source    -> base 0.40, +0.08 if source is high-quality, +0.1 if direct
- 2 sources   -> base 0.75, +0.06 each extra high-quality source
- 3+ sources  -> 0.92 minimum when sources are independent

Status labels map ranges as follows:
  >= 0.8 -> "Confirmed"
  >= 0.55 -> "Likely"
  else    -> "Needs Verification"
"""

HIGH_QUALITY_SOURCES = {"certificate", "dns", "whois", "leak_db_public"}

BASE_SINGLE = 0.40
BASE_DOUBLE = 0.75
BASE_TRIPLE = 0.92
HIGH_QUALITY_BONUS = 0.08
DIRECT_BONUS = 0.08


def compute_confidence(source_count: int, distinct_sources: set[str], direct: bool = False) -> tuple[float, str]:
    if source_count <= 0 or not distinct_sources:
        return 0.0, "Needs Verification"

    hq = len(distinct_sources & HIGH_QUALITY_SOURCES)

    if source_count == 1:
        score = BASE_SINGLE
    elif source_count == 2:
        score = BASE_DOUBLE
    else:
        score = BASE_TRIPLE

    score += hq * HIGH_QUALITY_BONUS
    if direct:
        score += DIRECT_BONUS

    score = round(min(1.0, max(0.0, score)), 2)

    if score >= 0.85:
        status = "Confirmed"
    elif score >= 0.55:
        status = "Likely"
    else:
        status = "Needs Verification"
    return score, status


def status_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "Confirmed"
    if confidence >= 0.55:
        return "Likely"
    return "Needs Verification"