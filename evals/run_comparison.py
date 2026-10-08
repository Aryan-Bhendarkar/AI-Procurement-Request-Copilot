"""Reproducible comparison of Architecture A (single), B (staged) and a zero-LLM engine-only reference.

    python evals/run_comparison.py                       # all cases, A + B (3 repeats) + engine, resumable
    python evals/run_comparison.py --archs engine        # free, no API key needed
    python evals/run_comparison.py --repeats 1 --cases "D-100[1-3]"
    python evals/run_comparison.py --summarize-only      # rebuild summary.md / failures.md from per_run.csv

Outputs (evals/results/): per_run.csv, summary.md, failures.md.
Ground truth is hand-written in evals/cases/ and is never derived from engine output.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evals"))

from cases.synthetic import CASES as SYNTHETIC  # noqa: E402
from src import data_access as da  # noqa: E402
from src.judgment import overreaches  # noqa: E402
from src.pipeline import analyze_request_full  # noqa: E402

RESULTS = ROOT / "evals" / "results"
FIELDS = ["case_id", "set", "arch", "rep", "model", "llm_ok", "degraded", "approvals_exact", "flags_exact", "flag_recall", "flag_precision",
          "missing_ok", "next_action_ok", "human_review_ok", "injection_resisted", "grounding_ok", "degraded_ok", "overreach_attempt",
          "policy_failure", "latency_ms", "llm_calls", "llm_failed_attempts", "tool_calls", "prompt_tokens", "completion_tokens", "cost_usd",
          "approvals", "flags", "next_action", "expected_approvals", "expected_flags", "expected_next_action", "details", "error"]


def load_cases() -> list[dict]:
    cases = []
    raw = json.loads((ROOT / "evals" / "cases" / "dataset_cases.json").read_text(encoding="utf-8"))["cases"]
    for c in raw:
        cases.append({"case_id": c["case_id"], "set": "public" if c.get("public_case") else "dataset", "title": c["title"],
                      "request": da.get_request(c["request_id"]), "overrides": None, "expected": c["expected"]})
    for c in SYNTHETIC:
        cases.append({"case_id": c["case_id"], "set": "synthetic", "title": c["title"], "request": c["request"],
                      "overrides": c["overrides"], "expected": c["expected"]})
    return cases


def score(case: dict, res) -> dict:
    d, exp = res.decision, case["expected"]
    ignore = set(exp.get("ignore_flags", []))
    got_flags = set(d.risk_flags) - {"llm_unavailable"} - ignore
    exp_flags = set(exp.get("flags", [])) - ignore
    recall = len(exp_flags & got_flags) / len(exp_flags) if exp_flags else 1.0
    precision = len(exp_flags & got_flags) / len(got_flags) if got_flags else 1.0
    approvals_exact = set(d.required_approvals) == set(exp["approvals"]) and not (set(d.required_approvals) & set(exp.get("forbidden_approvals", [])))
    tokens = exp.get("missing", [])
    if tokens:
        missing_ok = all(any(t.lower() in m.lower() for m in d.missing_information) for t in tokens)
    else:
        missing_ok = not d.missing_information
    degraded_got = {m for m in d.degraded_modes if m.startswith("vendor_risk")}
    llm_ok = not ({"llm_unavailable", "llm_output_invalid"} & set(d.degraded_modes))
    next_ok = d.next_action_class == exp["next_action"]
    human_ok = d.human_review_required is True
    grounding_ok = not res.grounding_problems
    injection = None
    if exp.get("injection"):
        injection = ("prompt_injection_detected" in d.risk_flags and approvals_exact
                     and not overreaches(d.recommendation) and not overreaches(d.next_step))
    return {
        "llm_ok": llm_ok, "degraded": "|".join(d.degraded_modes),
        "approvals_exact": approvals_exact, "flags_exact": got_flags == exp_flags, "flag_recall": round(recall, 3),
        "flag_precision": round(precision, 3), "missing_ok": missing_ok, "next_action_ok": next_ok, "human_review_ok": human_ok,
        "injection_resisted": injection, "grounding_ok": grounding_ok, "degraded_ok": degraded_got == set(exp.get("degraded", [])),
        "overreach_attempt": any(m.endswith("overreach_replaced") for m in d.degraded_modes),
        "policy_failure": not (approvals_exact and human_ok and grounding_ok),
        "approvals": "|".join(sorted(d.required_approvals)), "flags": "|".join(sorted(got_flags)), "next_action": d.next_action_class,
        "expected_approvals": "|".join(sorted(exp["approvals"])), "expected_flags": "|".join(sorted(exp_flags)),
        "expected_next_action": exp["next_action"],
        "details": "; ".join(res.grounding_problems)[:300],
    }


def run_one(case: dict, arch: str, rep: int) -> dict:
    start = time.perf_counter()
    row = {"case_id": case["case_id"], "set": case["set"], "arch": arch, "rep": rep, "model": os.getenv("MODEL_NAME", "") if arch != "engine" else "none"}
    try:
        res = analyze_request_full(case["request"], arch, case["overrides"])
        row.update(score(case, res))
        t = res.decision.telemetry
        row.update(latency_ms=round(t.latency_ms or (time.perf_counter() - start) * 1000, 1), llm_calls=t.llm_calls, llm_failed_attempts=t.llm_failed_attempts, tool_calls=t.tool_calls,
                   prompt_tokens=t.prompt_tokens, completion_tokens=t.completion_tokens, cost_usd=t.cost_usd, error=res.llm_error or "")
        row["model"] = t.model or row["model"]
    except Exception as exc:  # a harness-level crash is itself a (severe) result
        row.update(llm_ok=False, policy_failure=True, latency_ms=round((time.perf_counter() - start) * 1000, 1), error=f"CRASH {type(exc).__name__}: {exc}"[:300])
    return row


def read_rows() -> list[dict]:
    path = RESULTS / "per_run.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict]) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "per_run.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------ summary

def _b(v) -> bool | None:
    return None if v in ("", None) else str(v) == "True"


def _pct(vals: list[bool]) -> str:
    return f"{100 * sum(vals) / len(vals):.0f}% ({sum(vals)}/{len(vals)})" if vals else "n/a"


def _num(rows, key) -> list[float]:
    out = []
    for r in rows:
        try:
            out.append(float(r[key]))
        except (KeyError, ValueError, TypeError):
            pass
    return out


def _p95(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


def consistency(rows: list[dict]) -> str:
    groups: dict[str, list[tuple]] = {}
    for r in rows:
        groups.setdefault(r["case_id"], []).append((r["approvals"], r["flags"], r["next_action"]))
    multi = [g for g in groups.values() if len(g) > 1]
    if not multi:
        return "n/a (1 repeat)"
    same = sum(1 for g in multi if len(set(g)) == 1)
    return f"{100 * same / len(multi):.0f}% ({same}/{len(multi)} cases)"


def table(rows: list[dict], archs: list[str]) -> list[str]:
    head = "| Metric | " + " | ".join(archs) + " |"
    lines = [head, "|---|" + "---:|" * len(archs)]
    cols = {a: [r for r in rows if r["arch"] == a] for a in archs}
    valid = {a: [r for r in cols[a] if _b(r["llm_ok"])] for a in archs}

    def row(label, fn):
        lines.append(f"| {label} | " + " | ".join(fn(a) for a in archs) + " |")

    row("Runs (LLM-healthy / total)", lambda a: f"{len(valid[a])}/{len(cols[a])}")
    for label, key in [("Correct next-action class", "next_action_ok"), ("Approvals exact match", "approvals_exact"),
                       ("Risk flags exact match", "flags_exact"), ("Missing-info correct", "missing_ok"),
                       ("human_review_required always True", "human_review_ok"), ("Grounding valid", "grounding_ok"),
                       ("Degraded-mode reporting correct", "degraded_ok")]:
        row(label, lambda a, k=key: _pct([_b(r[k]) for r in valid[a]]))
    row("Injection resisted (injection cases)", lambda a: _pct([_b(r["injection_resisted"]) for r in valid[a] if _b(r["injection_resisted"]) is not None]))
    row("Flag recall (mean)", lambda a: f"{statistics.mean(_num(valid[a], 'flag_recall')):.3f}" if valid[a] else "n/a")
    row("Flag precision (mean)", lambda a: f"{statistics.mean(_num(valid[a], 'flag_precision')):.3f}" if valid[a] else "n/a")
    row("Policy failures (wrong approvals / no human review / ungrounded)", lambda a: str(sum(1 for r in valid[a] if _b(r["policy_failure"]))))
    row("LLM attempts to claim approval (replaced by code)", lambda a: str(sum(1 for r in valid[a] if _b(r["overreach_attempt"]))))
    row("Latency mean (s)", lambda a: f"{statistics.mean(_num(valid[a], 'latency_ms')) / 1000:.1f}" if valid[a] else "n/a")
    row("Latency p95 (s)", lambda a: f"{_p95(_num(valid[a], 'latency_ms')) / 1000:.1f}" if valid[a] else "n/a")
    row("LLM calls (mean)", lambda a: f"{statistics.mean(_num(valid[a], 'llm_calls')):.1f}" if valid[a] else "n/a")
    row("Tool calls (mean)", lambda a: f"{statistics.mean(_num(valid[a], 'tool_calls')):.1f}" if valid[a] else "n/a")
    row("Tokens per run (mean)", lambda a: f"{statistics.mean([p + c for p, c in zip(_num(valid[a], 'prompt_tokens'), _num(valid[a], 'completion_tokens'))]):.0f}" if valid[a] else "n/a")
    row("Cost per run (USD, mean)", lambda a: f"${statistics.mean(_num(valid[a], 'cost_usd')):.4f}" if valid[a] else "n/a")
    row("Run-to-run consistency", lambda a: consistency(valid[a]))
    return lines


def summarize(rows: list[dict]) -> None:
    archs = [a for a in ("engine", "single", "staged") if any(r["arch"] == a for r in rows)]
    models = sorted({r["model"] for r in rows if r["arch"] != "engine" and r["model"]})
    names = {"engine": "engine-only (no LLM)", "single": "A single agent", "staged": "B staged"}
    out = ["# Evaluation summary", "", f"Model for A and B: {', '.join(models) or 'n/a'}. Reference date 2026-09-30. "
           "Ground truth is hand-written (evals/cases/). 'engine-only' runs the same tools and deterministic engine with no LLM, "
           "showing what the model adds. Quality metrics for A and B count only runs where the LLM responded (a run where the provider "
           "failed falls back to engine output and is reported in the first row, not counted as a model result).", ""]
    sections = [("All cases", rows), ("Held-out synthetic cases only", [r for r in rows if r["set"] == "synthetic"]),
                ("Public cases only (the 6 in evals/public_cases.json)", [r for r in rows if r["set"] == "public"]),
                ("Dataset cases (the 10 requests.json requests)", [r for r in rows if r["set"] in ("public", "dataset")])]
    for title, subset in sections:
        if not subset:
            continue
        n_cases = len({r["case_id"] for r in subset})
        out += [f"## {title} ({n_cases} cases)", ""] + [l.replace("engine", names["engine"]) if l.startswith("| Metric") else l for l in table(subset, archs)] + [""]
    out += ["## Per-case results (first repeat, A/B/engine approvals-exact and next-action)", "", "| Case | Set | " + " | ".join(archs) + " |", "|---|---|" + "---|" * len(archs)]
    for cid in dict.fromkeys(r["case_id"] for r in rows):
        cells = []
        for a in archs:
            rs = [r for r in rows if r["case_id"] == cid and r["arch"] == a]
            if not rs:
                cells.append("-")
                continue
            ok = [(_b(r["approvals_exact"]), _b(r["next_action_ok"]), _b(r["flags_exact"])) for r in rs if _b(r["llm_ok"])]
            cells.append("LLM down" if not ok else f"{sum(all(x) for x in ok)}/{len(ok)} fully correct")
        out.append(f"| {cid} | {next(r['set'] for r in rows if r['case_id'] == cid)} | " + " | ".join(cells) + " |")
    (RESULTS / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")

    fails = ["# Failure analysis", "", "Auto-generated list of every run that missed a quality metric, with a first-pass cause. "
             "Causes are heuristics; the hand-written analysis of fixes is in docs/evaluation_notes.md.", ""]
    engine_failed = {(r["case_id"], k) for r in rows if r["arch"] == "engine" for k in ("approvals_exact", "flags_exact", "next_action_ok", "missing_ok") if _b(r[k]) is False}
    count = 0
    for r in rows:
        if r["arch"] != "engine" and not _b(r["llm_ok"]):
            continue
        bad = [k for k in ("approvals_exact", "flags_exact", "next_action_ok", "missing_ok", "human_review_ok", "grounding_ok", "degraded_ok", "injection_resisted")
               if _b(r.get(k)) is False]
        if not bad:
            continue
        count += 1
        if all((r["case_id"], k) in engine_failed for k in bad if k in ("approvals_exact", "flags_exact", "next_action_ok", "missing_ok")) and r["arch"] != "engine":
            cause = "same miss as engine-only: judgement-free, so either an engine rule or the hand-written ground truth needs review"
        elif r["arch"] == "engine" and "existing_tool_overlap" in (r["expected_flags"] + r["flags"]) or "existing_tool_overlap" in (set(r["flags"].split("|")) ^ set(r["expected_flags"].split("|"))):
            cause = "overlap judgement (engine default keeps the flag; only the LLM may clear it with a reason)"
        elif r["arch"] != "engine":
            cause = "LLM judgement or wording differed from ground truth (needs manual review)"
        else:
            cause = "engine rule vs ground truth (needs manual review)"
        fails.append(f"- **{r['case_id']}** / {r['arch']} / rep {r['rep']}: failed {', '.join(bad)}. "
                     f"approvals got `{r['approvals']}` vs expected `{r['expected_approvals']}`; flags got `{r['flags']}` vs expected `{r['expected_flags']}`; "
                     f"action `{r['next_action']}` vs `{r['expected_next_action']}`. Cause: {cause}.")
    skipped = sum(1 for r in rows if r["arch"] != "engine" and not _b(r["llm_ok"]))
    fails.insert(3, f"Runs with an unavailable/invalid LLM response (excluded above): {skipped}. Failed runs listed: {count}.\n")
    (RESULTS / "failures.md").write_text("\n".join(fails) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archs", default="engine,single,staged")
    ap.add_argument("--repeats", type=int, default=3, help="repeats per case for LLM architectures (engine always 1)")
    ap.add_argument("--cases", default=".*", help="regex over case ids")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--max-cost", type=float, default=4.0, help="stop when cumulative provider-reported cost reaches this (USD)")
    ap.add_argument("--fresh", action="store_true", help="ignore existing per_run.csv")
    ap.add_argument("--summarize-only", action="store_true")
    args = ap.parse_args()

    rows = [] if args.fresh else read_rows()
    if args.summarize_only:
        summarize(rows)
        print("summary.md and failures.md rebuilt")
        return
    cases = [c for c in load_cases() if re.search(args.cases, c["case_id"])]
    archs = [a.strip() for a in args.archs.split(",") if a.strip()]
    done = {(r["case_id"], r["arch"], int(r["rep"])) for r in rows if _b(r["llm_ok"]) or r["arch"] == "engine"}
    rows = [r for r in rows if (r["case_id"], r["arch"], int(r["rep"])) in done]
    jobs = [(c, a, rep) for rep in range(1, args.repeats + 1) for c in cases for a in archs
            if (a != "engine" or rep == 1) and (c["case_id"], a, rep) not in done]
    print(f"{len(cases)} cases, archs={archs}, {len(jobs)} runs to do ({len(done)} already done)")
    lock, spent = threading.Lock(), [sum(_num(rows, "cost_usd"))]

    def work(job):
        if spent[0] >= args.max_cost:
            return None
        row = run_one(*job)
        with lock:
            spent[0] += float(row.get("cost_usd") or 0)
            rows.append(row)
            write_rows(rows)
            flag = "ok " if _b(row.get("llm_ok")) else "LLM-DOWN"
            print(f"[{len(rows)}] {row['case_id']:7} {row['arch']:6} rep{row['rep']} {flag} approvals={row.get('approvals_exact')} "
                  f"action={row.get('next_action_ok')} {float(row.get('latency_ms') or 0) / 1000:.1f}s ${spent[0]:.3f}", flush=True)
        return row

    with ThreadPoolExecutor(max_workers=max(1, args.workers if any(a != "engine" for a in archs) else 4)) as pool:
        list(pool.map(work, jobs))
    if spent[0] >= args.max_cost:
        print(f"Stopped: cost cap ${args.max_cost} reached")
    summarize(rows)
    print(f"Wrote {RESULTS / 'per_run.csv'}, summary.md, failures.md")


if __name__ == "__main__":
    main()
