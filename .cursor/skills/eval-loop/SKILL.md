---
name: eval-loop
description: Run full retrospective eval loop for one feature bundle. Use for /eval-loop.
license: MIT
metadata:
  author: openspec
  version: "2.0"
---

Single command for the eval improvement pipeline. One feature bundle per invocation.

## When to use

User runs `/eval-loop` after filling `eval-generation/input/feature-bundle.yaml`.

## Execution

1. Read `eval-generation/eval-generation-workflow/pipeline.yaml`
2. Validate `eval-generation/input/feature-bundle.yaml` — halt on `PASTE_` placeholders
3. Load `eval-generation/output-eval-generation/`, `eval-generation/eval-generation-workflow/refined-templates/`, and `round-state.yaml`
4. Follow `eval-generation/eval-generation-workflow/epic-bug-analysis/SYSTEM_PROMPT.md` → write outputs
5. Follow `eval-generation/eval-generation-workflow/eval-generation/SYSTEM_PROMPT.md`:
   - Templates: read/write **`eval-generation/eval-generation-workflow/refined-templates/` only** (not `schemas/`)
   - Identify gaps → patch refined-templates
   - Merge evals into **`eval-generation/output-eval-generation/<stage>/<stage>_eval.yaml`** (one file per stage)
   - Author **code-generation** evals → `eval-generation/output-eval-generation/code-generation/code-generation_eval.yaml`
   - Sync flat copies to **`openspec/schemas/openspec-agile-workflow/eval-generation/<stage>_eval.yaml`**
   - Update round state
6. Increment round in `eval-generation/eval-generation-workflow/round-state.yaml`

## Template path

**Eval workflow:** `eval-generation/eval-generation-workflow/refined-templates/` — read and write.

**Do not** patch `openspec/schemas/openspec-agile-workflow/templates/` during eval. Seed refined-templates from schemas on round 1 if empty.

## Consolidated eval files

| Stage | File |
|-------|------|
| repo-assessment | `eval-generation/output-eval-generation/repo-assessment/repo-assessment_eval.yaml` |
| constitution | `eval-generation/output-eval-generation/constitution/constitution_eval.yaml` |
| plan | `eval-generation/output-eval-generation/plan/plan_eval.yaml` |
| tasks | `eval-generation/output-eval-generation/tasks/tasks_eval.yaml` |
| implementation | `eval-generation/output-eval-generation/implementation/implementation_eval.yaml` |
| code-generation | `eval-generation/output-eval-generation/code-generation/code-generation_eval.yaml` |

## Feedback loop

- Round 2+ reads `output-eval-generation/<stage>/<stage>_eval.yaml` and `eval-generation-workflow/refined-templates/` in both phases
- Templates accumulate refinements under `eval-generation-workflow/refined-templates/`

## Do not

- Split into multiple commands
- Patch schemas/ during eval workflow
- Write per-case `eval-r*.yaml` files — use consolidated `*_eval.yaml`
- Skip Eval Generation after Epic Bug Analysis
