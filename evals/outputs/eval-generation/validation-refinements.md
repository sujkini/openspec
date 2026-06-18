# Validation refinements — Round 3 Istio CSR

## Changes

Added **Code-generation eval bridge** section to `evals/refined-templates/validation.md` under Completeness rubric.

## Driver

PAT-015 — retrospective artifact evals (round 1) did not enforce patterns at `/opsx-apply` because
`code-generation_eval.yaml` was empty. Validation must flag specs whose tasks would not map to per-task
code-generation gates.

## Patterns addressed

- PAT-003 (unified manager) → codegen eval must forbid separate cache
- PAT-004 (Ready condition) → codegen eval + e2e assertion
- PAT-005 (OLM upgrade) → manual bundle codegen eval
- PAT-006 (bindata version) → manual manifest codegen eval
