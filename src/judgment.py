"""What the LLM is allowed to contribute, and the deterministic text used when it contributes nothing."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from src import policy_engine as pe


_FINDING_KEYS = ("finding", "fact", "note", "text", "detail", "description", "observation", "summary")


def _clean_notes(items) -> list[dict]:
    """Optional evidence notes: salvage what is usable, drop the rest (never fail the whole judgment)."""
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        finding = next((str(it[k]) for k in _FINDING_KEYS if it.get(k)), None)
        if finding and it.get("source") and it.get("reference"):
            out.append({"source": str(it["source"]), "finding": finding, "reference": str(it["reference"])})
    return out


def _clean_strings(items) -> list[str]:
    if isinstance(items, str):
        items = [] if items.strip().lower() in ("", "none", "n/a", "[]") else [items]
    out = []
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict):
            it = "; ".join(f"{k}: {v}" for k, v in it.items())
        if it not in (None, ""):
            out.append(str(it))
    return out


def _lenient(cls, data):
    """Models often emit null / "" / malformed items for optional fields; keep what is usable, default the rest."""
    if not isinstance(data, dict):
        return data
    out = dict(data)
    for name, field in cls.model_fields.items():
        if name not in out:
            continue
        if name in ("evidence_notes", "facts"):
            out[name] = _clean_notes(out[name])
        elif "list[str]" in str(field.annotation):
            out[name] = _clean_strings(out[name])
        elif out[name] in (None, "") and not field.is_required():
            out.pop(name)
        elif "bool" in str(field.annotation) and isinstance(out[name], str):
            out[name] = out[name].strip().lower() in ("true", "yes", "1")
    return out


class EvidenceNote(BaseModel):
    source: str
    finding: str
    reference: str


class Judgment(BaseModel):
    """LLM output. It carries prose and judgments only; approvals, flags and missing info come from the engine."""
    recommendation: str
    next_step: str
    overlap_cleared: bool = False
    overlap_reason: str | None = None
    injection_detected: bool = False
    injection_note: str | None = None
    injection_quote: str | None = None  # verbatim excerpt of the offending text; unverifiable claims are ignored
    legal_issue_identified: bool = False
    legal_issue_reason: str | None = None
    ambiguity_notes: list[str] = Field(default_factory=list)
    evidence_notes: list[EvidenceNote] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)  # staged reviewer: judgments it overruled, with reasons

    @classmethod
    def model_validate(cls, obj, *a, **k):
        return super().model_validate(_lenient(cls, obj), *a, **k)


# Wording that claims an approval or purchase has happened or is authorised. The copilot only recommends.
_OVERREACH = re.compile(
    r"\b(is|are|was|were|has been|have been|been|hereby|now)\s+(hereby\s+)?(approved|authori[sz]ed|purchased|cleared for purchase)\b"
    r"|\b(i|we)\s+(have\s+|hereby\s+)?approv(e|ed)\b|\bauto-?approv|\bapproved (this|the) (request|purchase)\b"
    r"|\b(purchase|order|payment)\s+(has|have|was|is)\s+(been\s+)?(placed|completed|made|processed)\b|\bproceed to purchase\b",
    re.I)


def overreaches(text: str | None) -> bool:
    return bool(text and _OVERREACH.search(text))


def template_recommendation(result: dict, request: dict) -> tuple[str, str]:
    """Deterministic recommendation and next step from the engine result (also the LLM-failure fallback)."""
    action = result["next_action_class"]
    approvals = result["required_approvals"]
    flags = result["risk_flags"]
    missing = result["missing_information"]
    product = request.get("product_name") or "the requested product"
    who = ", ".join(approvals) if approvals else "no approver can be determined yet"
    if action == pe.CLARIFY:
        return (f"Request clarification before review: missing {', '.join(missing)}.",
                f"Return the request to the requester to provide: {', '.join(missing)}. Do not route for approval until complete.")
    if action == pe.ESCALATE_MANUAL:
        reasons = [f for f in flags if f in pe.ESCALATION_FLAGS]
        return (f"Escalate {product} for manual Security review ({', '.join(reasons)}); do not approve until vendor evidence is verified.",
                f"Send the evidence package to Security for manual vendor review, then to: {who}.")
    if action == pe.NEEDS_REVIEWS:
        return (f"Route {product} for the required reviews before any approval ({who}); open flags: {', '.join(flags)}.",
                f"Send the evidence package to: {who}. A human must decide on each flag.")
    return (f"Route {product} for standard approval by {who}.", f"Send the evidence package to: {who} for human approval.")
