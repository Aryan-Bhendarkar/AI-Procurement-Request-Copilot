"""Deterministic procurement policy engine (policy version 2026.09).

Pure functions only: no LLM, no network, no file or clock access. Callers load the
data (employee, budget, vendor registry row, catalog rows, vendor-risk API result)
and pass it in as plain dicts. All date logic uses REFERENCE_DATE, never today's date.

Judgment calls stay outside this module. The LLM may supply two optional inputs,
`overlap_judgment` and `legal_issue_identified`, plus `injection_detected`.
It can never set approvals, thresholds, or budget results.

Assumption: the data has no "Department Head" field (employees.csv only has
manager_id), so "Department Head" is emitted as a role name for the requester's
department and is not resolved to a person.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

REFERENCE_DATE = date(2026, 9, 30)
REVIEW_VALIDITY_DAYS = 365
LEGAL_NEW_VENDOR_THRESHOLD = Decimal("10000")

MANAGER = "Manager"
DEPARTMENT_HEAD = "Department Head"
PROCUREMENT = "Procurement"
FINANCE = "Finance"
CFO = "CFO"
SECURITY = "Security"
PRIVACY = "Privacy"
LEGAL = "Legal"

# Next-action classes (deterministic).
APPROVE_PATH = "approve_path"  # only business approvals needed
NEEDS_REVIEWS = "needs_reviews"  # Security/Privacy/Legal/Finance-exception/overlap review needed
CLARIFY = "clarify"  # required information missing
ESCALATE_MANUAL = "escalate_manual"  # vendor evidence missing/conflicting/expired: manual Security review
ESCALATION_FLAGS = {"vendor_risk_unavailable", "vendor_risk_no_record", "conflicting_vendor_evidence", "vendor_review_expired"}
REVIEW_FLAGS = {"security_review_required", "privacy_review_required", "legal_review_required",
                "budget_insufficient", "budget_unverifiable", "existing_tool_overlap", "prompt_injection_detected"}
SAFE_DATA_PREFIXES = ("none", "public", "internal")  # any other unrecognised level fails closed to Security review


def next_action_class(missing: list[str], flags: list[str]) -> str:
    if missing:
        return CLARIFY
    if ESCALATION_FLAGS & set(flags):
        return ESCALATE_MANUAL
    if REVIEW_FLAGS & set(flags):
        return NEEDS_REVIEWS
    return APPROVE_PATH

# data_access_level values (and integration keywords) that trigger reviews. Policy sections 5 and 6.
SECURITY_DATA_LEVELS = {"source_code", "confidential_documents", "employee_pii", "customer_pii", "credentials", "secrets"}
PRIVACY_DATA_LEVELS = {"employee_pii", "customer_pii"}
SENSITIVE_DATA_LEVELS = SECURITY_DATA_LEVELS
PRODUCTION_KEYWORDS = ("production", "cloud account", "cloud-account")
UNKNOWN_DATA_LEVELS = {"", "unknown", "none_specified", "tbd"}

# Vendor-risk API outcomes.
RISK_OK = "ok"
RISK_NOT_FOUND = "not_found"  # HTTP 404: the service has no record for this vendor
RISK_UNAVAILABLE = "unavailable"  # HTTP 5xx, timeout, or connection error


def vendor_risk_ok(data: dict) -> dict:
    return {"status": RISK_OK, "data": data}


def vendor_risk_not_found() -> dict:
    return {"status": RISK_NOT_FOUND}


def vendor_risk_unavailable(reason: str = "") -> dict:
    return {"status": RISK_UNAVAILABLE, "reason": reason}


@dataclass
class Finding:
    rule: str  # short rule id
    section: str  # policy section
    detail: str  # factual, citable sentence


@dataclass
class PolicyResult:
    annual_cost_usd: float | None
    required_approvals: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    overlap_candidates: list[dict] = field(default_factory=list)
    budget: dict = field(default_factory=dict)
    vendor_security: dict = field(default_factory=dict)
    ready_for_approval_routing: bool = False
    next_action_class: str = "approve_path"
    human_review_required: bool = True  # always True: the copilot only recommends

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- helpers

def _blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):  # pandas NaN
        return True
    return isinstance(value, str) and not value.strip()


def _to_decimal(value: Any) -> Decimal | None:
    if _blank(value) or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def _to_date(value: Any) -> date | None:
    if _blank(value):
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def _norm(value: Any) -> str:
    return "" if _blank(value) else str(value).strip().lower()


def _level(value: Any) -> str:
    """Normalise a data access level: 'Source Code' / 'customer-PII' -> 'source_code' / 'customer_pii'."""
    return re.sub(r"[^a-z0-9]+", "_", _norm(value)).strip("_")


def _integrations(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [str(i) for i in value] if isinstance(value, (list, tuple)) else []


def approvals_for_amount(annual_cost: Any) -> list[str]:
    """Policy section 4. Boundaries are inclusive on the upper side: 1000.00 -> Manager."""
    amount = _to_decimal(annual_cost)
    if amount is None:
        return []
    if amount <= Decimal("1000"):
        return [MANAGER]
    if amount <= Decimal("10000"):
        return [DEPARTMENT_HEAD, PROCUREMENT]
    if amount <= Decimal("25000"):
        return [DEPARTMENT_HEAD, FINANCE, PROCUREMENT]
    return [DEPARTMENT_HEAD, FINANCE, CFO, PROCUREMENT]


def check_budget(annual_cost: Any, budget_row: dict | None) -> dict:
    """Policy section 2. status is one of: sufficient, insufficient, unknown."""
    amount = _to_decimal(annual_cost)
    available = _to_decimal((budget_row or {}).get("available_usd"))
    if amount is None or available is None:
        return {"status": "unknown", "available_usd": None if available is None else float(available),
                "shortfall_usd": None}
    if amount > available:
        return {"status": "insufficient", "available_usd": float(available), "shortfall_usd": float(amount - available)}
    return {"status": "sufficient", "available_usd": float(available), "shortfall_usd": 0.0}


def review_currency(review_date: Any, reference: date = REFERENCE_DATE) -> dict:
    """Policy section 5: an assessment is current for 365 days from its review date.

    currency: current | expired | missing. days_old is None when there is no valid date.
    """
    reviewed = _to_date(review_date)
    if reviewed is None or reviewed > reference:  # a review dated after the snapshot is not trusted as current
        return {"currency": "missing", "review_date": None, "days_old": None, "expires_on": None}
    expires = reviewed + timedelta(days=REVIEW_VALIDITY_DAYS)
    return {
        "currency": "current" if reference <= expires else "expired",
        "review_date": reviewed.isoformat(),
        "days_old": (reference - reviewed).days,
        "expires_on": expires.isoformat(),
    }


def find_overlap(request: dict, catalog: list[dict]) -> list[dict]:
    """Policy section 3: candidate existing software (same product, vendor, or category).

    Candidates only. Whether one credibly covers the use case is a judgment for the caller.
    """
    product, vendor, category = (_norm(request.get(k)) for k in ("product_name", "vendor_name", "category"))
    candidates = []
    for item in catalog:
        match_types = []
        if product and _norm(item.get("product_name")) == product:
            match_types.append("same_product")
        if vendor and _norm(item.get("vendor_name")) == vendor:
            match_types.append("same_vendor")
        if category and _norm(item.get("category")) == category:
            match_types.append("same_category")
        if match_types:
            candidates.append({
                "software_id": item.get("software_id"),
                "product_name": item.get("product_name"),
                "vendor_name": item.get("vendor_name"),
                "category": item.get("category"),
                "scope": item.get("scope"),
                "licensed_seats": item.get("licensed_seats"),
                "match_types": match_types,
            })
    return candidates


def _status_bucket(value: Any) -> str:
    """Collapse registry/API security wording to approved | expired | not_completed."""
    text = _norm(value)
    if text == "approved":
        return "approved"
    if text == "expired":
        return "expired"
    return "not_completed"  # pending, not_completed, unknown, blank


def assess_vendor_security(registry_row: dict | None, risk_result: dict | None,
                           reference: date = REFERENCE_DATE) -> dict:
    """Combine the internal registry and the vendor-risk API (policy section 5 and 10)."""
    risk_result = risk_result or vendor_risk_unavailable("not queried")
    api_status = risk_result.get("status")
    api = risk_result.get("data", {}) if api_status == RISK_OK else {}

    reg_currency = review_currency((registry_row or {}).get("security_review_date"), reference)
    api_currency = review_currency(api.get("last_review_date"), reference)

    reg_bucket = _status_bucket((registry_row or {}).get("security_status")) if registry_row else None
    api_bucket = _status_bucket(api.get("security_review_status")) if api_status == RISK_OK else None

    conflict = False
    conflict_detail = None
    if reg_bucket is not None and api_bucket is not None:
        if reg_bucket != api_bucket:
            conflict = True
            conflict_detail = (f"registry security_status={registry_row.get('security_status')!r} vs "
                               f"vendor-risk service security_review_status={api.get('security_review_status')!r}")
        elif (reg_currency["review_date"] and api_currency["review_date"]
              and reg_currency["review_date"] != api_currency["review_date"]):
            conflict = True
            conflict_detail = (f"registry review date {reg_currency['review_date']} vs "
                               f"vendor-risk service review date {api_currency['review_date']}")

    # Current only if every available source says approved and within 365 days.
    sources_current = []
    if registry_row:
        sources_current.append(reg_bucket == "approved" and reg_currency["currency"] == "current")
    if api_status == RISK_OK:
        sources_current.append(api_bucket == "approved" and api_currency["currency"] == "current")
    assessment_current = bool(sources_current) and all(sources_current)

    expired = (reg_currency["currency"] == "expired" or api_currency["currency"] == "expired"
               or reg_bucket == "expired" or api_bucket == "expired")

    return {
        "registry": {"status": reg_bucket, **reg_currency} if registry_row else None,
        "vendor_risk_service": ({"status": api_bucket, "risk_level": api.get("risk_level"), **api_currency}
                                if api_status == RISK_OK else {"status": api_status, "reason": risk_result.get("reason")}),
        "assessment_current": assessment_current,
        "expired": expired,
        "conflict": conflict,
        "conflict_detail": conflict_detail,
        "risk_service_status": api_status,
        "processes_personal_data": api.get("processes_personal_data"),
        "stores_data_outside_region": api.get("stores_data_outside_region"),
    }


def missing_request_fields(request: dict, employee: dict | None) -> list[str]:
    """Policy section 1. Returns human-readable names of missing or unusable fields."""
    missing = []
    if not employee:
        missing.append("requester")
    elif _blank(employee.get("department")):
        missing.append("department")
    if _blank(request.get("product_name")):
        missing.append("product name")
    if _blank(request.get("vendor_name")):
        missing.append("vendor")
    if _to_decimal(request.get("annual_cost_usd")) is None:
        missing.append("annual cost")
    users = request.get("user_count")
    if _blank(users) or isinstance(users, bool) or not isinstance(users, (int, float)) or not math.isfinite(users) or users <= 0:
        missing.append("user count (seats/licenses)")
    if _blank(request.get("business_justification")):
        missing.append("business purpose")
    if _level(request.get("data_access_level")) in UNKNOWN_DATA_LEVELS:
        missing.append("data access level")
    if request.get("requested_integrations") is None:  # an empty list means "none" and is valid
        missing.append("required integrations")
    return missing


# ---------------------------------------------------------------- main entry point

def run_policy_checks(
    request: dict,
    employee: dict | None,
    budget_row: dict | None,
    registry_row: dict | None,
    risk_result: dict | None,
    catalog: list[dict],
    *,
    overlap_judgment: bool | None = None,
    overlap_reason: str | None = None,
    legal_issue_identified: bool = False,
    injection_detected: bool = False,
    reference: date = REFERENCE_DATE,
) -> PolicyResult:
    """Apply every deterministic rule in the policy and return approvals, flags and findings.

    overlap_judgment: None -> flag whenever any overlap candidate exists (conservative);
        False -> caller judged the candidates do not cover the request (e.g. a seat expansion
        of the same product); True -> they do. A False judgment only clears the flag when a
        non-empty overlap_reason is given; otherwise it is ignored. Request text is never read here.
    legal_issue_identified: caller found a material data-processing or cross-region issue (section 7).
    injection_detected: caller found instructions embedded in business data (section 9).
    """
    cost = _to_decimal(request.get("annual_cost_usd"))
    result = PolicyResult(annual_cost_usd=None if cost is None else float(cost))
    approvals: set[str] = set()
    flags: list[str] = []

    def flag(name: str) -> None:
        if name not in flags:
            flags.append(name)

    def add(rule: str, section: str, detail: str) -> None:
        result.findings.append(Finding(rule, section, detail))

    # Section 1: required information
    result.missing_information = missing_request_fields(request, employee)
    if result.missing_information:
        flag("missing_information")
        add("missing_information", "1", "Missing or unusable request fields: " + ", ".join(result.missing_information))

    # Section 4: financial thresholds
    amount_approvals = approvals_for_amount(cost)
    approvals.update(amount_approvals)
    if amount_approvals:
        add("approval_threshold", "4", f"Annual cost ${cost:,.2f} requires: {', '.join(amount_approvals)}")

    # Section 2: budget
    department = (employee or {}).get("department")
    result.budget = check_budget(cost, budget_row)
    result.budget["department"] = None if _blank(department) else department
    if result.budget["status"] == "insufficient":
        flag("budget_insufficient")
        approvals.add(FINANCE)
        add("budget", "2", f"Cost ${cost:,.2f} exceeds {department} available software budget "
                           f"${result.budget['available_usd']:,.2f} (shortfall ${result.budget['shortfall_usd']:,.2f}); "
                           "Finance budget-exception review needed")
    elif result.budget["status"] == "sufficient":
        add("budget", "2", f"Cost ${cost:,.2f} is within {department} available software budget "
                           f"${result.budget['available_usd']:,.2f}. This does not imply approval.")
    elif cost is not None:
        flag("budget_unverifiable")  # Finance owns the budget record, so route to Finance instead of asking the requester
        approvals.add(FINANCE)
        add("budget", "2", f"No usable budget record for department {department!r}; budget check not possible, routed to Finance")

    # Section 3: overlap
    result.overlap_candidates = find_overlap(request, catalog)
    if result.overlap_candidates:
        names = ", ".join(f"{c['product_name']} ({'/'.join(c['match_types'])})" for c in result.overlap_candidates)
        reason = (overlap_reason or "").strip()
        # Code gate: a clear is honoured only when every candidate is from the same vendor (add-on, expansion or other
        # service from a vendor we already use). A different vendor's product in the same category can never be cleared.
        clearable = all("same_vendor" in c["match_types"] for c in result.overlap_candidates)
        if overlap_judgment is False and reason and not clearable:
            add("overlap_clear_rejected", "3", f"Attempt to clear overlap rejected: candidates include other vendors' products. Reason offered: {reason}")
        if overlap_judgment is False and reason and clearable:
            add("overlap_cleared", "3", f"Overlap candidates ({names}) judged not to block the request. Reviewer reason: {reason}")
        else:
            flag("existing_tool_overlap")
            add("overlap", "3", f"Existing catalog software to review before a new purchase: {names}")

    # Vendor evidence
    data_level = _level(request.get("data_access_level"))
    integrations = " ".join(_norm(i) for i in _integrations(request.get("requested_integrations")))
    is_new_vendor = registry_row is None or _norm(registry_row.get("procurement_status")) == "new"
    sec = assess_vendor_security(registry_row, risk_result, reference)
    result.vendor_security = sec

    if sec["risk_service_status"] == RISK_UNAVAILABLE:
        flag("vendor_risk_unavailable")
        add("vendor_risk_unavailable", "10", "Vendor-risk service could not be reached "
            f"({(risk_result or {}).get('reason') or 'no detail'}); security status not independently verified. "
            "No favorable status inferred.")
    elif sec["risk_service_status"] == RISK_NOT_FOUND:
        flag("vendor_risk_no_record")
        add("vendor_risk_no_record", "10", "Vendor-risk service has no record for this vendor (404, not an outage).")
    if sec["expired"]:
        flag("vendor_review_expired")
        dates = [s["review_date"] for s in (sec["registry"], sec["vendor_risk_service"])
                 if s and s.get("review_date")]
        add("vendor_review_expired", "5", f"Vendor security review is older than {REVIEW_VALIDITY_DAYS} days "
            f"as of {reference.isoformat()} (review date {dates[0] if dates else 'n/a'})")
    if sec["conflict"]:
        flag("conflicting_vendor_evidence")
        add("conflicting_vendor_evidence", "5", "Registry and vendor-risk service disagree: " + sec["conflict_detail"]
            + ". Routed to Security/manual review; neither source was chosen.")

    # Section 5: security review
    security_reasons = []
    if data_level in SECURITY_DATA_LEVELS:
        security_reasons.append(f"data access level {data_level}")
    if (data_level and data_level not in SECURITY_DATA_LEVELS and data_level not in UNKNOWN_DATA_LEVELS
            and not data_level.startswith(SAFE_DATA_PREFIXES + ("production",))):
        security_reasons.append(f"unrecognised data access level {data_level!r} (fails closed)")
    if data_level.startswith("production") or any(k in integrations for k in PRODUCTION_KEYWORDS):
        security_reasons.append("production or cloud-account access")
    if not sec["assessment_current"]:
        security_reasons.append("vendor security assessment is missing, expired, or not completed")
    if sec["conflict"]:
        security_reasons.append("conflicting vendor evidence")
    if sec["risk_service_status"] == RISK_UNAVAILABLE:
        security_reasons.append("vendor-risk service unavailable, so the registry cannot be corroborated")
    if sec["risk_service_status"] == RISK_NOT_FOUND:
        security_reasons.append("vendor-risk service has no record, so the registry cannot be corroborated")
    if security_reasons:
        approvals.add(SECURITY)
        flag("security_review_required")
        add("security_review", "5", "Security review required: " + "; ".join(security_reasons))

    # Section 6: privacy review
    privacy_reasons = []
    if data_level in PRIVACY_DATA_LEVELS:
        privacy_reasons.append(f"processes {data_level.replace('_', ' ')}")
    if sec["stores_data_outside_region"] is True and data_level in SENSITIVE_DATA_LEVELS:
        privacy_reasons.append("sensitive data may be stored outside the operating region")
    if privacy_reasons:
        approvals.add(PRIVACY)
        flag("privacy_review_required")
        add("privacy_review", "6", "Privacy review required: " + "; ".join(privacy_reasons))

    # Section 7: legal review
    legal_reasons = []
    if is_new_vendor and cost is not None and cost >= LEGAL_NEW_VENDOR_THRESHOLD:
        legal_reasons.append(f"new vendor with annual spend ${cost:,.2f} >= $10,000")
    terms = _norm((registry_row or {}).get("legal_terms_status"))
    if terms != "approved":
        legal_reasons.append(f"legal terms not already approved (status: {terms or 'no registry record'})")
    if sec["stores_data_outside_region"] is True and data_level in PRIVACY_DATA_LEVELS:
        legal_reasons.append(f"vendor stores data outside the operating region and request involves {data_level.replace('_', ' ')} "
                             "(cross-region data-processing issue, sections 7 and 8)")
    if legal_issue_identified and not result.missing_information:  # no model-driven approvals on an incomplete request
        legal_reasons.append("material data-processing or cross-region issue identified")
    if legal_reasons:
        approvals.add(LEGAL)
        flag("legal_review_required")
        add("legal_review", "7", "Legal review required: " + "; ".join(legal_reasons))

    # Section 9
    if injection_detected:
        flag("prompt_injection_detected")
        add("prompt_injection", "9", "Request text contained instructions aimed at the copilot; ignored and treated as data.")

    order = [MANAGER, DEPARTMENT_HEAD, FINANCE, CFO, PROCUREMENT, SECURITY, PRIVACY, LEGAL]
    result.required_approvals = [a for a in order if a in approvals]
    result.risk_flags = flags
    result.ready_for_approval_routing = not result.missing_information
    result.next_action_class = next_action_class(result.missing_information, flags)
    return result
