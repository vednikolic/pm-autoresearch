#!/usr/bin/env python3
"""
PM AutoResearch Meta-Run Eval Harness
Scores SKILL.md quality with 20 strict binary evals.
DO NOT MODIFY. The agent cannot touch this file.

Uses `claude -p` (Claude Code CLI) instead of the Anthropic API.
Runs on a Pro subscription with no API key required.

Usage:
    python eval.py target.md
    python eval.py target.md --verbose
    python eval.py target.md --output json
"""

import json
import subprocess
import sys
import os

EVALS = [
    {
        "id": "workflow_numbered_steps",
        "category": "instructional_clarity",
        "check": "Does the skill define a clear step-by-step workflow where each step is numbered and starts with an action verb specifying what to produce or do?",
        "weight": 1.5
    },
    {
        "id": "decision_points_explicit",
        "category": "instructional_clarity",
        "check": "Does the skill explicitly define decision points with conditional logic (if X then Y, if Z then W) for at least 3 different situations the user or agent might encounter?",
        "weight": 1.5
    },
    {
        "id": "behavioral_consistency",
        "category": "instructional_clarity",
        "check": "Is every instruction in the skill specific enough that two different Claude instances following it would produce substantially the same behavior?",
        "weight": 0.5
    },
    {
        "id": "no_unqualified_vague_words",
        "category": "instructional_clarity",
        "check": "Are there zero instances of vague directives like 'consider', 'think about', or 'as needed' that appear without an immediately following specification of the exact action to take?",
        "weight": 0.5
    },
    {
        "id": "workflow_commands_copy_pasteable",
        "category": "instructional_clarity",
        "check": "Are all shell commands in the numbered setup and workflow steps (Steps 1 through 6) complete and copy-pasteable without requiring the reader to fill in placeholder arguments or paths?",
        "weight": 0.5
    },
    {
        "id": "example_commands_use_concrete_values",
        "category": "instructional_clarity",
        "check": "When the skill shows example shell commands outside the core workflow (such as LLM_COMMAND usage or script invocations), does it use a concrete, realistic example value rather than an abstract placeholder like 'your-X-here'?",
        "weight": 0.5
    },
    {
        "id": "covers_setup_phase",
        "category": "completeness",
        "check": "Does the skill thoroughly cover the initialization and setup phase, including git initialization, baseline eval run, results.tsv creation, and branch setup, with explicit commands for each?",
        "weight": 1.0
    },
    {
        "id": "covers_iteration_phase",
        "category": "completeness",
        "check": "Does the skill describe the iteration loop in enough detail that an agent could execute it autonomously, including: how to read eval results, how to form a hypothesis, how to make an edit, how to run the eval, how to interpret the score, and how to keep or revert?",
        "weight": 1.5
    },
    {
        "id": "covers_analysis_phase",
        "category": "completeness",
        "check": "Does the skill explain how to analyze results after a run completes, including what to look for in the experiment log, how to detect plateaus, and what actions to take based on the analysis?",
        "weight": 1.0
    },
    {
        "id": "error_handling_documented",
        "category": "completeness",
        "check": "Does the skill address at least 3 specific failure modes or error cases (such as eval crashes, API errors, git conflicts, score regression, plateau) with concrete recovery steps for each?",
        "weight": 1.0
    },
    {
        "id": "cost_estimation_specific",
        "category": "completeness",
        "check": "Does the skill provide a specific cost estimate per round AND per full run, with the model and approximate token counts that drive those numbers?",
        "weight": 0.5
    },
    {
        "id": "good_eval_examples_with_contrast",
        "category": "eval_framework",
        "check": "Does the skill provide at least 3 examples of GOOD binary evals AND at least 3 examples of BAD binary evals, with explicit explanations of why each is good or bad?",
        "weight": 1.5
    },
    {
        "id": "eval_evolution_guidance",
        "category": "eval_framework",
        "check": "Does the skill explain how to evolve the eval suite between runs, including when to add harder evals, when to remove saturated ones, and when to adjust weights, with concrete criteria for each decision?",
        "weight": 1.0
    },
    {
        "id": "eval_templates_three_types",
        "category": "eval_framework",
        "check": "Does the skill provide complete, ready-to-use eval templates (not just category names, but actual eval check questions) for at least 3 different document types?",
        "weight": 1.0
    },
    {
        "id": "scoring_model_explained",
        "category": "eval_framework",
        "check": "Does the skill explain the scoring model in detail, including how weights work, what the composite score formula is, and what the keep/revert threshold logic is?",
        "weight": 1.0
    },
    {
        "id": "pattern_self_contained",
        "category": "self_containment",
        "check": "Does the skill explain the autoresearch pattern (loop, ratchet, single-file constraint, locked eval) thoroughly enough that someone who has never heard of Karpathy's autoresearch could understand and use it without reading any external source?",
        "weight": 1.5
    },
    {
        "id": "no_undefined_references",
        "category": "self_containment",
        "check": "Does every file path, script name, and template referenced in the skill have its purpose explained and its location specified, with no dangling references to files or tools that are mentioned but not described?",
        "weight": 1.0
    },
    {
        "id": "adaptation_has_specific_evals",
        "category": "adaptation",
        "check": "For each document type the skill claims to support (PRDs, strategy docs, prompts, etc.), does it provide at least 5 specific, ready-to-use binary eval check questions (not just category labels like 'focus on logical coherence')?",
        "weight": 1.5
    },
    {
        "id": "adaptation_has_program_hints",
        "category": "adaptation",
        "check": "For each document type the skill claims to support, does it provide specific research direction hints that an agent should explore, tailored to that document type?",
        "weight": 1.0
    },
    {
        "id": "trigger_description_comprehensive",
        "category": "triggering",
        "check": "Does the skill's description (in the YAML frontmatter) include at least 8 distinct trigger phrases or contexts that would cause it to activate, covering variations in how a user might request this capability?",
        "weight": 0.5
    }
]

