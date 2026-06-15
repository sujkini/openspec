# Stage Eval Gate — Forward workflow (`/opsx-continue`)

Score and refine **change artifacts** using stage evals shipped with the schema package. **Do not** modify schema templates or `evals/refined-templates/`.

Paths below are **relative to the schema root** (`openspec/schemas/openspec-agile-workflow/` when installed, or `schemas/openspec-agile-workflow/` in this distribution repo).

Read `stage-gate/artifact-eval-map.yaml` for artifact → eval file mapping.

## When this runs

After **openspec-agile-workflow** creates one artifact (step 6 of `/opsx-continue`), **before** user approval:

```
Generate v1 → Run evals → Refine artifact (v2+) → Present scorecard → User approval → STOP
```

Next `/opsx-continue` unlocks the following artifact only after user approved the current one.

## Template vs eval sources

| Purpose | Path |
|---------|------|
| **Generate artifact** | `templates/` (via `openspec instructions --json`) |
| **Score artifact** | `evals/<stage>_eval.yaml` |
| **Assertion schema** | `evals/stages/<stage>/eval-spec.yaml` |
| **Do NOT edit** | `schemas/.../templates/`, `evals/refined-templates/` |

## Step 1 — Generate artifact (v1)

Use existing `/opsx-continue` flow:

1. `openspec instructions <artifact-id> --change "<name>" --json`
2. Read all `dependencies` from the change directory
3. Write artifact to `outputPath` (v1)

Save a copy reference: you will need v1 text for refinement even after overwriting the file.

## Step 2 — Run stage evals

Load mapping from `artifact-eval-map.yaml`:

| `gate` | Action |
|--------|--------|
| `stage_evals` | Load `stage_eval_file`, score every case in `evals:` list |
| `rubric_only` | Score `validation.json` against `schemas/.../validation.md` rubric (no YAML cases) |
| `skip` | Skip eval scoring; proceed to user approval after generation |

### Scoring each case (`stage_evals`)

For each entry in `<stage>_eval.yaml` → `evals:`:

1. Read case `prompt`, `assertions`, `scoring.pass_threshold` (or per-case threshold)
2. Evaluate the **artifact at outputPath** against each assertion type in `evals/stages/<stage>/eval-spec.yaml`
3. Record per case: `pass`, `score` (0–100), `failures[]` (specific missed assertions with quotes)

**Assertion checks (agent judgment):**

- `must_mention`: each string appears in artifact (case-insensitive ok for paths; exact for ports/IDs)
- `must_not_mention` / `must_not_claim`: must be absent
- `must_identify_package`, `must_cite_pre_feature_gap`, `must_cite_repo_evidence`, etc.: apply as rubric intent
- `must_include_verification_matrix`, `must_pair_verification_tasks`, …: structural checks on artifact

Overall stage score: average of case scores (or weighted if case specifies). Stage passes if all cases ≥ their `pass_threshold`.

### Write eval results

```
openspec/changes/<change-name>/eval-results/<artifact-id>.yaml
```

```yaml
artifact_id: plan
artifact_path: openspec/changes/cm-830/plan.md
stage: plan
stage_eval_file: evals/plan_eval.yaml
scored_at: <ISO8601>
overall_score: 72
overall_pass: false
cases:
  - id: eval-r001-plan-001
    score: 100
    pass: true
    failures: []
  - id: eval-r002-plan-003
    score: 45
    pass: false
    failures:
      - "must_mention: tamper — not found in §6 verification matrix"
```

## Step 3 — Refine artifact (mandatory if any case fails)

If **any** case fails, produce a **refined artifact** at the same `outputPath` (v2). One refinement pass minimum; re-score after refinement. If still failing, refine again (max 2 auto passes) or present remaining gaps to user at approval.

### Refinement context bundle (pass ALL of these)

Include in the refinement prompt — do not regenerate blind:

| # | Context | Source |
|---|---------|--------|
| 1 | **Draft artifact v1** | Full text before overwrite |
| 2 | **Eval scorecard** | `eval-results/<artifact-id>.yaml` failures |
| 3 | **Failed case details** | `prompt` + `assertions` from each failed case in `*_eval.yaml` |
| 4 | **Openspec instructions** | `instruction`, `template`, `rules`, `context` from `openspec instructions --json` |
| 5 | **Schema template** | `templates/<template>.md` (structure only) |
| 6 | **Dependency artifacts** | All files listed in instructions `dependencies` / change deps |
| 7 | **Change inputs** | `openspec/changes/<name>/inputs/jira.yaml`, `jira-spec.md` if present |
| 8 | **User feedback** | If user rejected prior approval — include verbatim |

### Refinement rules

- **Fix only** failed assertions and obvious contradictions with dependencies
- **Preserve** content that already passes eval cases
- **Do not** edit `schemas/.../templates/` or `evals/refined-templates/`
- **Do not** invent facts not in dependencies / inputs
- Overwrite artifact at `outputPath` with v2

Re-run Step 2 on v2. Update eval-results file (append `refinement_round: 2` or replace with latest).

## Step 4 — User approval gate

Present to user:

1. **Artifact**: path + short summary of what was produced/refined
2. **Eval scorecard**: overall % + table of cases (pass/fail) + top failures
3. **Refinement**: "Refined after eval" yes/no; what was added/fixed
4. **Ask**:

> Eval score: **{overall_score}%** ({N}/{M} cases pass).  
> Approve this artifact and proceed to the next stage?  
> **(Approve / Reject with feedback)**

- **Approve** → mark artifact done per schema gate; STOP (one artifact per `/opsx-continue`)
- **Reject with feedback** → run Step 3 again with user feedback in context bundle; re-present Step 4; do not advance

Do **not** create the next artifact in the same invocation.

## Co-generated artifacts (repo-assessment + constitution)

If both are created in one session (same invocation per schema co-generation):

- Run eval gate **separately** for each artifact file
- Refine each failing artifact independently
- Single joint approval question covering both scorecards (per schema `joint_with`)

## Guardrails

- Forward workflow refines **artifacts only** — never templates
- Stage evals are **read-only** during forward workflow (do not add cases mid-change unless user asks)
- `evals/refined-templates/` is for `/eval-loop` only
- One artifact (+ eval gate) per `/opsx-continue` invocation
