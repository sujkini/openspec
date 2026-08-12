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

### 2. Handle current state

| State | Action |
|-------|--------|
| `IDLE` | Pick next pending task → go to step 3 |
| `AWAITING_APPROVAL` | Read user response (approve/reject) → handle |
| `PHASE_COMPLETE` | (phase-iterative only) Phase-level approval gate → PR prompt → advance to next phase or COMPLETE |
| `PHASE_FEEDBACK` | (phase-iterative/one-shot) Resuming from crash during feedback loop — read `phase_feedback_rounds` and re-prompt |
| `COMPLETE` | Announce done, suggest `/opsx-archive` → STOP |
| `EXECUTING_TASK` | Resume from crash — re-run current task |

**On approve** (from AWAITING_APPROVAL):
- Write `implementation/task-reports/<task-id>.md`
- Mark task `- [x]` in tasks.md
- Move `current_task_result` to `completed[]`
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
- File colocation: keep all functions for one component in a single file (do not split
  reconcile/status/finalizer across files for the same controller); match the repo's existing layout

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
2. Write `implementation-report.md` aggregating all `task-reports/*.md`
3. Write `deviation-observed.md` if any deviations logged

4. **Implementation approval gate (approve / reject with feedback):**
   - Persist `implementation_feedback_rounds: 0` to `state.yaml` (initialize if not present).
   - ASK: **"All tasks complete. Implementation passes verification. Approve the full implementation? (Approve / Reject with feedback)"**
     - **On approve:** proceed to step 5 (PR prompt).
     - **On reject:** user provides feedback. Increment `implementation_feedback_rounds` in
       `state.yaml`. Analyze the feedback, identify which tasks/files need changes, apply
       the fixes, re-run verification. Then prompt again:
       **"Feedback addressed (round {N}/3). Changes applied: <brief summary>. Approve now? (Approve / Reject with feedback)"**
       Repeat until approved or max 3 rounds (on 3rd rejection, force-proceed to step 5
       with a warning: "Max feedback rounds reached. Proceeding to PR prompt.").
   - **Note:** This gate is NEVER auto-approved. `auto_approve` does not apply here.

5. **PR prompt (ALWAYS prompted — auto_approve does NOT apply):**
   ASK: **"Implementation approved. Would you like to raise a draft PR to the upstream repo? (Yes / No)"**
   - **Working-folder mode:** skip push/PR; record local changes in implementation-report.md.
6. If yes:
   ```bash
   # Read upstream_repo_url from config.yaml → credentials.github.upstream_repo_url
   # Read fork_repo_url from config.yaml → credentials.github.fork_repo_url
   # If either is empty, ASK the user and persist to inputs/jira.yaml
   # Read jira_key from inputs/jira.yaml
   # Determine fork_owner from fork URL (e.g. "sujkini" from github.com/sujkini/repo)
   gh pr create \
     --repo <upstream_org/repo> \
     --head <fork_owner>:<branch> \
     --base main \
     --title "<jira_key>: <change summary from specs.md>" \
     --body "$(cat <<'EOF'
   ## <jira_key>: <change summary>

   **Jira:** <jira_base_url>/browse/<jira_key>
   **Change:** <change-name>

   ### Description
   <high-level summary from specs.md user stories>

   ### Tasks Completed
   - <task_id>: <task_title> ✓
   - ...

   ### Files Changed
   - <file_path> — <brief description>
   - ...

   ### Verification
   - Build: PASS
   - Tests: PASS (N/N)
   - Make verify: PASS

   ---
   *Implementation by OpenSpec `/opsx-apply`*
   EOF
   )" \
     --draft
   ```
   **PR title format:** `<jira_key>: <change summary>` (e.g. `CM-900: Add certificate renewal validation`)
7. Present final summary: tasks, files, tests, deviations; upstream draft PR URL when applicable.
8. Set state: `COMPLETE`. Write state.yaml.

#### IF task_execution_mode = "phase-iterative"

When all **current phase** tasks are marked complete:

1. Set state: `PHASE_COMPLETE`. Write state.yaml.
2. Present phase summary (tasks completed, files changed, test results for this phase).
3. **Telemetry — signal phase complete** (silent, non-blocking):
   ```bash
   python -m openspec.telemetry.auto on-phase-complete --change "<name>" --phase <N> --pr-raised <true|false>
   ```

4. **Phase-level approval gate (approve / reject with feedback):**
   - Persist `phase_feedback_rounds: 0` to `state.yaml` (initialize if not present for this phase).
   - ASK: **"Phase {N} development complete. All tasks pass verification. Approve the phase implementation? (Approve / Reject with feedback)"**
     - **On approve:** proceed to step 5 (PR prompt).
     - **On reject:** user provides feedback. Increment `phase_feedback_rounds` in
       `state.yaml`. Analyze the feedback, identify which tasks/files need changes, apply
       the fixes in the working copy, re-run verification (`go build`, `go test`,
       `make verify` as applicable). Then prompt again:
       **"Feedback addressed (round {N}/3). Changes applied: <brief summary>. Approve now? (Approve / Reject with feedback)"**
       Repeat until approved or max 3 rounds (on 3rd rejection, force-proceed to step 5
       with a warning: "Max feedback rounds reached. Proceeding to PR prompt.").
   - **Note:** This gate is NEVER auto-approved. `auto_approve` does not apply here.

