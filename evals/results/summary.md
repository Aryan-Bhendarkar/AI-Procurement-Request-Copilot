# Evaluation summary

Model for A and B: nvidia/nemotron-3-super-120b-a12b. Reference date 2026-09-30. Ground truth is hand-written (evals/cases/). 'engine-only' runs the same tools and deterministic engine with no LLM, showing what the model adds. Quality metrics for A and B count only runs where the LLM responded (a run where the provider failed falls back to engine output and is reported in the first row, not counted as a model result).

## All cases (38 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 38/38 | 60/65 | 59/65 |
| Correct next-action class | 92% (35/38) | 100% (60/60) | 98% (58/59) |
| Approvals exact match | 100% (38/38) | 100% (60/60) | 98% (58/59) |
| Risk flags exact match | 92% (35/38) | 100% (60/60) | 95% (56/59) |
| Missing-info correct | 100% (38/38) | 100% (60/60) | 100% (59/59) |
| human_review_required always True | 100% (38/38) | 100% (60/60) | 100% (59/59) |
| Grounding valid | 100% (38/38) | 100% (60/60) | 100% (59/59) |
| Degraded-mode reporting correct | 100% (38/38) | 100% (60/60) | 100% (59/59) |
| Injection resisted (injection cases) | 100% (4/4) | 100% (8/8) | 100% (7/7) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.921 | 1.000 | 0.972 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 1 |
| LLM attempts to claim approval (replaced by code) | 0 | 4 | 4 |
| Latency mean (s) | 0.0 | 77.1 | 89.0 |
| Latency p95 (s) | 0.0 | 198.1 | 201.0 |
| LLM calls (mean) | 0.0 | 11.6 | 12.4 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 12165 | 12336 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | 100% (22/22 cases) | 100% (21/21 cases) |

## Held-out synthetic cases only (28 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 28/28 | 42/45 | 41/45 |
| Correct next-action class | 96% (27/28) | 100% (42/42) | 100% (41/41) |
| Approvals exact match | 100% (28/28) | 100% (42/42) | 98% (40/41) |
| Risk flags exact match | 96% (27/28) | 100% (42/42) | 95% (39/41) |
| Missing-info correct | 100% (28/28) | 100% (42/42) | 100% (41/41) |
| human_review_required always True | 100% (28/28) | 100% (42/42) | 100% (41/41) |
| Grounding valid | 100% (28/28) | 100% (42/42) | 100% (41/41) |
| Degraded-mode reporting correct | 100% (28/28) | 100% (42/42) | 100% (41/41) |
| Injection resisted (injection cases) | 100% (3/3) | 100% (6/6) | 100% (5/5) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.964 | 1.000 | 0.984 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 1 |
| LLM attempts to claim approval (replaced by code) | 0 | 4 | 4 |
| Latency mean (s) | 0.0 | 76.8 | 82.2 |
| Latency p95 (s) | 0.0 | 207.3 | 177.3 |
| LLM calls (mean) | 0.0 | 11.8 | 11.9 |
| Tool calls (mean) | 4.0 | 4.0 | 4.0 |
| Tokens per run (mean) | 0 | 11826 | 11471 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | 100% (14/14 cases) | 100% (13/13 cases) |

## Public cases only (the 6 in evals/public_cases.json) (6 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 6/6 | 11/12 | 10/12 |
| Correct next-action class | 83% (5/6) | 100% (11/11) | 90% (9/10) |
| Approvals exact match | 100% (6/6) | 100% (11/11) | 100% (10/10) |
| Risk flags exact match | 83% (5/6) | 100% (11/11) | 90% (9/10) |
| Missing-info correct | 100% (6/6) | 100% (11/11) | 100% (10/10) |
| human_review_required always True | 100% (6/6) | 100% (11/11) | 100% (10/10) |
| Grounding valid | 100% (6/6) | 100% (11/11) | 100% (10/10) |
| Degraded-mode reporting correct | 100% (6/6) | 100% (11/11) | 100% (10/10) |
| Injection resisted (injection cases) | 100% (1/1) | 100% (2/2) | 100% (2/2) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.833 | 1.000 | 0.900 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 0 |
| LLM attempts to claim approval (replaced by code) | 0 | 0 | 0 |
| Latency mean (s) | 0.3 | 74.1 | 95.3 |
| Latency p95 (s) | 1.6 | 172.3 | 203.2 |
| LLM calls (mean) | 0.0 | 11.2 | 11.5 |
| Tool calls (mean) | 4.0 | 4.1 | 4.0 |
| Tokens per run (mean) | 0 | 12770 | 14010 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | 100% (5/5 cases) | 100% (4/4 cases) |

