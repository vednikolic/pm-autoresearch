#!/bin/bash
# PM AutoResearch Meta-Run: Setup Script
# Run this once to initialize the meta-run workspace.
#
# Usage:
#   chmod +x setup.sh && ./setup.sh

set -e

echo "=== PM AutoResearch Meta-Run Setup ==="

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 required"
    exit 1
fi

if ! command -v claude &> /dev/null; then
    echo "ERROR: claude CLI not found. Install Claude Code first."
    exit 1
fi

# Resolve repo root (walk up from meta-run/ to repo root)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_PATH="$REPO_ROOT/.claude/skills/pm-autoresearch/SKILL.md"

# Copy SKILL.md as target.md (the file the agent will edit)
if [ ! -f target.md ]; then
    if [ -f "$SKILL_PATH" ]; then
        cp "$SKILL_PATH" target.md
        echo "Copied $SKILL_PATH -> target.md"
    else
        echo "ERROR: Cannot find SKILL.md at $SKILL_PATH"
        echo "Expected repo structure: <repo>/.claude/skills/pm-autoresearch/SKILL.md"
        echo "Or manually copy it to this directory as target.md"
        exit 1
    fi
fi

# Initialize git if needed
if [ ! -d .git ]; then
    git init
    echo "run.log" >> .gitignore
    echo "baseline.log" >> .gitignore
    echo "results.tsv" >> .gitignore
    echo "__pycache__/" >> .gitignore
    git add .gitignore eval.py evals.json program.md target.md
    git commit -m "initial: meta-run setup with baseline SKILL.md"
    echo "Git initialized and baseline committed."
else
    echo "Git already initialized."
fi

# Create results.tsv
echo -e "round\tscore\tpassing\ttotal\thypothesis\tchange_description\tkept" > results.tsv
echo "Created results.tsv"

# Run baseline eval
echo ""
echo "Running baseline eval (this takes ~30 seconds)..."
python3 eval.py target.md --verbose 2>&1 | tee baseline.log

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Review baseline.log to see current pass/fail status"
echo "  2. Launch the loop with Claude Code:"
echo "     claude 'Read program.md and begin the autoresearch loop on target.md'"
echo ""
echo "  Or run the automated loop:"
echo "     python3 ../scripts/run_loop.py --target target.md --eval eval.py --program program.md --max-rounds 30 --tag meta-v1"
