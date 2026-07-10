# OpenSpec Telemetry

Lightweight, file-based telemetry for the OpenSpec agile workflow.
No server, no database, no frontend — just NDJSON event logs and a JSON metrics report per change.

## How It Works

1. **Telemetry hooks** (`openspec/telemetry/auto.py`) write NDJSON events to disk whenever a workflow lifecycle event occurs (new run, artifact start/complete, task start/complete, etc.).
2. After each hook call, **`report.py`** auto-generates a comprehensive `metrics-report.json` containing every metric previously displayed on the dashboard.
3. All data is stored locally under `openspec/changes/<change>/telemetry/`.

## Telemetry Firing Strategy

Every lifecycle hook emits structured events that update global metrics immediately — not just at approval or phase end.

| Hook timing | Event type | Purpose |
|-------------|------------|---------|
| **Start** (`on-artifact-start`, `on-apply-start`, `on-task-start`) | `phase_start` / `task_start` | Phase/task appears as **running** on the dashboard immediately |
| **Mid** (`on-artifact-created`, `on-waiting-approval`, `on-task-complete`) | `phase_progress` | Partial token/score/iteration update; global_health recomputes cost/tokens in real-time |
| **End** (`on-artifact-complete`, `on-apply-complete`) | `phase_end` / `run_end` | Final status, cumulative tokens, duration; closes phase |

**Why start+end matters:**
- Start events show the operator that work has begun (UI shows "running" status).
- Mid events update token burn and cost estimates progressively, so the operator doesn't see stale zeros until approval.
- End events finalize metrics and compute duration.

**Spec-understanding note:** `/opsx-new` registers the run (`run_create`) but does NOT start the phase clock. The first phase (`spec_understanding`) starts at `/opsx-continue` step 6 when `on-artifact-start --artifact validation` fires. Jira metadata fetch during `/opsx-new` is preparatory input, not a telemetry phase.

## Batch Mode

When multiple tasks or artifacts are completed in a single agent session (e.g. "approve all", "continue all"), file-based token estimation cannot distinguish per-item usage — the same shared context is counted identically for every item. To avoid overestimation, hooks support a `--batch` flag that shifts token attribution to the phase level.

**How it works:**

| Hook | Batch flag | Effect |
|------|------------|--------|
| `on-apply-start` | `--batch` | Marks phase 5 as batch mode |
| `on-task-complete` | `--batch` | Emits `task_end` with `tokens_in=0`, `tokens_out=0`, `attribution: "phase_aggregate"` — skips `phase_progress` |
| `on-apply-complete` | (none) | Detects batch mode; uses `estimate_phase5_tokens()` for a single honest phase total |
| `on-artifact-start` | `--batch` | Marks artifact phase as batch mode |
| `on-artifact-created` | `--batch` | Skips token-bearing `phase_progress` |
| `on-artifact-complete` | `--batch` | Uses `estimate_artifact_phase_tokens()` for phase-level total |

**Auto-detect:** If `--batch` is omitted but `on-apply-complete` detects 2+ tasks with near-identical token estimates (within 5%), it auto-corrects to phase-level attribution.

**Why background agents break metering:** Telemetry hooks run in the main agent session. Background sub-agents, background shells, or Task-tool agents with `run_in_background=true` produce work that cannot be metered, resulting in missing or incorrect metrics. Both `/opsx-apply` and `/opsx-continue` prohibit background sub-agents.

### Batch mode example

```bash
python -m openspec.telemetry.auto on-apply-start --change cm-830 --batch
python -m openspec.telemetry.auto on-task-start --change cm-830 --task-id T1_1 --agent API_Agent
python -m openspec.telemetry.auto on-task-complete --change cm-830 --task-id T1_1 --status passed --batch
python -m openspec.telemetry.auto on-task-start --change cm-830 --task-id T1_2 --agent API_Agent
python -m openspec.telemetry.auto on-task-complete --change cm-830 --task-id T1_2 --status passed --batch
python -m openspec.telemetry.auto on-apply-complete --change cm-830
```

## File Layout

```
openspec/
├── telemetry/
│   ├── __init__.py
│   ├── auto.py            # CLI hooks (on-new, on-artifact-complete, sync, report, …)
│   ├── client.py           # NDJSON event writer (disk-only, no HTTP)
│   ├── jira_metadata.py    # Jira/Epic metadata reader for report enrichment
│   ├── change_metrics.py   # Filesystem-based eval/feedback metrics parser
│   ├── tokens.py           # tiktoken-based token estimation
│   ├── report.py           # Metrics report generator
│   └── requirements.txt    # pyyaml, tiktoken
└── changes/
    └── <change>/
        ├── inputs/
        │   ├── jira.yaml             # Jira metadata (key, summary, epic, URLs)
        │   └── jira-spec.md          # Full ticket content
        ├── telemetry/
        │   ├── events.jsonl          # Raw NDJSON event log
        │   └── metrics-report.json   # Auto-generated metrics report
        └── .dashboard.json           # Hook state (run_id, phase tracking)
```

