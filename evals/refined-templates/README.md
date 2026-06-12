# Refined templates — eval workflow source of truth

Templates refined by `/eval-loop` Eval Generation. **Do not read or write `schemas/openspec-agile-workflow/templates/` during the eval pipeline.**

| Role | Path |
|------|------|
| **Upstream (unchanged)** | `schemas/openspec-agile-workflow/templates/` — distribution defaults for `/opsx-*` forward workflow |
| **Eval pipeline (read + write)** | `evals/refined-templates/` — cumulative refinements from retrospective eval loops |

## Rules

1. Epic Bug Analysis and Eval Generation **read** templates from `evals/refined-templates/` only.
2. Patchable gaps from `template-gaps.md` are applied **here** — not in `schemas/`.
3. Round 2+ loads the **already-refined** copies from this directory.
4. Audit trail: `evals/outputs/eval-generation/refinement-patches/` + `evals/baseline/refinement-changelog.md`.

## Initial seed

On first `/eval-loop` (empty refined-templates), seed from `schemas/openspec-agile-workflow/templates/` before gap analysis, then refine in place under this directory.
