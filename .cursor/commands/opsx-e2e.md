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

## Telemetry

This command emits QE telemetry events throughout execution. Events are written to:
```
openspec/changes/<name>/telemetry/e2e-events.jsonl
```

At completion, a `qe-metrics.json` report is generated with 7 key metrics:
- AC → scenario coverage %
- Automation coverage %
- E2E first-pass pass rate
- Flake rate
- Bugs found / verified
- Triage accuracy %
- QE tokens / $ / wall time

Use the same token estimation approach as the development workflow (`openspec/telemetry/tokens.py`).

**Telemetry module:** `openspec/telemetry/qe_events.py` (event emission),
`openspec/telemetry/qe_metrics.py` (report generation)

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

**Telemetry:** Emit `e2e_run_start` event with `pr_url`, `phase`, and `mode`.

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

**Telemetry:** Emit `e2e_stage_start` (stage=1, stage_name="pre_analysis") before processing.
On approval, emit `e2e_stage_end` with `tokens_in` (PR diff + qe-behaviour.md token count),
`tokens_out` (e2e-analysis.md token count), `duration_s`, and `refinement_rounds` (0 if approved first time).

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

**Telemetry:** Emit `e2e_stage_start` (stage=2, stage_name="test_plan") before processing.
On approval, emit `e2e_stage_end` with `tokens_in` (e2e-analysis.md + PR diff token count),
`tokens_out` (test-plan.md token count), `duration_s`, and `refinement_rounds`.

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

**Telemetry:** Emit `e2e_stage_start` (stage=3, stage_name="consolidation") before processing.
On approval, emit `e2e_stage_end` with `tokens_in` (test-plan.md token count),
`tokens_out` (revised-test-plan.md token count), `duration_s`, and `refinement_rounds`.

### 7. Stage 4 — Code Generation

Apply Section 13 of `test-plan-generation.md` (Journey Code Generation).

**Inputs:**
- Approved `revised-test-plan.md` (from stage 3)
- Target repo test patterns (detect framework, helpers, constants)

**Process:**
1. ASK: "Which journeys to generate code for? (all / specific numbers / none)"
2. Detect test framework from target repo (`ginkgo`, `testing`, `testify`)
3. Generate ONE test file per component/CR kind — all journeys for the same component go in a single
   `<component>_e2e_test.go`. Create a separate file only for a genuinely different component.
4. Write generated code to `openspec/changes/<name>/e2e/generated/`

**Approval gate:**
- Present generated code summary (file path, journey count, framework, helpers used)
- STOP and wait for user approval
- On reject → revise code
- On approve → proceed to Stage 5

**Telemetry:** Emit `e2e_stage_start` (stage=4, stage_name="code_generation") before processing.
On approval, emit `e2e_stage_end` with `tokens_in` (revised-test-plan.md + repo patterns token count),
`tokens_out` (sum of all generated *_test.go file token counts), `duration_s`, and `refinement_rounds`.

### 8. Stage 5 — Push, Execute, Evaluate, and PR

**Telemetry:** Emit `e2e_stage_start` (stage=5, stage_name="execution") before push.

#### Step 5.1 — Push test code to PR branch

Commit generated test files to the **same PR branch** (this triggers CI again on the PR):
```bash
# In fork working copy — push to the existing PR branch
cp openspec/changes/<name>/e2e/generated/*_test.go <repo-path>/test/e2e/
git add test/e2e/
git commit -m "Add E2E tests generated by OpenSpec /opsx-e2e"
git push origin HEAD
```
Output: **"E2E test code pushed to the PR branch. CI will re-run automatically to validate the new tests."**

#### Step 5.2 — Local execution prompt

ASK: **"Run E2E tests locally? (yes / no) — CI is already running on the PR."**

- **No** → skip to Step 5.6 (PR to upstream prompt).
- **Yes** → proceed to Step 5.3.

#### Step 5.3 — Cluster readiness gate

Before running tests, validate the target cluster is reachable and the operator is healthy.

1. Read `config.yaml → credentials.cluster.kubeconfig_path`.
   - If empty, ASK: **"Provide the absolute path to your KUBECONFIG file for the target cluster:"**
   - Persist the user's response to `config.yaml → credentials.cluster.kubeconfig_path` for future runs.

2. Export the kubeconfig:
   ```bash
   export KUBECONFIG=<path>
   ```

