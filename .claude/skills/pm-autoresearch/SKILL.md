---
name: pm-autoresearch
description: Autonomous iterative improvement of PM strategy documents, PRDs, system prompts, and skills using the Karpathy autoresearch loop pattern. Use this skill whenever the user wants to iterate on, optimize, or improve a strategy doc, PRD, one-pager, system prompt, or any PM artifact using automated eval loops. Also trigger when the user mentions "autoresearch", "overnight iteration", "eval loop", "auto-improve", or wants to run binary evals against a document to score and ratchet improvements. Works with Claude Code or any agent that can read/write files and use git.
---

# PM AutoResearch

An adaptation of Karpathy's autoresearch pattern for PM artifacts. Instead of optimizing `train.py` against `val_bpb`, you optimize a **target document** (strategy, PRD, prompt, skill) against a **binary eval suite** that scores the output programmatically.

## Core Pattern

Three files, same as the original:

| Autoresearch (ML) | PM AutoResearch | Role |
|---|---|---|
| `train.py` | `target.md` | The ONE file the agent edits |
| `prepare.py` | `eval.py` | Scoring harness. Agent CANNOT modify. |
| `program.md` | `program.md` | Instructions for the agent loop |

Plus: `results.tsv` for the experiment log (untracked by git).

## How It Works

```
1. Agent reads target.md (the PRD, strategy, etc.)
2. Agent forms a hypothesis about what would improve the score
3. Agent edits target.md with ONE focused change
4. Agent runs: python3 eval.py target.md > run.log
5. Agent reads composite score from run.log
6. If score improved → git commit (new baseline)
   If score equal or worse → git checkout -- target.md (revert)
7. Agent logs result to results.tsv
8. Repeat from step 1
```

## Step 1: Set Up the Target Document

Copy the user's document into the workspace as `target.md`. This is the ONLY file the agent will modify.

If the user provides a PRD, strategy doc, one-pager, or any PM artifact, that becomes `target.md`.

If the user wants to improve a system prompt or skill, that file becomes the target.

## Step 2: Define Binary Evals

This is the critical step. Binary evals are yes/no questions scored as 1 or 0. The composite score is the percentage of evals that pass.

### Writing Good Evals

Each eval tests ONE specific, unambiguous quality. Bad evals are subjective ("Is this compelling?"). Good evals are binary and deterministic.

**Read `references/eval-design.md` for the full eval design guide with examples per document type.**

Example eval entries for a PRD (add these to your `evals.json` file):

```python
EVALS = [
    # Structure
    {"id": "has_problem_statement", "check": "Does the document contain a clearly defined problem statement in its own section?"},
    {"id": "has_success_metrics", "check": "Does the document define at least 3 quantitative success metrics with specific targets?"},
    {"id": "has_non_goals", "check": "Does the document explicitly list what is NOT in scope?"},
    
    # Reasoning quality
    {"id": "metrics_trace_to_problem", "check": "Does every success metric directly address an aspect of the stated problem?"},
    {"id": "has_evidence", "check": "Does the document cite at least 2 pieces of external evidence (data, research, benchmarks)?"},
    
    # Specificity
    {"id": "no_vague_timelines", "check": "Are all timelines expressed as specific dates or sprint numbers, not 'soon' or 'later'?"},
    {"id": "has_technical_constraints", "check": "Does the document list at least 2 technical constraints or dependencies?"},
]
```

### Bad Eval Anti-Patterns

Avoid these patterns — they produce unreliable scores and give the agent bad signal:

