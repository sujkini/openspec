# Eval pipeline — retrospective workflow improvement

Continuous improvement loop for **openspec-agile-workflow**: derive evals from completed feature bundles (EP + epic + stories + PRs + bugs), refine templates, and accumulate learnings for the next bundle.

## One command, one feature bundle

```
Paste inputs → /eval-loop → baseline updated → paste next bundle → /eval-loop again
```

| Step | Action |
|------|--------|
| 1 | Fill `evals/inputs/` with one feature bundle (links + exports) |
| 2 | Run **`/eval-loop`** in Cursor |
| 3 | Review `evals/baseline/` and `evals/refined-templates/` |
| 4 | Replace `evals/inputs/` with the next feature bundle |
| 5 | Run **`/eval-loop`** again — prior evals and refined templates are auto-loaded |

## Data flow

```
evals/inputs/  ──────────────────►  Epic Bug Analysis  ──►  evals/outputs/epic-bug-analysis/*
                                              │
evals/refined-templates/  ───────┐          │
baseline/evals/*_eval.yaml  ───┤          ▼
baseline/agents.md  ───────────┴────►  Eval Generation
                                              │
                                              ├──► evals/baseline/evals/<stage>/<stage>_eval.yaml
                                              ├──► PATCH evals/refined-templates/
                                              └──► evals/baseline/agents.md
```

**Round 2+:** Eval Generation reads **refined templates** and **consolidated stage eval files** from prior rounds.

## Template paths

| Path | Role |
|------|------|
| `schemas/openspec-agile-workflow/templates/` | Upstream defaults for forward `/opsx-*` workflow — **not** eval pipeline input |
| `evals/refined-templates/` | **Eval workflow read/write** — cumulative template refinements |

On round 1 (empty `refined-templates/`), seed once from `schemas/`, then refine only under `evals/refined-templates/`.

### Template refinement (mandatory for patchable gaps)

| Gap type | Action |
|----------|--------|
| `patchable` | Update file in `evals/refined-templates/` |
| `eval-only` | Eval YAML only — document why in `template-gaps.md` |
| `deferred` | Open question — do not mark Fixed |

Audit trail: `evals/outputs/eval-generation/refinement-patches/` + `evals/baseline/refinement-changelog.md`

## Consolidated eval files (one per stage)

All eval cases for a stage live in a **single YAML file**:

| Stage | File |
|-------|------|
| repo-assessment | `evals/baseline/evals/repo-assessment/repo-assessment_eval.yaml` |
| constitution | `evals/baseline/evals/constitution/constitution_eval.yaml` |
| plan | `evals/baseline/evals/plan/plan_eval.yaml` |
| tasks | `evals/baseline/evals/tasks/tasks_eval.yaml` |
| implementation | `evals/baseline/evals/implementation/implementation_eval.yaml` |

Each file contains an `evals:` list with all cases (round 1, round 2, …). Do **not** scatter per-case `eval-r*.yaml` files.

## Directory layout

| Path | Purpose |
|------|---------|
| `inputs/` | Generic placeholders — replace each round |
| `refined-templates/` | Refined templates — eval workflow source of truth |
| `outputs/epic-bug-analysis/` | Current round RCA artifacts |
| `outputs/eval-generation/` | Gap analysis, patches, drafts |
| `baseline/evals/<stage>/<stage>_eval.yaml` | Cumulative eval cases per stage |
| `baseline/evals-registry.yaml` | Master index |
| `baseline/agents.md` | Refined agent routing |
| `baseline/rounds/round-N/` | Snapshot per completed loop |
| `epic-bug-analysis/SYSTEM_PROMPT.md` | Epic Bug Analysis instructions |
| `eval-generation/SYSTEM_PROMPT.md` | Eval Generation instructions |
| `round-state.yaml` | Current round number |

## Eval Generation stages

Evals are created/updated for: **repo-assessment → constitution → plan → tasks → implementation**.

**validation.md** is refined in `evals/refined-templates/` (spec-stage eval) — not duplicated under `baseline/evals/`.
