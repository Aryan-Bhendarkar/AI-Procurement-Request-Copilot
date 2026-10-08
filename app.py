from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import data_access as da  # noqa: E402
from src import grounding  # noqa: E402
from src.pipeline import RunResult, analyze_request_full  # noqa: E402
from src.review_packet import build_packet  # noqa: E402
from src.tools import ToolContext  # noqa: E402

ARCH_LABELS = {"single": "A - Single agent", "staged": "B - Staged (analyst + reviewer)", "engine": "Engine only (no LLM, reference)"}
DATA_LEVELS = ["none", "internal_marketing", "internal_documents", "production_telemetry", "source_code", "confidential_documents",
               "employee_pii", "customer_pii", "credentials", "unknown"]
FLAG_WHY = {
    "existing_tool_overlap": ("amber", "Existing catalog software may already meet the need (policy s.3)."),
    "budget_unverifiable": ("amber", "No budget record for the requester's department; routed to Finance (s.2)."),
    "budget_insufficient": ("red", "Cost exceeds the department's available software budget (s.2)."),
    "security_review_required": ("red", "Sensitive data/system access or an unverified vendor assessment (s.5)."),
    "privacy_review_required": ("red", "Employee or customer personal data is involved (s.6)."),
    "legal_review_required": ("red", "New vendor over $10k, non-standard terms or cross-region data (s.7)."),
    "vendor_review_expired": ("red", "Vendor security review is older than 365 days at 2026-09-30 (s.5)."),
    "conflicting_vendor_evidence": ("red", "Registry and vendor-risk service disagree; routed to Security (s.5)."),
    "vendor_risk_unavailable": ("red", "Vendor-risk service was unreachable; nothing favourable was assumed (s.10)."),
    "vendor_risk_no_record": ("amber", "Vendor-risk service has no record of this vendor (s.10)."),
    "prompt_injection_detected": ("amber", "Instructions found inside business data were ignored (s.9)."),
    "missing_information": ("amber", "Required request information is missing (s.1)."),
    "llm_unavailable": ("amber", "The model was unavailable; this is a deterministic-only result."),
}
COLORS = {"red": ("#fdecea", "#b3261e"), "amber": ("#fff4e0", "#8a5a00"), "blue": ("#e8f0fe", "#1a4fa3"), "grey": ("#eee", "#444")}

st.set_page_config(page_title="Procurement Request Copilot", layout="wide")


def chip(text: str, tone: str) -> str:
    bg, fg = COLORS[tone]
    return f"<span style='background:{bg};color:{fg};padding:2px 10px;border-radius:12px;margin:2px 6px 2px 0;display:inline-block;font-size:0.85em'>{text}</span>"


@st.cache_data(show_spinner=False)
def reference_data():
    return {"requests": da.load_requests(), "employees": da.load_employees().to_dict("records"),
            "budgets": {r["department"]: r for r in da.load_budgets().to_dict("records")}}


def run_one(request: dict, architecture: str, outage: str) -> RunResult:
    overrides = {"vendor_risk": {"fault": outage}} if outage != "none" else None
    return analyze_request_full(request, architecture, overrides)


def request_card(request: dict, emp: dict | None, budgets: dict) -> None:
    dept = emp["department"] if emp else "unknown"
    avail = budgets.get(dept, {}).get("available_usd")
    st.subheader("Purchase request")
    st.caption("Request text is untrusted business data. The copilot never follows instructions found in it.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Annual cost", f"${request['annual_cost_usd']:,.0f}" if request.get("annual_cost_usd") is not None else "not provided")
    c2.metric("Users", request.get("user_count") if request.get("user_count") is not None else "not provided")
    c3.metric(f"{dept} budget available", f"${avail:,.0f}" if avail is not None else "n/a")
    st.markdown(f"**{request.get('product_name')}** from **{request.get('vendor_name')}** ({request.get('category')})  \n"
                f"Requester: {emp['name'] if emp else request.get('requester_id')} ({dept})  \n"
                f"Data access: `{request.get('data_access_level')}` &nbsp; Integrations: {', '.join(request.get('requested_integrations') or []) or 'none'} "
                f"&nbsp; Urgency: {request.get('urgency')}")
    st.text_area("Business justification (untrusted)", request.get("business_justification") or "", disabled=True, height=90,
                 key=f"just_{request.get('request_id')}")