```python
# BAD: Subjective quality judgment
{"id": "is_compelling", "check": "Is this document compelling and well-written?"}
# Why bad: "Compelling" has no binary answer. Two judges will disagree.
# The agent will chase phantom improvements.

# BAD: Undefined scope
{"id": "is_comprehensive", "check": "Does this document cover everything relevant?"}
# Why bad: "Everything relevant" is undefined. Will always pass or always fail
# depending on judge interpretation, not document quality.

# BAD: Too easy to game
{"id": "has_metrics", "check": "Does the document mention metrics?"}
# Why bad: Any number anywhere passes. Agent adds one line and moves on.
# Replace with: "Does the document define at least 3 quantitative metrics
# with specific numeric targets?"

# BAD: Compound question (two requirements in one)
{"id": "good_structure", "check": "Does the document have a clear structure and use headers consistently?"}
# Why bad: If structure is clear but headers inconsistent, what's the answer?
# Split into two separate evals.

# BAD: Length as proxy for quality
{"id": "detailed_enough", "check": "Is this document sufficiently detailed?"}
# Why bad: Length does not equal quality. Agent will pad content to pass.

# BAD: Zero-tolerance on long documents
{"id": "no_vague_language", "check": "Are there zero instances of vague directives like 'consider' or 'as needed'?"}
# Why bad: LLM judges have ~5-7.5% variance per run. On a 300+ line document,
# the judge will randomly flag something in one run and miss it in the next.
# The eval becomes a coin flip, not a quality signal.
# Replace with a threshold: "Are there fewer than 3 instances of vague directives?"

# BAD: Tests two independent qualities in one check
{"id": "clear_and_complete", "check": "Is every instruction specific AND is every command copy-pasteable?"}
# Why bad: If instructions are specific but one command has a placeholder,
# the eval fails and you cannot tell which half caused it.
# Split into two evals so score changes are attributable.
```

### Eval Categories

Assign each eval to exactly one of these five tiers:

1. **Structure** (does it have the right sections/components?)
2. **Reasoning** (do the parts connect logically?)
3. **Specificity** (are claims backed by data, dates, numbers?)
4. **Completeness** (are edge cases, risks, dependencies covered?)
5. **Clarity** (no jargon without definition, no ambiguous pronouns?)

Use 10-20 evals per document. If you have fewer than 8, the agent lacks signal to distinguish good edits from bad ones. If you have more than 25, consolidate overlapping evals to reduce noise and eval cost.

## Step 3: Generate eval.py

Use the template at `scripts/generate_eval.py` to create the eval harness. The harness:

1. Reads `target.md`
2. Sends it to an LLM with each eval question
3. Forces a YES/NO response (binary)
4. Computes composite score = (passing evals / total evals)
5. Prints results in a parseable format

**The agent CANNOT modify eval.py.** If it could, it would just make the test easier.

To generate from an evals.json definition file:

```bash
python3 scripts/generate_eval.py --evals evals.json --output eval.py
```

To create eval.py by hand, copy `templates/eval_template.py` to `eval.py` and replace the example evals with your own.

## Step 4: Write program.md

Copy `templates/program_template.md` to `program.md` and fill in three required sections:

1. **Research direction hints**: List 5-7 specific areas the agent should explore. Write each as an imperative: "Add a competitive analysis section comparing X to Y" or "Replace vague timelines with sprint numbers."
2. **Constraints**: List every invariant the agent must preserve. Write each as a prohibition: "Do not change the core product name" or "Keep total length under 2000 words."
3. **Revert rules**: Set to "Score must strictly improve. Equal score = revert."

## Step 5: Initialize and Run

### 5a. Initialize git tracking

```bash
git init
git add target.md eval.py program.md
git commit -m "baseline: initial target and eval setup"
```

### 5b. Create a branch for the experiment run

```bash
git checkout -b autoresearch/run-1
```

### 5c. Run the baseline eval and save the output

```bash
python3 eval.py target.md --verbose 2>&1 | tee baseline.log
```

Read `baseline.log` to record which evals pass and fail. Note the `composite_score` value.

### 5d. Create the experiment log

```bash
echo -e "round\tscore\tpassing\ttotal\thypothesis\tchange_description\tkept" > results.tsv
```

### 5e. Launch the agent loop

