---
name: /opsx:apply
id: opsx-apply
category: Workflow
description: Implement tasks — one task per invocation, state machine driven (supports ai-helpers and direct modes)
---

Implement an OpenSpec change. State-machine driven with externalized state at `implementation/state.yaml`.

Read `config.yaml → flags.auto_approve` at the start of every invocation.

> **When `auto_approve` is `false` (default behaviour):** ONE task per invocation.
> After presenting a task for approval, YIELD and wait for the user to approve/reject.
>
> **When `auto_approve` is `true`:** Auto-approve each task after eval/verification,
> immediately proceed to the next task within the same invocation. Continue until all
> tasks in the current phase (phase-iterative) or all tasks (one-shot) are complete.
> At phase boundary, auto-trigger `/opsx-continue` to generate next-phase tasks.

**Mode**: Read `codegen_mode` from `openspec/config.yaml` → `flags.codegen_mode`:
- `ai-helpers` — OAPE command routing + code-generation eval gate
- `direct` — plain agent implementation, no OAPE commands, no code eval gate

**Per-task flow (ai-helpers, auto_approve=false):** OAPE → verify → tests → eval gate → refine → present → YIELD → wait for next invocation.
**Per-task flow (direct, auto_approve=false):** implement → verify → present → YIELD → wait for next invocation.
**Per-task flow (auto_approve=true, either mode):** execute → verify → tests → eval gate → refine → present (log only) → auto-approve → next task (no YIELD).

**Reference (ai-helpers only):** schema `oape_routing`, `code_generation_eval_gate`, `{schema_root}/stage-gate/CODE_GENERATION_EVAL_PROMPT.md`

**Reference (both modes — independent gate):** schema `solve_pipeline_kpi_eval_gate`, `{schema_root}/stage-gate/SOLVE_PIPELINE_KPI_EVAL_PROMPT.md` (4 hard gates + 6 LLM judges — `solution_correctness`/`code_quality` from ai-helpers, plus 4 repo-specific judges `cg01_reuse_over_reinvent`/`cg04_scope_boundaries`/`cg05_known_good_pattern`/`cg06_build_verify_order` from `{schema_root}/stage-gate/code-gen-eval-repo-specific.md` — see that doc for the full rubric). Runs regardless of `codegen_mode`, unless `config.yaml → flags.solve_pipeline_kpi_eval` is `false`. Scored **once per plan phase, never per task**. Never touches `evals/code-generation_eval.yaml` — writes its own `eval-results/solve-kpi-phase-<N>.yaml` and, at stage end, `implementation/code-gen-implement-report.md`. A mandatory backfill check runs at the start of EVERY invocation (Step 1a) to catch and repair any phase whose gate was skipped in a prior session.

**Input**: Optionally specify a change name (e.g., `/opsx:apply cm-830`). If omitted, infer from context or prompt.

## Architecture: State Machine

```
auto_approve=false (default):
  phase-iterative:
    ai-helpers:  IDLE → EXECUTING_TASK → RUNNING_TESTS → EVAL_GATE → AWAITING_APPROVAL → IDLE → ... → PHASE_COMPLETE → IDLE/COMPLETE
    direct:      IDLE → EXECUTING_TASK → RUNNING_TESTS → AWAITING_APPROVAL → IDLE → ... → PHASE_COMPLETE → IDLE/COMPLETE
  one-shot:
    ai-helpers:  IDLE → EXECUTING_TASK → RUNNING_TESTS → EVAL_GATE → AWAITING_APPROVAL → IDLE → ... → COMPLETE
    direct:      IDLE → EXECUTING_TASK → RUNNING_TESTS → AWAITING_APPROVAL → IDLE → ... → COMPLETE

auto_approve=true:
  phase-iterative:
    any mode:    IDLE → EXECUTING_TASK → RUNNING_TESTS → [EVAL_GATE] → IDLE → EXECUTING_TASK → ... → PHASE_COMPLETE → auto-trigger /opsx-continue → ...
  one-shot:
    any mode:    IDLE → EXECUTING_TASK → RUNNING_TESTS → [EVAL_GATE] → IDLE → EXECUTING_TASK → ... → COMPLETE
```

**When `auto_approve` is `false`:** The orchestrator reads state, executes ONE task, writes state, and YIELDS.
It NEVER advances to the next task within the same response.

**When `auto_approve` is `true`:** The orchestrator executes ALL pending tasks in a loop within a single response.
AWAITING_APPROVAL state is skipped — tasks are auto-approved after eval/verification.

## State File

Location: `openspec/changes/<name>/implementation/state.yaml`
Template: `{schema_root}/templates/implementation-state-template.yaml`

Initialize from template on first invocation if missing.

## HARD RULES — NON-NEGOTIABLE

