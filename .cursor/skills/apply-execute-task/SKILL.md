# Execute Task

Dispatches a single task to the appropriate codegen skill based on `codegen_mode`. Called by `/opsx-apply` for each pending task.

## Prerequisites

- `state.yaml` read and `current_task_id` identified
- `config.yaml` → `flags.codegen_mode` read (`direct` or `ai-helpers`)

## Steps

### 1. E2E Guard

Before executing, classify the task using schema `e2e_exclusion.task_criteria`:
- Assigned Agent is `Testing_Agent`
- Acceptance criteria references `make test-e2e` or `test-e2e-wait-for-stable-state`
- Target file(s) under `test/` (e2e, ginkgo, or `*_test.go` integration/e2e paths)
- Task Title or Objective contains "e2e" or "end-to-end" (case-insensitive)

If matched: mark `- [x]` in tasks.md with note `SKIPPED_E2E`, write minimal task-report with `status: skipped_e2e`, signal `on-task-complete --status skipped`, proceed to next pending task.

### 2. Context Windowing

Read ONLY the §4 payload for `current_task_id` from tasks.md. Do NOT read payloads for other tasks.

### 3. Set State

```bash
python -m openspec.telemetry.auto state-transition --change "<name>" --to EXECUTING_TASK --task "<TASK_ID>"
```

Fire telemetry:
```bash
python -m openspec.telemetry.auto on-task-start --change "<name>" --task-id "<TASK_ID>" --agent "<AGENT_ID>" --title "<task_title>"
```
Add `--phase <N>` when `task_execution_mode = phase-iterative`.

### 4. Dispatch

| `codegen_mode` | Skill |
|----------------|-------|
| `direct` | Read and follow `.cursor/skills/apply-direct/SKILL.md` |
| `ai-helpers` | Read and follow `.cursor/skills/apply-ai-helpers/SKILL.md` |

### 5. Present Result

Before setting `AWAITING_APPROVAL`, run source integrity check for changed Go files:
- Each changed `.go` file must contain exactly one `package` clause
- If any file has duplicate package declarations, restore from `HEAD`, re-apply edits, re-run verification

Set state: `AWAITING_APPROVAL`. Write state.yaml.

Present task summary (files changed, test results, eval scores, deviations).

**If `auto_approve: true`:** Treat as approved. Write task report, mark `- [x]`, set state `IDLE`, fire `on-task-complete --batch`, return to caller for next task.

**If `auto_approve: false`:** ASK approval question. YIELD — end response.
