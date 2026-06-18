# User Approval Feedback Gate — Forward workflow (`/opsx-continue`)

When the user **rejects with feedback** at artifact approval, run the feedback stage defined in schema `user_approval_feedback_gate`. **Do not** modify previously approved artifacts.

## When this runs

After **stage eval gate** (if applicable) and **user approval prompt**:

```
Present artifact → Ask approval →
  Approve → lock artifact → unlock next → STOP
  Reject with feedback → feedback stage → regenerate current artifact → re-eval → ask approval
```

Repeat until the user approves or explicitly stops.

## Step 1 — Capture feedback

1. Record user feedback verbatim in `openspec/changes/<change>/feedback/<artifact-id>.yaml` (append a round).
2. Do **not** edit any artifact file with status `done` in `openspec status --change "<name>" --json`.

## Step 2 — Load revision context

| # | Context | Source |
|---|---------|--------|
| 1 | **Original generation prompt** | `prompts/<artifact-id>.yaml` or reconstruct from `openspec instructions <id> --json` |
| 2 | **Current artifact draft** | Full text at `outputPath` (post eval-gate version) |
| 3 | **Dependency artifacts** | All `dependencies` / schema `requires` — **read-only** |
| 4 | **Eval scorecard** | `eval-results/<artifact-id>.yaml` if stage evals ran |
| 5 | **Prior feedback rounds** | `feedback/<artifact-id>.yaml` history |
| 6 | **Change inputs** | `inputs/jira.yaml`, `jira-spec.md` if present |

## Step 3 — Update prompt and regenerate

Build a revision prompt that includes:

- Original `instruction`, `template`, `rules`, `context` from the generation snapshot
- **USER FEEDBACK** — verbatim from this rejection
- **REVISION DIRECTIVES** — address every feedback point; revise only the current artifact
- **IMMUTABLE INPUTS** — list every dependency path with status `done`; read-only

Regenerate **only** the current artifact at `outputPath`. For joint gates (`repo-assessment` + `constitution`), regenerate both co-generated files in one round — still do not touch upstream approved artifacts.

Append an updated snapshot to `prompts/<artifact-id>.yaml` (`generation_round` + `feedback_applied` summary).

### Guardrails

- **Never** overwrite files for artifacts already marked `done` (except the artifact currently under approval).
- If feedback **requires** changing an approved upstream artifact, **stop** and tell the user which stage must be reopened — do not silently edit upstream files.
- **Do not** edit `templates/` or `evals/refined-templates/`.
- **Do not** create the next workflow artifact in the same invocation.

## Step 4 — Re-run eval gate (when applicable)

If `artifact-eval-map.yaml` maps this artifact to `gate: stage_evals`, re-score the refined artifact and update `eval-results/<artifact-id>.yaml`.

## Step 5 — Re-present approval

Present:

1. **Refined artifact** — path + summary of changes made for feedback
2. **Eval scorecard** — if evals ran (updated scores)
3. **Feedback addressed** — bullet list mapping feedback → changes
4. **Immutable inputs** — confirm no upstream approved artifacts were modified

Ask (schema `user_approval_feedback_gate.approval_prompt`):

> Approve this artifact and proceed to the next stage?  
> **(Approve / Reject with feedback)**

- **Approve** → mark artifact done; lock as immutable; STOP
- **Reject** → return to Step 1 with new feedback

## Co-generated artifacts (repo-assessment + constitution)

Single joint approval covers both. On reject, revise **both** artifacts using one shared feedback round. Run eval gate separately for each file. Still treat `specs.md` and all earlier artifacts as immutable.

## Implementation task approval variant

Implementation runs OAPE **task-by-task**. User approval is required **after every
task** before advancing to the next (including across phase boundaries). On reject,
append feedback to `implementation/design-bundle.md` **REVISION FEEDBACK** and
re-run OAPE commands for the **current task only** — do not regenerate approved
OpenSpec artifacts, do not mark the task complete, and do not start the next task.
