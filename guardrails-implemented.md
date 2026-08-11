# Guardrails & Enhancements — Implementation Log

Summary of all guardrails, QE metrics, constitution extraction, and code generation changes
implemented in the `openspec-agile-workflow` schema.

---

## 1. Constitution Extraction from Harness-Evals

**What changed:** Constitution generation now sources exclusively from local operator
documentation (`harness-evals/harness-docs/`) instead of fetching `AGENTS.md` from a
remote GitHub repo. Repo URL is optional (structural evidence only, not governance).

**Why:** The operator team's own documentation is the authoritative source for coding
conventions, architecture patterns, and testing rules — not a remote repo file that may
be stale or missing.

### Files changed

| File | Change |
|------|--------|
| `opsx-constitute.md` | Rewrote Steps 1-6: Step 1 reads `harness-evals/harness-docs/*.md` (required); repo URL is optional for structural evidence; output writes to `harness-evals/constitution.md` instead of `openspec/inputs/constitution.md`; removed `agents.md` copy step (expected at repo root) |
| `opsx-apply.md` step 4a | Updated context file paths: `constitution.md (harness-evals/constitution.md)`, `agents.md (repo root)` |
| `STAGE_EVAL_GATE_PROMPT.md` | Constitution lookup simplified to single path `harness-evals/constitution.md`; removed 4-location lookup chain; workflow stops if not found (prompts `/opsx-constitute`) |
| `artifact-eval-map.yaml` | All `stage_eval_file` paths updated from `evals/` to `harness-evals/evals/` (repo-assessment, plan, tasks, implementation) |
| `CODE_GENERATION_EVAL_PROMPT.md` | Eval cases path updated to `harness-evals/evals/code-generation_eval.yaml`; added graceful skip when file missing |
| `openspec/inputs/agents.md` | Removed (553 lines deleted) — agents.md now expected at operator repo root |
| `openspec/inputs/constitution.md` | Removed (132 lines deleted) — now lives at `harness-evals/constitution.md` |

---

## 2. Code Generation Guardrails

### 2a. File Colocation (single file per component)

**What changed:** Added a guardrail preventing the agent from splitting related functions
into separate files for the same controller/webhook/component. All reconcile, status,
finalizer, and helper functions for one controller must live in a single `*_controller.go`.

**Why:** AI tends to create `spireserver_reconcile.go`, `spireserver_status.go`,
`spireserver_finalizer.go` etc. for the same controller. Go convention for operators is
one file per controller.

| File | Change |
|------|--------|
| `code-generation-template.md` | Added core rule 12: "File colocation — all functions for one component belong in one file" (read by ai-helpers mode) |
| `opsx-apply.md` step 4b | Added bullet: "File colocation: keep all functions for one component in a single file; match the repo's existing layout" (read by direct mode) |
| `CODE_GENERATION_EVAL_PROMPT.md` | Added `must_colocate_component_code` assertion — eval gate fails if files were unnecessarily split |
| `opsx-e2e.md` Stage 4 step 3 | Changed "Generate test file(s)" to "Generate ONE test file per component/CR kind" |

### 2b. Direct Mode Eval Results

**What changed:** Added step 4f to direct mode in `opsx-apply.md` — writes a lightweight
eval result YAML per task so telemetry tracks refinement rounds and test outcomes
consistently across both ai-helpers and direct modes.

| File | Change |
|------|--------|
| `opsx-apply.md` step 4f | New section: writes `eval-results/code-generation-<task-id>.yaml` with `refinement_rounds`, `verification`, `test_execution` fields |

### 2c. Eval Gate Graceful Degradation

**What changed:** Both stage eval and code-gen eval prompts now handle missing eval YAML
files gracefully — skip scoring but still run verification and tests.

| File | Change |
|------|--------|
| `STAGE_EVAL_GATE_PROMPT.md` | Added: "If `harness-evals/evals/<stage>_eval.yaml` does not exist — skip eval scoring, proceed to user approval" |
| `CODE_GENERATION_EVAL_PROMPT.md` | Added: "If eval file does not exist — skip eval scoring but still execute verification and test block" |

---

## 3. QE Metrics & E2E Telemetry

**What changed:** Added a complete QE telemetry system for the `/opsx-e2e` workflow that
tracks 7 metrics across the E2E test generation and execution pipeline.

### 3a. Telemetry Commands

| File | What was added |
|------|----------------|
| `opsx-e2e.md` | Telemetry section at top defining `e2e-events.jsonl` output and 7 QE metrics; per-stage `e2e_stage_start`/`e2e_stage_end` events with `tokens_in`, `tokens_out`, `duration_s`, `refinement_rounds`; Stage 5 telemetry block with `e2e_execution`, `e2e_bug_found`, `e2e_bug_verified`, `e2e_triage` events; `qe-metrics.json` report generation |

