# OpenSpec Telemetry

Lightweight, file-based telemetry for the OpenSpec agile workflow.
No server, no database, no frontend — just NDJSON event logs and a JSON metrics report per change.

## How It Works

1. **Telemetry hooks** (`openspec/telemetry/auto.py`) write NDJSON events to disk whenever a workflow lifecycle event occurs (new run, artifact start/complete, task start/complete, etc.).
2. After each hook call, **`report.py`** auto-generates a comprehensive `metrics-report.json` containing every metric previously displayed on the dashboard.
3. All data is stored locally under `openspec/changes/<change>/telemetry/`.

## File Layout

```
openspec/
├── telemetry/
│   ├── __init__.py
│   ├── auto.py            # CLI hooks (on-new, on-artifact-complete, sync, report, …)
│   ├── client.py           # NDJSON event writer (disk-only, no HTTP)
│   ├── change_metrics.py   # Filesystem-based eval/feedback metrics parser
│   ├── tokens.py           # tiktoken-based token estimation
│   ├── report.py           # Metrics report generator
│   └── requirements.txt    # pyyaml, tiktoken
└── changes/
    └── <change>/
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
  "run": {
    "id": "...",
    "change_name": "CM-830 — cm-830",
    "jira_key": "CM-830",
    "branch": "feature/cm-830",
    "status": "completed",
    "started_at": "...",
    "completed_at": "..."
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
      "tokens_out": 2000
    }
  ],
  "events": [...],
  "global_health": {
    "total_tokens_consumed": 25000,
    "compliance_index": 100.0,
    "gate_passing_rate": 100.0,
    "human_rejection_rate": 0.0,
    "total_refinement_iterations": 0,
    "agent_success_rate": 100.0,
    "tasks_passed": 2,
    "tasks_total": 2
  },
  "token_burn": {
    "entries": [
      {"agent_id": "API_Agent", "tokens": 7000, "cost_usd": 0.0}
    ],
    "total_tokens": 7000,
    "total_cost_usd": 0.0
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
| `token_burn` | Token consumption grouped by agent |
| `artifact_edits` | Eval refinements + feedback rounds per artifact |

### Operator Name Detection

The `operator_name` field is auto-detected from `git remote get-url origin`.
For example, `https://github.com/org/cert-manager-operator.git` yields `cert-manager-operator`.
