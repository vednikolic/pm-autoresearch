#!/usr/bin/env python3
"""
PM AutoResearch Eval Harness Template

This is the scoring harness. The agent CANNOT modify this file.
It reads the target document, runs each binary eval via Claude,
and outputs a composite score.

Usage:
    python eval.py target.md
    python eval.py target.md --verbose
    python eval.py target.md --output json
"""

import json
import sys
import os
import time

try:
    import anthropic
except ImportError:
    print("ERROR: pip install anthropic")
    sys.exit(1)

# ============================================================
# EVALS: Define your binary eval suite here.
# Each eval is a yes/no question scored as 1 (pass) or 0 (fail).
# DO NOT let the agent modify this section.
# ============================================================

EVALS = [
    # --- STRUCTURE ---
    {
        "id": "has_problem_statement",
        "category": "structure",
        "check": "Does the document contain a clearly defined problem statement in its own section or paragraph?",
        "weight": 1.5
    },
    {
        "id": "has_success_metrics",
        "category": "structure",
        "check": "Does the document define at least 3 quantitative success metrics with specific numeric targets?",
        "weight": 1.5
    },
    {
        "id": "has_non_goals",
        "category": "structure",
        "check": "Does the document explicitly list what is NOT in scope?",
        "weight": 1.0
    },
    {
        "id": "has_target_user",
        "category": "structure",
        "check": "Does the document identify specific user segments or personas?",
        "weight": 1.0
    },

    # --- REASONING ---
    {
        "id": "metrics_trace_to_problem",
        "category": "reasoning",
        "check": "Does every success metric directly address an aspect of the stated problem?",
        "weight": 1.0
    },
    {
        "id": "has_evidence",
        "category": "reasoning",
        "check": "Does the document cite at least 2 pieces of external evidence (data, research, benchmarks, user feedback)?",
        "weight": 1.0
    },
    {
        "id": "risks_have_mitigations",
        "category": "reasoning",
        "check": "Does every identified risk have at least one mitigation or contingency?",
        "weight": 1.0
    },

    # --- SPECIFICITY ---
    {
        "id": "no_vague_timelines",
        "category": "specificity",
        "check": "Are all timelines expressed as specific dates, sprint numbers, or quarters (not 'soon', 'later', 'eventually')?",
        "weight": 1.0
    },
    {
        "id": "no_weasel_words",
        "category": "specificity",
        "check": "Is the document free of hedging language like 'might', 'could potentially', 'ideally', 'hopefully'?",
        "weight": 0.5
    },
    {
        "id": "metrics_have_targets",
        "category": "specificity",
        "check": "Does every success metric include a specific numeric target (not just 'improve' or 'increase')?",
        "weight": 1.0
    },

    # --- COMPLETENESS ---
    {
        "id": "has_edge_cases",
        "category": "completeness",
        "check": "Does the document address at least 2 edge cases or failure modes?",
        "weight": 1.0
    },
    {
        "id": "has_dependencies",
        "category": "completeness",
        "check": "Does the document identify external teams, systems, or decisions it depends on?",
        "weight": 1.0
    },

    # --- CLARITY ---
    {
        "id": "jargon_defined",
        "category": "clarity",
        "check": "Is every technical term or acronym either widely known or defined on first use?",
        "weight": 0.5
    },
]

# ============================================================
# SCORING ENGINE (do not modify below)
# ============================================================

MODEL = "claude-sonnet-4-20250514"

JUDGE_SYSTEM = """You are a binary document evaluator. You will be given a document and a yes/no question about it.

Rules:
- Answer ONLY "YES" or "NO". Nothing else.
- Be strict. If the answer is ambiguous or partially true, answer NO.
- Base your answer solely on what is explicitly present in the document.
- Do not infer, assume, or give benefit of the doubt.
"""


def evaluate_single(client, document: str, eval_item: dict) -> dict:
    """Run a single binary eval against the document."""
    prompt = f"""<document>
{document}
</document>

Question: {eval_item['check']}

Answer YES or NO only."""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=5,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.content[0].text.strip().upper()
        passed = answer.startswith("YES")
    except Exception as e:
        print(f"  ERROR evaluating {eval_item['id']}: {e}", file=sys.stderr)
        passed = False

    return {
        "id": eval_item["id"],
        "category": eval_item["category"],
        "passed": passed,
        "weight": eval_item.get("weight", 1.0),
    }


def run_evals(document_path: str, verbose: bool = False, output_format: str = "text") -> dict:
    """Run all evals against a document and return results."""
    client = anthropic.Anthropic()

    with open(document_path, "r") as f:
        document = f.read()

    results = []
    for i, eval_item in enumerate(EVALS):
        if verbose:
            print(f"  [{i+1}/{len(EVALS)}] {eval_item['id']}...", file=sys.stderr)
        result = evaluate_single(client, document, eval_item)
        results.append(result)
        time.sleep(0.2)  # rate limit buffer

    # Compute scores
    total_weight = sum(r["weight"] for r in results)
    passing_weight = sum(r["weight"] for r in results if r["passed"])
    composite_score = (passing_weight / total_weight * 100) if total_weight > 0 else 0
    passing_count = sum(1 for r in results if r["passed"])

    # Category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "total": 0, "weight_passed": 0, "weight_total": 0}
        categories[cat]["total"] += 1
        categories[cat]["weight_total"] += r["weight"]
        if r["passed"]:
            categories[cat]["passed"] += 1
            categories[cat]["weight_passed"] += r["weight"]

    output = {
        "composite_score": round(composite_score, 2),
        "passing": passing_count,
        "total": len(results),
        "categories": categories,
        "results": results,
    }

    return output


def print_results(output: dict, format: str = "text"):
    """Print results in the specified format."""
    if format == "json":
        print(json.dumps(output, indent=2))
        return

    # Text format (parseable by the agent)
    print(f"composite_score: {output['composite_score']}")
    print(f"passing: {output['passing']}/{output['total']}")
    print()
    print("--- Category Breakdown ---")
    for cat, data in output["categories"].items():
        pct = (data["weight_passed"] / data["weight_total"] * 100) if data["weight_total"] > 0 else 0
        print(f"  {cat}: {data['passed']}/{data['total']} ({pct:.0f}%)")
    print()
    print("--- Individual Results ---")
    for r in output["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['id']} (weight: {r['weight']})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python eval.py <target.md> [--verbose] [--output json]")
        sys.exit(1)

    doc_path = sys.argv[1]
    verbose = "--verbose" in sys.argv
    output_fmt = "json" if "--output" in sys.argv and "json" in sys.argv else "text"

    if not os.path.exists(doc_path):
        print(f"ERROR: {doc_path} not found")
        sys.exit(1)

    results = run_evals(doc_path, verbose=verbose)
    print_results(results, format=output_fmt)
