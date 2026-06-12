---
name: /eval-loop
id: eval-loop
category: Eval Pipeline
description: Run full retrospective eval loop for one feature bundle (Epic Bug Analysis → Eval Generation → baseline)
---

Run the **complete eval improvement loop** for whatever is currently in `evals/inputs/`.

One command. One feature bundle. When done, paste the next bundle into `evals/inputs/` and run again.

## What this command does

```
1. Validate evals/inputs/              (stop if PASTE_ placeholders remain)
2. Load evals/baseline/                (prior evals + agents.md — required on round 2+)
3. Epic Bug Analysis                   → evals/outputs/epic-bug-analysis/*
4. Eval Generation
   a. Identify template gaps           → evals/outputs/eval-generation/template-gaps.md
   b. Apply patchable gaps              → refine templates in schemas/openspec-agile-workflow/templates/
   c. Write eval cases                  → evals/baseline/evals/
   d. Update registry + round snapshot
5. Update round-state                  → increment round, snapshot under baseline/rounds/
```

## Before running

Fill **all** files under `evals/inputs/`:

| File | Paste |
|------|-------|
| `feature-meta.yaml` | Feature name, epic key (optional) |
| `01-ep-ard.md` | EP link + content |
| `02-jira-epic.md` | Epic export |
| `03-original-repo.md` | Pre-feature repo pin |
| `04-user-stories.md` | Stories |
| `05-repo-prs.md` | PR links |
| `bugs/index.yaml` | Bug keys |
| `bugs/<KEY>.md` | One file per bug |

Remove or rename `bugs/PASTE_BUG_KEY_1.md` when adding real bug files.

## Agent instructions

1. Read `evals/pipeline.yaml` for phase order and paths.
2. Read **`evals/epic-bug-analysis/SYSTEM_PROMPT.md`** — execute Epic Bug Analysis fully.
3. Read **`evals/eval-generation/SYSTEM_PROMPT.md`** — execute Eval Generation fully.
4. Do **not** stop between Epic Bug Analysis and Eval Generation unless the user explicitly asks.

### Template path resolution

Use the first path that exists:

1. `openspec/schemas/openspec-agile-workflow/templates/`
2. `schemas/openspec-agile-workflow/templates/`

Eval Generation **reads and writes** templates at that path. Updated templates are inputs for the **next** `/eval-loop`.

### Feedback loop (critical)

| Asset | Round 1 | Round 2+ |
|-------|---------|----------|
| `evals/baseline/evals/` | Empty → populated | **Read + merge/update** |
| `evals/baseline/evals-registry.yaml` | Initialized | **Read + append** |
| Schema templates | Read → refine in place | Read **updated** copies → refine again |
| `evals/baseline/agents.md` | Placeholder → updated if gaps | **Read + update** |

Epic Bug Analysis on round 2+ must cross-check bugs against prior evals in `baseline/evals/`.

## Outputs

| Location | Content |
|----------|---------|
| `evals/outputs/epic-bug-analysis/` | pattern-analysis, rca-summary, issue-taxonomy |
| `evals/outputs/eval-generation/` | template-gaps, validation-refinements, patches |
| `evals/baseline/evals/` | Cumulative eval YAML cases |
| `evals/baseline/rounds/round-N/` | Round snapshot |
| `schemas/openspec-agile-workflow/templates/*.md` | Refined templates (in place) |
| `evals/outputs/eval-generation/refinement-patches/` | Diff summary per patched template |
| `evals/baseline/refinement-changelog.md` | Append-only template change log |
| `evals/round-state.yaml` | Incremented round |

## After completion

Tell the user:

> Loop complete (round N). Review `evals/baseline/`. Replace `evals/inputs/` with the next feature bundle and run `/eval-loop` again.

## Guardrails

- Do not use `/opsx-*` commands in this pipeline
- Do not create feature-specific case folders — only generic `evals/inputs/`
- Do not copy templates to `baseline/` — templates live in schema path only
- Do not mark template-gaps Fixed unless the schema template file was actually patched
- Eval YAML supplements templates; it does not replace template refinement for patchable gaps
- Do not delete prior eval cases without explicit user approval
- Process bugs one at a time during Epic Bug Analysis
