---
name: Processing Time and Test Tracking
overview: Add agent-only processing time tracking, verification result capture, serve local metrics-report.json for export, and remove token burn from the entire codebase.
todos:
  - id: remove-token-burn-backend
    content: "Remove token burn: delete compute_token_burn, TokenBurnEntry/Out schemas, /token-burn endpoint, report_service reference"
    status: pending
  - id: remove-token-burn-frontend
    content: "Remove token burn: delete TokenBurnChart.tsx, useTokenBurn hook, fetchTokenBurn, SSE invalidation, App.tsx references"
    status: pending
  - id: remove-token-burn-types
    content: "Remove token burn: clean up TokenBurnOut from RunReportOut (Python + TypeScript), update docs"
    status: pending
  - id: serve-local-report
    content: Add GET /runs/{run_id}/local-report endpoint to serve metrics-report.json from disk
    status: pending
  - id: export-button-rewire
    content: Update DashboardHeader.tsx exportReport() to call local-report endpoint instead
    status: pending
  - id: processing-time-models
    content: Add processing_time_s to PhaseExecution and TaskExecution DB models
    status: pending
  - id: processing-time-auto
    content: Track agent start/stop timestamps in auto.py hooks and compute processing_time_s
    status: pending
  - id: processing-time-client
    content: Extend client.py end_phase/end_task with processing_time_s field
    status: pending
  - id: processing-time-poller
    content: Persist processing_time_s in FileEventPoller handlers
    status: pending
  - id: processing-time-metrics
    content: Add agent_processing_time_s to compute_global_health and GlobalHealthMetrics schema
    status: pending
  - id: processing-time-report
    content: Compute processing time from event pairs in report.py _reconstruct_phases
    status: pending
  - id: processing-time-ui
    content: Add Agent Processing Time card to GlobalHealthMetrics.tsx
    status: pending
  - id: fix-wall-time
    content: Fix cumulative_wall_time_s to use started_at/completed_at instead of unreliable duration_s
    status: pending
  - id: verify-db-model
    content: Add verification_pass, verification_command, verification_result, verification_output columns to TaskExecution
    status: pending
  - id: verify-auto-state
    content: Read state.yaml in on_task_complete to extract verification results automatically
    status: pending
  - id: verify-client-event
    content: Extend client.py end_task with verification result fields
    status: pending
  - id: verify-poller
    content: Persist verification fields in FileEventPoller._handle_task_end
    status: pending
  - id: verify-report
    content: Extend report.py _reconstruct_tasks and _compute_global_health with verification aggregation
    status: pending
  - id: verify-metrics-endpoint
    content: Add VerificationSummaryOut schema, compute_verification_summary service, and GET /metrics/verification-summary endpoint
    status: pending
  - id: verify-ui-component
    content: Create VerificationSummary.tsx component and wire into App.tsx
    status: pending
  - id: verify-export
    content: Include verification_summary in local metrics-report.json via report.py
    status: pending
isProject: false
---

# Dashboard Enhancements Plan

Four features: remove token burn, serve local report for export, agent processing time, and unit test tracking.

---

## Feature 0: Remove Token Burn (cleanup)

**Goal:** Remove the "Token Burn per Worker Role" chart and all supporting code from the entire codebase.

**Delete entirely:**
- [dashboard/web/src/components/metrics/TokenBurnChart.tsx](dashboard/web/src/components/metrics/TokenBurnChart.tsx) -- the full component

**Backend removals:**
- [dashboard/src/services/metrics_service.py](dashboard/src/services/metrics_service.py) -- delete `compute_token_burn()` function (lines 132-167) and `TokenBurnEntry`/`TokenBurnOut` imports (lines 18-19)
- [dashboard/src/schemas/metrics.py](dashboard/src/schemas/metrics.py) -- delete `TokenBurnEntry` and `TokenBurnOut` classes (lines 19-28)
- [dashboard/src/api/v1/metrics.py](dashboard/src/api/v1/metrics.py) -- delete `/token-burn/{run_id}` route (lines 17-19), remove `TokenBurnOut` and `compute_token_burn` imports
- [dashboard/src/services/report_service.py](dashboard/src/services/report_service.py) -- remove `compute_token_burn` import (line 22) and `token_burn=...` from `RunReportOut(...)` (line 61)
- [dashboard/src/schemas/report.py](dashboard/src/schemas/report.py) -- remove `TokenBurnOut` import (line 8) and `token_burn` field from `RunReportOut` (line 21)

