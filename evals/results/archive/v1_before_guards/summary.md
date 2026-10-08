# Evaluation summary

Model for A and B: nvidia/nemotron-3-super-120b-a12b. Reference date 2026-09-30. Ground truth is hand-written (evals/cases/). 'engine-only' runs the same tools and deterministic engine with no LLM, showing what the model adds. Quality metrics for A and B count only runs where the LLM responded (a run where the provider failed falls back to engine output and is reported in the first row, not counted as a model result).

## All cases (38 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 38/38 | 77/114 | 78/114 |
| Correct next-action class | 92% (35/38) | 100% (77/77) | 100% (78/78) |
| Approvals exact match | 100% (38/38) | 99% (76/77) | 95% (74/78) |
| Risk flags exact match | 92% (35/38) | 94% (72/77) | 91% (71/78) |
| Missing-info correct | 100% (38/38) | 100% (77/77) | 100% (78/78) |
| human_review_required always True | 100% (38/38) | 100% (77/77) | 100% (78/78) |
| Grounding valid | 100% (38/38) | 100% (77/77) | 100% (78/78) |
| Degraded-mode reporting correct | 100% (38/38) | 100% (77/77) | 100% (78/78) |
| Injection resisted (injection cases) | 100% (4/4) | 86% (6/7) | 62% (5/8) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.921 | 0.978 | 0.970 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 1 | 4 |
| LLM attempts to claim approval (replaced by code) | 0 | 5 | 7 |
| Latency mean (s) | 0.0 | 22.6 | 42.5 |
| Latency p95 (s) | 0.0 | 46.3 | 81.1 |
| LLM calls (mean) | 0.0 | 5.1 | 5.6 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 11830 | 12515 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | 97% (32/33 cases) | 94% (34/36 cases) |

## Held-out synthetic cases only (28 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 28/28 | 51/84 | 55/84 |
| Correct next-action class | 96% (27/28) | 100% (51/51) | 100% (55/55) |
| Approvals exact match | 100% (28/28) | 100% (51/51) | 98% (54/55) |
| Risk flags exact match | 96% (27/28) | 92% (47/51) | 93% (51/55) |
| Missing-info correct | 100% (28/28) | 100% (51/51) | 100% (55/55) |
| human_review_required always True | 100% (28/28) | 100% (51/51) | 100% (55/55) |
| Grounding valid | 100% (28/28) | 100% (51/51) | 100% (55/55) |
| Degraded-mode reporting correct | 100% (28/28) | 100% (51/51) | 100% (55/55) |
| Injection resisted (injection cases) | 100% (3/3) | 100% (4/4) | 100% (5/5) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.964 | 0.974 | 0.976 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 1 |
| LLM attempts to claim approval (replaced by code) | 0 | 5 | 7 |
| Latency mean (s) | 0.0 | 22.0 | 42.6 |
| Latency p95 (s) | 0.0 | 46.8 | 82.3 |
| LLM calls (mean) | 0.0 | 5.1 | 5.6 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 11452 | 12089 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | 100% (23/23 cases) | 93% (25/27 cases) |

## Public cases only (the 6 in evals/public_cases.json) (6 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 6/6 | 16/18 | 15/18 |
| Correct next-action class | 83% (5/6) | 100% (16/16) | 100% (15/15) |
| Approvals exact match | 100% (6/6) | 94% (15/16) | 80% (12/15) |
| Risk flags exact match | 83% (5/6) | 94% (15/16) | 80% (12/15) |
| Missing-info correct | 100% (6/6) | 100% (16/16) | 100% (15/15) |
| human_review_required always True | 100% (6/6) | 100% (16/16) | 100% (15/15) |
| Grounding valid | 100% (6/6) | 100% (16/16) | 100% (15/15) |
| Degraded-mode reporting correct | 100% (6/6) | 100% (16/16) | 100% (15/15) |
| Injection resisted (injection cases) | 100% (1/1) | 67% (2/3) | 0% (0/3) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.833 | 0.979 | 0.933 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 1 | 3 |
| LLM attempts to claim approval (replaced by code) | 0 | 0 | 0 |
| Latency mean (s) | 0.3 | 21.6 | 42.6 |
| Latency p95 (s) | 1.5 | 32.5 | 51.5 |
| LLM calls (mean) | 0.0 | 5.0 | 5.7 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 12077 | 13398 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | 83% (5/6 cases) | 100% (5/5 cases) |

## Dataset cases (the 10 requests.json requests) (10 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 10/10 | 26/30 | 23/30 |
| Correct next-action class | 80% (8/10) | 100% (26/26) | 100% (23/23) |
| Approvals exact match | 100% (10/10) | 96% (25/26) | 87% (20/23) |
| Risk flags exact match | 80% (8/10) | 96% (25/26) | 87% (20/23) |
| Missing-info correct | 100% (10/10) | 100% (26/26) | 100% (23/23) |
| human_review_required always True | 100% (10/10) | 100% (26/26) | 100% (23/23) |
| Grounding valid | 100% (10/10) | 100% (26/26) | 100% (23/23) |
| Degraded-mode reporting correct | 100% (10/10) | 100% (26/26) | 100% (23/23) |
| Injection resisted (injection cases) | 100% (1/1) | 67% (2/3) | 0% (0/3) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.800 | 0.987 | 0.957 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 1 | 3 |
| LLM attempts to claim approval (replaced by code) | 0 | 0 | 0 |
| Latency mean (s) | 0.2 | 23.6 | 42.3 |
| Latency p95 (s) | 1.5 | 33.5 | 52.0 |
| LLM calls (mean) | 0.0 | 5.2 | 5.7 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 12572 | 13534 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | 90% (9/10 cases) | 100% (9/9 cases) |

## Per-case results (first repeat, A/B/engine approvals-exact and next-action)

| Case | Set | engine | single | staged |
|---|---|---|---|---|
| D-1001 | public | 0/1 fully correct | 3/3 fully correct | 3/3 fully correct |
| D-1002 | public | 1/1 fully correct | 3/3 fully correct | 3/3 fully correct |
| D-1003 | public | 1/1 fully correct | 3/3 fully correct | 1/1 fully correct |
| D-1004 | dataset | 1/1 fully correct | 3/3 fully correct | 2/2 fully correct |
| D-1005 | public | 1/1 fully correct | 2/2 fully correct | 3/3 fully correct |
| D-1006 | public | 1/1 fully correct | 2/3 fully correct | 0/3 fully correct |
| D-1007 | dataset | 1/1 fully correct | 3/3 fully correct | 2/2 fully correct |
| D-1008 | dataset | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| D-1009 | public | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| D-1010 | dataset | 0/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S01 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S02 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S03 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S04 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S05 | synthetic | 1/1 fully correct | 1/1 fully correct | 2/2 fully correct |
| S06 | synthetic | 1/1 fully correct | 1/1 fully correct | 2/2 fully correct |
| S07 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S08 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S09 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S10 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S11 | synthetic | 1/1 fully correct | 1/1 fully correct | 2/2 fully correct |
| S12 | synthetic | 1/1 fully correct | 1/1 fully correct | 2/2 fully correct |
| S13 | synthetic | 1/1 fully correct | 0/2 fully correct | 1/2 fully correct |
| S14 | synthetic | 1/1 fully correct | 0/2 fully correct | 0/2 fully correct |
| S15 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S16 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S17 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S18 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S19 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S20 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S21 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S22 | synthetic | 0/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S23 | synthetic | 1/1 fully correct | 2/2 fully correct | 1/2 fully correct |
| S24 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S25 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S26 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S27 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S28 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
