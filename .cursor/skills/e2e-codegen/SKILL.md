# E2E Code Generation (Stage 3)

Generate executable test code from the approved test plan.

## Inputs (TARGETED — code-level context only)

- Approved `test-plan.md` or `revised-test-plan.md` (from Stage 2/2b)
- `agents.md` — helpers/style/framework sections ONLY
- `qe-e2e/helpers.md` (if found — operator-specific test builder signatures)
- Target repo `test/e2e/` patterns (auto-discovered: framework, helpers, constants)

Do NOT re-read full architecture sections from `agents.md`. Use embedded operator context from the test plan.

## Process

Apply Section 13 of `test-plan-generation.md` (Journey Code Generation).

1. ASK: "Which journeys to generate code for? (all / specific numbers / none)"
2. Read `agents.md` for code style conventions and helper function signatures
3. Read `qe-e2e/helpers.md` if present
4. Detect test framework from target repo (`ginkgo`, `testing`, `testify`)
5. Generate ONE test file per component/CR kind — all journeys for same component in a single `<component>_e2e_test.go`
6. Write generated code to `openspec/changes/<name>/e2e/generated/`

## Approval Gate

Present generated code summary (file path, journey count, framework, helpers used).
Wait for user approval.
- On reject: revise code
- On approve: proceed to Stage 4 (execute/push)

## Telemetry

Emit `e2e_stage_start` (stage=3) before processing. On approval, emit `e2e_stage_end`.
