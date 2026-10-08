# Failure analysis

Auto-generated list of every run that missed a quality metric, with a first-pass cause. Causes are heuristics; the hand-written analysis of fixes is in docs/evaluation_notes.md.
Runs with an unavailable/invalid LLM response (excluded above): 11. Failed runs listed: 6.


- **D-1001** / engine / rep 1: failed flags_exact, next_action_ok. approvals got `Manager` vs expected `Manager`; flags got `existing_tool_overlap` vs expected ``; action `needs_reviews` vs `approve_path`. Cause: overlap judgement (engine default keeps the flag; only the LLM may clear it with a reason).
- **D-1001** / staged / rep 1: failed flags_exact, next_action_ok. approvals got `Manager` vs expected `Manager`; flags got `existing_tool_overlap` vs expected ``; action `needs_reviews` vs `approve_path`. Cause: same miss as engine-only: judgement-free, so either an engine rule or the hand-written ground truth needs review.
- **D-1010** / engine / rep 1: failed flags_exact, next_action_ok. approvals got `Manager` vs expected `Manager`; flags got `existing_tool_overlap` vs expected ``; action `needs_reviews` vs `approve_path`. Cause: overlap judgement (engine default keeps the flag; only the LLM may clear it with a reason).
- **S14** / staged / rep 1: failed flags_exact. approvals got `Manager|Security` vs expected `Manager|Security`; flags got `prompt_injection_detected|security_review_required|vendor_risk_unavailable` vs expected `security_review_required|vendor_risk_unavailable`; action `escalate_manual` vs `escalate_manual`. Cause: LLM judgement or wording differed from ground truth (needs manual review).
- **S22** / engine / rep 1: failed flags_exact, next_action_ok. approvals got `Manager` vs expected `Manager`; flags got `existing_tool_overlap` vs expected ``; action `needs_reviews` vs `approve_path`. Cause: overlap judgement (engine default keeps the flag; only the LLM may clear it with a reason).
- **S23** / staged / rep 1: failed approvals_exact, flags_exact. approvals got `Department Head|Legal|Privacy|Procurement|Security` vs expected `Department Head|Privacy|Procurement|Security`; flags got `legal_review_required|privacy_review_required|security_review_required` vs expected `privacy_review_required|security_review_required`; action `needs_reviews` vs `needs_reviews`. Cause: LLM judgement or wording differed from ground truth (needs manual review).
