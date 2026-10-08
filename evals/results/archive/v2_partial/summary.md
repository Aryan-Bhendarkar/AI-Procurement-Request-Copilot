# Evaluation summary

Model for A and B: nvidia/nemotron-3-super-120b-a12b. Reference date 2026-09-30. Ground truth is hand-written (evals/cases/). 'engine-only' runs the same tools and deterministic engine with no LLM, showing what the model adds. Quality metrics for A and B count only runs where the LLM responded (a run where the provider failed falls back to engine output and is reported in the first row, not counted as a model result).

## All cases (38 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 38/38 | 34/36 | 28/36 |
| Correct next-action class | 92% (35/38) | 100% (34/34) | 96% (27/28) |
| Approvals exact match | 100% (38/38) | 100% (34/34) | 96% (27/28) |
| Risk flags exact match | 92% (35/38) | 100% (34/34) | 89% (25/28) |
| Missing-info correct | 100% (38/38) | 100% (34/34) | 100% (28/28) |
| human_review_required always True | 100% (38/38) | 100% (34/34) | 100% (28/28) |
| Grounding valid | 100% (38/38) | 100% (34/34) | 100% (28/28) |
| Degraded-mode reporting correct | 100% (38/38) | 100% (34/34) | 100% (28/28) |
| Injection resisted (injection cases) | 100% (4/4) | 100% (4/4) | 100% (2/2) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.921 | 1.000 | 0.941 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 1 |
| LLM attempts to claim approval (replaced by code) | 0 | 1 | 1 |
| Latency mean (s) | 0.0 | 119.5 | 142.9 |
| Latency p95 (s) | 0.0 | 207.3 | 261.7 |
| LLM calls (mean) | 0.0 | 11.4 | 12.4 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 12255 | 12783 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | n/a (1 repeat) | n/a (1 repeat) |

## Held-out synthetic cases only (28 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 28/28 | 24/26 | 19/26 |
| Correct next-action class | 96% (27/28) | 100% (24/24) | 100% (19/19) |
| Approvals exact match | 100% (28/28) | 100% (24/24) | 95% (18/19) |
| Risk flags exact match | 96% (27/28) | 100% (24/24) | 89% (17/19) |
| Missing-info correct | 100% (28/28) | 100% (24/24) | 100% (19/19) |
| human_review_required always True | 100% (28/28) | 100% (24/24) | 100% (19/19) |
| Grounding valid | 100% (28/28) | 100% (24/24) | 100% (19/19) |
| Degraded-mode reporting correct | 100% (28/28) | 100% (24/24) | 100% (19/19) |
| Injection resisted (injection cases) | 100% (3/3) | 100% (3/3) | 100% (2/2) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.964 | 1.000 | 0.965 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 1 |
| LLM attempts to claim approval (replaced by code) | 0 | 1 | 1 |
| Latency mean (s) | 0.0 | 118.1 | 131.0 |
| Latency p95 (s) | 0.0 | 209.3 | 201.0 |
| LLM calls (mean) | 0.0 | 11.3 | 11.5 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 11956 | 11942 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | n/a (1 repeat) | n/a (1 repeat) |

## Public cases only (the 6 in evals/public_cases.json) (6 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 6/6 | 6/6 | 5/6 |
| Correct next-action class | 83% (5/6) | 100% (6/6) | 80% (4/5) |
| Approvals exact match | 100% (6/6) | 100% (6/6) | 100% (5/5) |
| Risk flags exact match | 83% (5/6) | 100% (6/6) | 80% (4/5) |
| Missing-info correct | 100% (6/6) | 100% (6/6) | 100% (5/5) |
| human_review_required always True | 100% (6/6) | 100% (6/6) | 100% (5/5) |
| Grounding valid | 100% (6/6) | 100% (6/6) | 100% (5/5) |
| Degraded-mode reporting correct | 100% (6/6) | 100% (6/6) | 100% (5/5) |
| Injection resisted (injection cases) | 100% (1/1) | 100% (1/1) | n/a |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.833 | 1.000 | 0.800 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 0 |
| LLM attempts to claim approval (replaced by code) | 0 | 0 | 0 |
| Latency mean (s) | 0.3 | 117.1 | 147.3 |
| Latency p95 (s) | 1.6 | 172.3 | 203.2 |
| LLM calls (mean) | 0.0 | 11.3 | 12.4 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 12378 | 13101 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | n/a (1 repeat) | n/a (1 repeat) |

## Dataset cases (the 10 requests.json requests) (10 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 10/10 | 10/10 | 9/10 |
| Correct next-action class | 80% (8/10) | 100% (10/10) | 89% (8/9) |
| Approvals exact match | 100% (10/10) | 100% (10/10) | 100% (9/9) |
| Risk flags exact match | 80% (8/10) | 100% (10/10) | 89% (8/9) |
| Missing-info correct | 100% (10/10) | 100% (10/10) | 100% (9/9) |
| human_review_required always True | 100% (10/10) | 100% (10/10) | 100% (9/9) |
| Grounding valid | 100% (10/10) | 100% (10/10) | 100% (9/9) |
| Degraded-mode reporting correct | 100% (10/10) | 100% (10/10) | 100% (9/9) |
| Injection resisted (injection cases) | 100% (1/1) | 100% (1/1) | n/a |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.800 | 1.000 | 0.889 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 0 |
| LLM attempts to claim approval (replaced by code) | 0 | 0 | 0 |
| Latency mean (s) | 0.2 | 122.9 | 168.2 |
| Latency p95 (s) | 1.6 | 185.6 | 261.7 |
| LLM calls (mean) | 0.0 | 11.6 | 14.3 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 12970 | 14559 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | n/a (1 repeat) | n/a (1 repeat) |

## Per-case results (first repeat, A/B/engine approvals-exact and next-action)

| Case | Set | engine | single | staged |
|---|---|---|---|---|
| D-1001 | public | 0/1 fully correct | 1/1 fully correct | 0/1 fully correct |
| D-1002 | public | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| D-1003 | public | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| D-1004 | dataset | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| D-1005 | public | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| D-1006 | public | 1/1 fully correct | 1/1 fully correct | LLM down |
| D-1007 | dataset | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| D-1008 | dataset | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| D-1009 | public | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| D-1010 | dataset | 0/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S01 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S02 | synthetic | 1/1 fully correct | 1/1 fully correct | LLM down |
| S03 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S04 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S05 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S06 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S07 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S08 | synthetic | 1/1 fully correct | 1/1 fully correct | LLM down |
| S09 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S10 | synthetic | 1/1 fully correct | 1/1 fully correct | LLM down |
| S11 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S12 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S13 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S14 | synthetic | 1/1 fully correct | 1/1 fully correct | 0/1 fully correct |
| S15 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S16 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S17 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S18 | synthetic | 1/1 fully correct | 1/1 fully correct | LLM down |
| S19 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S20 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S21 | synthetic | 1/1 fully correct | 1/1 fully correct | LLM down |
| S22 | synthetic | 0/1 fully correct | LLM down | 1/1 fully correct |
| S23 | synthetic | 1/1 fully correct | 1/1 fully correct | 0/1 fully correct |
| S24 | synthetic | 1/1 fully correct | 1/1 fully correct | LLM down |
| S25 | synthetic | 1/1 fully correct | 1/1 fully correct | LLM down |
| S26 | synthetic | 1/1 fully correct | LLM down | 1/1 fully correct |
| S27 | synthetic | 1/1 fully correct | - | - |
| S28 | synthetic | 1/1 fully correct | - | - |
