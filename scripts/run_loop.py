#!/usr/bin/env python3
"""
PM AutoResearch Loop Runner

Orchestrates the full autoresearch loop: edit target via Claude,
run scoring, keep or revert, log results, repeat.

Uses `claude -p` (Claude Code CLI) instead of the Anthropic API.
Runs on a Pro subscription with no API key required.

Usage:
    python run_loop.py --target target.md --scoring scoring.py --max-rounds 50
    python run_loop.py --target target.md --scoring scoring.py --max-rounds 50 --tag mar21

Requirements:
    - claude CLI installed and authenticated
    - git initialized in the working directory
    - scoring.py and target.md present
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from functools import partial

# Unbuffered print so terminal shows progress immediately
print = partial(print, flush=True)


def run_command(cmd: str, timeout: int = 120) -> tuple:
    """Run a shell command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 1


def run_scoring(scoring_script: str, target: str) -> dict:
    """Run the scoring harness and parse results."""
    stdout, stderr, rc = run_command(
        f"python3 {scoring_script} {target} --output json",
        timeout=600,
    )
    if rc != 0:
        return {"error": stderr, "composite_score": 0}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": f"Parse error: {stdout[:200]}", "composite_score": 0}


def get_failing_checks(results: dict) -> list:
    """Extract list of failing check IDs and categories."""
    if "results" not in results:
        return []
    return [
        {"id": r["id"], "category": r["category"]}
        for r in results["results"]
        if not r["passed"]
    ]


def propose_edit(target_content: str, failing_checks: list, history: list, program: str) -> dict:
    """Ask Claude to propose a single focused edit to target.md via claude -p."""
    history_summary = ""
    if history:
        recent = history[-5:]
        history_summary = "Recent experiments:\n"
        for h in recent:
            status = "KEPT" if h["kept"] else "REVERTED"
            history_summary += f"  Round {h['round']}: {h['change']} -> {status} (score: {h['score']})\n"

    failing_summary = "\n".join(f"  FAILING: [{e['category']}] {e['id']}" for e in failing_checks)

    prompt = f"""You are improving a PM document through iterative experimentation.

<program>
{program}
</program>

<current_document>
{target_content}
</current_document>

<failing_checks>
{failing_summary}
</failing_checks>

{history_summary}

Make ONE focused change to improve the document's score. Target the most impactful failing check.

Respond with JSON only:
{{
    "hypothesis": "One sentence explaining what you'll change and why",
    "change_description": "Brief label for the change (for the experiment log)",
    "new_document": "The complete updated document content"
}}"""

    result = subprocess.run(
        [
            "claude", "-p",
            "--model", "sonnet",
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed: {result.stderr[:200]}")

    text = result.stdout.strip()
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
    parser.add_argument("--scoring", "--eval", required=True, dest="scoring", help="Path to scoring harness (e.g. eval.py)")
    parser.add_argument("--program", default="program.md", help="Path to program.md")
    parser.add_argument("--max-rounds", type=int, default=50, help="Max experiment rounds")
    parser.add_argument("--tag", default=None, help="Git branch tag (default: date)")
    parser.add_argument("--plateau-limit", type=int, default=10, help="Stop after N consecutive reverts")
    args = parser.parse_args()

    # Check claude CLI is available
    stdout, _, rc = run_command("claude --version")
    if rc != 0:
        print("ERROR: claude CLI not found. Install Claude Code first.")
        sys.exit(1)
    print(f"Using claude CLI: {stdout.strip()}")

    # Validate files exist
    for f in [args.target, args.scoring]:
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
    print("Running baseline scoring...")
    baseline = run_scoring(args.scoring, args.target)
    if "error" in baseline:
        print(f"Baseline scoring failed: {baseline['error']}")
        sys.exit(1)

    best_score = baseline["composite_score"]
    print(f"Baseline score: {best_score}%")

    # Log baseline
    with open(results_path, "a") as f:
        f.write(f"0\t{best_score}\t{baseline['passing']}\t{baseline['total']}\tbaseline\tbaseline\ttrue\n")

    history = []
    consecutive_reverts = 0
    last_results = baseline  # Reuse baseline; only re-score after edits

    for round_num in range(1, args.max_rounds + 1):
        print(f"\n{'='*40}")
        print(f"Round {round_num}/{args.max_rounds} | Best: {best_score}%")
        print(f"{'='*40}")

        # Use previous round's results for failing checks (avoids double-scoring)
        failing = get_failing_checks(last_results)

        if not failing:
            print("All checks passing! Score: 100%")
            break

        # Propose edit
        with open(args.target) as f:
            current_content = f.read()

        try:
            proposal = propose_edit(current_content, failing, history, program)
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

        # Run scoring
        new_results = run_scoring(args.scoring, args.target)
        new_score = new_results.get("composite_score", 0)
        passing = new_results.get("passing", 0)
        total = new_results.get("total", 0)

        print(f"  Score: {new_score}% (was {best_score}%)")

        # Keep or revert
        if new_score > best_score:
            git_commit(args.target, f"autoresearch: {proposal['change_description']} | score: {new_score}")
            print(f"  KEPT (+{round(new_score - best_score, 2)}%)")
            best_score = new_score
            last_results = new_results  # Carry forward new results
            kept = True
            consecutive_reverts = 0
        else:
            git_revert(args.target)
            print(f"  REVERTED")
            # last_results stays unchanged (document reverted to previous state)
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

        time.sleep(1)

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
