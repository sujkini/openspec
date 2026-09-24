# Artifact Feedback Loop

Handle artifact rejection and revision. Called when the user rejects an artifact during the eval gate.

## Trigger

User rejects an artifact during `STAGE_EVAL_GATE_PROMPT.md` Step 5.

## Steps

### 1. Load Revision Context

Read and follow `{schema_root}/stage-gate/USER_FEEDBACK_PROMPT.md`.

Gather:
- User's rejection feedback
- Current artifact content
- Eval results (scores, failing criteria)
- Original generation template and inputs

### 2. Determine Fix Strategy

- If feedback targets artifact content only: patch the artifact in-place.
- If feedback reveals a template deficiency (rare): may patch `{schema_root}/templates/` — document the template change.
- Write a round summary to `feedback_stage_artifacts/`.

### 3. Regenerate Artifact

Re-invoke `openspec instructions <artifact-id> --change "<name>" --json` with revision context.

If Phase N > 1 and artifact is `tasks`: ensure prior phase tasks are preserved when regenerating.

### 4. Re-run Eval Gate

Re-execute `STAGE_EVAL_GATE_PROMPT.md` Steps 1-5 on the revised artifact.

### 5. Re-present for Approval

Present the revised artifact with:
- Summary of changes from feedback
- New eval score vs. previous score
- Approval prompt (or auto-approve if `auto_approve: true`)

### 6. Special Case: Specs Rejection

If the rejected artifact is `specs` and `exit_on_reject.specs` is configured:
- Do NOT regenerate. STOP the workflow.
- Output the rejection reason and instruct user to revise the Jira ticket.
