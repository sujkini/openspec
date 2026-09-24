# E2E Pre-Analysis (Stage 1)

The HEAVY READ stage. All operator context is consumed here and distilled into `e2e-analysis.md`. Downstream stages read only this output.

## Inputs

All mode inputs (common):
- `agents.md` content (full — from step 0)
- `harness-evals/constitution.md` content (full)
- `{schema_root}/e2e-workflow/qe-behaviour.md` Sections 1-5 (generic QE rules)
- `qe-e2e/qe-behaviour.md` Sections 3a/3b (operator-specific, if present)
- `harness-docs/*.md` (if present)
- `harness-evals/evals/` (if present — for eval-aware pattern coverage)
- Target repo

PR Mode additional: PR URL, diff, review comments
Design Mode additional: ADR or EP document content
Combined Mode: both PR + ADR/EP inputs

## Process

Read and follow `{schema_root}/e2e-workflow/pre-analysis-gate.md` in full.

1. In PR Mode / Combined: fetch PR metadata, diff, and review comments via `gh`
2. In Design Mode: read ADR/EP document as primary scoping source
3. Classify change type
4. Impact analysis, coverage assessment, blast radius, regression risk
5. Cross-check against `agents.md` conventions and `constitution.md` guardrails
6. If stage evals exist: review them for patterns to cover
7. Produce proposed test cases (priority-ordered)
8. Embed operator context into output
9. Write `openspec/changes/<name>/e2e/e2e-analysis.md`

## Approval Gate

Present analysis to user. Wait for: Approved / Approved with changes / Rejected.
- On reject: re-run with feedback
- On approve: proceed to Stage 2

## Telemetry

```bash
# Before processing:
python -m openspec.telemetry.qe_events e2e_stage_start --change <name> --stage 1 --stage-name pre_analysis

# After approval:
python -m openspec.telemetry.qe_events e2e_stage_end --change <name> --stage 1 --tokens-in <N> --tokens-out <N> --duration-s <N> --refinement-rounds <N>
```