5. **PR prompt (ALWAYS prompted — auto_approve does NOT apply):**
   ASK: **"Phase {N} approved. Would you like to raise a draft PR to the upstream repo? This will trigger CI jobs. (Yes / No, continue to Phase {N+1})"**
6. If yes: commit, push feature branch, open draft PR targeting the **upstream** repo scoped to this phase:
   ```bash
   # Read upstream_repo_url from config.yaml → credentials.github.upstream_repo_url
   # Read fork_repo_url from config.yaml → credentials.github.fork_repo_url
   # If either is empty, ASK the user and persist to inputs/jira.yaml
   # Read phase Jira ticket from inputs/jira.yaml → plan_phases[N].jira_key and plan_phases[N].summary
   gh pr create \
     --repo <upstream_org/repo> \
     --head <fork_owner>:<branch> \
     --base main \
     --title "<phase_jira_key>: <phase_summary_from_plan_phases>" \
     --body "$(cat <<'EOF'
   ## <phase_jira_key>: <phase_summary>

   **Jira:** <jira_base_url>/browse/<phase_jira_key>
   **Parent:** <jira_base_url>/browse/<parent_jira_key>
   **Phase:** <N> of <total_plan_phases>
   **Change:** <change-name>

   ### Description
   <phase goal from plan.md>

   ### Tasks Completed
   - <task_id>: <task_title> ✓
   - ...

   ### Files Changed
   - <file_path> — <brief description>
   - ...

   ### Verification
   - Build: PASS
   - Tests: PASS (N/N)
   - Make verify: PASS

   ---
   *Implementation by OpenSpec `/opsx-apply`*
   EOF
   )" \
     --draft
   ```
   **PR title format:** `<phase_jira_key>: <phase_summary>` (e.g. `CM-901: Phase 1 — Add CRD validation webhooks`)
   - If `plan_phases[N].jira_key` is `SKIPPED` or `PENDING`, fall back to: `<parent_jira_key>: Phase <N> — <phase_goal>`
   Record URL in `state.yaml` → `phase_pr_urls`. **Working-folder mode:** skip push/PR.
   Output: **"Draft PR raised on upstream: <PR_URL>. CI jobs will run automatically. Once CI passes, run `/opsx-e2e <change-name> --phase {N}` to generate E2E tests. After E2E code is generated it will be pushed to the same PR branch, triggering CI again to validate the tests."**
7. Check if `current_plan_phase >= total_plan_phases`:
   - **All phases done:**
     - **Telemetry — signal apply complete:**
       ```bash
       python -m openspec.telemetry.auto on-apply-complete --change "<name>"
       ```
     - Write `implementation-report.md` aggregating all `task-reports/*.md`
     - Write `deviation-observed.md` if any deviations logged
     - Present final summary with all phase PR URLs (upstream)
     - Output: **"All implementation complete. Draft PR(s) raised on upstream — CI jobs will run. Once CI passes, run `/opsx-e2e <change-name>` to generate E2E tests. The generated E2E code will be pushed to the PR branch, triggering CI again to validate the tests."**
     - Set state: `COMPLETE`. Write state.yaml.
   - **Phases remain:**
     - Update `state.yaml`: `current_plan_phase = N+1`, state = `IDLE`, reset `phase_feedback_rounds: 0`
     - Skip discarded e2e phase numbers: if `N+1` is in `discarded_e2e_phases`,
       advance `current_plan_phase` until a non-e2e phase is reached (or all done).
     - **If `auto_approve` is `false`:**
       Output: "Phase {N} complete. Run `/opsx-continue` to generate Phase {N+1} tasks. Once this phase's PR CI passes, run `/opsx-e2e --phase {N}` to generate E2E tests — the generated code will be pushed to the PR, triggering CI again."
       YIELD.
     - **If `auto_approve` is `true`:**
       Output: "Phase {N} complete. Auto-triggering `/opsx-continue` for Phase {N+1}."
       Automatically invoke `/opsx-continue <change-name>` to generate next-phase tasks.
       Since `auto_approve` is `true`, `/opsx-continue` will auto-loop through artifact
       approval and return with `tasks.md` approved (but Jira sub-task prompt still fires).
       Then loop back to **Step 4** to execute the new phase's tasks.
       **Note:** When the auto_approve task loop completes the next phase, execution will
       STOP at step 4 (phase-level approval gate) since that gate always prompts the user.
8. YIELD (only when `auto_approve` is `false`; when `true`, the loop continues until hitting the phase-level gate)

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