3. Read `OPERATOR_NAMESPACE` from the repo's Makefile (grep for `OPERATOR_NAMESPACE`).
   Fall back to the `test/e2e/utils/constants.go` `OperatorNamespace` constant if not in Makefile.

4. Run pre-flight checks sequentially. Each check records pass/fail:
   ```bash
   oc whoami --show-server                                        # cluster reachable?
   oc whoami                                                      # authenticated?
   oc get ns <OPERATOR_NAMESPACE>                                 # namespace exists?
   oc get csv -n <OPERATOR_NAMESPACE> -o jsonpath='{.items[0].status.phase}'  # CSV Succeeded?
   ```

5. If **any check fails**, STOP with a checklist showing what passed and what failed:
   ```
   Cluster readiness check failed:
     [x] Cluster reachable: https://api.cluster.example.com:6443
     [x] Authenticated as: user@example.com
     [ ] FAILED: Namespace '<OPERATOR_NAMESPACE>' not found.
         Fix: Install the operator via OLM before running E2E tests.
   ```
   Do NOT proceed to test execution.

6. If **all checks pass**, output:
   ```
   Cluster readiness: OK
     Cluster: <server URL>
     User: <username>
     Namespace: <OPERATOR_NAMESPACE> exists
     Operator CSV: Succeeded
   ```
   Proceed to Step 5.4.

#### Step 5.4 — Execute tests

Run the E2E test suite. Track `attempt` counter starting at 1.

```bash
OPERATOR_NAMESPACE=<ns> make test-e2e 2>&1 | tee /tmp/opsx-e2e-output.log
```

Parse the Go test / Ginkgo output for per-test pass/fail results.

**Telemetry — emit after execution:**
- `e2e_execution` event with:
  - `attempt` (1 for first run, 2+ for retries)
  - `tests_run`, `tests_passed`, `tests_failed`
  - `exit_code` (0 = all pass)
  - `file_hash` (SHA-256 of generated test files — for flake detection)
  - `source: "local"`
- `e2e_bug_found` per distinct test failure with `test_name` and `failure_message`.

**Generate QE metrics:**
```bash
python -m openspec.telemetry.qe_metrics --change <name>
```
This produces `openspec/changes/<name>/telemetry/qe-metrics.json` with accurate first-pass
rate, flake rate, and bug count from the real local execution.

If `exit_code == 0` (all tests pass): skip Step 5.5, proceed to Step 5.6.
If `exit_code != 0` (any test failed): proceed to Step 5.5.

#### Step 5.5 — E2E evaluation report (on failures)

Generate an evaluation report analyzing every failure before asking the user to approve or fix.

Write to `openspec/changes/<name>/e2e/e2e-evaluation-report.md`:

```markdown
## E2E Evaluation Report: <change-name>

### Execution Summary
| Metric | Value |
|--------|-------|
| Total tests | N |
| Passed | N |
| Failed | N |
| Exit code | N |
| Duration | Xs |
| Attempt | N |

### Failed Tests

#### 1. TestName / It("description")
- **Error:** <exact error message from go test output>
- **File:** `test/e2e/e2e_test.go:LINE`
- **Root cause analysis:** <analysis of WHY it failed — missing CR, timing issue,
  wrong assertion, code bug in reconciler, etc.>
- **Suggested fix:** <concrete change needed — e.g. "increase timeout in
  WaitForDeploymentAvailable from 2m to 5m" or "reconciler does not set
  status.phase — add status update in controller">
- **Fix location:** <file:line where the fix should be applied>
- **Category:** test_bug | code_bug | environment | flaky

#### 2. ...
(repeat for each failed test)

### Overall Assessment
- **Ready for PR:** Yes / No
- **Blocking issues:** N code bugs, M test bugs, K environment issues
- **Recommendation:** <"Fix N issues before raising PR" or "All failures are
  environment-related — safe to raise PR">
```

Present the report to the user:

ASK: **"E2E evaluation report generated. {N} tests failed ({M code bugs, K test bugs, J environment). Review the report above."**
  - **Approve and proceed to PR** — failures are acceptable (environment/flaky/known)
  - **Fix and re-run** — apply suggested fixes, then re-execute tests

