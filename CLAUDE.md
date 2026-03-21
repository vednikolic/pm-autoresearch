# PM AutoResearch: Meta-Run Project Context

## What This Project Is

This is an application of Karpathy's autoresearch pattern to PM documents instead of ML training scripts. The core idea: define binary (yes/no) evals for a document, then let an agent iterate on the document in a loop, keeping only changes that strictly improve the eval score. Git acts as the ratchet.

Right now we are running the system on itself. The `pm-autoresearch` skill's own SKILL.md is the target document being improved. This is the meta-run.

## Why This Matters

The autoresearch loop replaces manual prompt/document tweaking with an automated experiment loop. Instead of a human doing 5 rounds of edits, an agent runs 30-50 rounds overnight, each scored against a locked eval harness, with every improvement committed to git and every failure reverted. The experiment log is the artifact, not just the final document.

## Project Structure

```
<repo-root>/
│
├── .claude/skills/pm-autoresearch/
│   └── SKILL.md                   # Skill definition. THIS BECOMES target.md IN THE META-RUN.
│
├── references/
│   └── eval-design.md             # Guide for writing good binary evals per doc type
├── scripts/
│   ├── generate_eval.py           # Creates eval.py from an evals.json definition
│   ├── run_loop.py                # Automated orchestrator for the full experiment loop
│   └── analyze_results.py         # Post-run analysis of results.tsv
├── templates/
│   ├── eval_template.py           # Boilerplate for hand-crafting eval.py
│   └── program_template.md        # Boilerplate for writing agent loop instructions
│
└── meta-run/                      # The self-improvement run (current task)
    ├── eval.py                    # LOCKED. 18 strict binary evals scoring SKILL.md quality.
    ├── evals.json                 # The eval definitions (reference copy, also locked)
    ├── program.md                 # Agent loop instructions for this specific run
    ├── setup.sh                   # One-time init: copies SKILL.md to target.md, inits git, runs baseline
    ├── README.md                  # Quick-start reference
    ├── target.md                  # CREATED BY setup.sh. Copy of SKILL.md. THE ONLY FILE THE AGENT EDITS.
    ├── results.tsv                # CREATED BY setup.sh. Experiment log. Untracked by git.
    └── baseline.log               # CREATED BY setup.sh. First eval output.
```

## File by File: What Each Does and Why

### `.claude/skills/pm-autoresearch/SKILL.md`
The skill definition that teaches Claude how to run autoresearch loops on PM documents. Contains the three-file pattern mapping, step-by-step workflow, eval design guidance, and adaptation notes for different doc types. This is the source file that gets copied into `meta-run/target.md` for improvement. After the run, the improved `target.md` gets copied back here.

### `references/eval-design.md`
Deep reference on writing binary evals. Covers the anatomy of an eval (id, category, check, weight), eval templates for PRDs, strategy docs, and system prompts, anti-patterns to avoid (subjective quality, length-as-proxy, redundant pairs), and the weighted scoring formula. The agent CAN inline content from this file into SKILL.md if it improves self-containment scores.

### `scripts/generate_eval.py`
Takes an `evals.json` file and outputs a complete `eval.py` harness. Useful for future runs where you want to quickly stand up an eval suite for a new document. Not used in the meta-run (we already have eval.py pre-built).

### `scripts/run_loop.py`
Fully automated orchestrator. Reads program.md, proposes edits via the Anthropic API, runs evals, keeps or reverts, logs to results.tsv. This is the "run overnight without Claude Code" option. Takes `--target`, `--eval`, `--program`, `--max-rounds`, and `--tag` arguments.

### `scripts/analyze_results.py`
Post-run analysis. Reads results.tsv and outputs: total rounds, keep/revert ratio, baseline-to-final score, top improvements by score delta, longest revert streak, and plateau warnings. Use this after a run to decide whether another pass is needed.

### `templates/eval_template.py`
Boilerplate eval harness with example PRD evals pre-filled. For hand-crafting eval.py when you want more control than generate_eval.py provides.

