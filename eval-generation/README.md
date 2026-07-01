# Eval Pipeline — Retrospective Workflow Improvement

Continuous improvement loop for **openspec-agile-workflow**: derive evals from completed feature bundles, refine templates, and accumulate learnings.

**Stage evals for `/opsx-continue`** ship with the schema package — not under `eval-generation/`:

`openspec/schemas/openspec-agile-workflow/eval-generation/*_eval.yaml`

`/eval-loop` writes eval cases to `eval-generation/output-eval-generation/` **and** syncs copies to the schema `eval-generation/` directory.

---

## Directory Structure

```
eval-generation/
├── input/                          # Single input file for each eval-loop round
│   └── feature-bundle.yaml         # All links and content for one feature bundle
├── output-eval-generation/                   # Stage-wise cumulative eval results
│   ├── repo-assessment/            # repo-assessment_eval.yaml
│   ├── constitution/               # constitution_eval.yaml
│   ├── plan/                       # plan_eval.yaml
│   ├── tasks/                      # tasks_eval.yaml
│   ├── implementation/             # implementation_eval.yaml
│   └── code-generation/            # code-generation_eval.yaml
└── eval-generation-workflow/       # All internal workflow machinery
    ├── pipeline.yaml               # Phase definitions and paths
    ├── round-state.yaml            # Current round counter
    ├── routing-learnings.md        # Bug-derived guardrails (cumulative)
    ├── refinement-changelog.md     # Template patch history
    ├── epic-bug-analysis/          # SYSTEM_PROMPT for analysis phase
    ├── eval-generation/            # SYSTEM_PROMPT + template-inventory
    ├── stages/                     # eval-spec.yaml rubrics per stage
    ├── refined-templates/          # Refined templates (eval workflow source of truth)
    ├── outputs/                    # Intermediate outputs per round
    │   ├── epic-bug-analysis/      # pattern-analysis, rca-summary, taxonomy
    │   └── eval-generation/        # template-gaps, patches
    └── rounds/                     # Round snapshots (round-1/, round-2/, ...)
```

---

## Getting Started

### 1. Fill the input file

Edit `eval-generation/input/feature-bundle.yaml` with data from **one completed feature**:

- Feature name and epic key
- Enhancement Proposal content
- Jira epic export
- Pre-feature repo state
- User stories
- PR links and diffs
- Bugs with root causes

### 2. Run `/eval-loop`

```
/eval-loop
```

### 3. Review outputs

- **`eval-generation/output-eval-generation/<stage>/`** — cumulative eval cases per stage
- **`eval-generation/eval-generation-workflow/refined-templates/`** — improved templates
- **`schemas/.../eval-generation/*_eval.yaml`** — synced for forward workflow

### 4. Repeat

Update `eval-generation/input/feature-bundle.yaml` with the next completed feature and run `/eval-loop` again. Prior evals accumulate — each round builds on the last.

---

## Data Flow

```
eval-generation/input/feature-bundle.yaml ──► Epic Bug Analysis ──► workflow/outputs/epic-bug-analysis/*
                                            │
eval-generation-workflow/                   │
  refined-templates/  ─────────┐          │
  routing-learnings.md  ───────┤          ▼
output-eval-generation/<stage>_eval.yaml ──┴────► Eval Generation
                                            │
                                            ├──► eval-generation/output-eval-generation/<stage>/<stage>_eval.yaml
                                            ├──► PATCH eval-generation-workflow/refined-templates/
                                            ├──► schemas/.../eval-generation/<stage>_eval.yaml (sync)
                                            └──► eval-generation-workflow/routing-learnings.md
```

**Round 2+:** Eval Generation reads **refined templates** and **consolidated stage eval files** from prior rounds in `output-eval-generation/`.

---

## Forward Workflow Integration

After `/eval-loop`, the forward workflow (`/opsx-continue` and `/opsx-apply`) reads:

| Forward workflow reads | Populated by |
|------------------------|--------------|
| `openspec/schemas/.../eval-generation/<stage>_eval.yaml` | `/eval-loop` sync (or `install.sh`) |
| `openspec/schemas/.../eval-generation/code-generation_eval.yaml` | `/eval-loop` code-gen eval authoring |

---

## Rules

- Do NOT modify `schemas/.../templates/` during eval — use `eval-generation-workflow/refined-templates/`
- Write all eval cases into ONE `<stage>_eval.yaml` per stage — no scattered per-case files
- `validation-template.md` is refined in refined-templates/ — not duplicated as eval YAML
- code-generation evals are tagged with `oape_command` and run during `/opsx-apply`
