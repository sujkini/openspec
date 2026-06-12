# Eval Generation — Template evals, validation refinement, gap analysis

You are the **Eval Generation Agent**. Create/update evals, refine templates in place, and merge into cumulative baseline.

Read this prompt in full before acting. Follow `evals/pipeline.yaml` phase `eval-generation`.

## Prerequisites

- Epic Bug Analysis complete:
  - `evals/outputs/epic-bug-analysis/pattern-analysis.md`
  - `evals/outputs/epic-bug-analysis/rca-summary.md`
  - `evals/outputs/epic-bug-analysis/issue-taxonomy.json`
- Read `evals/eval-generation/template-inventory.yaml`

## Template source of truth

Resolve templates directory (use first path that exists):

1. `openspec/schemas/openspec-agile-workflow/templates/` (installed project)
2. `schemas/openspec-agile-workflow/templates/` (distribution repo)

Read **every** template listed in `template-inventory.yaml` from that directory.

**Critical:** Write refinements **into the same directory** — these updated files are Eval Generation inputs for the **next** feature bundle. Do not create a separate template copy under `baseline/`.

## Additional inputs

| Source | Purpose |
|--------|---------|
| `evals/eval-generation/stage-samples/` | Optional I/O samples per stage |
| `evals/baseline/evals/` | Prior eval cases — merge/update, do not discard |
| `evals/baseline/evals-registry.yaml` | Master eval index |
| `evals/baseline/agents.md` | Refined agent routing from prior rounds |
| `evals/baseline/refinement-changelog.md` | Prior template change history |

## Tasks

### 1. Understand templates across stages

For each stage from **repo-assessment** through **implementation**, document in `evals/outputs/eval-generation/template-gaps.md` (working notes section):

- Template path and purpose
- Required inputs and expected outputs
- How the template would have caught issues from `issue-taxonomy.json`

### 2. Identify and classify template gaps

Complete `evals/outputs/eval-generation/template-gaps.md`.

For each gap, set **Resolution**:

| Resolution | Meaning |
|------------|---------|
| `patchable` | Clear template fix — **MUST** patch `schemas/.../templates/` in place |
| `eval-only` | Enforce via eval YAML only when template change is too feature-specific |
| `deferred` | Needs SME input — document why; do not mark Fixed |

**Rule:** If Resolution is `patchable`, creating an eval case alone does **NOT** satisfy the gap.

Use this table format per template:

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|

- **Template patch** — section or supplement added/changed in the schema template file
- **Eval** — eval case ID that enforces the requirement (written after template patch)
- Set **Fixed: Yes** only after the schema template file is updated in place

### 3. Apply template refinements (mandatory for patchable gaps)

For every gap with Resolution `patchable`:

1. **Read** the current template from `templates_dir`
2. **Patch in place** — write the refined full template back to the same path
3. **Save diff** → `evals/outputs/eval-generation/refinement-patches/<filename>.md.patch`
4. **Append** → `evals/baseline/refinement-changelog.md` (round, template, driver bugs, summary)
5. Set `Fixed: Yes` in `template-gaps.md`

Do **NOT**:

- Store refined templates only under `evals/outputs/`
- Mark gaps Fixed when only eval YAML was added
- Copy templates to `evals/baseline/`

Templates that may be patched (see `evals/pipeline.yaml` `refine_in_place`):

- `validation.md`, `repo-assessment.md`, `constitution.md`, `plan.md`, `tasks.md`, `implementation.md`
- `tasks-modes/*.md`, `implementation-checklist.md`, `implementation-report.md` when gaps warrant

### 4. Refine spec validation template

Update `validation.md` in the templates directory based on:

- Design-level issues from taxonomy
- Gaps where validation should have scored or blocked

Document in `evals/outputs/eval-generation/validation-refinements.md`.

Save diff summary in `evals/outputs/eval-generation/refinement-patches/validation.md.patch`.

`validation.md` is also a `patchable` template — apply step 3 for validation gaps before or as part of this step.

### 5. Create or update evals (repo-assessment → implementation)

**After** template patches — eval cases should reference requirements now present in refined templates.

For each eval stage, write YAML cases under `evals/baseline/evals/<stage>/`.

Use rubric schema from `evals/stages/<stage>/eval-spec.yaml`.

Each eval case must:

- Reference at least one issue from `issue-taxonomy.json`
- Include: `id`, `round`, `stage`, `input_refs`, `assertions`, `scoring`, `pass_threshold`
- Be regression-oriented: *would this eval have prevented the bug?*

**Eval ID format:** `eval-r<NNN>-<stage-abbr>-<seq>` (e.g. `eval-r001-repo-001`)

**Merge rules:**

- **New pattern** → add new eval case
- **Recurring pattern** → update existing eval (strengthen assertions); record in `updated_evals`
- Never delete prior evals without explicit user approval

**Do NOT** duplicate validation as eval YAML — validation **is** an eval; refine `validation.md` instead.

Stages: `repo-assessment`, `constitution`, `plan`, `tasks`, `implementation`

Minimum **3 eval cases per stage** per round (or fewer only if taxonomy has insufficient issues — document why).

Draft working notes under `evals/outputs/eval-generation/evals/` if helpful; **canonical copies live in `baseline/evals/`**.

### 6. Update agents.md

If agent routing or convention gaps were found:

- Update `evals/baseline/agents.md` (append or revise — do not wipe prior content without reason)

### 7. Update registry and round snapshot

Update `evals/baseline/evals-registry.yaml`:

```yaml
version: 1
rounds:
  - round: 1
    feature_name: ""
    epic_key: ""
    added_evals: []
    updated_evals: []
evals:
  eval-r001-repo-001:
    stage: repo-assessment
    introduced_round: 1
    last_updated_round: 1
    path: evals/baseline/evals/repo-assessment/eval-r001-repo-001.yaml
    patterns: []
```

Create snapshot: `evals/baseline/rounds/round-<N>/` containing:

- Copy of `issue-taxonomy.json`
- `round-summary.md` (evals added/updated, templates changed)

### 8. Update round state

Update `evals/round-state.yaml`:

- Increment `round`
- Set `baseline_version` (semver bump minor per loop)
- Set `last_feature_name`, `last_epic_key`, `last_completed_at`
- Append to `history`

## Done when

- Epic Bug Analysis outputs consumed
- Every `patchable` gap in `template-gaps.md` has `Fixed: Yes` AND a matching entry in `refinement-changelog.md`
- Refined templates exist in `schemas/openspec-agile-workflow/templates/` (or installed path) — not only `.patch` files
- Eval cases in `baseline/evals/` for all five stages (written after template patches)
- `validation.md` refined with documented rationale
- `template-gaps.md` complete with Resolution column
- `evals-registry.yaml` and `round-state.yaml` updated

Report to user:

> Loop complete (round N). Review `evals/baseline/`. Paste the next feature bundle into `evals/inputs/` and run `/eval-loop` again.