### `templates/program_template.md`
Generic agent loop instructions. Covers setup, the 7-step experiment cycle, research direction hints (customize these), constraints, error handling, and end-of-run reporting. Fork this for each new run.

### `meta-run/eval.py`
THE LOCKED SCORING HARNESS. Contains 18 binary evals across 6 categories, with a strict judge system prompt. Calls Claude Sonnet via the Anthropic API to answer each eval question YES/NO against the document. Outputs composite_score (weighted percentage), category breakdown, and individual pass/fail. **The agent must never modify this file.** If the agent could change the evals, it would just make the test easier instead of making the document better.

### `meta-run/evals.json`
The 18 eval definitions in JSON format. Reference copy. Same data as what's hardcoded in eval.py. Exists so you can review and evolve the evals between runs without reading Python.

### `meta-run/program.md`
Agent instructions for this specific run. Contains: setup steps, the 7-step experiment loop, 7 prioritized research direction hints (what's weak in SKILL.md and what to try), constraints (preserve the three-file mapping table, stay under 600 lines, don't invent fake data), error handling procedures, and end-of-run reporting format.

### `meta-run/setup.sh`
One-time initialization. Copies SKILL.md to target.md, initializes git, creates .gitignore, commits the baseline, creates results.tsv, runs the baseline eval, and prints next steps. Run this once before starting the loop.

## The 18 Evals (What Gets Scored)

### Instructional Clarity (4 evals, total weight 5.0)
These test whether an agent following SKILL.md would know exactly what to do at every step.

| ID | Weight | What it checks |
|---|---|---|
| `workflow_numbered_steps` | 1.5 | Every step numbered with an action verb and a specified output |
| `decision_points_explicit` | 1.5 | At least 3 if/then decision points for different situations |
| `no_ambiguous_instructions` | 1.0 | Zero instances of vague directives ("consider", "as needed") |
| `commands_copy_pasteable` | 1.0 | Every command complete without unspecified arguments |

### Completeness (5 evals, total weight 5.0)
These test whether the skill covers the full lifecycle.

| ID | Weight | What it checks |
|---|---|---|
| `covers_setup_phase` | 1.0 | Git init, baseline eval, results.tsv, branch setup all with commands |
| `covers_iteration_phase` | 1.5 | Full loop: read results, hypothesize, edit, eval, interpret, keep/revert |
| `covers_analysis_phase` | 1.0 | Post-run analysis: what to look for, plateau detection, next actions |
| `error_handling_documented` | 1.0 | At least 3 failure modes with concrete recovery steps |
| `cost_estimation_specific` | 0.5 | Per-round AND per-run cost with model and token context |

### Eval Framework (4 evals, total weight 4.5)
These test whether the skill teaches eval design well enough to be useful.

| ID | Weight | What it checks |
|---|---|---|
| `good_eval_examples_with_contrast` | 1.5 | 3+ good evals AND 3+ bad evals with explanations of why |
| `eval_evolution_guidance` | 1.0 | When to add harder evals, remove saturated ones, adjust weights |
| `eval_templates_three_types` | 1.0 | Complete eval check questions (not just categories) for 3+ doc types |
| `scoring_model_explained` | 1.0 | Weight formula, composite score math, keep/revert threshold |

### Self-Containment (2 evals, total weight 2.5)
These test whether someone can use the skill without external reading.

| ID | Weight | What it checks |
|---|---|---|
| `pattern_self_contained` | 1.5 | Autoresearch pattern explained without requiring Karpathy knowledge |
| `no_undefined_references` | 1.0 | Every file path and script name has purpose and location specified |

### Adaptation (2 evals, total weight 2.5)
These test whether the skill flexes to different document types.

| ID | Weight | What it checks |
|---|---|---|
| `adaptation_has_specific_evals` | 1.5 | 5+ specific eval check questions per doc type (not category labels) |
| `adaptation_has_program_hints` | 1.0 | Research direction hints tailored per doc type |

### Triggering (1 eval, total weight 0.5)
Tests whether the YAML description catches relevant queries.

