#!/usr/bin/env python3
"""
Generate an eval.py harness from an evals.json definition file.

Usage:
    python generate_eval.py --evals evals.json --output eval.py
    python generate_eval.py --evals evals.json --output eval.py --model claude-sonnet-4-20250514

evals.json format:
[
    {
        "id": "has_problem_statement",
        "category": "structure",
        "check": "Does the document contain a clearly defined problem statement?",
        "weight": 1.5
    },
    ...
]
"""

import json
import sys
import argparse

TEMPLATE_HEADER = '''#!/usr/bin/env python3
"""
PM AutoResearch Eval Harness (auto-generated)
DO NOT MODIFY. The agent cannot touch this file.

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

MODEL = "{model}"

EVALS = {evals_json}

JUDGE_SYSTEM = """You are a binary document evaluator. You will be given a document and a yes/no question about it.

Rules:
- Answer ONLY "YES" or "NO". Nothing else.
- Be strict. If the answer is ambiguous or partially true, answer NO.
- Base your answer solely on what is explicitly present in the document.
- Do not infer, assume, or give benefit of the doubt.
"""


def evaluate_single(client, document: str, eval_item: dict) -> dict:
    prompt = f"""<document>
{{document}}
</document>

Question: {{eval_item['check']}}

Answer YES or NO only."""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=5,
            system=JUDGE_SYSTEM,
            messages=[{{"role": "user", "content": prompt}}]
        )
        answer = response.content[0].text.strip().upper()
        passed = answer.startswith("YES")
    except Exception as e:
        print(f"  ERROR evaluating {{eval_item['id']}}: {{e}}", file=sys.stderr)
        passed = False

    return {{
        "id": eval_item["id"],
        "category": eval_item["category"],
        "passed": passed,
        "weight": eval_item.get("weight", 1.0),
    }}


def run_evals(document_path: str, verbose: bool = False) -> dict:
    client = anthropic.Anthropic()

    with open(document_path, "r") as f:
        document = f.read()

    results = []
    for i, eval_item in enumerate(EVALS):
        if verbose:
            print(f"  [{{i+1}}/{{len(EVALS)}}] {{eval_item['id']}}...", file=sys.stderr)
        result = evaluate_single(client, document, eval_item)
        results.append(result)
        time.sleep(0.2)

    total_weight = sum(r["weight"] for r in results)
    passing_weight = sum(r["weight"] for r in results if r["passed"])
    composite_score = (passing_weight / total_weight * 100) if total_weight > 0 else 0
    passing_count = sum(1 for r in results if r["passed"])

    categories = {{}}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {{"passed": 0, "total": 0, "weight_passed": 0, "weight_total": 0}}
        categories[cat]["total"] += 1
        categories[cat]["weight_total"] += r["weight"]
        if r["passed"]:
            categories[cat]["passed"] += 1
            categories[cat]["weight_passed"] += r["weight"]

    return {{
        "composite_score": round(composite_score, 2),
        "passing": passing_count,
        "total": len(results),
        "categories": categories,
        "results": results,
    }}


def print_results(output: dict, fmt: str = "text"):
    if fmt == "json":
        print(json.dumps(output, indent=2))
        return

    print(f"composite_score: {{output['composite_score']}}")
    print(f"passing: {{output['passing']}}/{{output['total']}}")
    print()
    print("--- Category Breakdown ---")
    for cat, data in output["categories"].items():
        pct = (data["weight_passed"] / data["weight_total"] * 100) if data["weight_total"] > 0 else 0
        print(f"  {{cat}}: {{data['passed']}}/{{data['total']}} ({{pct:.0f}}%)")
    print()
    print("--- Individual Results ---")
    for r in output["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{{status}}] {{r['id']}} (weight: {{r['weight']}})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python eval.py <target.md> [--verbose] [--output json]")
        sys.exit(1)

    doc_path = sys.argv[1]
    verbose = "--verbose" in sys.argv
    output_fmt = "json" if "--output" in sys.argv and "json" in sys.argv else "text"

    if not os.path.exists(doc_path):
        print(f"ERROR: {{doc_path}} not found")
        sys.exit(1)

    results = run_evals(doc_path, verbose=verbose)
    print_results(results, fmt=output_fmt)
'''


def main():
    parser = argparse.ArgumentParser(description="Generate eval.py from evals.json")
    parser.add_argument("--evals", required=True, help="Path to evals.json")
    parser.add_argument("--output", required=True, help="Output path for eval.py")
    parser.add_argument("--model", default="claude-sonnet-4-20250514", help="Model to use for judging")
    args = parser.parse_args()

    with open(args.evals, "r") as f:
        evals = json.load(f)

    # Validate eval structure
    required_fields = {"id", "category", "check"}
    for i, ev in enumerate(evals):
        missing = required_fields - set(ev.keys())
        if missing:
            print(f"ERROR: Eval {i} missing fields: {missing}")
            sys.exit(1)
        if "weight" not in ev:
            ev["weight"] = 1.0

    evals_json = json.dumps(evals, indent=4)

    output = TEMPLATE_HEADER.format(
        model=args.model,
        evals_json=evals_json,
    )

    with open(args.output, "w") as f:
        f.write(output)

    print(f"Generated {args.output} with {len(evals)} evals")
    print(f"Model: {args.model}")
    print(f"Categories: {', '.join(sorted(set(e['category'] for e in evals)))}")


if __name__ == "__main__":
    main()