JUDGE_SYSTEM = """You are a strict binary document evaluator. You will be given a document and a yes/no question about it.

Rules:
- Answer ONLY "YES" or "NO". Nothing else.
- Be strict. If the answer is ambiguous, partially true, or only loosely addressed, answer NO.
- Base your answer solely on what is explicitly present in the document.
- Do not infer, assume, or give benefit of the doubt.
- "Mentioned briefly" is not the same as "thoroughly addressed". If the question asks for thorough coverage, a passing mention does not count.
"""


def evaluate_single(document: str, eval_item: dict) -> dict:
    """Run a single binary eval via claude -p."""
    prompt = f"""<document>
{document}
</document>

Question: {eval_item['check']}

Answer YES or NO only."""

    try:
        result = subprocess.run(
            [
                "claude", "-p",
                "--model", "sonnet",
                "--system-prompt", JUDGE_SYSTEM,
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"  ERROR evaluating {eval_item['id']}: {result.stderr[:200]}", file=sys.stderr)
            return {
                "id": eval_item["id"],
                "category": eval_item["category"],
                "passed": False,
                "weight": eval_item.get("weight", 1.0),
            }
        answer = result.stdout.strip().upper()
        passed = answer.startswith("YES")
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT evaluating {eval_item['id']}", file=sys.stderr)
        passed = False
    except Exception as e:
        print(f"  ERROR evaluating {eval_item['id']}: {e}", file=sys.stderr)
        passed = False

    return {
        "id": eval_item["id"],
        "category": eval_item["category"],
        "passed": passed,
        "weight": eval_item.get("weight", 1.0),
    }


def run_evals(document_path: str, verbose: bool = False) -> dict:
    """Run all evals against a document."""
    with open(document_path, "r") as f:
        document = f.read()

    results = []
    for i, eval_item in enumerate(EVALS):
        if verbose:
            print(f"  [{i+1}/{len(EVALS)}] {eval_item['id']}...", file=sys.stderr)
        result = evaluate_single(document, eval_item)
        results.append(result)
        if verbose:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"           -> {status}", file=sys.stderr)

    total_weight = sum(r["weight"] for r in results)
    passing_weight = sum(r["weight"] for r in results if r["passed"])
    composite_score = (passing_weight / total_weight * 100) if total_weight > 0 else 0
    passing_count = sum(1 for r in results if r["passed"])

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

    return {
        "composite_score": round(composite_score, 2),
        "passing": passing_count,
        "total": len(results),
        "categories": categories,
        "results": results,
    }


def print_results(output: dict, fmt: str = "text"):
    if fmt == "json":
        print(json.dumps(output, indent=2))
        return

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
    print_results(results, fmt=output_fmt)