Option A (interactive, recommended for first runs):

Point your LLM agent at the working directory and instruct it:
```
Read program.md and begin the autoresearch loop on target.md
```

In Claude Code: `claude "Read program.md and begin the autoresearch loop on target.md"`

Option B (automated, for unattended runs):
```bash
python3 scripts/run_loop.py --target target.md --scoring eval.py --program program.md --max-rounds 30
```

The automated runner uses `claude -p` by default. Set `LLM_COMMAND` to use a different backend:
```bash
LLM_COMMAND="your-llm-cli" python3 scripts/run_loop.py --target target.md --scoring eval.py --max-rounds 30
```

## Step 6: Review the Experiment Log

After the run, `results.tsv` contains every experiment. Key things to look for:

- **Score trajectory**: Should ratchet upward monotonically (kept experiments only)
- **Revert ratio**: High revert rate (>80%) means the agent is exploring unproductive territory. Tighten `program.md` hints.
- **Plateau detection**: If score hasn't improved in 10+ rounds, the evals may be saturated. Add harder evals or raise the bar.

Use `scripts/analyze_results.py` to generate a summary:

```bash
python3 scripts/analyze_results.py results.tsv
```

## File Reference

All paths relative to the repository root.

| File | Purpose | Read when |
|---|---|---|
| `references/eval-design.md` | How to write good binary evals per document type | Always read before creating evals |
| `templates/eval_template.py` | Eval harness template | When generating eval.py |
| `templates/program_template.md` | Agent loop instructions template | When setting up program.md |
| `scripts/generate_eval.py` | Auto-generates eval.py from evals.json | During setup |
| `scripts/run_loop.py` | Orchestrates the full autoresearch loop | To run autonomously |
| `scripts/analyze_results.py` | Summarizes experiment log | After a run completes |

## Adapting for Different Document Types

### Strategy Docs

Sample binary eval check questions:
- "Does the document state a clear vision for a specific, named time horizon (e.g., 3-year, 5-year)?"
- "Does every tactic in the plan trace back to a specific strategic goal stated in this document?"
- "Does the document identify at least 2 distinct risks with named mitigation strategies?"
- "Are all goals expressed as measurable outcomes rather than activities or efforts?"
- "Does the document explicitly address budget, headcount, or resource constraints?"
- "Does the document cite at least 2 pieces of external evidence (market data, research, benchmarks)?"

Research direction hints for program.md: Focus agent on (1) making goals measurable with named metrics, (2) explicitly linking each tactic to a strategic goal, (3) adding a risks section with named mitigations, (4) replacing activity-framed goals ("we will build X") with outcome-framed goals ("X will increase by Y%").

### PRDs

Sample binary eval check questions:
- "Does the document contain a clearly defined problem statement in its own section?"
- "Does the document define at least 3 quantitative success metrics with specific numeric targets?"
- "Does the document explicitly list what is NOT in scope in a dedicated non-goals section?"
- "Does every success metric directly address an aspect of the stated problem?"
- "Does the document list at least 2 technical constraints or dependencies?"
- "Are all timelines expressed as specific dates or sprint numbers rather than 'soon' or 'later'?"

Research direction hints for program.md: Focus agent on (1) replacing directional metrics ("improve retention") with numeric targets ("increase 30-day retention from 42% to 55%"), (2) adding an explicit non-goals section, (3) adding technical constraints or dependencies, (4) ensuring every metric maps to the problem statement.

### System Prompts / Skills

Sample binary eval check questions:
- "Does every instruction use an imperative verb with a specific, named output or action?"
- "Does the document specify distinct handling for at least 3 different input scenarios?"
- "Does the document specify the exact output format (structure, length, tone) for at least one case?"
- "Are there explicit constraints listing what the model should NOT do?"
- "Does the document cover at least 2 edge cases with concrete handling instructions?"
- "Is every technical or domain-specific term either defined or used in unambiguous context?"

