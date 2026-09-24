# Direct Codegen

Implement a single task directly (without OAPE routing). Used when `codegen_mode = direct`.

## Inputs

- `current_task_id` from state.yaml
- §4 payload from tasks.md (already loaded by `apply-execute-task`)

## Steps

### 1. Read Context Files

Read the following for architecture patterns, guardrails, and task-specific guidance:
- `agents.md` (repo root) — architecture patterns, test exemplars, coding conventions
- `harness-evals/constitution.md` — guardrails and verification requirements
- `specs.md` — requirements traced by this task
- `plan.md` — phase goals and verification hooks
- `repo-assessment.md` — target files, reusable assets
- tasks.md §4 payload for **current Task ID only**
- REVISION FEEDBACK if retrying after rejection

### 2. Implement Code

Apply code changes in the working copy following:
- agents.md patterns and conventions
- constitution.md guardrails
- Task payload instructions (objective, target files, implementation notes)
- Acceptance criteria from the task
- File colocation: keep all functions for one component in a single file; match the repo's existing layout

### 3. Co-generate Unit Tests (Tier 1 tasks)

For tasks producing Go source files with testable logic:
- Scan files_changed for new/modified `.go` files (excluding `_test.go`)
- For Tier 1 tasks: verify corresponding `_test.go` exists
- If missing: generate it (follow agents.md test exemplar)
- Run `go test ./<package>/... -v -count=1`
- If tests fail: fix code/tests and re-run (up to 2 attempts)

Test tier classification:
- **Tier 1** (co-generate): Controller, API with webhooks/validation, manual Go with logic
- **Tier 2** (run existing): Packages with existing `_test.go` coverage
- **Tier 3** (build verify): Pure struct types, codegen output → `go build` + `go vet`
- **Tier 4** (non-Go): YAML, scripts, manifests → `make verify` or `bash -n`

### 4. Verify

Set state: `RUNNING_TESTS`. Write state.yaml.

Run Makefile targets from task's Acceptance criteria. Apply tiered classification above.

### 5. Write Result

Write `current_task_result` to state.yaml:
```yaml
current_task_result:
  task_id: <id>
  files_changed: [...]
  verification_pass: true/false
  build_status: passed/failed
  test_command: "..."
  test_result: PASS/FAIL
  test_status: passed/failed/skipped
  verify_status: passed/failed/skipped
  test_output_summary: "..."
```

### 6. Write Eval Results

Write a lightweight eval result YAML:
```
openspec/changes/<name>/eval-results/code-generation-<task-id>.yaml
```

Track `refinement_rounds`: start at 0, increment each fix+rerun cycle (max 2).
