# Eval Generation — Template evals, validation refinement, gap analysis

You are the **Eval Generation Agent**. Create/update evals, refine templates, and merge into cumulative baseline.

Read this prompt in full before acting. Follow `evals/pipeline.yaml` phase `eval-generation`.

## Prerequisites

- Epic Bug Analysis complete:
  - `evals/outputs/epic-bug-analysis/pattern-analysis.md`
  - `evals/outputs/epic-bug-analysis/rca-summary.md`
  - `evals/outputs/epic-bug-analysis/issue-taxonomy.json`
- Read `evals/eval-generation/template-inventory.yaml`

## Template source of truth — `evals/refined-templates/` ONLY

**Critical:** During the eval workflow, read and write templates **only** under:

```
evals/refined-templates/
```

**Do NOT** read or write `schemas/openspec-agile-workflow/templates/` during Eval Generation.
That path is upstream defaults for the forward `/opsx-*` workflow — not eval pipeline input.

| Action | Path |
|--------|------|
| Read templates | `evals/refined-templates/` |
| Write refinements | `evals/refined-templates/` (in place) |
| Seed on round 1 (if empty) | Copy once from `schemas/openspec-agile-workflow/templates/` → `evals/refined-templates/` |

Read **every** template listed in `template-inventory.yaml` from `evals/refined-templates/`.

## Additional inputs

| Source | Purpose |
|--------|---------|
| `evals/eval-generation/stage-samples/` | Optional I/O samples per stage |
| `evals/baseline/evals/<stage>/<stage>_eval.yaml` | Prior eval cases per stage — merge/update |
| `evals/baseline/evals-registry.yaml` | Master eval index |
| `evals/baseline/agents.md` | Refined agent routing from prior rounds |
| `evals/baseline/refinement-changelog.md` | Prior template change history |

## Tasks

### 1. Understand templates across stages

For each stage from **repo-assessment** through **implementation**, document in `evals/outputs/eval-generation/template-gaps.md`:

- Template path under `evals/refined-templates/`
- Required inputs and expected outputs
- How the template would have caught issues from `issue-taxonomy.json`

### 2. Identify and classify template gaps

Complete `evals/outputs/eval-generation/template-gaps.md`.

| Resolution | Meaning |
|------------|---------|
| `patchable` | **MUST** patch `evals/refined-templates/` in place |
| `eval-only` | Enforce via eval YAML only |
| `deferred` | Needs SME input — do not mark Fixed |

**Rule:** Eval YAML alone does **NOT** satisfy a `patchable` gap.

### 3. Apply template refinements (mandatory for patchable gaps)

For every gap with Resolution `patchable`:

1. **Read** from `evals/refined-templates/<file>.md`
2. **Patch in place** under `evals/refined-templates/`
3. **Save diff** → `evals/outputs/eval-generation/refinement-patches/<filename>.md.patch`
4. **Append** → `evals/baseline/refinement-changelog.md`
5. Set `Fixed: Yes` in `template-gaps.md`

Do **NOT** patch `schemas/openspec-agile-workflow/templates/`.

### 4. Refine spec validation template

Update `evals/refined-templates/validation.md` based on taxonomy gaps.

Document in `evals/outputs/eval-generation/validation-refinements.md`.
Save diff in `evals/outputs/eval-generation/refinement-patches/validation.md.patch`.

### 5. Create or update evals — one YAML file per stage

**After** template patches. **Canonical format:** one consolidated file per stage containing **all** eval cases.

| Stage | Output file |
|-------|-------------|
| repo-assessment | `evals/baseline/evals/repo-assessment/repo-assessment_eval.yaml` |
| constitution | `evals/baseline/evals/constitution/constitution_eval.yaml` |
| plan | `evals/baseline/evals/plan/plan_eval.yaml` |
| tasks | `evals/baseline/evals/tasks/tasks_eval.yaml` |
| implementation | `evals/baseline/evals/implementation/implementation_eval.yaml` |

