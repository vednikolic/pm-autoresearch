# Eval Design Guide for PM Documents

## The Golden Rule

An eval is good if two reasonable PMs would agree on the answer 95%+ of the time. If they'd argue about it, the eval is too subjective and the agent will chase noise instead of signal.

## Binary Eval Anatomy

```json
{
    "id": "unique_snake_case_id",
    "category": "structure|reasoning|specificity|completeness|clarity",
    "check": "A yes/no question that can be answered by reading the document",
    "weight": 1.0,
    "notes": "Optional context for why this matters"
}
```

### Weight Guidelines
- 1.0 = standard importance (default)
- 1.5 = critical (failing this is a serious gap)
- 0.5 = nice to have (absence is acceptable in some contexts)

Weighted score = sum(passing * weight) / sum(all weights)

## Eval Templates by Document Type

### PRD Evals

**Structure (the skeleton exists)**
- `has_problem_statement`: Does the document contain a section that explicitly states the problem being solved?
- `has_target_user`: Does the document identify specific user segments or personas affected?
- `has_proposed_solution`: Does the document describe what will be built or changed?
- `has_success_metrics`: Does the document define at least 3 measurable success metrics?
- `has_non_goals`: Does the document explicitly list what is out of scope?
- `has_dependencies`: Does the document identify external teams, systems, or decisions it depends on?
- `has_rollout_plan`: Does the document describe how the feature will be launched (phased, A/B, full)?

**Reasoning (the parts connect)**
- `problem_drives_solution`: Does the proposed solution directly address the stated problem (not a tangential opportunity)?
- `metrics_trace_to_problem`: Does each success metric connect to a specific aspect of the problem statement?
- `risks_have_mitigations`: Does every identified risk have at least one mitigation or contingency plan?
- `non_goals_justified`: Are non-goals explained (why they're excluded), not just listed?

**Specificity (vague language eliminated)**
- `metrics_have_targets`: Does every success metric include a specific numeric target (not "improve" or "increase")?
- `timelines_are_dates`: Are all timelines expressed as specific dates, sprints, or quarters (not "soon" or "later")?
- `user_numbers_cited`: Does the document cite specific user counts, percentages, or data points?
- `no_weasel_words`: Is the document free of "might", "could potentially", "ideally", "hopefully"?

**Completeness (nothing critical is missing)**
- `has_edge_cases`: Does the document address at least 2 edge cases or failure modes?
- `has_technical_constraints`: Does the document list technical limitations or platform constraints?
- `addresses_existing_users`: Does the document consider impact on existing users/workflows?
- `has_open_questions`: Does the document list unresolved questions that need answers before build?

### Strategy Doc Evals

**Structure**
- `has_current_state`: Does the document describe where things stand today with specific metrics?
- `has_vision`: Does the document articulate a future end state that differs from today?
- `has_strategic_pillars`: Does the document define 2-5 strategic themes or pillars?
- `has_resource_model`: Does the document address resourcing (headcount, budget, or prioritization tradeoffs)?
- `has_timeline_horizons`: Does the document distinguish between near-term (0-3mo), mid-term (3-12mo), and long-term (12mo+)?

**Reasoning**
- `pillars_connect_to_vision`: Does each strategic pillar clearly advance the stated vision?
- `has_competitive_context`: Does the strategy reference competitive landscape or market dynamics?
- `tradeoffs_explicit`: Does the document name what is being deprioritized or sacrificed?
- `evidence_supports_direction`: Are strategic choices backed by data, research, or precedent (not just assertion)?

**Specificity**
- `milestones_are_concrete`: Are intermediate milestones defined with measurable criteria?
- `ownership_assigned`: Is every pillar or workstream assigned to a team or individual?
- `current_metrics_quantified`: Are current-state metrics expressed as specific numbers?

### System Prompt / Skill Evals

**Structure**
- `has_role_definition`: Does the prompt define what the AI should act as?
- `has_output_format`: Does the prompt specify the expected output format?
- `has_constraints`: Does the prompt list at least 2 things the AI should NOT do?
- `has_examples`: Does the prompt include at least 1 input/output example?

**Reasoning**
- `constraints_non_contradictory`: Are all constraints compatible with each other (no impossible combinations)?
- `examples_match_instructions`: Do the examples actually follow the stated instructions?

**Specificity**
- `no_ambiguous_instructions`: Is every instruction specific enough that two people would interpret it the same way?
- `edge_cases_handled`: Does the prompt address what to do when input is malformed, empty, or off-topic?

## Anti-Patterns (Evals to Avoid)

1. **Subjective quality**: "Is the writing compelling?" (two PMs will disagree)
2. **Length as proxy**: "Is the document at least 2000 words?" (length ≠ quality)
3. **Format worship**: "Does it use bullet points?" (unless format is a real requirement)
4. **Redundant pairs**: Having both "has metrics" and "metrics section exists" (same thing)
5. **Unfalsifiable**: "Is the strategy sound?" (no binary test possible)

## Scoring Model

```
composite_score = sum(passed_i * weight_i) / sum(weight_i) * 100

Example:
  15 evals, all weight 1.0
  11 passing
  Score = 11/15 * 100 = 73.3%
```

The agent commits if and only if `new_score > current_score`. Equal score = revert. This prevents lateral moves that don't improve quality.

## Evolving Evals Between Runs

After a run plateaus (10+ rounds with no improvement), you should:

1. Review which evals are all passing (saturated). Consider replacing with harder versions.
2. Review which evals never pass. Either the eval is too strict or the document genuinely can't satisfy it under current constraints. Adjust or remove.
3. Add evals targeting weaknesses you notice in the current document that aren't captured.

This is the PM equivalent of Karpathy iterating on `program.md` between overnight runs.
