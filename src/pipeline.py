"""Orchestration shared by both architectures: run the agent(s), then merge authoritatively.

Merge rule: approvals, risk flags and missing information ALWAYS come from the deterministic engine.
The LLM contributes the recommendation / next-step wording, judgments (overlap, injection, legal) and evidence notes.
If the LLM is unavailable or returns unusable output, a deterministic decision is returned and marked degraded.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from src import grounding
from src import policy_engine as pe
from src import tools as T
from src.contracts import Architecture, ProcurementDecision, RunTelemetry
from src.judgment import Judgment, overreaches, template_recommendation
from src.llm import LLMClient, LLMUnavailable
from src.vendor_client import ensure_local_mock_api


@dataclass
class RunResult:
    decision: ProcurementDecision
    engine: dict
    tool_outputs: dict[str, list[dict]]
    tool_calls: list[T.ToolCall]
    judgment: Judgment | None
    degraded: list[str]
    grounding_problems: list[str]
    stage_trace: dict = field(default_factory=dict)
    llm_error: str | None = None


def _injection_verified(ctx: T.ToolContext, j: Judgment | None) -> bool:
    """A model-reported injection counts only if its quote appears verbatim in the untrusted data it was given."""
    quote = " ".join((j.injection_quote or "").lower().split()) if j else ""
    if not (j and j.injection_detected and len(quote) >= 8):
        return False
    corpus = " ".join(json.dumps([ctx.request, ctx.registry_row(ctx.request.get("vendor_name")),
                                  ctx.vendor_risk(str(ctx.request.get("vendor_name") or "")), ctx.sources.catalog], default=str).lower().split())
    return quote in corpus


def _gap_fill(ctx: T.ToolContext) -> None:
    """Code guarantees the evidence tools ran, whatever the model decided."""
    for name in T.EVIDENCE_TOOLS:
        if not ctx.called(name):
            args = {"vendor_name": ctx.request.get("vendor_name")} if name == "get_vendor_status" else {"request_id": ctx.request_id}
            ctx.dispatch(name, args, by="code")


def finalize(ctx: T.ToolContext, judgment: Judgment | None, llm: LLMClient | None, architecture: str,
             degraded: list[str], started: float, stage_trace: dict | None = None, llm_error: str | None = None) -> RunResult:
    _gap_fill(ctx)
    j = judgment
    # Model claims are verified in code before they can add anything
    injection_ok = _injection_verified(ctx, j)
    legal_ok = bool(j and j.legal_issue_identified and (j.legal_issue_reason or "").strip())
    if j and j.injection_detected and not injection_ok:
        degraded.append("llm_injection_claim_unverified")
    # Final authoritative engine pass with the final judgments
    engine = T.evaluate_policy(
        ctx,
        overlap_cleared=bool(j and j.overlap_cleared and (j.overlap_reason or "").strip()),
        overlap_reason=j.overlap_reason if j else None,
        legal_issue_identified=legal_ok,
        injection_detected=injection_ok)
    if not ctx.called("run_policy_checks"):
        ctx.dispatch("run_policy_checks", {"request_id": ctx.request_id}, by="code")  # makes the engine a recorded source
    ctx.outputs["run_policy_checks"].append(engine)  # the merge pass is recorded as output, not as an extra tool call

    # Degraded-mode notes
    risk = ctx.vendor_risk(str(ctx.request.get("vendor_name") or ""))
    if risk.get("status") == pe.RISK_UNAVAILABLE:
        degraded.append("vendor_risk_unavailable")
    elif risk.get("status") == pe.RISK_NOT_FOUND:
        degraded.append("vendor_risk_no_record")
    flags = list(engine["risk_flags"])
    if "llm_unavailable" in degraded and "llm_unavailable" not in flags:
        flags.append("llm_unavailable")

    # Prose: LLM text unless absent or it overreaches (claims approval/purchase)
    template_rec, template_next = template_recommendation(engine, ctx.request)
    rec, nxt = template_rec, template_next
    if j:
        if j.recommendation.strip() and not overreaches(j.recommendation):
            rec = j.recommendation.strip()
        elif j.recommendation.strip():
            degraded.append("recommendation_overreach_replaced")
        if j.next_step.strip() and not overreaches(j.next_step):
            nxt = j.next_step.strip()
        elif j.next_step.strip():
            degraded.append("next_step_overreach_replaced")

    outputs = {name: ctx.latest(name) for name in ctx.outputs}
    called = set(ctx.tool_names)
    notes: list[dict] = []
    if j:
        notes = grounding.valid_notes([n.model_dump() for n in j.evidence_notes], called)
        for text in j.ambiguity_notes:
            if text.strip():
                notes.append({"source": "get_request_context", "finding": f"LLM note (ambiguity): {text.strip()}", "reference": ctx.request_id})
        if legal_ok and not engine["missing_information"]:
            notes.append({"source": "run_policy_checks", "finding": f"LLM note (legal): {j.legal_issue_reason.strip()}", "reference": "Policy section 7"})
        if injection_ok and j.injection_note and not engine.get("injection_hits"):
            notes.append({"source": "run_policy_checks", "finding": f"LLM note (injection): {j.injection_note.strip()}", "reference": "Policy section 9"})
    evidence = grounding.build_evidence(
        outputs, engine, notes,
        overlap_reason=j.overlap_reason if (j and j.overlap_cleared and (j.overlap_reason or "").strip()) else None)

    usage = llm.usage if llm else None
    total_ms = (time.perf_counter() - started) * 1000 - (usage.rate_limit_wait_ms if usage else 0.0)
    telemetry = RunTelemetry(
        llm_calls=usage.calls if usage else 0, tool_calls=len(ctx.calls), tool_names=ctx.tool_names,
        llm_failed_attempts=usage.failed_attempts if usage else 0,
        prompt_tokens=usage.prompt_tokens if usage else 0, completion_tokens=usage.completion_tokens if usage else 0,
        cost_usd=round(usage.cost_usd, 6) if usage else 0.0, latency_ms=round(total_ms, 1),
        stage_latency_ms={k: round(v, 1) for k, v in (usage.stage_latency_ms.items() if usage else [])},
        model=llm.model if llm else None)
    decision = ProcurementDecision(
        request_id=ctx.request_id, recommendation=rec, evidence=evidence,
        required_approvals=engine["required_approvals"], missing_information=engine["missing_information"],
        risk_flags=flags, next_step=nxt, human_review_required=True,  # never anything else
        next_action_class=engine["next_action_class"], degraded_modes=sorted(set(degraded)), telemetry=telemetry)
    problems = grounding.validate_grounding(decision, ctx.outputs, ctx.tool_names)
    return RunResult(decision, engine, ctx.outputs, ctx.calls, j, sorted(set(degraded)), problems, stage_trace or {}, llm_error)


def analyze_request_full(request: dict, architecture: Architecture = "single", overrides: dict | None = None,
                         llm: LLMClient | None = None) -> RunResult:
    """Run one request end to end. `overrides` injects faults/patches for evals (see tools.apply_overrides)."""
    from src import agents  # local import keeps module import light

    if architecture not in ("single", "staged", "engine"):
        raise ValueError(f"unknown architecture {architecture!r}")
    started = time.perf_counter()
    if not (overrides or {}).get("vendor_risk"):
        ensure_local_mock_api()
    ctx = T.ToolContext(request, overrides=overrides)
    llm = None if architecture == "engine" else (llm or LLMClient())
    judgment: Judgment | None = None
    degraded: list[str] = []
    trace: dict = {}
    error: str | None = None
    if architecture != "engine":
        try:
            if architecture == "single":
                judgment = agents.run_single(llm, ctx)
            else:
                judgment, trace = agents.run_staged(llm, ctx)
        except LLMUnavailable as exc:
            degraded.append("llm_unavailable")
            error = str(exc)
        except Exception as exc:  # invalid model output, parsing errors, anything unexpected
            degraded.extend(["llm_unavailable", "llm_output_invalid"])
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
    return finalize(ctx, judgment, llm, architecture, degraded, started, trace, error)