**Frontend removals:**
- [dashboard/web/src/App.tsx](dashboard/web/src/App.tsx) -- remove `TokenBurnChart` import (line 8), `useTokenBurn` from import (line 12), `useTokenBurn` call (line 27), `<TokenBurnChart>` render (line 85)
- [dashboard/web/src/hooks/useMetrics.ts](dashboard/web/src/hooks/useMetrics.ts) -- remove `fetchTokenBurn` import (line 2), delete entire `useTokenBurn` hook (lines 14-21)
- [dashboard/web/src/services/api.ts](dashboard/web/src/services/api.ts) -- remove `TokenBurnOut` from imports (line 8), delete `fetchTokenBurn` function (lines 56-58)
- [dashboard/web/src/hooks/useLiveTelemetry.ts](dashboard/web/src/hooks/useLiveTelemetry.ts) -- remove `tokenBurn` query invalidation (line 25)
- [dashboard/web/src/types/index.ts](dashboard/web/src/types/index.ts) -- delete `TokenBurnEntry` and `TokenBurnOut` interfaces (lines 103-113), remove `token_burn` from `RunReportOut` (line 135)

**Docs:**
- [dashboard/README.md](dashboard/README.md) -- remove token burn curl example (line 140), update descriptions (lines 221, 243), remove checklist item (line 328)
- [TELEMETRY_README.md](TELEMETRY_README.md) -- reword "token burn" bullet (line 24)

**Keep untouched:** `token_attribution` field on `TaskExecution` (used by batch mode logic, not token-burn-specific), `token_cost_per_million` in config (used by global health cost computation).

---

## Feature 1: Serve Local metrics-report.json for Export

**Goal:** When the user clicks "Export JSON," download the local `metrics-report.json` file that `report.py` generates after every telemetry hook. This file is the authoritative source -- it has Jira metadata (`jira_epic_link`, `jira_task_name`, `operator_name`) that the DB-based export lacks.

**Approach:** Add a new endpoint that resolves the change directory from the run's `change_name`, reads the pre-generated `metrics-report.json` from disk, and returns it. The frontend button calls this instead of the old DB-based endpoint.

**Backend:**
- [dashboard/src/api/v1/runs.py](dashboard/src/api/v1/runs.py) -- add `GET /{run_id}/local-report` endpoint:
  - Look up the `PipelineRun` by `run_id` to get `change_name`
  - Extract the change slug from `change_name` (split on ` — `)
  - Resolve `openspec/changes/<slug>/telemetry/metrics-report.json` via `get_change_dir()`
  - If file exists, return its JSON content directly (`Response(content=..., media_type="application/json")`)
  - If not, fall back to calling `generate_report(slug)` to create it, then return it
  - No Pydantic schema needed -- return raw JSON to preserve all fields including Jira metadata

**Frontend:**
- [dashboard/web/src/services/api.ts](dashboard/web/src/services/api.ts) -- add `fetchLocalReport(runId)` that calls `GET /runs/{runId}/local-report`
- [dashboard/web/src/components/layout/DashboardHeader.tsx](dashboard/web/src/components/layout/DashboardHeader.tsx) -- change `exportReport()` to call `fetchLocalReport` instead of `fetchRunReport`. Remove the old `fetchRunReport` import. Download filename: `metrics-report-{runId}.json`

**Cleanup:** After token burn removal and this rewiring, `fetchRunReport` and the old `GET /{run_id}/report` endpoint can optionally be kept as an internal API or removed entirely. The `RunReportOut` schema (minus `token_burn`) remains useful for programmatic consumers if needed.

---

## Feature A: Agent-Only Processing Time

**Goal:** Track the time the AI agent is actively working, excluding human review/approval wait time. Surface this as a separate metric alongside the existing wall time.

**Approach -- event-pair timing (recommended):**

The telemetry hooks already fire at natural start/stop boundaries. We compute processing time as the sum of `(agent_stop - agent_start)` intervals within each phase:

- **Phases 1-4:** `on-artifact-start` to `on-waiting-approval` = agent active. `on-waiting-approval` to `on-artifact-complete` = human wait. For multi-artifact phases (phase 1 has validation + specs), sum each artifact's active interval.
- **Phase 5:** `on-task-start` to task presentation (YIELD) = agent active. YIELD to `on-task-complete` = human wait.

This requires NO new hooks -- just new timestamp tracking in `.dashboard.json` state and a subtraction.

**Files to change:**

