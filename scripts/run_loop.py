#!/usr/bin/env python3
"""
PM AutoResearch Loop Runner

Orchestrates the full autoresearch loop: edit target via Claude,
run evals, keep or revert, log results, repeat.

Usage:
    python run_loop.py --target target.md --eval eval.py --max-rounds 50
    python run_loop.py --target target.md --eval eval.py --max-rounds 50 --tag mar21

Requirements:
    - anthropic SDK installed
    - git initialized in the working directory
    - eval.py and target.md present
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("ERROR: pip install anthropic")
    sys.exit(1)

MODEL = "claude-sonnet-4-20250514"


def run_command(cmd: str, timeout: int = 120) -> tuple:
    """Run a shell command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 1


def run_eval(eval_script: str, target: str) -> dict:
    """Run the eval harness and parse results."""
    stdout, stderr, rc = run_command(f"python {eval_script} {target} --output json")
    if rc != 0:
        return {"error": stderr, "composite_score": 0}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": f"Parse error: {stdout[:200]}", "composite_score": 0}


def get_failing_evals(eval_results: dict) -> list:
    """Extract list of failing eval IDs and checks."""
    if "results" not in eval_results:
        return []
    return [
        {"id": r["id"], "category": r["category"]}
        for r in eval_results["results"]
        if not r["passed"]
    ]


def propose_edit(client, target_content: str, failing_evals: list, history: list, program: str) -> dict:
    """Ask Claude to propose a single focused edit to target.md."""
    history_summary = ""
    if history:
        recent = history[-5:]  # last 5 experiments
        history_summary = "Recent experiments:\n"
        for h in recent:
            status = "KEPT" if h["kept"] else "REVERTED"
            history_summary += f"  Round {h['round']}: {h['change']} -> {status} (score: {h['score']})\n"

    failing_summary = "\n".join(f"  FAILING: [{e['category']}] {e['id']}" for e in failing_evals)

    prompt = f"""You are improving a PM document through iterative experimentation.

<program>
{program}
</program>

<current_document>
{target_content}
</current_document>

<failing_evals>
{failing_summary}
</failing_evals>

{history_summary}

Make ONE focused change to improve the document's eval score. Target the most impactful failing eval.

Respond with JSON only:
{{
    "hypothesis": "One sentence explaining what you'll change and why",
    "change_description": "Brief label for the change (for the experiment log)",
    "new_document": "The complete updated document content"
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]

    return json.loads(text)


def git_commit(target: str, message: str):
    run_command(f'git add {target} && git commit -m "{message}"')


def git_revert(target: str):
    run_command(f"git checkout -- {target}")


def main():
    parser = argparse.ArgumentParser(description="PM AutoResearch Loop Runner")
    parser.add_argument("--target", required=True, help="Path to target.md")
    parser.add_argument("--eval", required=True, help="Path to eval.py")
    parser.add_argument("--program", default="program.md", help="Path to program.md")
    parser.add_argument("--max-rounds", type=int, default=50, help="Max experiment rounds")
    parser.add_argument("--tag", default=None, help="Git branch tag (default: date)")
    parser.add_argument("--plateau-limit", type=int, default=10, help="Stop after N consecutive reverts")
    args = parser.parse_args()

    # Validate files exist
    for f in [args.target, args.eval]:
        if not os.path.exists(f):
            print(f"ERROR: {f} not found")
            sys.exit(1)

    # Read program.md if it exists
    program = ""
    if os.path.exists(args.program):
        with open(args.program) as f:
            program = f.read()

    # Setup git branch
    tag = args.tag or datetime.now().strftime("%b%d").lower()
    branch = f"autoresearch/{tag}"
    run_command(f"git checkout -b {branch}")

    # Initialize results.tsv
    results_path = "results.tsv"
    with open(results_path, "w") as f:
        f.write("round\tscore\tpassing\ttotal\thypothesis\tchange_description\tkept\n")

    # Run baseline
    print("Running baseline eval...")
    baseline = run_eval(args.eval, args.target)
    if "error" in baseline:
        print(f"Baseline eval failed: {baseline['error']}")
        sys.exit(1)

    best_score = baseline["composite_score"]
    print(f"Baseline score: {best_score}%")

    # Log baseline
    with open(results_path, "a") as f:
        f.write(f"0\t{best_score}\t{baseline['passing']}\t{baseline['total']}\tbaseline\tbaseline\ttrue\n")

    client = anthropic.Anthropic()
    history = []
    consecutive_reverts = 0

    for round_num in range(1, args.max_rounds + 1):
        print(f"\n{'='*40}")
        print(f"Round {round_num}/{args.max_rounds} | Best: {best_score}%")
        print(f"{'='*40}")

        # Get current failing evals
        current_eval = run_eval(args.eval, args.target)
        failing = get_failing_evals(current_eval)

        if not failing:
            print("All evals passing! Score: 100%")
            break

        # Propose edit
        with open(args.target) as f:
            current_content = f.read()

        try:
            proposal = propose_edit(client, current_content, failing, history, program)
        except Exception as e:
            print(f"  Proposal failed: {e}")
            history.append({"round": round_num, "score": best_score, "change": "PROPOSAL_ERROR", "kept": False})
            consecutive_reverts += 1
            continue

        print(f"  Hypothesis: {proposal['hypothesis']}")
        print(f"  Change: {proposal['change_description']}")

        # Apply edit
        with open(args.target, "w") as f:
            f.write(proposal["new_document"])

        # Run eval
        new_eval = run_eval(args.eval, args.target)
        new_score = new_eval.get("composite_score", 0)
        passing = new_eval.get("passing", 0)
        total = new_eval.get("total", 0)

        print(f"  Score: {new_score}% (was {best_score}%)")

        # Keep or revert
        if new_score > best_score:
            git_commit(args.target, f"autoresearch: {proposal['change_description']} | score: {new_score}")
            print(f"  KEPT (+{round(new_score - best_score, 2)}%)")
            best_score = new_score
            kept = True
            consecutive_reverts = 0
        else:
            git_revert(args.target)
            print(f"  REVERTED")
            kept = False
            consecutive_reverts += 1

        # Log
        with open(results_path, "a") as f:
            hyp = proposal.get("hypothesis", "").replace("\t", " ")
            desc = proposal.get("change_description", "").replace("\t", " ")
            f.write(f"{round_num}\t{new_score}\t{passing}\t{total}\t{hyp}\t{desc}\t{kept}\n")

        history.append({
            "round": round_num,
            "score": new_score,
            "change": proposal.get("change_description", ""),
            "kept": kept,
        })

        # Plateau check
        if consecutive_reverts >= args.plateau_limit:
            print(f"\nPLATEAU: {consecutive_reverts} consecutive reverts. Stopping.")
            break

        time.sleep(1)  # brief pause between rounds

    # Summary
    print(f"\n{'='*50}")
    print(f"RUN COMPLETE")
    print(f"{'='*50}")
    print(f"Rounds: {round_num}")
    print(f"Baseline: {baseline['composite_score']}% -> Final: {best_score}%")
    print(f"Improvement: +{round(best_score - baseline['composite_score'], 2)}%")
    kept_count = sum(1 for h in history if h["kept"])
    print(f"Kept: {kept_count} | Reverted: {len(history) - kept_count}")
    print(f"\nResults logged to {results_path}")
    print(f"Git log: git log --oneline {branch}")


if __name__ == "__main__":
    main()
