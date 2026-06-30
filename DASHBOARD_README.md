# Agentic AI Observability Dashboard

SDLC Observability for the OpenSpec Agile Workflow pipeline. Tracks multi-phase metrics for autonomous LLM agents: quality scores, token consumption, cost estimation, agent success rates, and real-time event streaming.

## Architecture

```
┌─────────────────────────┐     SSE stream      ┌──────────────────────────┐
│  React + TypeScript SPA │ ◄──────────────────► │  FastAPI Backend (8000)  │
│  (Vite, port 5173)      │     REST polling     │  SQLite + SSE Broker     │
└─────────────────────────┘                      └──────────┬───────────────┘
                                                            │
                                                            │ HTTP POST/PATCH
                                                            │
                                              ┌─────────────┴──────────────┐
                                              │  openspec_wrapper.py       │
                                              │  (wraps real openspec CLI) │
                                              │  + tiktoken estimation     │
                                              └─────────────┬──────────────┘
                                                            │
                                                            │ subprocess
                                                            ▼
                                              ┌────────────────────────────┐
                                              │  openspec CLI (npm)        │
                                              │  @fission-ai/openspec     │
                                              │  (UNMODIFIED)             │
                                              └────────────────────────────┘
```

**Key design principle**: The dashboard is a separate, optional layer. The openspec CLI is never modified. If the dashboard backend is down, all telemetry calls fail silently and the pipeline works exactly as before.

## Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **OpenSpec CLI**: `npm install -g @fission-ai/openspec`

## Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install frontend dependencies
cd web && npm install && cd ..

# 3. Start backend (Terminal 1)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Start frontend (Terminal 2)
cd web && npm run dev

# 5. Open http://localhost:5173 in your browser
```

## How It Works

### The Wrapper (Option B)

The SKILL.md files call `python -m src.telemetry.openspec_wrapper` instead of bare `openspec`. This wrapper:

1. Runs the real `openspec` CLI via `subprocess`
2. Prints the CLI output to stdout **unchanged** (the agent processes it normally)
3. Parses the JSON output as a side-effect
4. Detects lifecycle transitions (artifact done, phase completed, tasks finished)
5. Pushes telemetry to the dashboard backend via HTTP

If the backend is down, step 3-5 fail silently. The CLI output in step 2 is always correct.

### Token Estimation (tiktoken)

Since Cursor doesn't expose actual LLM token usage, we estimate tokens from the artifact files on disk using `tiktoken` with the `cl100k_base` encoding (GPT-4/Claude-class). This gives ~5-10% accuracy for most modern LLMs.

- **Input tokens**: Sum of dependency artifacts + input files the agent reads as context
- **Output tokens**: The generated artifact file itself
- **Cost**: Derived from `config.json > metrics.token_cost_per_million` pricing table

### Phase Detection

| Phase | Name | Detected When |
|-------|------|---------------|
| 1 | spec_understanding | `specs.md` exists and has status "done" |
| 2 | repo_assessment | `constitution.md` exists and has status "done" |
| 3 | arch_planning | `plan.md` exists and has status "done" |
| 4 | subtask_creation | `tasks.md` exists and has status "done" |
| 5 | code_generation | All task reports in `implementation/task-reports/` match task IDs from `tasks.md` Section 2 |

## Testing From Zero

### Option A: Seed from existing artifacts (fast, recommended)

```bash
# Clean old state
rm -f data/dashboard.db openspec/changes/<name>/.dashboard.json

# Start backend + frontend (two terminals)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
cd web && npm run dev

# One command seeds everything from disk
python -m src.telemetry.openspec_wrapper status --change <name> --json
```

### Option B: Full pipeline re-run (slow, tests real-time flow)

```bash
# Delete everything
rm -rf openspec/changes/<name>
rm -f data/dashboard.db