- [dashboard/src/models/phase.py](dashboard/src/models/phase.py) -- add `processing_time_s` column to `PhaseExecution`
- [dashboard/src/models/task.py](dashboard/src/models/task.py) -- add `processing_time_s` column to `TaskExecution`
- [dashboard/src/schemas/metrics.py](dashboard/src/schemas/metrics.py) -- add `agent_processing_time_s` to `GlobalHealthMetrics`
- [openspec/telemetry/auto.py](openspec/telemetry/auto.py) -- record timestamps in `.dashboard.json` at each hook, compute `processing_time_s = total_duration - human_wait`
- [openspec/telemetry/client.py](openspec/telemetry/client.py) -- add `processing_time_s` to `end_phase()` and `end_task()` event payloads
- [dashboard/src/services/file_event_poller.py](dashboard/src/services/file_event_poller.py) -- persist `processing_time_s` from events
- [dashboard/src/services/metrics_service.py](dashboard/src/services/metrics_service.py) -- sum `processing_time_s` across phases for `agent_processing_time_s`
- [openspec/telemetry/report.py](openspec/telemetry/report.py) -- compute processing time from event timestamps in `_reconstruct_phases`
- [dashboard/web/src/types/index.ts](dashboard/web/src/types/index.ts) -- add `agent_processing_time_s` to `GlobalHealthMetrics`
- [dashboard/web/src/components/metrics/GlobalHealthMetrics.tsx](dashboard/web/src/components/metrics/GlobalHealthMetrics.tsx) -- add "Agent Processing Time" metric card
- [dashboard/src/schemas/report.py](dashboard/src/schemas/report.py) -- include in `RunReportOut`

**Computation logic (in `auto.py`):**

```python
# on-artifact-start: record agent_start_ts in state
# on-waiting-approval: record agent_stop_ts, compute agent_active += (stop - start)
# on-artifact-complete: processing_time_s = agent_active (excludes approval wait)
```

For phase 5:
```python
# on-task-start: record task_agent_start_ts
# on-task-complete: compute task_processing = now - task_agent_start - (approval_wait if any)
```

Also fix the existing `cumulative_wall_time_s` to use `PhaseExecution.started_at` / `completed_at` directly in `compute_global_health()` instead of the unreliable `duration_s` field (fixes the 60-second placeholder for single-artifact phases).

---

### Feature B: Verification Result Tracking

**Goal:** Capture per-task verification results (build pass/fail, command run, output summary) and surface them in the dashboard. This covers ALL verification types -- not just unit tests:

| Task Type | Verification Command | What it checks |
|---|---|---|
| Controller tasks | `go test ./...` | Unit tests |
| API tasks | `go build` + `go vet` | Compilation + linting |
| E2E tasks | `go build` | Compilation |
| Manual tasks | Varies per acceptance criteria | Depends |

The label in the UI should be **"Verification Results"**, not "Unit Test Results."

**Recommended approach -- extend the existing `task_end` event pipeline (full DB schema):**

Structured data in the DB, proper schema, dedicated endpoint, purpose-built UI component.

**The data already exists** in `state.yaml`'s `current_task_result`. Every task records these verification-only fields (no eval gate fields):
- `verification_pass: true/false`
- `test_command: "go test ./..." or "go build" or "make verify"`
- `test_result: PASS/FAIL`
- `test_output_summary: "..."` (brief output)

**Files to change:**

- [dashboard/src/models/task.py](dashboard/src/models/task.py) -- add 4 columns:
  - `verification_pass: Mapped[bool | None]` (nullable Boolean -- did the verification step pass?)
  - `verification_command: Mapped[str]` (String 512 -- what was run: `go test`, `go build`, `make verify`, etc.)
  - `verification_result: Mapped[str]` (String 16, default "" -- "PASS" or "FAIL")
  - `verification_output: Mapped[str]` (Text, default "" -- brief output summary)

- [openspec/telemetry/auto.py](openspec/telemetry/auto.py) -- in `on_task_complete`:
  - Read `implementation/state.yaml` to extract `current_task_result` verification fields
  - Pass them to `client.end_task()` automatically (no new CLI args needed)

- [openspec/telemetry/client.py](openspec/telemetry/client.py) -- extend `end_task()` signature and event dict with the 4 verification fields

- [openspec/telemetry/report.py](openspec/telemetry/report.py) -- extend `_reconstruct_tasks()` to pick up verification fields; add verification aggregation to `_compute_global_health()`

- [dashboard/src/services/file_event_poller.py](dashboard/src/services/file_event_poller.py) -- extend `_handle_task_end` to persist verification fields

