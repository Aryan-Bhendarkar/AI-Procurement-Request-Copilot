"""Deterministic prompt-injection heuristics (policy section 9).

Business data (request text, vendor/catalog/API notes) is untrusted. This detector scans every
free-text field for instruction-like content. It is intentionally a cheap first line of defence:
the LLM judge is a second, and neither can change approvals (the policy engine ignores free text).
"""
from __future__ import annotations

import re
from typing import Any, Iterable

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("override_rules", re.compile(
        r"\b(ignore|disregard|forget|override|bypass|circumvent|skip)\b[^.\n]{0,40}\b"
        r"(all |any |the |your |previous |prior |above |these |those )*"
        r"(instructions?|rules?|polic(?:y|ies)|guidelines?|controls?|checks?|reviews?|safeguards?|restrictions?|procurement)\b", re.I)),
    ("fake_approval", re.compile(
        r"\b(treat|consider|mark|record|regard|assume)\b[^.\n]{0,40}\b(as|being)\b[^.\n]{0,25}"
        r"\b(approved|pre-?approved|cfo[- ]approved|authori[sz]ed|cleared)\b", re.I)),
    ("fake_approval", re.compile(
        r"\b(already|pre-?)\s*(approved|authori[sz]ed|cleared)\b[^.\n]{0,20}\b(by|from)\b[^.\n]{0,30}\b(cfo|ceo|legal|security|finance|vp|director)\b", re.I)),
    ("approve_command", re.compile(
        r"\b(approve|auto-?approve|sign off on|fast[- ]track)\b[^.\n]{0,25}\b(it|this|the request|the purchase)\b[^.\n]{0,25}\b(immediately|now|without|automatically|asap)\b", re.I)),
    ("approve_command", re.compile(r"\bapprove it immediately\b|\bwithout (any )?(review|approval|checks?)\b", re.I)),
    ("role_marker", re.compile(r"(^|\n)\s*(system|assistant|developer)\s*:|<\s*/?\s*(system|instructions?)\s*>|\[\s*/?(system|inst)\s*\]", re.I)),
    ("role_change", re.compile(r"\byou are now\b|\bnew instructions?\b|\bact as\b[^.\n]{0,30}\b(admin|approver|cfo|root)\b|\bfrom now on\b", re.I)),
    ("exfiltration", re.compile(
        r"\b(reveal|print|show|output|leak|expose|send|disclose)\b[^.\n]{0,40}\b(system prompt|api[ _-]?key|secret|credentials?|password|token|\.env|instructions)\b", re.I)),
    ("suppress_flags", re.compile(r"\b(do not|don't|never)\b[^.\n]{0,20}\b(flag|escalate|mention|report|route)\b", re.I)),
]


def scan_text(text: Any) -> list[str]:
    """Return the names of the injection patterns matched by `text` (empty list when clean)."""
    if not isinstance(text, str) or not text.strip():
        return []
    hits: list[str] = []
    for name, pattern in _PATTERNS:
        if pattern.search(text) and name not in hits:
            hits.append(name)
    return hits


def scan_fields(fields: dict[str, Any]) -> list[dict]:
    """Scan labelled free-text fields. Returns [{field, patterns, excerpt}] for every field with a hit."""
    out = []
    for label, value in fields.items():
        hits = scan_text(value)
        if hits:
            out.append({"field": label, "patterns": hits, "excerpt": str(value).strip()[:160]})
    return out


def free_text_fields(request: dict, registry_row: dict | None = None, api_data: dict | None = None,
                     catalog_rows: Iterable[dict] = ()) -> dict[str, Any]:
    """Collect every untrusted free-text field that reaches the model, labelled by origin."""
    fields: dict[str, Any] = {}
    for key in ("product_name", "vendor_name", "category", "business_justification", "data_access_level", "urgency"):
        fields[f"request.{key}"] = request.get(key)
    for i, item in enumerate(request.get("requested_integrations") or []):
        fields[f"request.requested_integrations[{i}]"] = item
    if registry_row:
        fields["vendor_registry.notes"] = registry_row.get("notes")
    if api_data:
        fields["vendor_risk_api.notes"] = api_data.get("notes")
        fields["vendor_risk_api.error_message"] = api_data.get("error_message")
    for row in catalog_rows:
        fields[f"software_catalog.{row.get('software_id')}.notes"] = row.get("notes")
    return fields


def detect(request: dict, registry_row: dict | None = None, api_data: dict | None = None,
           catalog_rows: Iterable[dict] = ()) -> list[dict]:
    return scan_fields(free_text_fields(request, registry_row, api_data, catalog_rows))
