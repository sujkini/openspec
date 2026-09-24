# Crash Recovery

Detect and recover from interrupted `/opsx-apply` sessions. Referenced by the preflight skill when `state.yaml` shows an in-flight state.

## Trigger

This skill activates when `implementation/state.yaml` → `machine.state` is one of:
- `EXECUTING_TASK`
- `RUNNING_TESTS`
- `EVAL_GATE`

These states indicate a previous agent session crashed or was interrupted mid-task.

## Recovery Steps

1. **Read state.yaml** — get `current_task_id`, `current_task_index`, `machine.state`.

2. **Check git status** for uncommitted changes:
   ```bash
   git status --porcelain
   ```

3. **Check for partial task report**:
   ```
   openspec/changes/<name>/implementation/task-reports/<current_task_id>.md
   ```
   If the report exists and shows `PASS`, the task was likely completed but state was not advanced.

4. **Present recovery options** via `AskQuestion`:

   **Option A — Resume (recommended):**
   Retry the current task from where it left off. Keeps uncommitted changes.
   - Set state → `IDLE` via `state-transition`
   - Re-enter normal `/opsx-apply` flow (will pick up `current_task_id` as next task)

   **Option B — Skip:**
   Mark current task as incomplete and move to next task.
   - Add to `completed[]` with `test_result: SKIPPED (crash recovery)`
   - Advance `current_task_index`
   - Set state → `IDLE`

   **Option C — Rollback:**
   Discard uncommitted changes and retry clean.
   ```bash
   git checkout -- .
   git clean -fd
   ```
   - Set state → `IDLE`
   - Re-enter `/opsx-apply` flow

5. **Log recovery event** (telemetry):
   ```bash
   python -m openspec.telemetry.auto state-transition --change "<name>" --to IDLE --task "<current_task_id>"
   ```

## Guard

If `last_transition` in state.yaml is within the last 30 seconds, the session may still be active. Warn the user before proceeding with recovery.