| ID | Weight | What it checks |
|---|---|---|
| `trigger_description_comprehensive` | 0.5 | 8+ distinct trigger phrases in the frontmatter description |

**Total weight: 20.0. Composite score = sum(passed * weight) / 20.0 * 100.**

## Desired Outcome

After the meta-run completes, SKILL.md should score 85%+ on these 18 evals. Concretely that means:

1. The adaptation sections contain actual eval questions, not just category names
2. There are explicit good and bad eval examples with explanations
3. Error handling covers at least eval crashes, API failures, and plateau recovery
4. Decision logic uses if/then structure ("if fewer than 8 evals, add more because...")
5. The scoring model (weighted sum, keep threshold) is explained directly in SKILL.md
6. Every command is copy-pasteable
7. The pattern is understandable without external context

The improved SKILL.md then gets copied back to `.claude/skills/pm-autoresearch/SKILL.md` and becomes the production version.

## How to Run

### Step 1: Setup
```bash
cd meta-run
chmod +x setup.sh
./setup.sh
```

This copies SKILL.md to target.md, inits git, and runs the baseline eval. Read `baseline.log` to see the starting score and which evals pass/fail.

### Step 2: Run the Loop

**Option A: Claude Code (recommended for first run, interactive, you can watch)**
```
claude "Read program.md and begin the autoresearch loop on target.md"
```

**Option B: Automated (run overnight, no interaction)**
```bash
python3 ../scripts/run_loop.py \
  --target target.md \
  --eval eval.py \
  --program program.md \
  --max-rounds 30 \
  --tag meta-v1
```

### Step 3: Review Results
```bash
# Score trajectory
git log --oneline autoresearch/meta-v1

# Full analysis
python3 ../scripts/analyze_results.py results.tsv

# See what changed
git diff main..autoresearch/meta-v1 -- target.md
```

### Step 4: Copy Back
```bash
cp target.md ../.claude/skills/pm-autoresearch/SKILL.md
```

## Rules for the Agent During the Run

1. **ONLY edit `target.md`.** Everything else is read-only.
2. **Never modify `eval.py` or `evals.json`.** If the eval seems wrong, that's a human decision for after the run.
3. **ONE change per round.** If you change two things and the score goes up, you can't attribute the improvement.
4. **Strictly greater to keep.** Equal score = revert. This prevents lateral moves.
5. **Log every round.** Even crashes. The experiment log is the most valuable artifact.
6. **Stop on plateau.** 10 consecutive reverts means the current eval suite is saturated or the hints need updating. Stop and report.
7. **Stay under 600 lines.** The skill must remain readable. Dense, precise content beats sprawling coverage.

## Predicted Baseline Score

Expected: ~45-55%. The SKILL.md has good bones but will likely fail on:

| Expected FAIL | Reason |
|---|---|
| `good_eval_examples_with_contrast` | No bad eval examples anywhere |
| `adaptation_has_specific_evals` | Category labels ("logical coherence") instead of actual eval questions |
| `adaptation_has_program_hints` | No per-doc-type research direction hints |
| `error_handling_documented` | Only cost mentioned, no crash/plateau/API recovery |
| `decision_points_explicit` | No if/then decision logic |
| `scoring_model_explained` | Formula lives in eval-design.md, not SKILL.md |
| `no_ambiguous_instructions` | "Aim for 10-20 evals" without criteria is vague |

These gaps map directly to the 7 research direction hints in `program.md`, so the agent has a clear path to improve.

## After the Run: Decision Points

1. **Score > 85%**: Copy target.md back to SKILL.md. Run is successful.
2. **Score 70-85%**: Review failing evals. If they're legitimately hard to satisfy within 600 lines, adjust eval weights or split into a v2 run with tightened hints.
3. **Score < 70%**: Review the experiment log for patterns. If the agent keeps reverting on the same evals, the hints may be too vague or the evals may be poorly calibrated. Adjust program.md and re-run.
4. **Plateau before 70%**: The eval suite may need recalibration. Some evals may be testing for content that conflicts with the 600-line constraint. Review and potentially split heavy evals into separate concerns.
