"""AI service module.

Provider-agnostic LLM wrapper. When an API key is configured it sends the
investigation's evidence to the model with a strict "grounded in evidence"
system prompt. When no key is configured (or the call fails) it falls back to
a deterministic summarizer so the platform stays fully functional offline.

Configuration (environment variables):
    HAMRABI_AI_PROVIDER  - one of: openai, anthropic, none (default: none)
    HAMRABI_AI_MODEL     - model id (e.g. gpt-4o-mini, claude-3-5-haiku-...)
    OPENAI_API_KEY      - OpenAI API key
    ANTHROPIC_API_KEY   - Anthropic API key
"""
import json
import os

import httpx

from app.core.config import REQUEST_TIMEOUT
from app.models.entities import Investigation

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
}


class AIClient:
    def __init__(self):
        self.provider = os.getenv("HAMRABI_AI_PROVIDER", "none").strip()
        self.model = os.getenv("HAMRABI_AI_MODEL") or _DEFAULT_MODELS.get(self.provider, "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def enabled(self) -> bool:
        if self.provider == "openai":
            return bool(self.openai_key)
        if self.provider == "anthropic":
            return bool(self.anthropic_key)
        return False

    def summarize(self, inv: Investigation) -> str:
        if not self.enabled:
            return deterministic_summary(inv)
        try:
            return self._chat(SYSTEM_PROMPT, _build_context(inv),
                              "Write an executive summary of this investigation. "
                              "Do not invent facts not present in the evidence.")
        except Exception:
            return deterministic_summary(inv)

    def classify(self, inv: Investigation) -> str:
        if not self.enabled:
            return deterministic_classify(inv)
        try:
            return self._chat(SYSTEM_PROMPT, _build_context(inv),
                              "Classify this investigation into one single word: "
                              "infrastructure, person, reputation, incident, "
                              "osint_research or other. Base it only on the evidence.")
        except Exception:
            return deterministic_classify(inv)

    def classify_comments(self, comments: list[str]) -> list[str] | None:
        """Classify comments as positive/negative/neutral. Offline -> rules."""
        if not self.enabled:
            return None
        try:
            payload = "\n".join(f"{i}. {c}" for i, c in enumerate(comments))
            label_line = self._chat(
                SYSTEM_PROMPT,
                "COMMENTS TO CLASSIFY:\n" + payload[:6000],
                "Return a single label per comment (one per line, in order) "
                "using exactly one of: positive, negative, neutral. "
                "Output only the labels, no bullets or numbering.",
            )
            labels = [ln.strip().lower() for ln in label_line.splitlines() if ln.strip()]
            labels = [l for l in labels if l in ("positive", "negative", "neutral")]
            if not labels:
                return None
            return labels
        except Exception:
            return None

    def explain(self, inv: Investigation, relationship) -> str:
        if not self.enabled:
            return deterministic_explain(inv, relationship)
        try:
            ctx = _build_context(inv) + (
                f"\n\nRelationship under analysis: source={relationship.source_id} "
                f"relation={relationship.relation} target={relationship.target_id}")
            return self._chat(SYSTEM_PROMPT, ctx,
                              "Explain how these two entities are connected using the "
                              "evidence only. If no evidence supports the link, say so.")
        except Exception:
            return deterministic_explain(inv, relationship)

    # ---- provider backends -------------------------------------------------

    def _chat(self, system: str, context: str, user: str) -> str:
        if self.provider == "openai":
            return self._chat_openai(system, context, user)
        if self.provider == "anthropic":
            return self._chat_anthropic(system, context, user)
        raise RuntimeError(f"unsupported provider: {self.provider}")

    def _chat_openai(self, system, context, user) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}"}
        body = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system + "\n\nEvidence:\n" + context},
                {"role": "user", "content": user},
            ],
        }
        resp = httpx.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT * 2)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _chat_anthropic(self, system, context, user) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": 400,
            "system": system,
            "messages": [{"role": "user", "content": f"Evidence:\n{context}\n\n{user}"}],
        }
        resp = httpx.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT * 2)
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


SYSTEM_PROMPT = (
    "You are an OSINT evidence analyst embedded in a lawful OSINT research "
    "platform. Your answers MUST be grounded exclusively in the provided "
    "evidence. Never invent names, addresses, figures, or conclusions that "
    "are not present in the evidence. When evidence is missing, state that "
    "verification is needed. Be concise, neutral and factual."
)


def _build_context(inv: Investigation) -> str:
    lines = [
        f"Target: {inv.raw_input} (type: {inv.input_type})",
        f"Entities ({len(inv.entities)}):",
    ]
    for e in inv.entities:
        lines.append(f"  - {e.type}: {e.value}")
    lines.append(f"\nFindings ({len(inv.findings)}):")
    for f in inv.findings:
        snippet = json.dumps(f.value)[:500]
        lines.append(f"  - [{f.source}] {f.key} conf={f.confidence} "
                     f"evidence={f.evidence_count} data={snippet}")
    lines.append(f"\nRelationships ({len(inv.relationships)}):")
    for r in inv.relationships:
        lines.append(f"  - {r.source_id[:8]} --({r.relation})-> {r.target_id[:8]} "
                     f"conf={r.confidence}")
    return "\n".join(lines)


# ---- deterministic offline fallbacks ----------------------------------------


def deterministic_summary(inv: Investigation) -> str:
    n_ent = len(inv.entities)
    n_find = len(inv.findings)
    n_links = len(inv.relationships)
    top = max((f.confidence for f in inv.findings), default=0.0)
    srcs = sorted({f.source for f in inv.findings})

    text = (
        f"Investigation focused on '{inv.raw_input}' ({inv.input_type}). "
        f"The pipeline extracted {n_ent} entities"
        + (": " + ", ".join(f"{e.type} {e.value}" for e in inv.entities) if n_ent else ".")
        + f" It gathered {n_find} evidence-recorded findings"
        + (f" from {', '.join(srcs)}" if srcs else ".")
        + f" Maximum evidence confidence: {top:.0%}."
    )
    if n_links:
        text += f" The correlation engine built {n_links} relationship(s) between entities."
    else:
        text += " No correlations were derived between entities."
    return text


def deterministic_explain(inv, relationship) -> str:
    s = next((e.value for e in inv.entities if e.id == relationship.source_id),
             relationship.source_id)
    t = next((e.value for e in inv.entities if e.id == relationship.target_id),
             relationship.target_id)
    if relationship.relation == "uses_domain":
        return (f"'{s}' is an e-mail address whose domain part is '{t}'. They are "
                "linked because e-mail delivery routes through that domain.")
    if relationship.relation.startswith("linked_by_"):
        return (f"'{s}' and '{t}' co-occur in a finding produced by the "
                f"'{relationship.relation.replace('linked_by_', '')}' source.")
    return (f"'{s}' is connected to '{t}' through the "
            f"'{relationship.relation}' relation "
            f"with confidence {relationship.confidence:.0%}.")


def deterministic_classify(inv: Investigation) -> str:
    types = {e.type for e in inv.entities}
    if types & {"domain", "url", "ip"}:
        return "infrastructure"
    if types & {"email", "username"}:
        return "person"
    return "osint_research"