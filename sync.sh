#!/bin/bash
# Sync between standalone pm-autoresearch repo and the claude-workspace monorepo.
#
# Usage:
#   ./sync.sh pull   # Copy FROM workspace INTO this repo
#   ./sync.sh push   # Copy FROM this repo INTO workspace
#
# Set WORKSPACE_ROOT if your workspace is not at ~/claude:
#   WORKSPACE_ROOT=~/my-workspace ./sync.sh pull

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$HOME/claude}"
WORKSPACE_SKILL="$WORKSPACE_ROOT/.claude/skills/pm-autoresearch/SKILL.md"
WORKSPACE_PROJECT="$WORKSPACE_ROOT/1-projects/pm-autoresearch"

if [ ! -d "$WORKSPACE_ROOT" ]; then
    echo "ERROR: Workspace not found at $WORKSPACE_ROOT"
    echo "Set WORKSPACE_ROOT to your claude-workspace location."
    exit 1
fi

case "${1:-}" in
    pull)
        echo "Pulling from workspace -> standalone repo"
        cp "$WORKSPACE_SKILL" "$SCRIPT_DIR/.claude/skills/pm-autoresearch/SKILL.md"
        cp "$WORKSPACE_PROJECT/CLAUDE.md" "$SCRIPT_DIR/CLAUDE.md"
        cp -r "$WORKSPACE_PROJECT/references/" "$SCRIPT_DIR/references/"
        cp -r "$WORKSPACE_PROJECT/scripts/" "$SCRIPT_DIR/scripts/"
        cp -r "$WORKSPACE_PROJECT/templates/" "$SCRIPT_DIR/templates/"
        cp -r "$WORKSPACE_PROJECT/meta-run/eval.py" "$SCRIPT_DIR/meta-run/eval.py"
        cp -r "$WORKSPACE_PROJECT/meta-run/evals.json" "$SCRIPT_DIR/meta-run/evals.json"
        cp -r "$WORKSPACE_PROJECT/meta-run/program.md" "$SCRIPT_DIR/meta-run/program.md"
        cp -r "$WORKSPACE_PROJECT/meta-run/setup.sh" "$SCRIPT_DIR/meta-run/setup.sh"
        cp -r "$WORKSPACE_PROJECT/meta-run/README.md" "$SCRIPT_DIR/meta-run/README.md"
        echo "Done. Review changes with: git diff"
        ;;
    push)
        echo "Pushing from standalone repo -> workspace"
        cp "$SCRIPT_DIR/.claude/skills/pm-autoresearch/SKILL.md" "$WORKSPACE_SKILL"
        cp "$SCRIPT_DIR/CLAUDE.md" "$WORKSPACE_PROJECT/CLAUDE.md"
        cp "$SCRIPT_DIR/references/"* "$WORKSPACE_PROJECT/references/"
        cp "$SCRIPT_DIR/scripts/"* "$WORKSPACE_PROJECT/scripts/"
        cp "$SCRIPT_DIR/templates/"* "$WORKSPACE_PROJECT/templates/"
        cp "$SCRIPT_DIR/meta-run/eval.py" "$WORKSPACE_PROJECT/meta-run/eval.py"
        cp "$SCRIPT_DIR/meta-run/evals.json" "$WORKSPACE_PROJECT/meta-run/evals.json"
        cp "$SCRIPT_DIR/meta-run/program.md" "$WORKSPACE_PROJECT/meta-run/program.md"
        cp "$SCRIPT_DIR/meta-run/setup.sh" "$WORKSPACE_PROJECT/meta-run/setup.sh"
        cp "$SCRIPT_DIR/meta-run/README.md" "$WORKSPACE_PROJECT/meta-run/README.md"
        echo "Done. Review changes in workspace with: cd $WORKSPACE_ROOT && git diff"
        ;;
    *)
        echo "Usage: ./sync.sh [pull|push]"
        echo "  pull  Copy from workspace into this repo"
        echo "  push  Copy from this repo into workspace"
        exit 1
        ;;
esac
