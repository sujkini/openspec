# Task Implementation Report

**Change**: [CHANGE_NAME]
**Task ID**: [TASK_ID]
**Task Title**: [TASK_TITLE]
**Phase**: [PHASE_NAME]
**Assigned Agent**: [ASSIGNED_AGENT]
**Approved**: [ISO8601_DATE]
**User approved by**: [user confirmation]

<!-- [ai-helpers mode — codegen_mode: ai-helpers] -->

**OAPE Command**: [OAPE_COMMAND or manual]

<!-- [END mode-specific] -->

## Summary

[2–4 sentences: what this task implemented, outcome, and test status.]

<!-- [ai-helpers mode — codegen_mode: ai-helpers] -->

[Include OAPE command outcome and eval gate result.]

<!-- [END mode-specific] -->

<!-- [ai-helpers mode — codegen_mode: ai-helpers] -->

## OAPE Commands Executed

| Command | Args | Outcome |
|---------|------|---------|
| /oape:… | … | Success / Failed |

<!-- [END mode-specific] -->

## Code Changes

### Files modified or created

| File | Change |
|------|--------|
| `relative/path` | [brief description] |

### Git diff summary

```
[Key hunks or `git diff --stat` for this task's scope]
```

## Verification

| Check | Result | Notes |
|-------|--------|-------|
| Task acceptance criteria | PASSED / FAILED | |
| make targets | PASSED / FAILED | |

<!-- [ai-helpers mode — codegen_mode: ai-helpers] -->

## Code Generation Eval Gate

**Eval results**: `eval-results/code-generation-[TASK_ID].yaml`

| Metric | Value |
|--------|-------|
| Overall score | [N]% |
| Cases pass | [N]/[M] |
| Refinement rounds | [0–2] |

### Cases

| Case ID | Score | Pass | Notes |
|---------|-------|------|-------|
| eval-r…-codegen-… | … | yes/no | |

### Eval-driven code fixes applied

- [List fixes made to pass eval cases — or "None; all cases passed on first score"]

<!-- [END mode-specific] -->

## Solve-Pipeline KPI Gate

Independent eval gate (both `codegen_mode` values) — see
`stage-gate/SOLVE_PIPELINE_KPI_EVAL_PROMPT.md`. 4 hard gates + 6 LLM judges:
`solution_correctness`/`code_quality` from
[eval-solve.yaml](https://github.com/openshift-eng/ai-helpers/blob/main/plugins/openshift-developer/evals/eval-solve.yaml)
(openshift-eng/ai-helpers PR #628), plus 4 repo-specific judges
(`cg01_reuse_over_reinvent`/`cg04_scope_boundaries`/`cg05_known_good_pattern`/
`cg06_build_verify_order`) from this team's own internal pattern-review
table — see `stage-gate/code-gen-eval-repo-specific.md` (not ai-helpers).
Skip this section entirely if `config.yaml → flags.solve_pipeline_kpi_eval`
is `false`.

**Scored once per plan phase, not per task** — this task's individual result
is rolled into its phase's gate, not scored on its own. See:

**Phase eval results**: `eval-results/solve-kpi-phase-[PHASE_NUMBER].yaml`

This task contributes `verify_status`/`test_status` (recorded in
`state.yaml → completed[]`) to that phase-level `make_verify_passes` /
`make_test_passes` aggregation. See the Phase [PHASE_NUMBER] summary
(presented when the phase completed) for the actual hard-gate and LLM-judge
scores, and `implementation/code-gen-implement-report.md` for the full
stage-wide rollup.

## Deviations

[None — or describe deviation from task payload / constitution and rationale]

<!-- [ai-helpers mode — codegen_mode: ai-helpers] -->

## Links

- Design bundle: `implementation/design-bundle.md` (snapshot at approval time)

<!-- [END mode-specific] -->
