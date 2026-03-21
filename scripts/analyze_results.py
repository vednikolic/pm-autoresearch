#!/usr/bin/env python3
"""
Analyze results.tsv from a PM AutoResearch run.

Usage:
    python analyze_results.py results.tsv
    python analyze_results.py results.tsv --output json
"""

import sys
import csv
import json


def load_results(path: str) -> list:
    results = []
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            row["round"] = int(row["round"])
            row["score"] = float(row["score"])
            row["passing"] = int(row["passing"])
            row["total"] = int(row["total"])
            row["kept"] = row["kept"].lower() == "true"
            results.append(row)
    return results


def analyze(results: list) -> dict:
    if not results:
        return {"error": "No results to analyze"}

    total_rounds = len(results)
    kept = [r for r in results if r["kept"]]
    reverted = [r for r in results if not r["kept"]]

    baseline_score = results[0]["score"]
    final_score = max(r["score"] for r in kept) if kept else baseline_score

    # Score trajectory (kept only)
    trajectory = []
    current_best = baseline_score
    for r in results:
        if r["kept"] and r["score"] > current_best:
            current_best = r["score"]
        trajectory.append({"round": r["round"], "best_score": current_best, "kept": r["kept"]})

    # Biggest improvements
    improvements = []
    prev_best = baseline_score
    for r in kept:
        if r["score"] > prev_best:
            delta = r["score"] - prev_best
            improvements.append({
                "round": r["round"],
                "delta": round(delta, 2),
                "new_score": r["score"],
                "change": r.get("change_description", ""),
            })
            prev_best = r["score"]

    improvements.sort(key=lambda x: x["delta"], reverse=True)

    # Plateau detection
    longest_streak = 0
    current_streak = 0
    for r in results:
        if not r["kept"]:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

    return {
        "summary": {
            "total_rounds": total_rounds,
            "kept": len(kept),
            "reverted": len(reverted),
            "keep_rate": round(len(kept) / total_rounds * 100, 1) if total_rounds > 0 else 0,
            "baseline_score": baseline_score,
            "final_score": final_score,
            "total_improvement": round(final_score - baseline_score, 2),
        },
        "top_improvements": improvements[:5],
        "longest_revert_streak": longest_streak,
        "plateau_warning": longest_streak >= 10,
        "trajectory": trajectory,
    }


def print_analysis(analysis: dict, fmt: str = "text"):
    if fmt == "json":
        print(json.dumps(analysis, indent=2))
        return

    s = analysis["summary"]
    print("=" * 50)
    print("PM AUTORESEARCH RUN ANALYSIS")
    print("=" * 50)
    print()
    print(f"Rounds:      {s['total_rounds']}")
    print(f"Kept:        {s['kept']} ({s['keep_rate']}%)")
    print(f"Reverted:    {s['reverted']}")
    print()
    print(f"Baseline:    {s['baseline_score']}%")
    print(f"Final:       {s['final_score']}%")
    print(f"Improvement: +{s['total_improvement']}%")
    print()

    if analysis["top_improvements"]:
        print("Top Improvements:")
        for imp in analysis["top_improvements"]:
            print(f"  Round {imp['round']}: +{imp['delta']}% -> {imp['new_score']}%")
            if imp["change"]:
                print(f"    {imp['change']}")
        print()

    if analysis["plateau_warning"]:
        print(f"WARNING: Longest streak of {analysis['longest_revert_streak']} consecutive reverts.")
        print("Consider updating evals or program.md hints before the next run.")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py results.tsv [--output json]")
        sys.exit(1)

    results = load_results(sys.argv[1])
    analysis = analyze(results)
    fmt = "json" if "--output" in sys.argv and "json" in sys.argv else "text"
    print_analysis(analysis, fmt=fmt)
