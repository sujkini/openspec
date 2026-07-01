---
name: /eval-loop
id: eval-loop
category: Eval Pipeline
description: Run full retrospective eval loop for one feature bundle (Epic Bug Analysis → Eval Generation → output-evals)
---

Run the **complete eval improvement loop** for whatever is currently in `eval-generation/input/`.

One command. One feature bundle. When done, update `eval-generation/input/feature-bundle.yaml` with the next bundle and run again.

## What this command does

```
1. Validate eval-generation/input/feature-bundle.yaml       (stop if PASTE_ placeholders remain)
2. Load prior output-eval-generation/ + refined-templates/   (round 2+)
3. Epic Bug Analysis                              → eval-generation-workflow/outputs/epic-bug-analysis/*
4. Eval Generation
   a. Identify template gaps                      → eval-generation-workflow/outputs/eval-generation/template-gaps.md
   b. Apply patchable gaps                        → refine templates in eval-generation-workflow/refined-templates/
   c. Merge eval cases per stage                  → eval-generation/output-eval-generation/<stage>/<stage>_eval.yaml
   d. Create code-generation evals                → eval-generation/output-eval-generation/code-generation/code-generation_eval.yaml
   e. Sync flat stage evals                       → openspec/schemas/openspec-agile-workflow/eval-generation/<stage>_eval.yaml
   f. Update round state
5. Increment round                                → eval-generation-workflow/round-state.yaml
```

## Before running

Fill `eval-generation/input/feature-bundle.yaml` with data from **one completed feature**:

| Field | What to paste |
|-------|---------------|
| `feature_name` | Feature name |
| `epic_key` | Jira epic key |
| `target_repo` | Target repository URL |
| `enhancement_proposal` | Full EP/ARD content |
| `jira_epic` | Jira epic export |
| `repo_state` | Pre-feature repo state |
| `user_stories` | User stories linked to the epic |
| `repo_prs` | PR links and diffs |
| `bugs` | Bug list with root causes |

## Agent instructions

1. Read `eval-generation/eval-generation-workflow/pipeline.yaml` for phase order and paths.
2. Read **`eval-generation/eval-generation-workflow/epic-bug-analysis/SYSTEM_PROMPT.md`** — execute Epic Bug Analysis fully.
3. Read **`eval-generation/eval-generation-workflow/eval-generation/SYSTEM_PROMPT.md`** — execute Eval Generation fully.
4. Do **not** stop between Epic Bug Analysis and Eval Generation unless the user explicitly asks.

### Template path (eval workflow)

| Read / write | Path |
|--------------|------|
| **Eval pipeline templates** | `eval-generation/eval-generation-workflow/refined-templates/` only |
| **Do NOT use during eval** | `openspec/schemas/openspec-agile-workflow/templates/` |

Seed `eval-generation/eval-generation-workflow/refined-templates/` from `schemas/` once on round 1 if empty. All refinements go to `eval-generation-workflow/refined-templates/`.

### Consolidated eval files

One YAML per stage — all cases in `evals:` list:

| Stage | File |
|-------|------|
| repo-assessment | `eval-generation/output-eval-generation/repo-assessment/repo-assessment_eval.yaml` |
| constitution | `eval-generation/output-eval-generation/constitution/constitution_eval.yaml` |
| plan | `eval-generation/output-eval-generation/plan/plan_eval.yaml` |
| tasks | `eval-generation/output-eval-generation/tasks/tasks_eval.yaml` |
| implementation | `eval-generation/output-eval-generation/implementation/implementation_eval.yaml` |
| code-generation | `eval-generation/output-eval-generation/code-generation/code-generation_eval.yaml` |

Also sync each merged file to **`openspec/schemas/openspec-agile-workflow/eval-generation/<stage>_eval.yaml`** for forward `/opsx-continue`. **code-generation** has no template — synced for `/opsx-apply` per-task gate.

Do **not** write scattered `eval-r001-*.yaml` per-case files.

### Feedback loop (critical)

| Asset | Round 1 | Round 2+ |
|-------|---------|----------|
| `eval-generation/output-eval-generation/<stage>/<stage>_eval.yaml` | Empty → populated | **Read + merge** |
| `eval-generation/eval-generation-workflow/refined-templates/` | Seed from schemas → refine | Read **refined** copies → refine again |
| `eval-generation/eval-generation-workflow/routing-learnings.md` | Placeholder → updated | **Read + update** |

Epic Bug Analysis on round 2+ must cross-check bugs against prior evals in `output-eval-generation/` files.

## Outputs

| Location | Content |
|----------|---------|
| `eval-generation/eval-generation-workflow/outputs/epic-bug-analysis/` | pattern-analysis, rca-summary, issue-taxonomy |
| `eval-generation/eval-generation-workflow/outputs/eval-generation/` | template-gaps, validation-refinements, patches |
| `eval-generation/output-eval-generation/<stage>/<stage>_eval.yaml` | Consolidated eval cases per stage |
| `openspec/schemas/openspec-agile-workflow/eval-generation/<stage>_eval.yaml` | Forward workflow stage evals (synced) |
| `eval-generation/eval-generation-workflow/rounds/round-N/` | Round snapshot |
| `eval-generation/eval-generation-workflow/refined-templates/*.md` | Refined templates (eval workflow source of truth) |
| `eval-generation/eval-generation-workflow/round-state.yaml` | Incremented round |

## After completion

Tell the user:

> Loop complete (round N). Review `eval-generation/output-eval-generation/` and `eval-generation/eval-generation-workflow/refined-templates/`. Update `eval-generation/input/feature-bundle.yaml` with the next feature bundle and run `/eval-loop` again.

## Guardrails

- Do not use `/opsx-*` commands in this pipeline
- Do not patch `openspec/schemas/openspec-agile-workflow/templates/` during eval — use `eval-generation-workflow/refined-templates/`
- Do not mark template-gaps Fixed unless refined-templates/ was actually patched
- Write all eval cases into `<stage>_eval.yaml` — not per-case files
- Do not delete prior eval cases without explicit user approval
- Process bugs one at a time during Epic Bug Analysis
