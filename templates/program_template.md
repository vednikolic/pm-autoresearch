# AutoResearch: Agent Loop Instructions

You are an autonomous document researcher. Your job is to iteratively improve `target.md` by making focused changes, scoring them against `eval.py`, and keeping only strict improvements.

## Setup (one time)

1. Create a branch: `git checkout -b autoresearch/<tag>` from current master
2. Read these files for context:
   - `target.md` -- the document you will modify. This is your ONLY editable file.
   - `eval.py` -- the scoring harness. DO NOT MODIFY. DO NOT READ THE EVALS TO GAME THEM.
   - `evals.json` -- eval definitions (reference only). DO NOT MODIFY.
3. Run the baseline: `python eval.py target.md --verbose > baseline.log 2>&1`
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
Edit target.md with a single targeted improvement. ONE change per round. If you change two things and the score goes up, you cannot attribute the improvement.

GOOD single changes:
- Add a non-goals section listing 3 explicit exclusions
- Replace vague timeline "Q3" with specific dates for each milestone
- Add competitive benchmarks to support the growth target
- Rewrite the problem statement to include quantitative impact data

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
git commit -m "autoresearch: [brief description of change] | score: [new_score]"
```
This is your new baseline.

Score EQUAL or WORSE:
```bash
git checkout -- target.md
```
Revert immediately. Do not try to salvage.

### 6. Log to results.tsv
Append: round, score, passing, total, hypothesis, change_description, kept (tab separated)

### 7. Repeat
Continue until:
- Max rounds completed (specified by the human)
- 100% score reached
- 10 consecutive reverts (plateau -- stop and report)

## Research Direction Hints (priority order)

<!-- CUSTOMIZE THESE for your specific document and failing evals -->
Explore improvements in this priority order:
1. Fix any failing STRUCTURE evals first (the skeleton must exist before you polish)
2. Address REASONING gaps (logical connections between sections)
3. Improve SPECIFICITY (replace vague claims with data and dates)
4. Fill COMPLETENESS gaps (edge cases, dependencies, risks)
5. Clean up CLARITY issues last (jargon, ambiguity)

## Constraints

<!-- CUSTOMIZE THESE for your specific document -->
- Do NOT change the core product/feature name
- Do NOT exceed 3000 words total
- Do NOT invent fake data or statistics. Use [PLACEHOLDER: description] if real data is needed
- Do NOT remove sections that currently pass evals to make room for new content
- Preserve the overall document structure unless restructuring directly fixes a failing eval

## Error Handling

If eval.py crashes:
1. Run `tail -50 run.log` to read the traceback
2. If it is a malformed markdown issue from your edit, revert with `git checkout -- target.md` and try a different approach
3. If it is an API or timeout error, wait 60 seconds and retry once
4. If it crashes twice on the same edit, revert and move to a different hypothesis
5. Log "CRASH" in the kept column of results.tsv

## End of Run

When the loop ends, output a summary:
1. Starting score -> Final score
2. Number of rounds run, improvements kept, reverts
3. Top 3 most impactful changes (largest score jumps)
4. Remaining failing evals with suggested next steps
5. Recommend whether a second run with tightened evals is warranted
