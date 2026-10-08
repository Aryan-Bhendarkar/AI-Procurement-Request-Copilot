"""Human hand-off: a review packet addressed to each required approver. It never approves anything."""
from __future__ import annotations

from src.contracts import ProcurementDecision

# approver -> (what they decide, engine rules that explain why they are included)
ROLE_GUIDE: dict[str, tuple[str, set[str]]] = {
    "Manager": ("Confirm the business need for this low-value purchase.", {"approval_threshold"}),
    "Department Head": ("Confirm the business need and that the spend belongs in the department.", {"approval_threshold", "budget"}),
    "Procurement": ("Confirm vendor, pricing and whether existing software should be used first.", {"approval_threshold", "overlap"}),
    "Finance": ("Confirm spend and budget; decide on any budget exception.", {"approval_threshold", "budget"}),
    "CFO": ("Approve spend above $25,000.", {"approval_threshold"}),
    "Security": ("Review vendor security posture and the data/system access requested.",
                 {"security_review", "vendor_review_expired", "conflicting_vendor_evidence", "vendor_risk_unavailable", "vendor_risk_no_record"}),
    "Privacy": ("Review processing of personal data and any out-of-region storage.", {"privacy_review"}),
    "Legal": ("Review contract terms, data-processing and cross-region issues.", {"legal_review"}),
}

NOTICE = ("This packet was prepared by the Procurement Request Copilot. It is a recommendation only. The copilot cannot approve, "
          "purchase, change budgets or accept vendor terms; each approver below decides outside this tool.")


def build_packet(request: dict, decision: ProcurementDecision, engine: dict, requester: dict | None = None,
                 department_head: dict | None = None) -> str:
    findings = engine.get("findings", [])
    lines = [f"# Review packet: {decision.request_id} - {request.get('product_name')}", "", f"> {NOTICE}", ""]
    lines += ["## Summary", f"- **Recommendation:** {decision.recommendation}", f"- **Next step:** {decision.next_step}",
              f"- **Action class:** {decision.next_action_class}",
              f"- **Human review required:** {decision.human_review_required}"]
    if decision.degraded_modes:
        lines.append(f"- **Degraded modes:** {', '.join(decision.degraded_modes)} (some evidence could not be verified)")
    lines += ["", "## Request",
              f"- Requester: {(requester or {}).get('name', request.get('requester_id'))} ({(requester or {}).get('department', 'unknown')})",
              f"- Vendor / product: {request.get('vendor_name')} / {request.get('product_name')}",
              f"- Annual cost: {request.get('annual_cost_usd')}   Users: {request.get('user_count')}",
              f"- Data access: {request.get('data_access_level')}   Integrations: {', '.join(request.get('requested_integrations') or []) or 'none'}",
              f"- Justification (untrusted requester text): {request.get('business_justification')}", ""]
    if decision.missing_information:
        lines += ["## Missing information (blocks routing)"] + [f"- {m}" for m in decision.missing_information] + [""]
    lines += ["## Risk flags"] + ([f"- `{f}`" for f in decision.risk_flags] or ["- none"]) + ["", "## Evidence",
              "| Source | Finding | Reference |", "|---|---|---|"]
    lines += [f"| {e.source} | {e.finding.replace('|', '/')} | {e.reference or ''} |" for e in decision.evidence]
    lines += ["", "## Per-approver sections"]
    if not decision.required_approvals:
        lines += ["No approver can be determined yet. Clarify the missing information first.", ""]
    for role in decision.required_approvals:
        decide, rules = ROLE_GUIDE.get(role, ("Review the request.", set()))
        why = [f["detail"] for f in findings if f["rule"] in rules] or ["Required by policy."]
        who = ""
        if role == "Department Head" and department_head:
            who = f" ({department_head['name']}, assumed - see docs/decisions.md #12)"
        lines += [f"### To: {role}{who}", f"**Decision needed:** {decide}", "**Why you are included:**"] + [f"- {w}" for w in why] + [""]
    lines += ["---", NOTICE]
    return "\n".join(lines)
