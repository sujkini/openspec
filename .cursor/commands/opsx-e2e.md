---
name: /opsx-e2e
id: opsx-e2e
category: QE
description: Generate and run E2E tests for a phase/final PR after CI passes
argument-hint: "[change-name] [--phase N | --pr <URL>]"
---

Generate E2E test plans and executable test code for a PR raised by `/opsx-apply`. Runs the
full pipeline: pre-analysis → test plan → consolidation → code generation → execute.

**Trigger:** After phase PR (phase-iterative) or final PR (one-shot) is raised and CI passes.

**Input**: Optional change name + phase number or PR URL. If omitted, infer from context.

## Schema package

| Role | Path |
|------|------|
| E2E workflow templates | `{schema_root}/e2e-workflow/` |
| Pre-analysis gate | `{schema_root}/e2e-workflow/pre-analysis-gate.md` |
| Test plan generation | `{schema_root}/e2e-workflow/test-plan-generation.md` |
| QE behaviour (project input) | `{schema_root}/e2e-workflow/qe-behaviour.md` |

## Steps

### 1. Resolve PR URL

Determine the target PR for E2E generation:

**Phase-iterative mode:**
- Read `openspec/changes/<name>/implementation/state.yaml`
- Get PR URL from `phase_pr_urls[N]` (where N = specified phase or latest completed phase)
- If no `--phase` specified, use the most recently completed phase

**One-shot mode:**
- Read `openspec/changes/<name>/implementation/implementation-report.md`
- Extract PR URL from the Draft Pull Request section

**Direct PR:**
- If user provides `--pr <URL>`, use that directly (skips change lookup)

If no PR URL found → STOP: "No PR found. Run `/opsx-apply` first to raise a PR."

### 2. Verify CI status

```bash
gh pr checks <PR-NUMBER> --repo <org/repo>
```

- If all checks pass → proceed
- If checks pending → STOP: "CI checks still running. Wait for CI to pass, then re-run `/opsx-e2e`."
- If checks failed → STOP: "CI checks failed. Fix the failures first, then re-run `/opsx-e2e`."

### 3. Set up working directory

Create E2E artifacts directory:
```
openspec/changes/<name>/e2e/
```

All E2E artifacts are written here: `e2e-analysis.md`, `test-plan.md`, `revised-test-plan.md`, generated code.

### 4. Stage 1 — Pre-Analysis

Read and follow **`{schema_root}/e2e-workflow/pre-analysis-gate.md`** in full.

**Inputs:**
- PR URL (from step 1)
- `{schema_root}/e2e-workflow/qe-behaviour.md` (if present — project-specific QE context)
- Target repo (from `inputs/jira.yaml → target_repo`)

**Process:**
1. Fetch PR metadata and diff via `gh`
2. Fetch review comments (`gh api repos/.../pulls/NNN/comments` + `/reviews`)
3. Classify change type
4. Perform impact analysis, coverage assessment, blast radius, regression risk
5. Produce proposed test cases (priority-ordered, 15–20 range)
6. Write `openspec/changes/<name>/e2e/e2e-analysis.md`

**Approval gate:**
- Present the analysis to the user
- STOP and wait for: **Approved** / **Approved with changes** / **Rejected**
- On reject → re-run with feedback
- On approve → proceed to Stage 2

### 5. Stage 2 — Test Plan Generation

Read and follow **`{schema_root}/e2e-workflow/test-plan-generation.md`** in full.

**Inputs:**
- Approved `e2e-analysis.md` (from stage 1)
- PR URL + diff
- `qe-behaviour.md` (for deployment constraints)

**Process:**
1. Read approved `e2e-analysis.md` as scoping input
2. Expand proposed test cases into full test steps (preconditions, steps, expected outcomes, cleanup)
3. Build traceability matrix
4. Run quality gates (Section 8 of template) — revise until all pass
5. Write `openspec/changes/<name>/e2e/test-plan.md`