**If user selects "Fix and re-run":**
1. Apply the suggested fixes from the report (edit test files or source code as needed).
2. Increment `attempt` counter.
3. Re-run `make test-e2e` (Step 5.4 again).
4. If previously-failing tests now pass, emit `e2e_bug_verified` events.
5. Regenerate `qe-metrics.json` (includes retry data for flake rate calculation).
6. If triage RCA was provided, ASK: "Was the root cause analysis correct? (y/n)" per bug.
   Emit `e2e_triage` with `user_confirmed: true/false`. Skip if user declines.
7. Re-evaluate: if still failing, regenerate `e2e-evaluation-report.md` and prompt again.
8. **Max 2 fix-and-rerun loops.** After 2 retries, force proceed to Step 5.6 with current results.

**If user selects "Approve and proceed":** proceed to Step 5.6.

#### Step 5.6 — PR to upstream

After test execution completes (or if local execution was skipped), prompt for upstream PR.

ASK: **"Raise a draft PR from your fork to the upstream repo? (yes / no)"**

**If No:** skip to Step 5.7.

**If Yes:**
1. Read `config.yaml → credentials.github.upstream_repo_url` and `credentials.github.fork_repo_url`.
2. If either is empty, ASK: **"Provide your fork repo URL and the upstream repo URL:"**
   Persist responses to `inputs/jira.yaml`.
3. Determine `fork_owner` from the fork URL (e.g. `sujkini` from `github.com/sujkini/repo`).
4. Get current branch name: `git rev-parse --abbrev-ref HEAD`.
5. Create cross-repo draft PR:
   ```bash
   gh pr create \
     --repo <upstream_org/repo> \
     --head <fork_owner>:<branch> \
     --base main \
     --title "<JIRA-KEY>: <change summary>" \
     --body "Generated by OpenSpec /opsx-e2e. Includes E2E tests for <change-name>." \
     --draft
   ```
6. Record PR URL in `state.yaml → upstream_pr_url`.
7. Output: **"Draft PR created on upstream: <PR_URL>"**

#### Step 5.7 — Write summary and close

1. Write E2E summary to `openspec/changes/<name>/e2e/e2e-summary.md`.

**Telemetry (Stage 5 close):**
- Emit `e2e_stage_end` with `tokens_in`, `tokens_out`, `duration_s`.
- Emit `e2e_run_end` with status (`passed`, `failed_approved`, `not_executed`).

### 9. Final Summary

```
## E2E Generation Complete: <change-name>

**PR (fork):** <PR URL>
**PR (upstream):** <upstream PR URL or "not raised">
**Phase:** <N> (or "final")

### Artifacts Generated
| Stage | Artifact | Path |
|-------|----------|------|
| Pre-analysis | e2e-analysis.md | openspec/changes/<name>/e2e/ |
| Test plan | test-plan.md | openspec/changes/<name>/e2e/ |
| Revised plan | revised-test-plan.md | openspec/changes/<name>/e2e/ |
| Generated code | <file>_test.go | openspec/changes/<name>/e2e/generated/ |
| Evaluation report | e2e-evaluation-report.md | openspec/changes/<name>/e2e/ |
| QE Metrics | qe-metrics.json | openspec/changes/<name>/telemetry/ |

### Test Results
| Journey | Status |
|---------|--------|
| Journey 1: ... | PASS/FAIL/NOT RUN |

### QE Metrics Summary
| Metric | Value |
|--------|-------|
| AC → Scenario Coverage | X% (N/M criteria covered) |
| Automation Coverage | X% (N automated, M manual) |
| First-Pass Pass Rate | X% (N/M passed first run) |
| Flake Rate | X% (N flaky retries) |
| Bugs Found / Verified | N found, M verified |
| Triage Accuracy | X% (or N/A) |
| QE Cost | $X.XX (N tokens, Xs wall time) |

### Next Steps
- Review test code in the PR
- If upstream PR raised: monitor CI on the upstream PR
- Re-run with `/opsx-e2e --phase N` after fixes if tests failed
```

### 10. Time Saved Prompt

After presenting the final summary, ASK the user:

```
How much time (%) did OpenSpec save you compared to doing this manually?
  - Development workflow (specs → plan → tasks → code): ___%
  - E2E workflow (test plan → code gen → execution): ___%
  Enter two numbers (e.g. '40 60') or press Enter to skip.
```

- Parse response: two integers (development_pct, e2e_pct).
- If user presses Enter or says "skip" → record `null` for both.
- Emit `e2e_time_saved` telemetry event with `development_pct` and `e2e_pct`.
- Include in the final `qe-metrics.json` under `"time_saved"`.

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
