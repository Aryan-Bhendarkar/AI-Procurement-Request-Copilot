# Evaluation notes: failures found and fixed

Auto-generated per-run failures are in [../evals/results/failures.md](../evals/results/failures.md). This file records what was learned and changed.

## Before / after log

| # | Found by | Symptom | Cause | Fix | After |
|---|---|---|---|---|---|
| 1 | First engine-only run over the 38 hand-labelled cases (S15) | A vendor-risk **404** with a current-looking registry row did not add Security | `assessment_current` only looked at sources that returned data, so a missing API record left the registry as the sole (favourable) source | `policy_engine.py`: a `not_found` result adds Security ("registry cannot be corroborated"), same as an outage; unit test added | S15 passes; engine-only approvals exact 38/38 |
| 2 | Writing the cross-region rule | REQ-1004 (customer PII at a vendor that stores data outside the region) had no Legal reviewer | an early hand-derived expectation predated the policy s.7 / s.8 reading | Cross-region + PII now adds Legal deterministically; expectation corrected; tests added | D-1004 expects Legal and passes |
| 3 | Reviewing overlap handling | Request text such as "this does not overlap" could in principle influence the flag | Overlap clearing was a plain boolean | Clearing requires a non-empty reason, is recorded as evidence, and the engine never reads request text; test proves a justification claiming "no overlap" cannot clear it | `test_overlap_clear_needs_a_reason_and_ignores_request_text` |
| 4 | Offline pipeline tests | A model reply such as "This purchase is approved" would have reached the user | No check on prose | `overreaches()` guard replaces such text with the template and records `recommendation_overreach_replaced`; counted as a metric | tested |
| 5 | First live smoke run | Provider returned HTTP 402 (no credit) and the run degraded | Infrastructure, not logic | Confirmed fallback path: deterministic decision, `llm_unavailable` flag, human review true; harness separates LLM-degraded runs from model results | tested with a mocked outage |

## What the engine-only reference shows

Engine-only (no LLM) matches the hand-written ground truth on approvals for all 38 cases and on flags/next action everywhere except D-1001, D-1010 and S22. Those three are the cases where a model must judge that a seat add-on or a training pack is not an overlap with the owned product. They are the measurable value of the LLM. The remaining LLM contributions (wording, injection second opinion, ambiguity notes) are not scored against ground truth and are reviewed manually.

## LLM-driven failures from the first full run (NVIDIA, nemotron-3-super)

| # | Case | Symptom | Cause | Fix | After |
|---|---|---|---|---|---|
| 6 | D-1006 (A, B) | Legal approval added to an incomplete request | model set `legal_issue_identified` while reasoning about the injection | legal claim needs a reason and is ignored when information is missing | D-1006 passes in A and B |
| 7 | S13, S14 (A, B) | `prompt_injection_detected` on a plain API outage | model treated the outage text as injection | injection claim needs `injection_quote` found verbatim in the data | A passes; B S14 still flagged (fault text contains the word "injected", a test artefact) |
| 8 | many | whole judgment rejected for malformed optional fields (`evidence_notes`, `challenges`) | model schema drift | tolerant parsing drops unusable optional items | invalid-output runs gone |
| 9 | rate limits | many runs lost to 429 | free tier | 429 waits in the client; failed runs excluded and re-runnable | see README |

## What still needs a larger run

* Does A or B clear overlap correctly for D-1001, D-1010, S22, and correctly **keep** it for D-1002, D-1004, D-1007, D-1008, S21 and S11?
* Does the B reviewer ever overrule the analyst correctly, or just add latency?
* Run-to-run consistency at temperature 0 over 3 repeats.
* How often model prose is replaced by the overreach guard.

`python evals/run_comparison.py` answers these; `evals/results/failures.md` then lists each miss with expected and actual values. Do not tune prompts to individual case ids: develop on the public cases, report on the held-out synthetic ones.
