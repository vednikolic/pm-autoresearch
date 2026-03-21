# PM AutoResearch Meta-Run: Improve SKILL.md

You are an autonomous researcher improving a Claude skill file. Your job is to iteratively improve `target.md` (which is the pm-autoresearch SKILL.md) by making focused changes, scoring them against `eval.py`, and keeping only strict improvements.

## Setup (one time)

1. Create a branch: `git checkout -b autoresearch/meta-v1` from current master
2. Read these files:
   - `target.md` — the SKILL.md you will modify. This is your ONLY editable file.
   - `eval.py` — the scoring harness. DO NOT MODIFY. DO NOT READ THE EVALS LIST TO GAME THEM.
   - `evals.json` — for reference only. DO NOT MODIFY.
3. Run baseline: `python eval.py target.md --verbose > baseline.log 2>&1`
4. Read baseline.log. Record the composite_score and individual pass/fail results.
5. Create results.tsv: `echo -e "round\tscore\tpassing\ttotal\thypothesis\tchange_description\tkept" > results.tsv`
6. Record baseline as round 0.
7. Begin experimentation.

## Experiment Loop

Each round, in exact order:

### 1. Read current eval results
Run `python eval.py target.md --verbose` and identify failing evals by category.

### 2. Form a hypothesis
Before editing, state: "Adding [specific content] to [specific section] should flip [specific eval ID] from FAIL to PASS because [the eval requires X and the document currently lacks X]."

### 3. Make ONE focused change
Edit target.md with a single targeted improvement. ONE change per round. Examples:

GOOD single changes:
- Add a "Bad Eval Examples" subsection with 3 anti-patterns and explanations
- Expand the Strategy Doc adaptation section with 5 specific binary eval check questions
- Add an error handling section covering eval crashes, API errors, and plateau recovery
- Replace the vague "Aim for 10-20 evals" with explicit decision criteria for eval count

BAD changes (too broad, will obscure what helped):
- Rewrite the entire document
- Add three new sections at once
- Restructure AND add content simultaneously

### 4. Run the eval
```bash
python eval.py target.md --verbose > run.log 2>&1
```
Read composite_score from run.log.

### 5. Keep or revert

Score STRICTLY IMPROVED (new > previous best):
```bash
git add target.md
git commit -m "autoresearch: [description] | score: [new_score]"
```

Score EQUAL or WORSE:
```bash
git checkout -- target.md
```

### 6. Log to results.tsv
Append: round, score, passing, total, hypothesis, change_description, kept (tab separated)

### 7. Repeat
Continue until:
- 30 rounds completed
- 100% score reached
- 10 consecutive reverts (plateau, stop and report)

## Research Direction Hints (priority order)

1. **Adaptation sections are thin.** The skill says "focus evals on: logical coherence..." but does not provide actual eval check questions for each document type. Each adaptation section needs at least 5 copy-paste-ready binary eval questions, not category labels.

2. **No bad eval examples.** The skill shows good eval examples but never shows what bad evals look like or why they fail. Add explicit anti-patterns with explanations.

3. **Error handling is sparse.** The "Important Notes" section mentions cost but doesn't cover what happens when eval.py crashes, when the API rate limits, when git gets into a bad state, or when the agent hits a plateau. Add concrete recovery procedures.

4. **Decision logic is implicit.** When should the user choose 10 evals vs 20? When should weights be 1.5 vs 0.5? When should they use the run_loop.py script vs Claude Code directly? These decision points need explicit if/then guidance.

5. **Scoring model is mentioned but not explained in SKILL.md itself.** The eval-design.md reference has the formula, but SKILL.md should contain the core scoring logic (weighted sum, keep threshold) directly so it's self-contained.

6. **Program.md hints per document type are missing.** The adaptation section tells you what to eval but not what research directions to give the agent for each document type.

7. **The iteration loop description could be tighter.** Step 5 in the "How It Works" section is minimal. The agent needs to know: read which specific fields from the output, compare against what stored value, and execute which exact git command.

## Constraints

- DO NOT change the YAML frontmatter name field (keep "pm-autoresearch")
- DO NOT remove the three-file pattern mapping table (train.py → target.md, etc.)
- DO NOT remove the File Reference table
- DO NOT exceed 600 lines total (skill files should stay under 500, we have some buffer)
- DO NOT remove any section that currently passes an eval
- DO NOT invent fake benchmark results or statistics
- PRESERVE the overall structure: Core Pattern → Setup Steps → Eval Design → Run → Review
- Content from references/eval-design.md CAN be inlined into SKILL.md if it helps self-containment, but do not duplicate excessively

## Error Handling

If eval.py crashes:
1. Run `tail -50 run.log` to read the traceback
2. If it's a malformed markdown issue from your edit, revert with `git checkout -- target.md` and try a different approach
3. If it's an API error (rate limit, timeout), wait 60 seconds and retry once
4. If it crashes twice on the same edit, revert and move to a different hypothesis
5. Log "CRASH" in the kept column of results.tsv

## End of Run

Output a summary:
1. Starting score → Final score
2. Rounds run, improvements kept, reverts
3. Top 3 changes by score impact
4. Remaining failing evals with suggested next steps
5. Recommend whether a second run with tightened evals is warranted