- [dashboard/src/schemas/metrics.py](dashboard/src/schemas/metrics.py) -- add schemas:
  ```python
  class TaskVerificationEntry(BaseModel):
      task_id: str
      task_title: str
      agent_id: str
      verification_pass: bool | None
      verification_command: str
      verification_result: str
      verification_output: str

  class VerificationSummaryOut(BaseModel):
      tasks_verified: int       # tasks that ran any verification
      tasks_green: int          # verification_pass == True
      tasks_red: int            # verification_pass == False
      pass_rate: float          # tasks_green / tasks_verified * 100
      per_task: list[TaskVerificationEntry]
  ```

- [dashboard/src/services/metrics_service.py](dashboard/src/services/metrics_service.py) -- add `compute_verification_summary()` function

- [dashboard/src/api/v1/metrics.py](dashboard/src/api/v1/metrics.py) -- add `GET /metrics/verification-summary/{run_id}` endpoint

- [dashboard/web/src/types/index.ts](dashboard/web/src/types/index.ts) -- add `VerificationSummaryOut` and `TaskVerificationEntry` types

- [dashboard/web/src/services/api.ts](dashboard/web/src/services/api.ts) -- add `fetchVerificationSummary()` function

- [dashboard/web/src/hooks/useMetrics.ts](dashboard/web/src/hooks/useMetrics.ts) -- add `useVerificationSummary()` hook

- New file: `dashboard/web/src/components/metrics/VerificationSummary.tsx` -- table with columns: Task ID, Agent, Command, Result (PASS/FAIL with color), Output. Header shows "Verification Results" with a summary badge `(N/M passed)`.

- [dashboard/web/src/App.tsx](dashboard/web/src/App.tsx) -- render `VerificationSummary` component in the metrics section

**Why read from `state.yaml` instead of adding CLI args (recommended approach):**

Reading `state.yaml` in `on_task_complete` is more reliable than CLI args because:
- The data is already structured and validated in `current_task_result`
- No risk of the agent forgetting to pass flags
- Works identically for both `ai-helpers` and `direct` codegen modes
- No changes needed to [opsx-apply.md](.cursor/commands/opsx-apply.md) command syntax

**Helper function in `auto.py`:**

```python
def _read_task_verification(change: str, task_id: str) -> dict:
    """Read verification results from state.yaml's current_task_result."""
    state_path = CHANGES_DIR / change / "implementation" / "state.yaml"
    if not state_path.exists():
        return {}
    import yaml
    state = yaml.safe_load(state_path.read_text()) or {}
    result = state.get("current_task_result", {})
    if result.get("task_id") != task_id:
        for c in state.get("completed", []):
            if c.get("task_id") == task_id:
                result = c
                break
        else:
            return {}
    return {
        "verification_pass": result.get("verification_pass"),
        "verification_command": result.get("test_command", ""),
        "verification_result": result.get("test_result", ""),
        "verification_output": result.get("test_output_summary", ""),
    }
```

**Note:** The `state.yaml` field names (`test_command`, `test_result`, `test_output_summary`) are mapped to the new `verification_*` names at this boundary. No changes needed to `opsx-apply.md`'s result format.

---

---

### Known Issue: Background Sub-Agents (Opus 4.6)

The "no background sub-agents" guardrail already exists in:
- [opsx-apply.md](.cursor/commands/opsx-apply.md) Hard Rule #8 (line 48)
- [opsx-continue.md](.cursor/commands/opsx-continue.md) Guardrails (line 93)
- [TELEMETRY_README.md](TELEMETRY_README.md) (line 46)

Opus 4.6 sometimes ignores this instruction and launches background sub-agents, which breaks telemetry (hooks run in the main session only). The guardrail is NOT in the OpenSpec schema (`openspec/schemas/openspec-agile-workflow/`). This is a prompt-compliance issue, not a code bug -- no code changes will fix it. Options to reinforce: make the instruction more prominent in command files, add it to the schema YAML, or add it to `openspec/config.yaml`.

---

### Migration Note

Features A and B add columns to existing SQLite tables. Since this project uses raw SQLAlchemy without Alembic, the simplest approach is:
- SQLite supports `ALTER TABLE ... ADD COLUMN` for nullable columns with defaults
- Add a lightweight migration script or startup check in the poller that adds missing columns
- Alternatively, delete and recreate the DB (`data/dashboard.db`) since it's populated from `events.jsonl` on restart

### Execution Order

Recommended implementation sequence:
1. **Feature 0** (remove token burn) -- clean removal, no dependencies
2. **Feature 1** (local report export) -- quick win, independent
3. **Feature A** (processing time) -- medium complexity, backend + frontend
4. **Feature B** (test tracking) -- largest scope, touches the most files
