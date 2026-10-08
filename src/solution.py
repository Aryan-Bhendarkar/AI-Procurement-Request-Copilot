from __future__ import annotations

from src import data_access
from src.contracts import Architecture, ProcurementDecision
from src.pipeline import RunResult, analyze_request_full


def analyze_request(request: dict, architecture: Architecture = "single", overrides: dict | None = None) -> ProcurementDecision:
    """Analyse an arbitrary request dict (used by evals and the UI's custom-request form)."""
    return analyze_request_full(request, architecture, overrides).decision


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter: analyse one of the dataset requests by id.

    architecture: "single" (one tool-calling agent) or "staged" (analyst -> policy/risk reviewer).
    Approvals, risk flags and missing information come from the deterministic policy engine;
    the model only writes the recommendation and supplies judgments. human_review_required is always True.
    """
    return analyze_request(data_access.get_request(request_id), architecture)


def handle_request_full(request_id: str, architecture: Architecture = "single") -> RunResult:
    return analyze_request_full(data_access.get_request(request_id), architecture)
