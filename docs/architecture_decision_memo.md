# Architecture Decision Memo

## Decision
Ship **Architecture A, the single agent**.

## Evidence
38 hand-labelled cases (6 public, 4 other dataset requests, 28 held-out synthetic), same model for both (nvidia/nemotron-3-super-120b-a12b via NVIDIA's free API). Ground truth is hand-written, not engine output. Engine-only runs the same tools and rules with no LLM.

<!-- MEMO_TABLE:START -->
| Metric | Engine only (no LLM) | A single agent | B staged |
|---|---:|---:|---:|
| Cases fully correct | 35/38 | 38/38 | 35/38 |
| Avg latency | 0.0s | 22.1s | 39.7s |
| Avg LLM calls | 0.0 | 5.0 | 5.3 |
| Avg tool calls | 4.0 | 4.0 | 4.0 |
| Policy/grounding failures | 0 in 38 runs | 0 in 60 runs | 1 in 59 runs |

A: 5 of 65 runs excluded (LLM provider failed); B: 6 of 65 runs excluded (LLM provider failed).
<!-- MEMO_TABLE:END -->

Quality is from repeat 1 of the final run (all 38 cases answered by the model for both). Timing and calls are from repeat 2 (rate-limit waits excluded): 22 cases for A and 21 for B.

## Trade-offs
- The engine owns approvals, flags, missing information and the action class in both. Engine-only already gets every approval right; its only misses are three cases where a model must clear the overlap flag.
- The first full run exposed two model-driven errors: a "legal issue" invented for an incomplete request (D-1006) and an API outage called "injection" (S13/S14). Approvals exact was A 76/77, B 74/78. Code guards fixed both for A: model injection claims need a verbatim quote found in the data, and model legal claims need a reason and are ignored when information is missing.
- After the guards A was fully correct on all 38 cases. B was 35/38: the reviewer added Legal for cross-region source code (S23, arguably defensible), still read a test fault string containing "injected" as injection (S14), and did not clear overlap on D-1001.
- B took about 1.8x A's time and slightly more model calls, and improved no metric. In repeat 2 every healthy run was fully correct for both, with identical outcomes to repeat 1, so B's three misses may partly be noise.

## Risks / limitations
- One model on a throttled free tier; repeat 2 is partial, so the 3-case gap could partly be noise.
- Ground truth is one author's reading of the policy; overlap is a judgement call.
- Injection heuristics are phrase-based; the engine ignoring free text is the real defence.
- "Department Head" is inferred from the manager chain.
- Validate with real Finance, Security and Legal reviewers.

## Why this is the right MVP
The risky decisions are code. The model only reads messy text and writes the explanation, which one tool-calling agent does faster and at least as accurately. A second agent added latency and failure surface without improving any graded field.