1. **Read `state.yaml` FIRST** — before any other action, every single invocation
2. **Read `codegen_mode`** — from `openspec/config.yaml` → `flags.codegen_mode` (default: `direct`)
3. **Read `auto_approve`** — from `openspec/config.yaml` → `flags.auto_approve` (default: `true`)
4. **When `auto_approve` is `false`: ONE task per invocation** — you MUST NOT execute more than one task in a single response. When you finish presenting a task for approval, your response is DONE. Period.
5. **When `auto_approve` is `true`: ALL tasks in a loop** — auto-approve each task after eval/verification, write task report, and immediately proceed to the next task. Do NOT YIELD between tasks. Use `--batch` telemetry flags.
6. **YIELD = END YOUR RESPONSE** (only when `auto_approve` is `false`) — after the approval question, you MUST stop generating text. YOUR RESPONSE ENDS. When `auto_approve` is `true`, there is no YIELD — you loop through all tasks.
7. **On user "approve"** (only when `auto_approve` is `false`) — write task report, mark complete, update state to IDLE, then STOP. Tell the user to run `/opsx-apply` again. Do NOT start the next task.
8. **Context windowing** — only load §4 payload for `current_task_id`, not all tasks
9. **Write state after every transition** — state must survive agent crashes
10. **No background sub-agents** — Do NOT launch background sub-agents, background shells, or Task-tool agents with `run_in_background=true` during `/opsx-apply`. Telemetry hooks execute in the main agent session only; background work cannot be metered and produces missing or incorrect metrics.
11. **Edit safety for existing source files** — never append to source files using `>>` / `tee -a`; use in-place edits only.
12. **No unsafe fallback rewrites** — if an existing file edit cannot be applied cleanly, STOP and request user guidance rather than appending/replacing with full-file dumps.
13. **Solve-Pipeline KPI backfill check is not optional** — unless `flags.solve_pipeline_kpi_eval` is `false`, Step 1a MUST run before Step 2 on EVERY invocation, in EVERY state (including `EXECUTING_TASK` resume and `AWAITING_APPROVAL`). It exists precisely because inline per-phase triggers have previously been skipped under time/token pressure — do not treat it as skippable "housekeeping." Never advance `current_plan_phase` or set state `COMPLETE` while any fully-completed phase is missing from `solve_kpi_gate_completed_phases`.

## YIELD BOUNDARY — CRITICAL (only when `auto_approve` is `false`)

When `auto_approve` is `false` and you reach the approval question, you have TWO possible next actions:
- If user has NOT yet responded → END YOUR RESPONSE after the question
- If user says "approve" → write report, mark done, say "Run `/opsx-apply` for next task", then END YOUR RESPONSE
- If user says "reject" → re-run THIS task only (not the next one)

**WHAT YIELD MEANS:** You literally stop generating output. No "let me also...", no "now moving to...", no "next up...". The response terminates. The user must send a NEW message or re-invoke `/opsx-apply` to trigger the next task.

**WHY:** Without YIELD, you will batch tasks together. This destroys the per-task approval flow. The user MUST be able to review each task's code in isolation before the next one starts.

## AUTO-APPROVE LOOP (only when `auto_approve` is `true`)

When `auto_approve` is `true`, do NOT YIELD or prompt the user. Instead:

1. After presenting the task summary (Step 5), treat it as automatically approved.
2. Write task report, mark task `- [x]`, update state to `IDLE`.
3. Fire `on-task-complete --batch` telemetry.
4. Check if more pending tasks remain for the current phase (phase-iterative) or overall (one-shot).
5. If tasks remain → pick next pending task, loop back to **Step 4** (execute next task).
6. If all tasks done → proceed to **Step 6** (post-loop / phase boundary).

At **phase boundary** (phase-iterative, phases remain):
- Auto-commit and push if applicable.
- Instead of telling the user "Run `/opsx-continue`", **automatically invoke `/opsx-continue`**
  to generate next-phase tasks. Since `auto_approve` is `true`, `/opsx-continue` will also
  auto-loop through artifact approval and return with `tasks.md` approved.
- Then loop back and execute the new phase's tasks.
- Continue until ALL phases are complete.

## Steps

### 1. Read state and config

Read `openspec/changes/<name>/implementation/state.yaml`.
If file doesn't exist, initialize from template.

Read `openspec/config.yaml` → `flags.codegen_mode`. If not set, default to `direct`.
Read `openspec/config.yaml` → `flags.task_execution_mode`. If not set, default to `phase-iterative`.

### 1a. Solve-Pipeline KPI gate — MANDATORY BACKFILL CHECK (every invocation, before Step 2)

**This step is not optional and does not depend on the current `state.yaml` state.**
It exists specifically because the per-phase gate trigger below (Step 6 / one-shot
phase transitions) can be skipped by an agent that prioritizes code+tests during a
long batch run or a session handoff/continuation. Running this check first, on
every single invocation, makes a missed phase self-repairing instead of
permanently lost. Skip this entire step ONLY if `config.yaml → flags.solve_pipeline_kpi_eval` is `false`.