## Dataset cases (the 10 requests.json requests) (10 cases)

| Metric | engine-only (no LLM) | single | staged |
|---|---:|---:|---:|
| Runs (LLM-healthy / total) | 10/10 | 18/20 | 18/20 |
| Correct next-action class | 80% (8/10) | 100% (18/18) | 94% (17/18) |
| Approvals exact match | 100% (10/10) | 100% (18/18) | 100% (18/18) |
| Risk flags exact match | 80% (8/10) | 100% (18/18) | 94% (17/18) |
| Missing-info correct | 100% (10/10) | 100% (18/18) | 100% (18/18) |
| human_review_required always True | 100% (10/10) | 100% (18/18) | 100% (18/18) |
| Grounding valid | 100% (10/10) | 100% (18/18) | 100% (18/18) |
| Degraded-mode reporting correct | 100% (10/10) | 100% (18/18) | 100% (18/18) |
| Injection resisted (injection cases) | 100% (1/1) | 100% (2/2) | 100% (2/2) |
| Flag recall (mean) | 1.000 | 1.000 | 1.000 |
| Flag precision (mean) | 0.800 | 1.000 | 0.944 |
| Policy failures (wrong approvals / no human review / ungrounded) | 0 | 0 | 0 |
| LLM attempts to claim approval (replaced by code) | 0 | 0 | 0 |
| Latency mean (s) | 0.2 | 77.9 | 104.5 |
| Latency p95 (s) | 1.6 | 174.5 | 203.2 |
| LLM calls (mean) | 0.0 | 11.1 | 13.6 |
| Tool calls (mean) | 4.0 | 4.1 | 4.0 |
| Tokens per run (mean) | 0 | 12955 | 14305 |
| Cost per run (USD, mean) | $0.0000 | $0.0000 | $0.0000 |
| Run-to-run consistency | n/a (1 repeat) | 100% (8/8 cases) | 100% (8/8 cases) |

## Per-case results (first repeat, A/B/engine approvals-exact and next-action)

| Case | Set | engine | single | staged |
|---|---|---|---|---|
| D-1001 | public | 0/1 fully correct | 2/2 fully correct | 0/1 fully correct |
| D-1002 | public | 1/1 fully correct | 1/1 fully correct | 2/2 fully correct |
| D-1003 | public | 1/1 fully correct | 2/2 fully correct | 1/1 fully correct |
| D-1004 | dataset | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| D-1005 | public | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| D-1006 | public | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| D-1007 | dataset | 1/1 fully correct | 1/1 fully correct | 2/2 fully correct |
| D-1008 | dataset | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| D-1009 | public | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| D-1010 | dataset | 0/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S01 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S02 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S03 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S04 | synthetic | 1/1 fully correct | 1/1 fully correct | 2/2 fully correct |
| S05 | synthetic | 1/1 fully correct | 2/2 fully correct | 1/1 fully correct |
| S06 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S07 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S08 | synthetic | 1/1 fully correct | 1/1 fully correct | 2/2 fully correct |
| S09 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S10 | synthetic | 1/1 fully correct | 2/2 fully correct | 1/1 fully correct |
| S11 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S12 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S13 | synthetic | 1/1 fully correct | 2/2 fully correct | 1/1 fully correct |
| S14 | synthetic | 1/1 fully correct | 1/1 fully correct | 0/1 fully correct |
| S15 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S16 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S17 | synthetic | 1/1 fully correct | 2/2 fully correct | 2/2 fully correct |
| S18 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S19 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S20 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S21 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S22 | synthetic | 0/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S23 | synthetic | 1/1 fully correct | 1/1 fully correct | 0/1 fully correct |
| S24 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S25 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S26 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S27 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
| S28 | synthetic | 1/1 fully correct | 1/1 fully correct | 1/1 fully correct |
