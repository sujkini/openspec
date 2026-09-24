# AI-Helpers Codegen (OAPE Routing)

Implement a single task using OAPE command routing. Used when `codegen_mode = ai-helpers`.

## Inputs

- `current_task_id` from state.yaml
- §4 payload from tasks.md (already loaded by `apply-execute-task`)

## Steps

### 1. Compose Design Bundle

Write `implementation/design-bundle.md` containing:
- constitution, specs, plan, repo-assessment excerpts
- §4 payload **ONLY for current Task ID**
- REVISION FEEDBACK if retrying after rejection

### 2. Run OAPE Command (exactly one)

Resolve the OAPE command from the task's assigned agent and task type:

| Condition | OAPE command |
|-----------|-------------|
| E2E task | SKIP (`SKIPPED_E2E` — handled by `/opsx-e2e`) |
| `API_Agent` verification-only | `/oape:api-generate-tests <api-path>` |
| `API_Agent` | `/oape:api-generate --design-doc <bundle>` + `make update && make verify` |
| `OperatorController_Agent` | `/oape:api-implement --design-doc <bundle>` |
| Manual agent | Implement task payload directly |

### 3. Verify and Test

Set state: `RUNNING_TESTS`. Write state.yaml.

Run Makefile targets from task's Acceptance criteria. Test tier classification:
- **Tier 1** (co-generate): Controller, API with webhooks/validation → co-gen `_test.go` → `go test`
- **Tier 2** (run existing): Packages with existing `_test.go` → `go test`
- **Tier 3** (build verify): Struct types, codegen → `go build` + `go vet` (+ `make verify`)
- **Tier 4** (non-Go): YAML, scripts → `make verify` or `bash -n`

### 4. Code Eval Gate

Set state: `EVAL_GATE`. Write state.yaml.

Read and follow `{schema_root}/stage-gate/CODE_GENERATION_EVAL_PROMPT.md` Steps 1-7 exactly.

Key paths:
- Eval cases: `harness-evals/evals/code-generation_eval.yaml`
- Eval results: `openspec/changes/<name>/eval-results/code-generation-<task-id>.yaml`
- Task report template: `{schema_root}/templates/implementation-task-report-template.md`
- Max refinement passes: 2

### 5. Write Result

Write `current_task_result` to state.yaml:
```yaml
current_task_result:
  task_id: <id>
  oape_command: <command>
  files_changed: [...]
  verification_pass: true/false
  build_status: passed/failed
  test_command: "..."
  test_result: PASS/FAIL
  test_status: passed/failed/skipped
  verify_status: passed/failed/skipped
  test_output_summary: "..."
  eval_score: <N>
  eval_cases_pass: <N>
  eval_cases_total: <N>
  refinement_rounds: <N>
```