def decision_panel(res: RunResult, request: dict, emp: dict | None, key: str) -> None:
    d = res.decision
    st.warning("Recommendation only - human approval required. The copilot cannot approve, purchase or change budgets.", icon="⚠️")
    if d.degraded_modes:
        st.error("Degraded mode: " + ", ".join(d.degraded_modes) +
                 ". Some evidence could not be verified or the model was unavailable; nothing favourable was assumed.")
    st.markdown(f"### {d.recommendation}")
    st.markdown(f"**Next step:** {d.next_step}")
    st.markdown(f"**Action class:** `{d.next_action_class}`")
    st.markdown("**Required approvals**")
    st.markdown("".join(chip(a, "blue") for a in d.required_approvals) or "_none can be determined yet_", unsafe_allow_html=True)
    st.markdown("**Risk flags**")
    for f in d.risk_flags:
        tone, why = FLAG_WHY.get(f, ("grey", ""))
        st.markdown(chip(f, tone) + f"<span style='font-size:0.85em'>{why}</span>", unsafe_allow_html=True)
    if not d.risk_flags:
        st.caption("none")
    if d.missing_information:
        st.markdown("**Missing information**")
        for m in d.missing_information:
            st.markdown(f"- {m}")
    st.markdown("**Evidence**")
    rows = [{"": "⚠️" if grounding.TOOL_FAILURE_MARK in e.finding else "", "source": e.source,
             "finding": e.finding.replace(grounding.TOOL_FAILURE_MARK, "").strip(), "reference": e.reference} for e in d.evidence]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if res.grounding_problems:
        st.caption("Grounding check: " + "; ".join(res.grounding_problems))
    else:
        st.caption("Grounding check passed: every evidence item cites a tool called in this run.")
    t = d.telemetry
    m = st.columns(5)
    m[0].metric("Latency", f"{t.latency_ms / 1000:.1f}s")
    m[1].metric("LLM calls", t.llm_calls)
    m[2].metric("Tool calls", t.tool_calls)
    m[3].metric("Tokens", (t.prompt_tokens or 0) + (t.completion_tokens or 0))
    m[4].metric("Cost", f"${t.cost_usd:.4f}" if t.cost_usd else "n/a")
    st.caption("Tools: " + (" > ".join(t.tool_names) or "none") + (f" | model: {t.model}" if t.model else ""))
    with st.expander("Prepare review packet (human hand-off)"):
        if st.button("Prepare review packet", key=f"pk_{key}"):
            ctx = ToolContext(request)
            head = ctx.department_head(emp)
            md = build_packet(request, d, res.engine, emp, head)
            st.session_state[f"packet_{key}"] = md
        md = st.session_state.get(f"packet_{key}")
        if md:
            st.download_button("Download packet (.md)", md, file_name=f"review_packet_{d.request_id}.md", key=f"dl_md_{key}")
            st.download_button("Download decision (.json)", json.dumps(d.model_dump(), indent=2), file_name=f"decision_{d.request_id}.json",
                               key=f"dl_js_{key}")
            st.markdown(md)
    with st.expander("Raw decision JSON"):
        st.json(d.model_dump())