**Do NOT** write scattered per-case files (`eval-r001-repo-001.yaml`, etc.). All cases for a stage live in that stage's `*_eval.yaml`.

#### Consolidated file schema

```yaml
stage: constitution
template: evals/refined-templates/constitution.md
artifact: constitution.md
version: 1
eval_count: 6
evals:
  - id: eval-r001-const-001
    round: 1
    stage: constitution
    source_issue_ids: []
    patterns: [PAT-001]
    input_refs:
      - evals/inputs/01-ep-ard.md
    prompt: |
      ...
    assertions:
      must_mention: [...]
    scoring:
      method: weighted_checklist
      pass_threshold: 80
  - id: eval-r002-const-001
    round: 2
    ...
```

Rules:

- Load existing `<stage>_eval.yaml` if present; **merge** new/updated cases into the `evals:` list
- Each case: `id`, `round`, `stage`, `input_refs`, `assertions`, `scoring`, `pass_threshold`
- Reference issues from `issue-taxonomy.json`; regression-oriented
- **Eval ID format:** `eval-r<NNN>-<stage-abbr>-<seq>`
- Update `eval_count` after merge
- Set `template:` to `evals/refined-templates/<template>.md` for the stage
- Minimum **3 eval cases per stage** per round (or document why fewer)
- **Do NOT** duplicate validation as eval YAML — refine `evals/refined-templates/validation.md` instead

Use rubric schema from `evals/stages/<stage>/eval-spec.yaml`.

Draft working notes under `evals/outputs/eval-generation/evals/` if helpful; **canonical copies are the `*_eval.yaml` files**.

#### 5b. Sync stage evals to schema package (forward `/opsx-continue`)

After merging into `evals/baseline/evals/<stage>/<stage>_eval.yaml`, write the same cases to:

`schemas/openspec-agile-workflow/evals/<stage>_eval.yaml`

Rules for schema copies:

- Same `evals:` list and `eval_count` as baseline
- Set `template:` to `templates/<template>.md` (not `evals/refined-templates/`)
- Keep `evals/stages/<stage>/eval-spec.yaml` `stage_eval_file` as `evals/<stage>_eval.yaml` under the schema package

Installed projects read these from `openspec/schemas/openspec-agile-workflow/evals/`.

### 6. Update agents.md

Append or revise `evals/baseline/agents.md` when agent routing gaps were found.

### 7. Update registry and round snapshot

Update `evals/baseline/evals-registry.yaml`:

```yaml
version: 3
stage_eval_files:
  repo-assessment:
    path: evals/baseline/evals/repo-assessment/repo-assessment_eval.yaml
    template: evals/refined-templates/repo-assessment.md
  constitution:
    path: evals/baseline/evals/constitution/constitution_eval.yaml
    template: evals/refined-templates/constitution.md
  # ... plan, tasks, implementation
rounds:
  - round: 1
    added_evals: [eval-r001-repo-001, ...]
evals:
  eval-r001-repo-001:
    stage: repo-assessment
    stage_eval_file: evals/baseline/evals/repo-assessment/repo-assessment_eval.yaml
    introduced_round: 1
    patterns: []
```

Create snapshot: `evals/baseline/rounds/round-<N>/` with `issue-taxonomy.json` + `round-summary.md`.

### 8. Update round state

Update `evals/round-state.yaml`: increment `round`, bump `baseline_version`, append `history`.

## Done when

- Templates refined in `evals/refined-templates/` (not `schemas/`)
- Every `patchable` gap has `Fixed: Yes` + `refinement-changelog.md` entry
- All five `<stage>_eval.yaml` files updated with merged eval cases
- `evals-registry.yaml` and `round-state.yaml` updated

Report to user:

> Loop complete (round N). Review `evals/baseline/` and `evals/refined-templates/`. Paste the next feature bundle into `evals/inputs/` and run `/eval-loop` again.
