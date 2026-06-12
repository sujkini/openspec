---
name: eval-loop
description: Run full retrospective eval loop for one feature bundle. Use for /eval-loop.
license: MIT
metadata:
  author: openspec
  version: "1.0"
---

Single command for the eval improvement pipeline. One feature bundle per invocation.

## When to use

User runs `/eval-loop` after pasting a feature bundle into `evals/inputs/`.

## Execution

1. Read `evals/pipeline.yaml`
2. Validate `evals/inputs/` — halt on `PASTE_` placeholders
3. Load `evals/baseline/` and `evals/round-state.yaml`
4. Follow `evals/epic-bug-analysis/SYSTEM_PROMPT.md` → write `evals/outputs/epic-bug-analysis/*`
5. Follow `evals/eval-generation/SYSTEM_PROMPT.md`:
   - Identify gaps → `template-gaps.md` (classify patchable vs eval-only)
   - **Patch every patchable gap into `schemas/openspec-agile-workflow/templates/` in place**
   - Then merge evals and update baseline
6. Increment round in `evals/round-state.yaml`

## Template path

Prefer `openspec/schemas/openspec-agile-workflow/templates/`, else `schemas/openspec-agile-workflow/templates/`.

## Feedback loop

- Round 2+ reads cumulative `evals/baseline/evals/` in both phases
- Templates read from schema path are already refined from prior rounds

## Do not

- Split into multiple commands
- Store templates under baseline/
- Skip Eval Generation after Epic Bug Analysis
