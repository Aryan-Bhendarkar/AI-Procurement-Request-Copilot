# Judgment-call log

Each entry: decision, policy section, reason.

| # | Decision | Policy | Reason |
|---|---|---|---|
| 1 | Reference date is 2026-09-30 for every date check; the system clock is never used. | Data README, s.5 | Policy snapshot date; makes results reproducible. |
| 2 | Boundaries are inclusive on the upper side: $1,000.00 -> Manager, $10,000.00 -> Dept Head + Procurement, $25,000.00 -> Dept Head + Finance + Procurement. | s.4 | The table says "Up to $1,000" and ranges starting at x.01. Amounts use `Decimal` to avoid float noise. |
| 3 | A review is current through review date + 365 days inclusive; day 366 is expired. | s.5 | "current for 365 days from its review date". |
| 4 | Vendor-risk API 503 / timeout / connection error -> `vendor_risk_unavailable` + Security. | s.10, s.5 | Registry cannot be corroborated; no favourable status is inferred. |
| 5 | Vendor-risk API 404 -> `vendor_risk_no_record` + Security (separate from an outage). | s.10 | A missing record is not an outage, but the assessment is still unverified. |
| 6 | Registry vs API conflict = different status bucket (approved / expired / not_completed) or different review date. Raw registry status is compared, so SignalWatch ("Approved" in the registry, "expired" in the API) is a conflict. | s.5 | "do not silently choose one". "Pending" vs "not_completed" is the same bucket, so no false conflict. |
| 7 | Budget shortfall -> `budget_insufficient` + Finance approval. Cost equal to available budget is sufficient. | s.2 | "route for Finance/budget exception review". |
| 8 | Missing information: approvals are computed only from determinable facts; `data_access_level: "unknown"` counts as missing; an empty integrations list is valid. | s.1 | "request clarification instead of inventing values". |
| 9 | Legal is required when: new vendor and cost >= $10,000; legal terms not Approved; vendor stores data outside the region AND data class is employee/customer PII; or the LLM reports `legal_issue_identified`. | s.7, s.8 | Cross-region PII is a material data-processing issue; a prior purchase does not authorise a new data class. |
| 10 | Overlap is flagged by default. The LLM may clear it only with a non-empty reason (kept as a finding and evidence item). Request text can never clear it. | s.3 | Overlap is "not an automatic rejection" but must be surfaced. |
| 11 | REQ-1004 and REQ-1006 keep `existing_tool_overlap`: NeuralDesk Business already has 150 company-wide seats. | s.3 | Unused existing capacity should be reviewed first. |
| 12 | "Department Head" is not a data field (employees.csv has only manager_id). It is emitted as a role for the requester's department; the review packet resolves it as the most senior non-VP person in the department (or the requester's manager chain). | s.4 | Documented assumption; Sales/Customer Success report to a "Go To Market" director who has no budget row. |
| 13 | Final approvals, flags and missing-information always come from the deterministic engine, regardless of LLM output. The LLM supplies prose and judgments only. | s.11, brief | AI interprets, code applies thresholds, humans approve. |
| 14 | The OpenRouter account has no credit (/credits: total_credits 0; paid models limited to ~170-460 tokens per call). Development and smoke runs use free models (nvidia/nemotron-3-super-120b-a12b:free supports tool calling). | - | Blocker found 2026-10-08 ~10:50 IST. Everything else is built and tested offline with a scripted fake LLM. Any comparison numbers state the model used. |
| 15 | Overlap clearing is gated in code: honoured only when every candidate is from the same vendor and a reason is given; otherwise `overlap_clear_rejected` is recorded and the flag stays. | s.3 | Independent review: a model reading untrusted text could otherwise drop the flag for a competing product. |
| 16 | Data access levels are normalised (`Source Code`, `customer-PII` -> snake_case); an unrecognised level not starting with none/public/internal fails closed to Security review; a plain-string integrations value is wrapped. | s.5 | Hidden cases may use different spellings; never silently skip a sensitive class. |
| 17 | `prompt_injection_detected` alone routes to `needs_reviews`, not `approve_path`. | s.9 | A human should look at a request that tried to manipulate the copilot. |
| 18 | Vendor lookups use the registry's canonical spelling; the mock API also matches case-insensitively. | s.10 | A case/whitespace difference must not cause a false 404 and Security escalation. |
| 19 | Cross-region sensitive non-PII data (e.g. source code) adds Privacy but not Legal; `processes_personal_data` from the API is displayed as evidence but not used as a trigger. | s.6, s.7 | Policy s.7 names a "material" cross-region issue; PII is the unambiguous case. Reviewer flagged this as a judgement call; kept conservative-but-narrow. |
| 20 | LLM provider switched to NVIDIA build.nvidia.com (OpenAI-compatible, free). NVIDIA_API_KEY takes precedence over OPENROUTER_API_KEY; model from NVIDIA_MODEL (default nvidia/nemotron-3-super-120b-a12b, unverified until a key is present). | - | OpenRouter account had no credit (see #14). A and B must use the same model. |
| 21 | Model injection claims need a verbatim quote present in the data; model legal claims need a reason and are ignored when information is missing. | s.9, s.7, s.1 | First full run showed the model inventing both. |
| 22 | Final decision: ship A. Timing in the memo/README comes from the unthrottled run 1; quality from run 2. | - | Run 2 waited out rate limits inside the timer. |
