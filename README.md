# PM AutoResearch

An adaptation of [Karpathy's autoresearch pattern](https://x.com/karpathy/status/1886192184808149383) for PM documents. Instead of optimizing `train.py` against validation loss, you optimize a **target document** (strategy, PRD, prompt, skill) against a **binary eval suite** that scores quality programmatically.

An agent edits the document in a loop. Each round: propose one change, score it, keep if improved, revert if not. Git is the ratchet. Every improvement is committed. Every failure is reverted. The experiment log shows what worked and why.

## What It Does

You give it:
1. A document to improve (PRD, strategy doc, system prompt, skill, one-pager)
2. A set of binary evals (yes/no questions that score specific qualities)
3. Loop instructions (what areas to explore, what constraints to respect)

It runs an automated improvement loop and returns the improved document plus a full experiment log.

## Quick Start

### Prerequisites

- An LLM CLI installed and authenticated ([Claude Code](https://docs.anthropic.com/en/docs/claude-code) recommended, or set `LLM_COMMAND` for alternatives)
- Python 3.10+

### Install

```bash
git clone https://github.com/vednikolic/pm-autoresearch.git
cd pm-autoresearch
```

### With Claude Code

Claude Code automatically discovers the skill from `.claude/skills/pm-autoresearch/SKILL.md`.

```
/pm-autoresearch path/to/your-document.md
```

The skill walks you through setting up evals, initializing git tracking, and running the loop.

### With Any LLM

Copy the content of [`.claude/skills/pm-autoresearch/SKILL.md`](.claude/skills/pm-autoresearch/SKILL.md) and use it as instructions for your LLM agent. The pattern works with any LLM that can read/write files and use git.

For automated runs, set the `LLM_COMMAND` env var to your CLI tool:
```bash
LLM_COMMAND="your-llm-cli" python3 scripts/run_loop.py --target target.md --scoring eval.py --max-rounds 30
```

### With Other AI Coding Tools

| Tool | Install |
|------|---------|
| ChatGPT | Paste `SKILL.md` content into a Custom GPT's instructions or a project's custom instructions |
| Cursor | Copy `SKILL.md` content into `.cursor/rules/pm-autoresearch.md` |
| Windsurf | Copy `SKILL.md` content into `.windsurfrules` |
| Cline / Roo | Add `SKILL.md` path to your custom instructions |
| Gemini CLI | Copy `SKILL.md` into `.gemini/instructions/pm-autoresearch.md` |

### Use Manually (Step by Step)

#### 1. Prepare your target document

Copy the document you want to improve into a working directory as `target.md`.

#### 2. Define binary evals

Create an `evals.json` file with yes/no questions that score specific qualities:

```json
[
  {
    "id": "has_problem_statement",
    "category": "structure",
    "check": "Does the document contain a clearly defined problem statement in its own section?",
    "weight": 1.5
  },
  {
    "id": "has_success_metrics",
    "category": "structure",
    "check": "Does the document define at least 3 quantitative success metrics with specific numeric targets?",
    "weight": 1.5
  },
  {
    "id": "no_vague_timelines",
    "category": "specificity",
    "check": "Are all timelines expressed as specific dates or sprint numbers, not 'soon' or 'later'?",
    "weight": 1.0
  }
]
```

Good evals are binary, specific, and testable. Bad evals are subjective ("Is this compelling?"), undefined ("Does it cover everything?"), or compound ("Is it clear AND complete?"). The skill documentation has detailed guidance and examples for writing evals across document types.

#### 3. Generate the eval harness

```bash
python3 scripts/generate_eval.py --evals evals.json --output eval.py
```

Or copy `templates/eval_template.py` and customize it by hand.

#### 4. Write loop instructions

Copy `templates/program_template.md` to `program.md` and fill in:
- **Research direction hints**: specific areas the agent should explore
- **Constraints**: invariants the agent must preserve
- **Revert rules**: score must strictly improve (equal = revert)

#### 5. Initialize and run

```bash
git init
git add target.md eval.py program.md
git commit -m "baseline: initial target and eval setup"
git checkout -b autoresearch/run-1

# Run baseline eval
python3 eval.py target.md --verbose 2>&1 | tee baseline.log

# Create experiment log
echo -e "round\tscore\tpassing\ttotal\thypothesis\tchange_description\tkept" > results.tsv

# Start the loop (interactive)
claude "Read program.md and begin the autoresearch loop on target.md"

# Or start the loop (automated, unattended)
python3 scripts/run_loop.py --target target.md --scoring eval.py --program program.md --max-rounds 30
```

#### 6. Review results

```bash
# Score trajectory
git log --oneline autoresearch/run-1

# Full analysis
python3 scripts/analyze_results.py results.tsv

# See what changed
git diff main..autoresearch/run-1 -- target.md
```

## How the Loop Works

```
1. Agent reads target.md
2. Agent forms a hypothesis about what would improve the score
3. Agent edits target.md with ONE focused change
4. Agent runs: python3 eval.py target.md
5. Agent reads composite score
6. If score improved -> git commit (new baseline)
   If score equal or worse -> git checkout -- target.md (revert)
7. Agent logs result to results.tsv
8. Repeat from step 1
```

The key constraint: **one change per round**. If you change two things and the score goes up, you cannot attribute the improvement. Single changes make the experiment log interpretable.

## Scoring Model

Each eval has a weight (default 1.0). Higher weights (1.5) mark critical evals; lower weights (0.5) mark nice-to-haves.

```
composite_score = (sum of weights for passing evals) / (sum of all weights) * 100
```

The keep/revert threshold is **strictly greater**. Equal scores are reverted because LLM judges have variance; a lateral move might actually be a regression.

## Project Structure

```
pm-autoresearch/
├── .claude/skills/pm-autoresearch/
│   └── SKILL.md              # Skill definition (auto-discovered by Claude Code)
├── scripts/
│   ├── generate_eval.py      # Create eval.py from evals.json
│   ├── run_loop.py           # Automated loop orchestrator
│   └── analyze_results.py    # Post-run analysis
├── templates/
│   ├── eval_template.py      # Eval harness boilerplate
│   └── program_template.md   # Agent loop instruction boilerplate
├── references/
│   └── eval-design.md        # Deep guide on writing good binary evals
└── meta-run/                 # Example: the skill improving itself
    ├── eval.py               # 18 binary evals scoring SKILL.md quality
    ├── evals.json            # Eval definitions
    ├── program.md            # Agent loop instructions for this run
    ├── setup.sh              # One-time init script
    └── README.md             # Meta-run specific docs
```

## Meta-Run: The Skill Improving Itself

The `meta-run/` directory contains a complete example where the skill was used to improve its own SKILL.md. Starting from a 15% baseline score, the autoresearch loop brought it to 90%+ across 18 binary evals in under 10 rounds. See `meta-run/README.md` for details.

## Adapting for Different Document Types

The skill includes eval templates and research direction hints for:
- **Strategy docs** -- vision coherence, evidence, risk identification
- **PRDs** -- problem-solution fit, metric specificity, scope boundaries
- **System prompts / skills** -- instruction clarity, edge cases, output format
- **One-pagers / briefs** -- executive summary quality, action item specificity

See the full SKILL.md at `.claude/skills/pm-autoresearch/SKILL.md` for detailed guidance per document type.

## Syncing with a Workspace

If you use this inside a larger monorepo:

```bash
./sync.sh pull   # Copy FROM workspace INTO this repo
./sync.sh push   # Copy FROM this repo INTO workspace
```

Set `WORKSPACE_ROOT` if your workspace is not at `~/claude`.

## Author

Ved Nikolic ([vednikolic](https://github.com/vednikolic)) -- ved@vednikolic.com

## License

MIT