## Dependencies

Only two Python packages are required:

```
pip install pyyaml tiktoken
```

Or install from the requirements file:

```
pip install -r openspec/telemetry/requirements.txt
```

## Usage

All commands should be run from the **operator project root** (where `openspec/` lives).

### Register a new workflow run

```bash
python -m openspec.telemetry.auto on-new --change cm-830 --jira-key CM-830
```

### Signal artifact lifecycle

```bash
python -m openspec.telemetry.auto on-artifact-start --change cm-830 --artifact specs
python -m openspec.telemetry.auto on-artifact-complete --change cm-830 --artifact specs --status passed --score 91
```

### Signal task lifecycle

```bash
python -m openspec.telemetry.auto on-task-start --change cm-830 --task-id T1_1 --agent API_Agent
python -m openspec.telemetry.auto on-task-complete --change cm-830 --task-id T1_1 --status passed
python -m openspec.telemetry.auto on-apply-complete --change cm-830
```

### Sync filesystem state (backfill from existing artifacts)

```bash
python -m openspec.telemetry.auto sync --change cm-830
```

### Regenerate metrics report on demand

```bash
python -m openspec.telemetry.auto report --change cm-830
```

## Metrics Report Format

The generated `metrics-report.json` contains:

```json
{
  "exported_at": "2025-07-08T12:00:00+00:00",
  "operator_name": "cert-manager-operator",
  "jira_epic_link": "https://issues.redhat.com/browse/CM-800",
  "jira_epic_name": "Cert-manager Q3 features",
  "jira_task_name": "Trust manager addon controller",
  "Jira_task_link": "https://issues.redhat.com/browse/CM-830",
  "run": {
    "id": "...",
    "change_name": "CM-830 — cm-830",
    "jira_key": "CM-830",
    "branch": "feature/cm-830",
    "status": "completed",
    "started_at": "...",
    "completed_at": "...",
    "total_tokens_in": 0,
    "total_tokens_out": 0
  },
  "phases": [
    {
      "phase_number": 1,
      "phase_name": "spec_understanding",
      "status": "passed",
      "tokens_in": 1234,
      "tokens_out": 567,
      "quality_score": 92,
      "iteration_count": 1,
      "duration_s": 45.2
    }
  ],
  "tasks": [
    {
      "task_id": "T1_1",
      "agent_id": "API_Agent",
      "status": "passed",
      "tokens_in": 5000,
      "tokens_out": 2000,
      "attribution": null
    },
    {
      "task_id": "T1_2",
      "agent_id": "API_Agent",
      "status": "passed",
      "tokens_in": 0,
      "tokens_out": 0,
      "attribution": "phase_aggregate"
    }
  ],
  "events": [...],
  "global_health": {
    "total_tokens_consumed": 25000,
    "estimated_cost_usd": 0.105,
    "compliance_index": 100.0,
    "gate_passing_rate": 100.0,
    "human_rejection_rate": 0.0,
    "total_refinement_iterations": 0,
    "agent_success_rate": 100.0,
    "tasks_passed": 2,
    "tasks_total": 2
  },
  "artifact_edits": {
    "artifacts": [
      {
        "artifact_id": "specs",
        "phase_name": "spec_understanding",
        "eval_refinements": 0,
        "feedback_rounds": 0,
        "total_edits": 0
      }
    ],
    "total_edits": 0
  }
}
```

### Key Metrics

| Metric | Description |
|--------|-------------|
| `compliance_index` | % of phases that passed on first attempt |
| `gate_passing_rate` | % of eval gates passed without refinement |
| `human_rejection_rate` | % of phases with user-requested revisions |
| `agent_success_rate` | % of code-generation tasks that passed |
| `estimated_cost_usd` | Approximate cost based on Claude Sonnet pricing ($3/M in, $15/M out) |
| `artifact_edits` | Eval refinements + feedback rounds per artifact |

### Operator Name Detection

The `operator_name` field is auto-detected from `git remote get-url origin`.
For example, `https://github.com/org/cert-manager-operator.git` yields `cert-manager-operator`.