# Start backend + frontend, then run the pipeline in Cursor:
# /opsx-new <JIRA-KEY>
# /opsx-continue  (repeat until all artifacts done)
# /opsx-apply
```

### Populating per-task data (Token Burn chart + Agent Success Rate)

```bash
# For each completed task:
python -m src.telemetry.auto on-task-start --change <name> --task-id T1_1 --title "Task title" --agent Agent_Name
python -m src.telemetry.auto on-task-complete --change <name> --task-id T1_1 --status passed
```

## File Structure

### Backend (`src/`)

| Path | Purpose |
|------|---------|
| `src/main.py` | FastAPI app entry point |
| `src/api/v1/` | REST endpoints (runs, phases, tasks, events, metrics) |
| `src/core/config.py` | Configuration loader (`config.json`) |
| `src/core/sse.py` | Server-Sent Events broker |
| `src/db/` | SQLAlchemy engine, base, seed |
| `src/models/` | ORM models (PipelineRun, PhaseExecution, TaskExecution, AgentEvent) |
| `src/schemas/` | Pydantic request/response schemas |
| `src/services/metrics_service.py` | Global health + token burn computation |
| `src/services/pipeline_scanner.py` | Filesystem scanner for eval results |
| `src/services/telemetry_service.py` | Event ingestion + SSE publish |

### Telemetry (`src/telemetry/`)

| Path | Purpose |
|------|---------|
| `src/telemetry/client.py` | HTTP client SDK for the dashboard API |
| `src/telemetry/cli.py` | CLI for manual telemetry commands |
| `src/telemetry/auto.py` | Auto-telemetry lifecycle hooks |
| `src/telemetry/openspec_wrapper.py` | Drop-in wrapper for `openspec` CLI |
| `src/telemetry/tokens.py` | tiktoken-based token estimation |
| `src/telemetry/decorators.py` | Python decorators for tracking |

### Frontend (`web/`)

| Path | Purpose |
|------|---------|
| `web/src/App.tsx` | Main app, merges REST + SSE data |
| `web/src/hooks/useRun.ts` | React-query hooks for runs, phases, tasks, events |
| `web/src/hooks/useSSE.ts` | SSE stream hook for live events |
| `web/src/hooks/useMetrics.ts` | Metrics polling hooks |
| `web/src/services/api.ts` | REST API client |
| `web/src/components/` | UI components (waterfall, metrics, logs, charts) |

### Configuration

| Path | Purpose |
|------|---------|
| `config.json` | Dashboard config (DB URL, SSE, token pricing, fallbacks) |
| `requirements.txt` | Python dependencies |
| `bin/opsx` | Shell alias for the wrapper |

### Data (auto-generated, gitignored)

| Path | Purpose |
|------|---------|
| `data/dashboard.db` | SQLite database (created on first backend start) |
| `openspec/changes/<name>/.dashboard.json` | Per-change tracking state (run_id, phase_ids) |

## Configuration Reference (`config.json`)

```jsonc
{
  "server": { "port": 8000, "cors_origins": ["http://localhost:5173"] },
  "database": { "url": "sqlite+aiosqlite:///data/dashboard.db" },
  "sse": { "retry_ms": 3000, "heartbeat_interval_s": 15 },
  "telemetry": { "endpoint": "http://localhost:8000/api/v1/events" },
  "metrics": {
    "token_cost_per_million": {
      "claude-sonnet-4": { "input": 3.00, "output": 15.00 },
      "gemini-2.5-pro": { "input": 1.25, "output": 5.00 },
      "default": { "input": 2.00, "output": 8.00 }
    }
  },
  "vertex_ai": { "enabled": false }  // Optional LLM-as-judge
}
```

No LLM provider configuration is needed. Token estimation uses tiktoken (local, no API calls). Cost is derived by multiplying token counts by the pricing table above.

## Isolation Guarantees

- The dashboard never modifies the openspec CLI, schemas, or pipeline artifacts
- The wrapper outputs identical JSON to the real `openspec` CLI
- All telemetry calls are wrapped in try/except; failures are silent
- Deleting `src/`, `web/`, `data/`, `config.json` has zero impact on the pipeline
- The SKILL.md modifications are backward-compatible (wrapper runs the real CLI underneath)

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Empty dashboard | Backend not running or DB deleted | Start backend, run wrapper command |
| Phase 5 stuck on RUNNING | Not all task reports exist | Complete remaining tasks, or manually close with `python -m src.telemetry.cli end-phase --change <name> --phase 5 --status passed` |
| Tokens/Cost = 0 | Existing run created before tiktoken integration | Delete DB + `.dashboard.json`, re-run wrapper |
| Logs vanish on refresh | Old frontend without REST hydration | Rebuild: `cd web && npm run build` |
| Token Burn empty | No TaskExecution records | Run `on-task-start` / `on-task-complete` for each task |
| Action buttons don't work | Backend action endpoints not implemented | Stubs only; future work |
| Wrapper hangs | Backend process crashed | Restart: `uvicorn src.main:app --port 8000 --reload` |
