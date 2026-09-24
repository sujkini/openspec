# Continue Artifact

Generate the next artifact in the pipeline, run eval gate, and present for approval. Called by `/opsx-continue` for each ready artifact.

## Steps

### 1. Pick Ready Artifact

Run `openspec status --change "<name>" --json`. Pick first artifact with `status: "ready"`.

### 2. Pre-generation Checks

**If artifact is `repo-assessment`:**
- Check `inputs/jira.yaml` → `target_repo`. If absent/empty: STOP — ask user for repo URL. Persist to `inputs/jira.yaml`. Verify accessible.

**If artifact is `plan`:**
- Read `harness-evals/constitution.md`. If missing/empty: STOP — tell user to run `/opsx-constitute` or place it manually.

**If artifact is `tasks`:**
- Delegate to `.cursor/skills/continue-phase-tasks/SKILL.md` for phase-specific logic.

### 3. Telemetry — Artifact Start

```bash
python -m openspec.telemetry.auto on-artifact-start --change "<name>" --artifact "<id>"
```
Add `--phase <N>` only when `task_execution_mode = phase-iterative` AND artifact is `tasks`.
Add `--batch` when in auto-approve loop.

### 4. Generate Artifact

```bash
openspec instructions <artifact-id> --change "<name>" --json
```
Create artifact at `outputPath` (v1).
- **phase-iterative tasks**: pass `phase_scope` and `task_sizing` metadata. Append to tasks.md if Phase N > 1.
- **one-shot tasks**: pass `task_sizing` only. Generate all phases.

### 5. Telemetry — Artifact Created

```bash
python -m openspec.telemetry.auto on-artifact-created --change "<name>" --artifact "<id>"
```

### 6. Stage Eval Gate

Read and follow `{schema_root}/stage-gate/STAGE_EVAL_GATE_PROMPT.md` Steps 1-5.

Key paths:
- Artifact-to-eval mapping: `{schema_root}/stage-gate/artifact-eval-map.yaml`
- Stage eval cases: `harness-evals/evals/<stage>_eval.yaml`
- Eval results: `openspec/changes/<name>/eval-results/<artifact-id>.yaml`
- Eval report: `openspec/changes/<name>/eval-results/<artifact-id>_evaluation_report.md`

If eval file missing: skip eval scoring, proceed directly to approval.

On user rejection: follow `{schema_root}/stage-gate/USER_FEEDBACK_PROMPT.md`.
On `specs` rejection: exit workflow (`exit_on_reject.specs`) — do NOT regenerate. STOP.

Read `config.yaml → flags.auto_approve`: if `true`, auto-approve (no prompt).

### 7. Telemetry — Post-Approval

```bash
python -m openspec.telemetry.auto on-artifact-complete --change "<name>" --artifact "<id>" --status passed --score <N> --label "<label>"
```
Use `--status failed` if rejected. Add `--phase <N>` for phase-iterative tasks.

### 8. Post-Approve Actions

After approval, check if post-approval steps apply:
- Delegate to `.cursor/skills/continue-jira-story/SKILL.md` when conditions match (step 11b or 12).
