"""Refresh the generated blocks in README.md and docs/architecture_decision_memo.md from evals/results/per_run.csv.

    python evals/finalize_docs.py

Only text between the <!-- ...:START --> / <!-- ...:END --> markers is replaced, so every number in the docs
comes from the committed result files. Also prints the memo word count (limit 500).
"""
from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
from run_comparison import _b, _num, read_rows  # noqa: E402

QUALITY = ("approvals_exact", "flags_exact", "next_action_ok", "missing_ok", "human_review_ok", "grounding_ok", "degraded_ok")


def case_ok(r: dict) -> bool:
    return all(_b(r[k]) for k in QUALITY) and _b(r["injection_resisted"]) is not False


def column(rows: list[dict], arch: str) -> dict | None:
    rs = [r for r in rows if r["arch"] == arch and (_b(r["llm_ok"]) or arch == "engine")]
    if not rs:
        return None
    by_case: dict[str, list[dict]] = {}
    for r in rs:
        by_case.setdefault(r["case_id"], []).append(r)
    mean = lambda k: statistics.mean(_num(rs, k)) if _num(rs, k) else 0.0  # noqa: E731
    return {"cases": len(by_case), "pass": sum(all(case_ok(r) for r in v) for v in by_case.values()),
            "latency": mean("latency_ms") / 1000, "llm": mean("llm_calls"), "tool": mean("tool_calls"),
            "policy_fail": sum(1 for r in rs if _b(r["policy_failure"])), "runs": len(rs), "total": len([r for r in rows if r["arch"] == arch])}


def memo_table(rows: list[dict]) -> str:
    cols = {a: column(rows, a) for a in ("engine", "single", "staged")}
    # Timing: repeat-2 rows, which exclude time spent waiting on provider 429s; LLM calls exclude those failed attempts.
    for a in ("single", "staged"):
        r2 = [r for r in rows if r["arch"] == a and r["rep"] == "2" and _b(r["llm_ok"])]
        if cols[a] and r2:
            cols[a]["latency"] = statistics.mean(_num(r2, "latency_ms")) / 1000
            cols[a]["llm"] = statistics.mean(c - (f or 0) for c, f in zip(_num(r2, "llm_calls"), _num(r2, "llm_failed_attempts") or [0] * len(r2)))

    def cell(a, f):
        c = cols[a]
        return "not run" if c is None else f(c)

    lines = ["| Metric | Engine only (no LLM) | A single agent | B staged |", "|---|---:|---:|---:|",
             "| Cases fully correct | " + " | ".join(cell(a, lambda c: f"{c['pass']}/{c['cases']}") for a in cols) + " |",
             "| Avg latency | " + " | ".join(cell(a, lambda c: f"{c['latency']:.1f}s") for a in cols) + " |",
             "| Avg LLM calls | " + " | ".join(cell(a, lambda c: f"{c['llm']:.1f}") for a in cols) + " |",
             "| Avg tool calls | " + " | ".join(cell(a, lambda c: f"{c['tool']:.1f}") for a in cols) + " |",
             "| Policy/grounding failures | " + " | ".join(cell(a, lambda c: f"{c['policy_fail']} in {c['runs']} runs") for a in cols) + " |"]
    notes = []
    for a, name in (("single", "A"), ("staged", "B")):
        c = cols[a]
        if c is None:
            notes.append(f"{name}: no LLM-healthy runs recorded")
        elif c["runs"] < c["total"]:
            notes.append(f"{name}: {c['total'] - c['runs']} of {c['total']} runs excluded (LLM provider failed)")
    if notes:
        lines.append("\n" + "; ".join(notes) + ".")
    return "\n".join(lines)


def replace_block(path: Path, name: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"(<!-- {name}:START -->).*?(<!-- {name}:END -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker {name} not found in {path}")
    path.write_text(pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text), encoding="utf-8")


def main() -> None:
    rows = read_rows()
    if not rows:
        raise SystemExit("no results: run python evals/run_comparison.py first")
    summary = (ROOT / "evals" / "results" / "summary.md").read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## ", summary)
    keep = [s for s in sections if s.startswith(("All cases", "Held-out synthetic"))]
    replace_block(ROOT / "README.md", "RESULTS", "\n".join("### " + s.strip() + "\n" for s in keep))
    replace_block(ROOT / "docs" / "architecture_decision_memo.md", "MEMO_TABLE", memo_table(rows))
    memo = (ROOT / "docs" / "architecture_decision_memo.md").read_text(encoding="utf-8")
    words = len(re.findall(r"\S+", memo))
    print(f"memo words: {words} (limit 500)")


if __name__ == "__main__":
    main()