def custom_form(data: dict) -> dict | None:
    emps = {f"{e['name']} ({e['department']})": e["employee_id"] for e in data["employees"]}
    with st.sidebar.form("custom"):
        who = st.selectbox("Requester", list(emps))
        product = st.text_input("Product", "Acme Notes")
        vendor = st.text_input("Vendor", "Acme")
        category = st.text_input("Category", "Knowledge Management")
        cost = st.text_input("Annual cost USD (blank = missing)", "5000")
        users = st.text_input("Users (blank = missing)", "10")
        level = st.selectbox("Data access level", DATA_LEVELS, index=1)
        integ = st.text_input("Integrations (comma separated)", "")
        just = st.text_area("Business justification", "Team wiki for onboarding documents.")
        urgency = st.selectbox("Urgency", ["normal", "high", "urgent"])
        submitted = st.form_submit_button("Use this request")
    if submitted or "custom_req" in st.session_state:
        if submitted:
            try:
                c = float(cost.replace(",", "")) if cost.strip() else None
                u = int(users) if users.strip() else None
            except ValueError:
                st.sidebar.error("Cost must be a number and users an integer.")
                return st.session_state.get("custom_req")
            st.session_state["custom_req"] = {
                "request_id": "REQ-CUSTOM", "requester_id": emps[who], "product_name": product, "vendor_name": vendor,
                "category": category, "annual_cost_usd": c, "user_count": u, "business_justification": just,
                "data_access_level": level, "requested_integrations": [i.strip() for i in integ.split(",") if i.strip()], "urgency": urgency}
        return st.session_state.get("custom_req")
    return None


def main() -> None:
    data = reference_data()
    employees = {e["employee_id"]: e for e in data["employees"]}
    st.title("AI Procurement Request Copilot")
    st.caption("Gathers evidence with tools, applies deterministic policy rules, and recommends the next action. Humans approve.")

    mode = st.sidebar.radio("Request source", ["Dataset request", "Custom request"], horizontal=True)
    if mode == "Dataset request":
        by_id = {r["request_id"]: r for r in data["requests"]}
        rid = st.sidebar.selectbox("Request", list(by_id), format_func=lambda r: f"{r} - {by_id[r]['product_name']}")
        request = by_id[rid]
    else:
        request = custom_form(data)
    compare = st.sidebar.checkbox("Compare A vs B side by side")
    architecture = st.sidebar.radio("Architecture", list(ARCH_LABELS), format_func=ARCH_LABELS.get, disabled=compare)
    outage = st.sidebar.selectbox("Simulate vendor-risk service fault", ["none", "503", "timeout", "404"],
                                  help="Fault injection for demos: replaces the live vendor-risk call with a failure.")
    run = st.sidebar.button("Run analysis", type="primary", use_container_width=True, disabled=request is None)

    if request is None:
        st.info("Fill in the custom request form in the sidebar and press 'Use this request'.")
        return
    emp = employees.get(request.get("requester_id"))
    request_card(request, emp, data["budgets"])
    st.divider()

    sig = (request.get("request_id"), json.dumps(request, sort_keys=True), architecture, compare, outage)
    if run:
        archs = ["single", "staged"] if compare else [architecture]
        try:
            with st.spinner("Gathering evidence and applying policy ..."):
                with ThreadPoolExecutor(max_workers=len(archs)) as pool:
                    results = list(pool.map(lambda a: run_one(request, a, outage), archs))
            st.session_state["last"] = {"sig": sig, "archs": archs, "results": results}
        except Exception as exc:  # last-resort guard so the UI never shows a stack trace
            st.error(f"The analysis could not be completed ({type(exc).__name__}). Try again or use the engine-only option. Details: {str(exc)[:200]}")
            return
    last = st.session_state.get("last")
    if not last or last["sig"] != sig:
        st.info("Press 'Run analysis' to see the recommendation.")
        return
    if len(last["archs"]) == 1:
        decision_panel(last["results"][0], request, emp, last["archs"][0])
    else:
        cols = st.columns(2, gap="large")
        for col, arch, res in zip(cols, last["archs"], last["results"]):
            with col:
                st.subheader(ARCH_LABELS[arch])
                decision_panel(res, request, emp, arch)
        a, b = (r.decision for r in last["results"])
        same = (a.required_approvals == b.required_approvals, set(a.risk_flags) == set(b.risk_flags))
        st.success("A and B agree on approvals and flags (the engine owns both)." if all(same) else
                   "A and B differ: approvals identical = %s, flags identical = %s" % same)


main()