Research direction hints for program.md: Focus agent on (1) replacing passive/vague directives ("consider", "try to") with imperative instructions ("always return", "never include"), (2) adding explicit output format specifications, (3) adding edge case handling with concrete examples, (4) listing explicit constraints on what the model must not do.

### One-Pagers / Briefs

Sample binary eval check questions:
- "Does the first paragraph state the core recommendation or decision being requested?"
- "Does every recommendation include at least one specific next action with a named owner or deadline?"
- "Does the document state the single most important thing the reader must decide or do?"
- "Are all supporting details subordinate to the main recommendation rather than parallel to it?"
- "Does the document avoid jargon that would be unfamiliar to an executive audience?"

Research direction hints for program.md: Focus agent on (1) moving the core recommendation to the opener, (2) making action items specific with owners and dates, (3) trimming supporting detail that doesn't directly serve the main recommendation, (4) replacing technical jargon with plain language.

## Scoring Model

Each eval has a weight (default 1.0). Higher weights (1.5) mark critical evals; lower weights (0.5) mark nice-to-haves.

**Composite score formula**: `composite_score = (sum of weights for passing evals) / (sum of all weights) * 100`

Example: 18 evals with total weight 20.0. If 9 evals pass with combined weight 10.5, the composite score is `10.5 / 20.0 * 100 = 52.5%`.

**Keep/revert threshold**: The new score must be STRICTLY GREATER than the previous best score. If the new score equals or is less than the previous best, revert the change with `git checkout -- target.md`. Equal scores are reverted because LLM judges have variance; a lateral move might actually be a regression that happened to score the same.

**Choosing eval weights**:
- If the eval tests a core structural requirement (problem statement exists, steps are numbered), set weight to 1.5.
- If the eval tests a secondary quality (cost info present, trigger phrases in description), set weight to 0.5.
- If the eval tests standard completeness or reasoning quality, keep weight at 1.0.

## Decision Logic

**How many evals to define**:
- If the document type is simple (one-pager, brief): use 8-12 evals.
- If the document type is complex (PRD, strategy doc): use 15-20 evals.
- If you have more than 25 evals, consolidate overlapping ones. More than 25 adds noise and increases eval cost per round without proportional signal gain.

**When to use `run_loop.py` vs an interactive agent**:
- If you want to watch the agent work and intervene on bad hypotheses: use an interactive session (e.g., `claude "Read program.md and begin the autoresearch loop"`).
- If you want to run overnight unattended: use `python scripts/run_loop.py --target target.md --scoring eval.py --max-rounds 50`.
- If the first run plateaued and you need tighter hints: update `program.md` research direction hints, then re-run interactively to observe whether the new hints help.

**When to stop a run**:
- If the score reaches 90%+ and remaining evals are low-weight (0.5): stop, the document is good enough.
- If 10 consecutive rounds revert without improvement: the eval suite is saturated or the hints are too vague. Stop and review.
- If the agent starts making changes that hurt previously passing evals: stop, the document may be at a local maximum. Add new evals or adjust weights before the next run.

## Cost Estimation

Each eval sends the full document plus the eval question to an LLM judge. Approximate token usage per eval call: ~2,000 tokens input (document + question) + ~5 tokens output (YES/NO).

- **Per eval call**: ~2,000 input tokens + ~5 output tokens.
- **Per round**: 18 evals for scoring + 1 proposal call (~4,000 tokens) + 18 evals for re-scoring = 37 calls.
- **Per full run** (30 rounds): ~1,100 LLM calls. Actual cost depends on your provider and model.
- **With Claude Code Pro subscription**: calls use your subscription quota, not API billing. No per-token cost, but subject to rate limits.

## Error Handling

**Eval harness crashes**: Run `tail -50 run.log` to read the traceback. If the crash is caused by malformed markdown from your edit (unclosed code fence, broken table), revert with `git checkout -- target.md` and retry with a different edit. If the crash is an import error or script bug, stop the run and report the issue.

