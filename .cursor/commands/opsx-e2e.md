---
name: /opsx-e2e
id: opsx-e2e
category: QE
description: Generate E2E test plans and code from ADR, EP, PR, or any combination
argument-hint: "[change-name] [--pr <URL>] [--adr <path-or-URL>] [--ep <path-or-URL>]"
---

Generate E2E test plans and executable test code. Supports **three input modes** — the pipeline depth adapts based on what is provided. This command is a thin router — all stage logic lives in skills.

| Input | Mode | Pipeline |
|-------|------|----------|
| **PR only** | PR Mode | Full: pre-analysis → plan → consolidation → codegen → execute → push |
| **ADR or EP only** | Design Mode | pre-analysis → plan → consolidation → codegen → [optional local execute] |
| **ADR/EP + PR** | Combined Mode | Full pipeline with enriched design context |
| **Change name** | Change Mode | Resolves PR from `state.yaml`, then runs Full |

**Input**: At least one of: change name, `--pr <URL>`, `--adr <path-or-URL>`, `--ep <path-or-URL>`.

## Telemetry

Events written to `openspec/changes/<name>/telemetry/e2e-events.jsonl`.
At completion, `qe-metrics.json` generated with 7 key metrics.
Time-saved, story points, and feedback are collected by `/opsx-archive` — not here.

## Schema Package

| Role | Path |
|------|------|
| E2E workflow templates | `{schema_root}/e2e-workflow/` |
| Pre-analysis gate | `{schema_root}/e2e-workflow/pre-analysis-gate.md` |
| Test plan generation | `{schema_root}/e2e-workflow/test-plan-generation.md` |
| QE behaviour (generic) | `{schema_root}/e2e-workflow/qe-behaviour.md` |
| QE behaviour (operator) | `<operator-repo>/qe-e2e/qe-behaviour.md` |

## Steps

### 0. Operator Context Check (MANDATORY)

**Before any other step, verify these operator context files exist.**

#### 0a. `agents.md`
Look for `agents.md` (or `AGENTS.md`) at operator repo root. STOP if not found.

#### 0b. `harness-evals/`
Check `harness-evals/constitution.md` — STOP if missing. Check `harness-docs/` (warn if missing).

#### 0c. `qe-e2e/` directory
Check `qe-e2e/qe-behaviour.md` (warn if missing). Check `qe-e2e/helpers.md` (optional).

#### 0d. Preflight output
Print operator context preflight checklist.

### 1. Resolve Inputs and Mode

Parse arguments to determine mode (PR / Design / Combined / Change).
Resolve target repo, fetch PR data and/or ADR/EP content.

Emit `e2e_run_start` telemetry event.

### 2. Set Up Working Directory

Create `openspec/changes/<name>/e2e/`.

### 3. Stage 1 — Pre-Analysis

Read and follow `.cursor/skills/e2e-pre-analysis/SKILL.md`.

### 4. Stage 2 — Test Plan

Read and follow `.cursor/skills/e2e-test-plan/SKILL.md`.

### 5. Stage 2b — Consolidation

Read and follow `.cursor/skills/e2e-consolidation/SKILL.md`.

### 6. Stage 3 — Code Generation

Read and follow `.cursor/skills/e2e-codegen/SKILL.md`.

### 7. Stage 4 — Execute and Push

Read and follow `.cursor/skills/e2e-execute-push/SKILL.md`.

### 8. Final Summary

Present pipeline completion summary with all artifacts, test results, and PR status.

## Guardrails

- User approval gate after every stage
- Respect pre-analysis exclusions in all downstream stages
- Match target repo test style (framework, helpers, constants)
- No hardcoded durations — use repo constants
- DeferCleanup for every created resource
- No background sub-agents
