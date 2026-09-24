# Telemetry Hooks Reference

Lookup table for all OpenSpec telemetry CLI invocations. When a command or skill needs to fire a telemetry event, consult this table for the exact invocation.

All hooks are **silent and non-blocking** — failures are logged but never block the workflow.

## Event Table

| Event | CLI invocation | When to fire |
|-------|---------------|--------------|
| New change | `python -m openspec.telemetry.auto on-new --change "<name>" --jira-key <KEY>` | After `/opsx-new` creates the change directory |
| Artifact start | `python -m openspec.telemetry.auto on-artifact-start --change "<name>" --artifact "<id>"` | Before generating an artifact in `/opsx-continue` |
| Artifact created | `python -m openspec.telemetry.auto on-artifact-created --change "<name>" --artifact "<id>"` | After artifact file is written to disk |
| Waiting approval | `python -m openspec.telemetry.auto on-waiting-approval --change "<name>" --artifact "<id>" --score <N>` | After eval, before user approval prompt |
| Artifact complete | `python -m openspec.telemetry.auto on-artifact-complete --change "<name>" --artifact "<id>" --status passed --score <N> --label "<label>"` | After user approves/rejects artifact |
| Apply start | `python -m openspec.telemetry.auto on-apply-start --change "<name>"` | When `/opsx-apply` task loop begins |
| Task start | `python -m openspec.telemetry.auto on-task-start --change "<name>" --task-id <TID> --title "<title>" --agent "<agent>"` | Before executing each task |
| Task complete | `python -m openspec.telemetry.auto on-task-complete --change "<name>" --task-id <TID> --status passed` | After task approved/failed |
| Phase complete | `python -m openspec.telemetry.auto on-phase-complete --change "<name>" --phase <N> --pr-raised <true\|false>` | After all phase tasks done (phase-iterative) |
| Apply complete | `python -m openspec.telemetry.auto on-apply-complete --change "<name>"` | After all tasks/phases done |
| Archive feedback | `python -m openspec.telemetry.auto on-archive-feedback --change "<name>" --story-points <N> --manual-effort "<bucket>" --satisfaction <1-5> --comments "<text>"` | During `/opsx-archive` feedback collection |
| QE archive feedback | `python -m openspec.telemetry.auto on-qe-archive-feedback --change "<name>" --story-points <N> --manual-effort "<bucket>" --satisfaction <1-5> --comments "<text>"` | During `/opsx-archive` if E2E run exists |

## Optional Flags

### `--batch`

Add `--batch` to `on-artifact-start`, `on-artifact-created`, `on-artifact-complete`, and `on-task-complete` when processing multiple artifacts or tasks in a single session (i.e., `auto_approve: true` loop). Batch mode skips per-item token attribution and uses phase-level estimates instead.

### `--phase <N>`

Add `--phase <N>` to any hook when `task_execution_mode = phase-iterative` AND the artifact is `tasks` or the event is task/apply-related. This creates sub-phase tracking rows on the telemetry dashboard.

Omit `--phase` for:
- One-shot mode
- Non-task artifacts (validation, specs, repo-assessment, plan)

## State CLI Helpers

| Command | Purpose |
|---------|---------|
| `python -m openspec.telemetry.auto state-get --change "<name>"` | Return current state as JSON |
| `python -m openspec.telemetry.auto state-next --change "<name>"` | Determine next action + skill to invoke |
| `python -m openspec.telemetry.auto state-transition --change "<name>" --to <STATE> [--task <TID>]` | Validate and perform state transition |

State helpers read/write `implementation/state.yaml` and enforce legal transitions.
