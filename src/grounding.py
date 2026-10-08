"""Evidence construction from tool results, and the grounding validator used by evals."""
from __future__ import annotations

import json
import re

from src.contracts import EvidenceItem, ProcurementDecision

TOOL_FAILURE_MARK = "[TOOL FAILURE]"


def money(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"${value:,.0f}" if float(value).is_integer() else f"${value:,.2f}"


def build_evidence(outputs: dict[str, dict], engine: dict, judgment_notes: list[dict] | None = None,
                   overlap_reason: str | None = None) -> list[EvidenceItem]:
    """Evidence is composed by code from tool outputs (never from model memory).

    `outputs` maps tool name -> latest result; `engine` is the final run_policy_checks result.
    `judgment_notes` are LLM-supplied notes, already validated against the tools actually called.
    """
    items: list[EvidenceItem] = []
    ctx = outputs.get("get_request_context")
    req_id = ""
    if ctx and "request" in ctx:
        r, emp, head = ctx["request"], ctx.get("requester") or {}, ctx.get("department_head")
        req_id = r.get("request_id", "")
        cost = r.get("annual_cost_usd")
        items.append(EvidenceItem(
            source="get_request_context",
            finding=(f"{r.get('product_name')} from {r.get('vendor_name')}: annual cost {money(cost) if cost is not None else 'not provided'}, "
                     f"{r.get('user_count') if r.get('user_count') is not None else 'unspecified'} users, data access "
                     f"{r.get('data_access_level')}; requested by {emp.get('name', 'unknown requester')} "
                     f"({ctx.get('department') or 'unknown department'})"
                     + (f"; department head assumed: {head['name']}" if head else "")),
            reference=req_id))
        budget = ctx.get("department_budget")
        if budget and not any(f["rule"] == "budget" for f in engine.get("findings", [])):
            items.append(EvidenceItem(source="get_request_context",
                                      finding=f"{ctx.get('department')} available software budget is {money(budget.get('available_usd'))}",
                                      reference=f"department_budgets.csv:{ctx.get('department')}"))
    existing = outputs.get("find_existing_software")
    if existing and "candidates" in existing:
        cands = existing["candidates"]
        if cands:
            for c in cands[:4]:
                items.append(EvidenceItem(
                    source="find_existing_software",
                    finding=(f"Existing {c['product_name']} ({c['category']}, {c['scope']} scope, {c['licensed_seats']} seats) "
                             f"matches on {', '.join(c['match_types'])}"),
                    reference=c["software_id"]))
        else:
            items.append(EvidenceItem(source="find_existing_software",
                                      finding="No existing catalog software matches the product, vendor or category",
                                      reference="software_catalog.csv"))
        for h in existing.get("purchase_history", [])[:2]:
            items.append(EvidenceItem(
                source="find_existing_software",
                finding=f"Past purchase {h['purchase_id']} on {h['purchase_date']}: {h['product_name']} {money(h['annual_amount_usd'])}/yr ({h['status']})",
                reference=h["purchase_id"]))
        if overlap_reason:
            ids = ", ".join(c["software_id"] for c in cands) or "software_catalog.csv"
            items.append(EvidenceItem(source="find_existing_software",
                                      finding=f"LLM judgment (overlap cleared): {overlap_reason}", reference=ids))
    vendor = outputs.get("get_vendor_status")
    if vendor:
        reg = vendor.get("registry")
        name = vendor.get("vendor_name")
        if reg:
            items.append(EvidenceItem(
                source="get_vendor_status",
                finding=(f"Registry: {name} procurement {reg['procurement_status']}, security {reg['security_status']} "
                         f"(reviewed {reg['security_review_date'] or 'never'}), legal terms {reg['legal_terms_status']}"),
                reference=f"vendors.csv:{reg['vendor_id']}"))
        else:
            items.append(EvidenceItem(source="get_vendor_status", finding=f"{name} is not in the internal vendor registry",
                                      reference="vendors.csv"))
        risk = vendor.get("vendor_risk_service", {})
        endpoint = f"GET /vendor-risk/{name}"
        if risk.get("status") == "ok":
            d = risk["data"]
            items.append(EvidenceItem(
                source="get_vendor_status",
                finding=(f"Vendor-risk service: risk {d.get('risk_level')}, security review {d.get('security_review_status')} "
                         f"(last review {d.get('last_review_date') or 'never'}), personal data {d.get('processes_personal_data')}, "
                         f"stores data outside region {d.get('stores_data_outside_region')}"),
                reference=endpoint))
        elif risk.get("status") == "not_found":
            items.append(EvidenceItem(source="get_vendor_status",
                                      finding=f"{TOOL_FAILURE_MARK} Vendor-risk service has no record for {name} (404); security status unverified",
                                      reference=endpoint))
        else:
            items.append(EvidenceItem(source="get_vendor_status",
                                      finding=f"{TOOL_FAILURE_MARK} Vendor-risk service unavailable ({risk.get('reason') or 'unknown'}); "
                                              "security status could not be verified and no favourable status was assumed",
                                      reference=endpoint))
    for f in engine.get("findings", []):
        items.append(EvidenceItem(source="run_policy_checks", finding=f["detail"], reference=f"Policy section {f['section']} ({f['rule']})"))
    for hit in engine.get("injection_hits", []):
        items.append(EvidenceItem(
            source="run_policy_checks",
            finding=f"Possible prompt injection in {hit['field']} ({', '.join(hit['patterns'])}): \"{hit['excerpt']}\" - treated as data and ignored",
            reference="Policy section 9"))
    for note in judgment_notes or []:
        items.append(EvidenceItem(source=note["source"], finding=note["finding"], reference=note["reference"]))
    return items


def valid_notes(notes: list, called: set[str]) -> list[dict]:
    """Keep only LLM evidence notes whose source is a tool actually called and that carry a reference."""
    kept = []
    for n in notes or []:
        data = n if isinstance(n, dict) else n.model_dump()
        if data.get("source") in called and str(data.get("reference") or "").strip() and str(data.get("finding") or "").strip():
            kept.append({"source": data["source"], "finding": "LLM note: " + data["finding"].strip(), "reference": data["reference"].strip()})
    return kept


_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> set[float]:
    out = set()
    for m in _NUM.findall(text):
        try:
            out.add(round(float(m.replace(",", "")), 2))
        except ValueError:
            pass
    return out


def validate_grounding(decision: ProcurementDecision, outputs: dict[str, list[dict]], called: list[str]) -> list[str]:
    """Return grounding problems: unknown source, missing reference, or figures/dates absent from tool outputs."""
    problems = []
    haystack = json.dumps(outputs, default=str)
    known = _numbers(haystack)
    called_set = set(called)
    for i, ev in enumerate(decision.evidence):
        if ev.source not in called_set:
            problems.append(f"evidence[{i}] source {ev.source!r} was not called in this run")
        if not (ev.reference or "").strip():
            problems.append(f"evidence[{i}] has no reference")
        # figures: dollar amounts and ISO dates must appear in tool output
        for amount in re.findall(r"\$(\d[\d,]*(?:\.\d+)?)", ev.finding):
            if round(float(amount.replace(",", "")), 2) not in known:
                problems.append(f"evidence[{i}] amount ${amount} not found in tool outputs")
        for iso in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", ev.finding):
            if iso not in haystack:
                problems.append(f"evidence[{i}] date {iso} not found in tool outputs")
    return problems