**Approval gate:**
- Present test plan summary (test count, tier distribution, quality gate results)
- STOP and wait for user approval
- On reject → revise with feedback
- On approve → proceed to Stage 3

### 6. Stage 3 — Consolidation (Config-Driven)

Apply Section 12 of `test-plan-generation.md` (Revised Plan Consolidation).

**Inputs:**
- Approved `test-plan.md` (from stage 2)
- `openspec/config.yaml → qe.max_test_cases` (hard limit)

**Process:**
1. Read `config.yaml` for `qe.max_test_cases`
   - If not set → ASK: "How many consolidated journeys? Enter a number (e.g. 5–8):"
   - Use response as the limit
2. Apply consolidation rules (create journeys, eliminate redundancy, enforce limit)
3. Write `openspec/changes/<name>/e2e/revised-test-plan.md`

**Approval gate:**
- Present revised plan (journey count, merged tests, dropped requirements if any)
- STOP and wait for user approval
- On reject → adjust consolidation
- On approve → proceed to Stage 4

### 7. Stage 4 — Code Generation

Apply Section 13 of `test-plan-generation.md` (Journey Code Generation).

**Inputs:**
- Approved `revised-test-plan.md` (from stage 3)
- Target repo test patterns (detect framework, helpers, constants)

**Process:**
1. ASK: "Which journeys to generate code for? (all / specific numbers / none)"
2. Detect test framework from target repo (`ginkgo`, `testing`, `testify`)
3. Generate test file(s) following repo patterns
4. Write generated code to `openspec/changes/<name>/e2e/generated/`

**Approval gate:**
- Present generated code summary (file path, journey count, framework, helpers used)
- STOP and wait for user approval
- On reject → revise code
- On approve → proceed to Stage 5

### 8. Stage 5 — Push and Execute

1. Commit generated test files to the **same PR branch** (this triggers CI again on the PR):
   ```bash
   # In fork working copy — push to the existing PR branch
   cp openspec/changes/<name>/e2e/generated/*_test.go <repo-path>/test/e2e/
   git add test/e2e/
   git commit -m "Add E2E tests generated by OpenSpec /opsx-e2e"
   git push origin HEAD
   ```
   Output: **"E2E test code pushed to the PR branch. CI will re-run automatically to validate the new tests."**

2. ASK: **"Run E2E tests locally now? (yes / no) — CI is already running on the PR."**
   - **Yes** → execute the test suite locally:
     ```bash
     make test-e2e
     ```
     Report results (pass/fail per journey, failures with diagnostics).
   - **No** → skip local execution; present summary of what was generated and pushed.

3. Write E2E summary to `openspec/changes/<name>/e2e/e2e-summary.md`

### 9. Final Summary

```
## E2E Generation Complete: <change-name>

**PR:** <PR URL>
**Phase:** <N> (or "final")

### Artifacts Generated
| Stage | Artifact | Path |
|-------|----------|------|
| Pre-analysis | e2e-analysis.md | openspec/changes/<name>/e2e/ |
| Test plan | test-plan.md | openspec/changes/<name>/e2e/ |
| Revised plan | revised-test-plan.md | openspec/changes/<name>/e2e/ |
| Generated code | <file>_test.go | openspec/changes/<name>/e2e/generated/ |

### Test Results
| Journey | Status |
|---------|--------|
| Journey 1: ... | PASS/FAIL/NOT RUN |

### Next Steps
- Review test code in the PR
- Re-run with `/opsx-e2e --phase N` after fixes if tests failed
```

## Guardrails

- **User approval gate after every stage** — do not advance until approved
- **CI must be green** before running — do not generate E2E for failing PRs
- Never skip the pre-analysis gate — it prevents wasted effort
- Respect pre-analysis exclusions in all downstream stages
- Match target repo test style exactly (framework, helpers, constants)
- No hardcoded durations — use repo constants
- No inline K8s resource specs — use repo builders/helpers
- DeferCleanup for every created resource
- Generated code must compile — verify before presenting