**API rate limits or timeouts**: If the LLM returns a rate limit error or times out, wait 60 seconds and retry the same eval. If it fails a second time, log "TIMEOUT" in the kept column of results.tsv, revert the current edit, and continue to the next round. Do not retry more than once per round.

**Score plateau (10+ consecutive reverts)**: Stop the run. Review results.tsv to identify which evals the agent keeps targeting unsuccessfully. If the same eval fails repeatedly, the research direction hints in program.md are too vague for that eval. Add a more specific hint. If different evals fail each time, the document may be at a local maximum. Add 2-3 new evals that test finer-grained qualities, then start a new run.

**Git in a bad state (uncommitted changes, merge conflicts)**: Run `git status` to assess. If target.md has uncommitted changes, run `git diff target.md` to review them. If they look like a partial edit, revert with `git checkout -- target.md`. If the git history is corrupted, copy target.md to a safe location, re-run setup, and paste the content back.

**Agent edits the wrong file**: If the agent modifies eval.py, program.md, or any file other than target.md, immediately revert all changes with `git checkout -- .` and re-read program.md to the agent with emphasis on the single-file constraint.

## Evolving the Eval Suite Between Runs

After a run completes, review the results to decide how to evolve the evals for the next run:

- **If an eval passes in 100% of rounds (always PASS)**: remove it from the suite. It is saturated and adds eval cost without signal. Replace it with a harder eval testing the same category at a higher bar.
- **If an eval fails in 100% of rounds (always FAIL) despite multiple attempts**: the eval may be too strict, poorly worded, or testing something the document cannot satisfy within its constraints (e.g., line limit). Rewrite the eval to be more specific, or lower its weight to 0.5 if it tests a secondary quality.
- **If the overall score is above 85% but specific categories score below 50%**: add 2-3 new evals in the weak category to give the agent more signal about what to improve there.
- **If you want to raise the bar after a successful run**: keep all passing evals, add 5-8 new evals that test deeper qualities (reasoning coherence, cross-reference consistency, edge case coverage), and increase weights on the new evals to 1.5 so they dominate the score.

### Diagnosing a Score Ceiling

When the score plateaus, the problem is not always the document. Run this checklist before adding more content:

1. **Check eval variance**: Run the eval 3 times without changing the document. If the score swings by more than 5%, the LLM judge is unreliable on one or more evals. Identify which evals flip between runs and rewrite them to be less ambiguous.
2. **Check for zero-tolerance evals**: Any eval that requires "zero instances" or "every single X" on a document over 200 lines will be dominated by judge noise, not document quality. Replace absolute requirements with thresholds (e.g., "fewer than 3 instances" instead of "zero instances").
3. **Check for compound evals**: If an eval tests two independent qualities ("Is X clear AND is Y complete?"), the agent cannot tell which half is failing. Split it into two evals.
4. **Check the constraint budget**: If the document has a line limit (e.g., 600 lines) and the remaining failing evals require substantial new content, the constraint and the eval are in conflict. Either raise the line limit, lower the eval weight, or accept the current score as the ceiling for this constraint set.
5. **Check attribution feasibility**: If the agent keeps making edits that flip one eval from FAIL to PASS but flip another from PASS to FAIL (net zero), the evals may be testing overlapping or contradictory qualities. Consolidate or reweight so improvements in one area do not penalize another.

If 2+ of these checks fire, the eval suite needs recalibration before another run. The ceiling is an eval design problem, not a document quality problem.

## Important Notes

- The agent must make ONE focused change per round. Multiple changes make it impossible to attribute score improvements.
- Git is the ratchet. Every improvement is committed. Every failure is reverted. The git log IS your changelog of improvements with reasoning.
- The experiment log (results.tsv) is more valuable than the final document. It shows you what the agent tried, what worked, and why.
