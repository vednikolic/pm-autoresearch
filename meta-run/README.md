# PM AutoResearch Meta-Run

Running pm-autoresearch on its own SKILL.md to improve it.

## Directory Structure

```
meta-run/
  eval.py          # Locked scoring harness (18 strict binary evals). DO NOT EDIT.
  evals.json       # Eval definitions (reference copy)
  program.md       # Agent loop instructions
  setup.sh         # One-time setup script
  target.md        # SKILL.md copy (created by setup.sh). Agent edits ONLY this file.
  results.tsv      # Experiment log (created by setup.sh)
  baseline.log     # Baseline eval output (created by setup.sh)
```

## Quick Start

```bash
cd meta-run
chmod +x setup.sh
./setup.sh
```

Then either:

```bash
# Option A: Claude Code (interactive, recommended for first run)
claude "Read program.md and begin the autoresearch loop on target.md"

# Option B: Automated loop
python3 ../pm-autoresearch/scripts/run_loop.py \
  --target target.md \
  --eval eval.py \
  --program program.md \
  --max-rounds 30 \
  --tag meta-v1
```

## After the Run

```bash
# View score trajectory
git log --oneline autoresearch/meta-v1

# Analyze results
python3 ../pm-autoresearch/scripts/analyze_results.py results.tsv

# Copy improved SKILL.md back
cp target.md ../pm-autoresearch/SKILL.md
```

## Eval Categories (18 evals total)

| Category | Count | Weight | What it tests |
|---|---|---|---|
| instructional_clarity | 4 | 5.0 | Can an agent follow the instructions unambiguously? |
| completeness | 5 | 5.0 | Setup, iteration, analysis, errors, cost all covered? |
| eval_framework | 4 | 4.5 | Good/bad examples, evolution guidance, templates, scoring? |
| self_containment | 2 | 2.5 | Usable without external reading? |
| adaptation | 2 | 2.5 | Concrete per-doc-type evals and hints? |
| triggering | 1 | 0.5 | Description activates on relevant queries? |

Total weight: 20.0. Composite score = weighted pass percentage.