1. Read `tasks.md` §3. Compute `fully_completed_phases` = every phase number `N`
   such that **all** task IDs with prefix `T<N>_` are marked `- [x]`.
2. Read `state.yaml → solve_kpi_gate_completed_phases` (treat as `[]` if absent).
3. Compute `missing = fully_completed_phases − solve_kpi_gate_completed_phases`, sorted ascending.
4. If `missing` is empty → proceed to Step 2 normally.
5. If `missing` is non-empty → **before doing anything else** (before resuming a
   crashed task, before handling an approval, before picking a new task), read and
   follow `{schema_root}/stage-gate/SOLVE_PIPELINE_KPI_EVAL_PROMPT.md` Step B/C for
   each phase `N` in `missing`, in order:
   - Determine `phase_shas.<N>.start_sha` using the fallback order in the prompt
     (recorded value → previous phase's `end_sha` → `stage_start_sha` scoped to
     that phase's target files).
   - Run the 4 hard gates + 6 LLM judges against that phase's whole diff.
   - Write `eval-results/solve-kpi-phase-<N>.yaml` (mark `backfilled: true` and
     record which SHA fallback was used, if any).
   - Record `phase_shas.<N>.end_sha` and append `N` to
     `state.yaml → solve_kpi_gate_completed_phases`. Write state.yaml.
6. Only once `missing` is fully cleared, proceed to Step 2.

**HARD RULE**: never advance `current_plan_phase`, never set state `COMPLETE`,
and never write `code-gen-implement-report.md` while a fully-completed phase is
absent from `solve_kpi_gate_completed_phases`.

### 2. Handle current state

| State | Action |
|-------|--------|
| `IDLE` | Pick next pending task → go to step 3 |
| `AWAITING_APPROVAL` | Read user response (approve/reject) → handle |
| `PHASE_COMPLETE` | (phase-iterative only) Offer optional PR → advance to next phase or COMPLETE |
| `COMPLETE` | Announce done, suggest `/opsx-archive` → STOP |
| `EXECUTING_TASK` | Resume from crash — re-run current task |

**On approve** (from AWAITING_APPROVAL):
- Write `implementation/task-reports/<task-id>.md`
- Mark task `- [x]` in tasks.md
- Move `current_task_result` to `completed[]`. **Must preserve `verify_status`
  and `test_status`** (not just `test_result`) — the per-phase Solve-Pipeline
  KPI gate aggregates `make_verify_passes`/`make_test_passes` across a phase
  by reading these two fields from every task's `completed[]` entry.
- Clear `current_task_result` and `rejections`
- **Telemetry — signal task complete** (silent, non-blocking; rolls up phase-5 tokens incrementally):
  ```bash
  python -m openspec.telemetry.auto on-task-complete --change "<name>" --task-id "<TASK_ID>" --status passed --metadata '{"build_status":"<passed|failed>","test_status":"<passed|failed|skipped>","verify_status":"<passed|failed|skipped>","eval_score":<N>}'
  ```
  Populate `build_status`, `test_status`, `verify_status` from the task's verification/test
  results in `current_task_result`. Use `"skipped"` when a check was not applicable (e.g.
  Tier 3/4 tasks have no unit tests → `test_status: "skipped"`).
  Add `--phase <N>` only when task_execution_mode = "phase-iterative".
- Set state: `IDLE`
- Check if all tasks done (one-shot) or all current-phase tasks done (phase-iterative)
- **One-shot mode only — phase transition check** (unless
  `config.yaml → flags.solve_pipeline_kpi_eval` is `false`): let `N` be the
  phase number of the task just approved. If EITHER (a) no pending task
  remains with prefix `T<N>_` (i.e., phase `N` is now fully complete), OR (b)
  the next pending task in tasks.md §2 order has a different phase prefix
  than `N` — then phase `N` is complete. Read and follow
  `{schema_root}/stage-gate/SOLVE_PIPELINE_KPI_EVAL_PROMPT.md` Step C now,
  before picking the next task: run the 4 hard gates + 6 LLM judges against
  phase `N`'s whole diff (`phase_shas.N.start_sha` → HEAD), write
  `eval-results/solve-kpi-phase-<N>.yaml`, append `N` to
  `solve_kpi_gate_completed_phases`, write state.yaml. This is silent/internal
  in one-shot mode (no user-facing yield) — it does not change one-shot's
  task-by-task approval flow, it only ensures the phase-level gate actually
  runs at every phase boundary instead of only at the very end.
- **If `auto_approve` is `false`:**
  Output EXACTLY: "Task {id} approved. Report written. State: IDLE.\n\nRun `/opsx-apply` to execute the next task."
  **>>> STOP. END RESPONSE. DO NOT CONTINUE. <<<**
- **If `auto_approve` is `true`:**
  Output: "Task {id} auto-approved. Report written."
  Then immediately pick next pending task and loop back to step 4 (no YIELD).

**On reject** (from AWAITING_APPROVAL):
- Append feedback to `rejections[]`
- Set state: `EXECUTING_TASK`
- **ai-helpers mode**: Add REVISION FEEDBACK to design-bundle
- **direct mode**: Incorporate feedback into implementation approach
- Continue to step 3 (re-execute current task)

### 3. Select change and verify (first invocation only)

On first run (no state.yaml):
1. Select change (`openspec list --json` if name not given)
2. `openspec status --change "<name>" --json`
3. Verify prerequisites:
   - **ai-helpers mode**: OAPE commands in `.cursor/commands/`, artifacts approved, gh/go/git/make available
   - **direct mode**: artifacts approved, go/git/make available
4. Fork setup: read `inputs/jira.yaml`, clone fork, create feature branch
5. Create `implementation/` and `task-reports/` dirs
6. Parse tasks.md §2 order, set `total_tasks`
6b. **Solve-Pipeline KPI gate — BEFORE (stage-level, once)**: unless `config.yaml → flags.solve_pipeline_kpi_eval` is `false`, and only if `state.yaml → stage_start_sha` is not already set, run `git rev-parse HEAD` in the fork/working copy and persist as `stage_start_sha` in `state.yaml`. This is the baseline used later for the stage-wide coverage figure in `code-gen-implement-report.md`. Do not overwrite on later invocations.
7. Initialize `state.yaml` with state: IDLE
8. **Retry PENDING phase Jira ticket** (phase-iterative only):
   - Read `inputs/jira.yaml` → `plan_phases[]` for current phase.
   - If entry exists with `jira_key: PENDING`: retry `create_ticket` once using
     schema `phases_jira_sync.create_ticket_spec`. Update `jira_key` / `jira_url`
     on success; leave PENDING on failure (do not block implementation).
9. **Telemetry — signal apply start / phase 5** (silent, non-blocking):
   ```bash
   python -m openspec.telemetry.auto on-apply-start --change "<name>"
   ```
   Add `--phase <N>` only when task_execution_mode = "phase-iterative" (where `<N>` is `current_plan_phase` from state.yaml).
10. Pick first pending task → continue to step 4
   - **phase-iterative**: pick first pending task for the current phase only
   - **one-shot**: pick first pending task across all phases in §2 order

### 4. Execute ONE task

**E2e guard:** Before executing, classify the current task using schema `e2e_exclusion.task_criteria`.
If it matches (Testing_Agent, e2e in title/objective, e2e target files, would use e2e-generate):
mark `- [x]` in tasks.md with note `SKIPPED_E2E`, write minimal task-report with
`status: skipped_e2e`, signal `on-task-complete --status skipped`, and proceed to the
next pending task — do NOT invoke `e2e-generate` or any OAPE command.

**Context windowing**: Read ONLY the §4 payload for `current_task_id` from tasks.md.
Do NOT read payloads for other tasks.

**Solve-Pipeline KPI gate — phase start SHA (once per phase, NOT per task)**: unless
`config.yaml → flags.solve_pipeline_kpi_eval` is `false`, derive this task's phase
number `N` from its task ID (`T<N>_<m>`). If `state.yaml → phase_shas.<N>.start_sha`
does not exist yet, run `git rev-parse HEAD` in the fork/working copy and persist it
as `phase_shas.<N>.start_sha`. This only happens once, at the first task of each
phase — do NOT capture a new SHA for every task.

Set state: `EXECUTING_TASK`. Write state.yaml.

**Telemetry — signal task start** (silent, non-blocking):
```bash
python -m openspec.telemetry.auto on-task-start --change "<name>" --task-id "<TASK_ID>" --agent "<AGENT_ID>" --title "<task_title>"
```
Add `--phase <N>` only when task_execution_mode = "phase-iterative".
```

---

<!-- ╔══════════════════════════════════════════════════════════════╗ -->
<!-- ║  MODE BRANCH: codegen_mode determines steps 4a–4e          ║ -->
<!-- ╚══════════════════════════════════════════════════════════════╝ -->

#### IF codegen_mode = ai-helpers

##### 4a. Compose design bundle

Write `implementation/design-bundle.md`:
- constitution, specs, plan, repo-assessment excerpts
- §4 payload **ONLY for current Task ID**
- REVISION FEEDBACK if retrying after rejection

##### 4b. Run OAPE command (exactly one)

1. **IF e2e task** → `/oape:e2e-generate <fork-default-branch>`
2. **ELIF** `API_Agent` verification-only → `/oape:api-generate-tests <api-path>`
3. **ELIF** `API_Agent` → `/oape:api-generate --design-doc <bundle>` + `make update && make verify`
4. **ELIF** `OperatorController_Agent` → `/oape:api-implement --design-doc <bundle>`
5. **ELIF** manual agent → implement task payload directly

##### 4c. Verify and test

Set state: `RUNNING_TESTS`. Write state.yaml.

Run Makefile targets from this task's Acceptance criteria. Test tier classification:
- **Tier 1** (co-generate): Controller, API with webhooks/validation, manual Go with logic
  → co-generate `_test.go` → `go test ./<package>/... -v -count=1`
- **Tier 2** (run existing): Packages with existing `_test.go` coverage
  → `go test ./<package>/... -v -count=1`
- **Tier 3** (build verify): Pure struct types, codegen output, e2e
  → `go build` + `go vet` (+ `make verify` for codegen)
- **Tier 4** (non-Go): YAML, scripts, manifests
  → `make verify` or `bash -n`

##### 4d. Code eval gate

Set state: `EVAL_GATE`. Write state.yaml.

Read and follow **`{schema_root}/stage-gate/CODE_GENERATION_EVAL_PROMPT.md`** Steps 1–7 exactly.
This is the single source of truth for per-task code eval scoring, verification, test execution,
refinement, and result recording. Key paths used by the prompt:
- Eval cases: `harness-evals/evals/code-generation_eval.yaml`
- Eval results output: `openspec/changes/<name>/eval-results/code-generation-<task-id>.yaml`
- Task report template: `{schema_root}/templates/implementation-task-report-template.md`
- Max refinement passes: 2

##### 4e. Write result

Write `current_task_result` to state.yaml:
```yaml
current_task_result:
  task_id: <id>
  oape_command: <command>
  files_changed: [...]
  verification_pass: true/false
  build_status: passed/failed        # go build + go vet result
  test_command: "..."
  test_result: PASS/FAIL
  test_status: passed/failed/skipped # go test result (skipped for Tier 3/4)
  verify_status: passed/failed/skipped # make verify result (skipped if not applicable)
  test_output_summary: "..."
  eval_score: <N>
  eval_cases_pass: <N>
  eval_cases_total: <N>
  refinement_rounds: <N>
```

---

#### ELSE (codegen_mode = direct)

##### 4a. Read context files

Read the following for architecture patterns, guardrails, and task-specific guidance:
- agents.md (repo root) — architecture patterns, test exemplars, coding conventions
- constitution.md (harness-evals/constitution.md) — guardrails and verification requirements
- specs.md — requirements traced by this task
- plan.md — phase goals and verification hooks
- repo-assessment.md — target files, reusable assets
- tasks.md §4 payload for **current Task ID only**
- REVISION FEEDBACK if retrying after rejection

##### 4b. Implement code directly

Apply code changes in the working copy following:
- agents.md patterns and conventions
- constitution.md guardrails
- Task payload instructions (objective, target files, implementation notes)
- Acceptance criteria from the task

##### 4c. Co-generate unit tests (mandatory for Tier 1 tasks)

For tasks producing Go source files with testable logic:
- Scan files_changed for new/modified `.go` files (excluding `_test.go`)
- For Tier 1 tasks: verify corresponding `_test.go` exists for each production `.go` file
- If any `_test.go` missing: generate it before proceeding (follow agents.md test exemplar)
- Run `go test ./<package>/... -v -count=1`
- If tests fail: fix code/tests and re-run (up to 2 attempts)
- Record test file paths + pass/fail in `current_task_result`
- Tier 2: run existing `go test` on modified packages
- Tier 3: `go build` + `go vet`
- Tier 4 (non-Go): `make verify` or `bash -n`

##### 4d. Verify and test

Set state: `RUNNING_TESTS`. Write state.yaml.

Run Makefile targets from this task's Acceptance criteria. Apply same tiered
classification as ai-helpers mode step 4c.

##### 4e. Write result

Write `current_task_result` to state.yaml:
```yaml
current_task_result:
  task_id: <id>
  files_changed: [...]
  verification_pass: true/false
  build_status: passed/failed        # go build + go vet result
  test_command: "..."
  test_result: PASS/FAIL
  test_status: passed/failed/skipped # go test result (skipped for Tier 3/4)
  verify_status: passed/failed/skipped # make verify result (skipped if not applicable)
  test_output_summary: "..."
```

##### 4f. Write eval results (direct mode equivalent)

Write a lightweight eval result YAML so telemetry can track refinement rounds
and verification/test outcomes consistently across both modes:

```
openspec/changes/<name>/eval-results/code-generation-<task-id>.yaml
```

```yaml
task_id: <id>
stage: code-generation
mode: direct
scored_at: <ISO8601>
refinement_rounds: <N>
verification:
  commands:
    - cmd: "<command executed>"
      exit_code: <N>
      pass: true/false
  overall_pass: true/false
test_execution:
  strategy: <co_generated_tests|existing_tests|build_only|make_verify>
  commands:
    - cmd: "<test command>"
      exit_code: <N>
      pass: true/false
      tests_run: <N>
      tests_passed: <N>
      tests_failed: <N>
  overall_pass: true/false
  test_files_generated: [...]
```

Track `refinement_rounds`:
- Start at 0
- Each time code/tests are fixed and re-run in steps 4c/4d, increment by 1
- Max value: 2 (matching the 2-attempt retry limit)

---

<!-- ╔══════════════════════════════════════════════════════════════╗ -->
<!-- ║  END MODE BRANCH — shared flow resumes                     ║ -->
<!-- ╚══════════════════════════════════════════════════════════════╝ -->

**Note — no per-task Solve-Pipeline KPI scoring here.** That gate is scored
ONCE PER PHASE, not per task (see schema `solve_pipeline_kpi_eval_gate`). The
per-phase gate runs at phase completion — Step 6 (phase-iterative) or the
phase-transition check in Step 2's "On approve" (one-shot) — and at the
mandatory backfill check (Step 1a) on every invocation. Do not add per-task
solve-kpi scoring here even if it seems convenient — that reintroduces the
cost/noise problem this cadence was redesigned to avoid.

### 5. Present and YIELD

Before setting `AWAITING_APPROVAL`, run a source integrity check for changed Go files:
- Each changed `.go` file must contain exactly one `package` clause.
- If any file has duplicate package declarations, treat as a failed verification/refinement outcome.
- Restore the affected file(s) from `HEAD`, re-apply intended task edits, re-run verification/tests, and only then proceed to presentation.

Set state: `AWAITING_APPROVAL`. Write state.yaml.

#### ai-helpers mode — presentation format

```
## Task: <TASK_ID> — <title>
Phase: <phase> | Task <index>/<total>

### OAPE Commands Executed
| Command | Args | Outcome |

### Files Changed
- path/to/file — brief description

### Test Results
| Test | Command | Result |

### Code Eval Scorecard
Score: N% (pass/total cases) | Refinement rounds: N

### Deviations (if any)
```

ASK (skip if `auto_approve: true`): **"Code eval score: {N}% ({pass}/{total} cases pass). Approve the code changes for task {task_id} ({task_title})? (Approve / Reject with feedback)"**

Note: the Solve-Pipeline KPI Gate is scored once per phase, not per task — it
is not part of this per-task presentation. See the Phase {N} summary (Step 6)
for its scorecard.

#### direct mode — presentation format

```
## Task: <TASK_ID> — <title>
Phase: <phase> | Task <index>/<total>

### Files Changed
- path/to/file — brief description

### Test Results
| Test | Command | Result |

### Deviations (if any)
```

ASK (skip if `auto_approve: true`): **"Approve the code changes for task {task_id} ({task_title})? (Approve / Reject with feedback)"**

Note: the Solve-Pipeline KPI Gate is scored once per phase, not per task — it
is not part of this per-task presentation. See the Phase {N} summary (Step 6)
for its scorecard.

---

**IF `auto_approve` is `true`:** Do NOT YIELD. Treat as approved → write task report, mark complete, proceed to next task (see AUTO-APPROVE LOOP above).

**IF `auto_approve` is `false`:**

**╔══════════════════════════════════════════════════════════════╗**
**║  >>> YIELD — STOP GENERATING. END YOUR RESPONSE NOW. <<<   ║**
**║  Do NOT read the next task. Do NOT compose another bundle.  ║**
**║  Do NOT continue with any other action.                     ║**
**║  The user must send a new message to proceed.               ║**
**╚══════════════════════════════════════════════════════════════╝**

### 6. Post-loop / Phase boundary

Read `config.yaml → flags.task_execution_mode`.

#### IF task_execution_mode = "one-shot"

When ALL tasks in tasks.md §3 are marked `- [x]`:

1. **Telemetry — signal apply complete** (silent, non-blocking):
   ```bash
   python -m openspec.telemetry.auto on-apply-complete --change "<name>"
   ```
1a. **Solve-Pipeline KPI gate — backfill check** (unless
    `config.yaml → flags.solve_pipeline_kpi_eval` is `false`): re-run Step 1a's
    check right now. Every phase's per-phase gate should already have run via
    the phase-transition check in Step 2's "On approve" — but this is the
    final safety net before writing the report. If any phase is still
    missing from `solve_kpi_gate_completed_phases`, backfill it now. Do not
    proceed to 1b while a gap remains.
1b. **Solve-Pipeline KPI gate — AFTER (stage end, once)**: read and follow
    `{schema_root}/stage-gate/SOLVE_PIPELINE_KPI_EVAL_PROMPT.md` Step D
    **before** the push in step 4 below:
    - Run `commit_message_format` against the real commit message about to be
      pushed (the "stage and commit any remaining changes" step in
      `fork_repo.draft_pr`); rewrite/amend the message if it fails the
      conventional-commit pattern — do not create a second commit.
    - Compute stage-wide coverage (`stage_start_sha` → current `HEAD`).
    - Aggregate every `eval-results/solve-kpi-phase-*.yaml` (ONE PER PHASE,
      not per task) plus `openspec/telemetry/tokens.py` estimates, `tasks.md`,
      and `inputs/jira.yaml` into `implementation/code-gen-implement-report.md`
      using `templates/code-gen-implement-report-template.md` (5 tables —
      Hard Gates, LLM Quality Judges, Execution/Cost KPIs, Per-Task Context,
      Output Artifacts). Fill all tables with real data — no placeholders.
2. Write `implementation-report.md` aggregating all `task-reports/*.md`
3. Write `deviation-observed.md` if any deviations logged
4. **Default mode:** Commit, push feature branch, open draft PR.
   **Working-folder mode:** skip push/PR; record local changes in implementation-report.md.
5. Present final summary: tasks, files, tests, deviations; draft PR URL when applicable. Include the `code-gen-implement-report.md` path in the summary.
6. Set state: `COMPLETE`. Write state.yaml.

#### IF task_execution_mode = "phase-iterative"

When all **current phase** tasks are marked complete:

1. Set state: `PHASE_COMPLETE`. Write state.yaml.
1a. **Solve-Pipeline KPI gate — PER-PHASE** (unless
    `config.yaml → flags.solve_pipeline_kpi_eval` is `false`): if phase `N`
    (the phase just completed) is not already in
    `state.yaml → solve_kpi_gate_completed_phases`, read and follow
    `{schema_root}/stage-gate/SOLVE_PIPELINE_KPI_EVAL_PROMPT.md` Step C now:
    run the 4 hard gates + 6 LLM judges against phase `N`'s whole diff
    (`phase_shas.N.start_sha` → `HEAD`), write
    `eval-results/solve-kpi-phase-<N>.yaml`, record `phase_shas.N.end_sha`,
    append `N` to `solve_kpi_gate_completed_phases`. Write state.yaml. Do
    this BEFORE step 2 so the phase summary can include the scorecard.
2. Present phase summary (tasks completed, files changed, test results for
   this phase), including the Solve-Pipeline KPI Gate scorecard: hard gates
   N/4 pass, `solution_correctness` N/5, `code_quality` N/5,
   `cg01_reuse_over_reinvent` N/5, `cg04_scope_boundaries` N/5,
   `cg05_known_good_pattern` N/5 or n/a, `cg06_build_verify_order` N/5 or n/a.
3. **Telemetry — signal phase complete** (silent, non-blocking):
   ```bash
   python -m openspec.telemetry.auto on-phase-complete --change "<name>" --phase <N> --pr-raised <true|false>
   ```
4. **If `auto_approve` is `false`:**
   ASK: **"All Phase {N} tasks complete. Would you like to raise a draft PR to `main` for Phase {N}? This will trigger CI jobs on the PR. (Yes / No, continue to Phase {N+1})"**
   **If `auto_approve` is `true`:**
   Skip prompt. Auto-commit and push a draft PR for this phase (default mode). Skip push/PR in working-folder mode.
5. If yes (or auto-approved): commit, push, open draft PR to `main` scoped to this phase. Record URL in `state.yaml` → `phase_pr_urls`. **Working-folder mode:** skip push/PR.
   Output: **"Draft PR raised: <PR_URL>. CI jobs will run automatically. Once CI passes, run `/opsx-e2e <change-name> --phase {N}` to generate E2E tests. After E2E code is generated it will be pushed to the same PR branch, triggering CI again to validate the tests."**
6. Check if `current_plan_phase >= total_plan_phases`:
   - **All phases done:**
     - **Telemetry — signal apply complete:**
       ```bash
       python -m openspec.telemetry.auto on-apply-complete --change "<name>"
       ```
     - **Solve-Pipeline KPI gate — backfill check** (unless
       `config.yaml → flags.solve_pipeline_kpi_eval` is `false`): re-run Step
       1a's check. Every phase should already be in
       `solve_kpi_gate_completed_phases` from step 1a above, phase by phase —
       but this is the final safety net. Backfill any gap now; do NOT proceed
       while one remains.
     - **Solve-Pipeline KPI gate — AFTER (stage end, once, all phases)**: read
       and follow `{schema_root}/stage-gate/SOLVE_PIPELINE_KPI_EVAL_PROMPT.md`
       Step D **before** this final push: run `commit_message_format` on the
       real pre-push commit message; compute stage-wide coverage from
       `stage_start_sha` (captured at the very first task of Phase 1) to
       current `HEAD` across all phases; aggregate every
       `eval-results/solve-kpi-phase-*.yaml` (ONE PER PHASE) plus telemetry
       estimates into `implementation/code-gen-implement-report.md` (5 tables,
       real data, no placeholders). This is written **once**, here — not per
       phase.
     - Write `implementation-report.md` aggregating all `task-reports/*.md`
     - Write `deviation-observed.md` if any deviations logged
     - Present final summary with all phase PR URLs. Include the
       `code-gen-implement-report.md` path.
     - Output: **"All implementation complete. Draft PR(s) raised — CI jobs will run. Once CI passes, run `/opsx-e2e <change-name>` to generate E2E tests. The generated E2E code will be pushed to the PR branch, triggering CI again to validate the tests."**
     - Set state: `COMPLETE`. Write state.yaml.
   - **Phases remain:**
     - Update `state.yaml`: `current_plan_phase = N+1`, state = `IDLE`
     - Skip discarded e2e phase numbers: if `N+1` is in `discarded_e2e_phases`,
       advance `current_plan_phase` until a non-e2e phase is reached (or all done).
     - **If `auto_approve` is `false`:**
       Output: "Phase {N} complete. Run `/opsx-continue` to generate Phase {N+1} tasks. Once this phase's PR CI passes, run `/opsx-e2e --phase {N}` to generate E2E tests — the generated code will be pushed to the PR, triggering CI again."
       YIELD.
     - **If `auto_approve` is `true`:**
       Output: "Phase {N} complete. Auto-triggering `/opsx-continue` for Phase {N+1}."
       Automatically invoke `/opsx-continue <change-name>` to generate next-phase tasks.
       Since `auto_approve` is `true`, `/opsx-continue` will auto-loop through artifact
       approval and return with `tasks.md` approved.
       Then loop back to **Step 4** to execute the new phase's tasks.
7. YIELD (only when `auto_approve` is `false`; when `true`, the loop continues)

**Reminder — this is exactly the step that was previously skipped for phases
after Phase 1.** Step 1a here (per-phase scoring) and Step 1a at the very top
of the command (mandatory backfill check, every invocation) are two
independent, redundant safety nets for the same requirement — do not treat
either as optional busywork; do not defer them "to do later in this
response."

## Guardrails

- **Read state.yaml FIRST** — every invocation, no exceptions
- **Read codegen_mode and auto_approve** — from config.yaml, every invocation
- **When `auto_approve` is `false`: ONE task per response** — NEVER implement two tasks in one invocation
- **When `auto_approve` is `true`: ALL tasks in a loop** — auto-approve each task and immediately proceed to the next; no YIELD between tasks
- **YIELD after approval question** (only when `auto_approve` is `false`) — HARD STOP. End your response.
- **YIELD after processing approval** (only when `auto_approve` is `false`) — write report, say "run /opsx-apply", then HARD STOP.
- **Context windowing** — only §4 for current task, never load all task payloads at once
- **Write state on every transition** — crash recovery
- **Mandatory test execution** — never skip verification or tests
- **Solve-Pipeline KPI gate is per-phase, not per-task** — never score `has_code_changes`/`make_verify_passes`/`make_test_passes`/`coverage_meets_threshold`/`solution_correctness`/`code_quality`/`cg01_reuse_over_reinvent`/`cg04_scope_boundaries`/`cg05_known_good_pattern`/`cg06_build_verify_order` per task; score them once when a phase completes (Step 6 phase-iterative, or the phase-transition check in Step 2's "On approve" for one-shot)
- **Run the backfill check every invocation** — Step 1a, before Step 2, in every state, no exceptions — this is what prevents a phase's gate from being silently and permanently skipped
- On reject (only possible when `auto_approve` is `false`): re-run current task only (full loop)
- **ai-helpers mode**: One OAPE command per task; OAPE in fork/working-folder cwd only
- **Never append source files** — prohibit `>>` / `tee -a` and similar append semantics for code edits
- **Duplicate package recovery** — if `go build`/`go test` shows duplicate `package` blocks, reset affected file(s) from git `HEAD` before reapplying task edits

## Anti-Batching Contract (only when `auto_approve` is `false`)

When `auto_approve` is `false`, you are PROHIBITED from:
- Executing task N+1 in the same response where task N was approved
- Reading §4 payload for any task other than current_task_id
- Composing a design bundle for the next task after an approval (ai-helpers mode)
- Writing "now moving to..." or "let me start the next task..."
- Any action that advances the workflow after presenting an approval question or processing an approval

If you find yourself about to start a new task in the same response — STOP. You are violating the contract.

When `auto_approve` is `true`, the anti-batching contract does NOT apply — you are expected to loop through all tasks.

## Batch / Apply-All Telemetry

When the user requests "approve all", "continue all tasks", or similar batch execution that completes multiple tasks in a single session, per-task token estimation is unreliable (file-based estimation repeats the same shared context for every task). Use `--batch` flags on telemetry hooks so tokens are attributed at the phase level only:

1. At batch start: `python -m openspec.telemetry.auto on-apply-start --change "<name>" --batch`
   Add `--phase <N>` only for phase-iterative mode.
2. Per task: still call `on-task-start` and `on-task-complete --batch` for each task (records status, agent, eval loops — but tokens_in/out = 0 with attribution = "phase_aggregate").
   Add `--phase <N>` to both only for phase-iterative mode.
3. At end: `python -m openspec.telemetry.auto on-apply-complete --change "<name>"` (phase-level tokens computed once, not summed per-task)
4. Do **not** expect per-task token breakdown in metrics for batch runs

**Auto-detect fallback:** If `--batch` is accidentally omitted, `on-apply-complete` auto-detects batch mode when 2+ tasks have near-identical token estimates and corrects to phase-level attribution.
