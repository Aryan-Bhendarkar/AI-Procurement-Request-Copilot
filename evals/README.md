# Evaluation

Two runners share the same code under test (`src.solution.handle_request` / `src.pipeline.analyze_request_full`).

| Runner | Purpose | Command |
|---|---|---|
| `run_public_evals.py` | Starter-pack harness: the 6 public cases, minimum checks, latency CSV. Unmodified. | `python evals/run_public_evals.py --architecture single` (or `staged`) |
| `run_comparison.py` | Full comparison of **A**, **B** and an **engine-only** (no LLM) reference on 38 hand-labelled cases | `python evals/run_comparison.py` |
| `finalize_docs.py` | Refresh the generated tables in the root README and the decision memo from `results/per_run.csv` | `python evals/finalize_docs.py` |

The public harness is deliberately weak: because the deterministic engine decides every graded field, it also passes 6/6 with **no LLM at all**. Use `run_comparison.py` to judge the model.

## Cases (`cases/`)

* `dataset_cases.json`: the 10 requests in `data/requests.json` (6 are the public cases) with expected approvals, flags, missing information and next-action class.
* `synthetic.py`: 28 held-out edge cases: amount boundaries ($1,000.00 / $1,000.01 / $10,000.00 / $10,000.01 / $25,000.00 / $25,000.01), review age 365 vs 366 days, injection in the request, vendor notes and a catalog note, registry-vs-API conflict, API 503 / timeout / 404, unknown vendor, each required field missing, existing tool that does and does not cover the need, AI tool with a new data class, new vendor just under and at $10k, cross-region PII, budget equal to / one dollar under cost.

Ground truth is **hand-written from the policy**, never produced by running the engine. Faults and fixture vendors are injected through `overrides`, so the data files are never edited. Next-action classes: `approve_path`, `needs_reviews`, `clarify`, `escalate_manual`.

## Running the comparison

```powershell
python evals/run_comparison.py --archs engine           # free, no key: deterministic reference only
python evals/run_comparison.py --repeats 1 --workers 1  # one pass of A + B + engine
python evals/run_comparison.py --repeats 3 --workers 1  # variance estimate (resumable)
python evals/run_comparison.py --summarize-only         # rebuild summary.md / failures.md
```

Runs are saved after every case, so an interrupted run resumes where it stopped. A run where the provider failed (rate limit, outage) is recorded as `llm_ok=False`, **excluded** from A/B quality metrics and re-run on the next invocation; it is never counted as a model result. `--max-cost` caps provider-reported spend.

## Metrics

Next-action class, approvals exact match, risk-flag exact / recall / precision, missing-information match, `human_review_required` always true, injection resisted (no approval change, no fabricated approval), grounding validity (every evidence item cites a tool called in the run and its figures appear in tool output), degraded-mode reporting, policy failures, latency (mean / p95), LLM calls, tool calls, tokens, cost, run-to-run consistency.

## Outputs (`results/`)

* `per_run.csv`: one row per case, architecture and repeat.
* `summary.md`: comparison tables (all cases, held-out synthetic only, public only, dataset only) and a per-case grid.
* `failures.md`: every missed metric with expected vs actual and a first-pass cause.
* `archive/`: earlier runs kept for the before/after story (`v1_before_guards`) and smoke runs.