### 3b. QE Metrics (7 metrics in `qe-metrics.json`)

| # | Metric | Source | Requires execution? |
|---|--------|--------|---------------------|
| 1 | AC → Scenario Coverage % | `specs.md` FR/US/SC IDs vs `test-plan.md` traceability | No |
| 2 | Automation Coverage % | `revised-test-plan.md` journey count vs `e2e/generated/*_test.go` file count | No |
| 3 | First-Pass Pass Rate | `e2e_execution` events (attempt=1) | Yes |
| 4 | Flake Rate | Retries with same `file_hash` that pass without code change | Yes |
| 5 | Bugs Found / Verified | `e2e_bug_found` and `e2e_bug_verified` events | Yes |
| 6 | Triage Accuracy % | `e2e_triage` events with `user_confirmed` | Yes |
| 7 | QE Cost (tokens / $ / time) | `e2e_stage_start`/`e2e_stage_end` events per stage | No |

### 3c. Telemetry Python Modules

| File | Purpose |
|------|---------|
| `openspec/telemetry/qe_events.py` | `QETelemetryClient` — writes NDJSON events to `e2e-events.jsonl` (start/end run, start/end stage, record execution, bug found/verified, triage) |
| `openspec/telemetry/qe_metrics.py` | Reads `e2e-events.jsonl` + artifacts, computes all 7 metrics, writes `qe-metrics.json` |

---

## 4. Phase-Iterative Dashboard Telemetry

**What changed:** Added `plan_phase` support across the telemetry stack so the dashboard
can show per-plan-phase sub-rows under stages 4 (Sub-Task Creation) and 5 (Code Generation).

```
4. Sub-Tasks Creation (DAG)        ✅ PASSED
   → Phase 1                       ✅ PASSED
   → Phase 2                       🔄 RUNNING
5. Code Generation / Harness       🔄 RUNNING
   → Phase 1                       ✅ PASSED
   → Phase 2                       🔄 RUNNING
```

### Files changed (9 files, 4 layers)

| Layer | File | Change |
|-------|------|--------|
| CLI args | `telemetry/auto.py` | `--phase` added to 8 subcommands; new `on-phase-complete` subcommand |
| CLI logic | `telemetry/auto.py` | `_sub_phase_key()`, `_ensure_sub_phase()`, `_emit_sub_phase_progress()` helpers; handlers create sub-phase rows when `--phase` present |
| Client | `telemetry/client.py` | `start_phase()` accepts `plan_phase: int \| None`; included in NDJSON event |
| DB model | `dashboard/src/models/phase.py` | `plan_phase: Mapped[int \| None]` nullable column |
| Event ingestion | `dashboard/src/services/file_event_poller.py` | Reads `plan_phase` from event; includes in SSE publishes |
| API schema | `dashboard/src/schemas/phase.py` | `plan_phase: int \| None` in `PhaseCreate` and `PhaseOut` |
| API endpoint | `dashboard/src/api/v1/phases.py` | `create_phase` passes `plan_phase`; `list_phases` sorts with `nullsfirst()` |
| Frontend types | `dashboard/web/src/types/index.ts` | `plan_phase: number \| null` in `PhaseExecution` |
| Frontend render | `dashboard/web/src/components/phases/PhaseWaterfall.tsx` | Separates parent/sub-phases; passes children to `PhaseRow` |
| Frontend render | `dashboard/web/src/components/phases/PhaseRow.tsx` | New `SubPhaseRow` component renders indented `→ Phase N` rows |

**One-shot mode impact:** Zero — `--phase` is never passed, `plan_phase` stays null, no sub-rows appear.

---

## 5. Additional Changes

| Area | File | Change |
|------|------|--------|
| Jira phase sync | `schema.yaml` | Replaced per-user-story Jira sync with per-phase Jira sync |
| E2E exclusion | `schema.yaml`, `opsx-apply.md` | E2E tasks are skipped during `/opsx-apply` (marked `SKIPPED_E2E`); E2E tests generated separately via `/opsx-e2e` |
| Auto-approve | `config.yaml` | `auto_approve: true` by default; scoped to artifact approval only (task approval always prompted) |
| Plan template | `plan-template.md` | Added user-story-to-task mapping section |
| Report enrichment | `telemetry/report.py` | Added `plan_phase` to `_reconstruct_phases` |
| Eval loop | `eval-loop.md` | Updated eval file paths to `harness-evals/evals/` |
