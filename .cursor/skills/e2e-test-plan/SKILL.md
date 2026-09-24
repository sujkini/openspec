# E2E Test Plan Generation (Stage 2)

Generate a full tiered test plan from the approved pre-analysis.

## Inputs (NARROW — no raw operator docs)

- Approved `e2e-analysis.md` (from Stage 1 — carries all scoping decisions + embedded operator context)
- `{schema_root}/e2e-workflow/qe-behaviour.md` Sections 1-5 (generic QE writing rules)
- PR diff (for traceability to specific file:line — PR Mode / Combined Mode only)

Do NOT re-read `agents.md` or `constitution.md` at this stage. The operator context they provided is already embedded in `e2e-analysis.md`.

## Process

Read and follow `{schema_root}/e2e-workflow/test-plan-generation.md` in full.

1. Read approved `e2e-analysis.md` as scoping input
2. Read generic QE writing rules
3. Expand proposed test cases into full test steps (preconditions, steps, expected outcomes, cleanup)
4. Build traceability matrix
5. Run quality gates (Section 8 of template) — revise until all pass
6. Write `openspec/changes/<name>/e2e/test-plan.md`

## Approval Gate

Present test plan summary (test count, tier distribution, quality gate results).
Wait for user approval.
- On reject: revise with feedback
- On approve: proceed to Stage 3

## Telemetry

Emit `e2e_stage_start` (stage=2) before processing. On approval, emit `e2e_stage_end`.
