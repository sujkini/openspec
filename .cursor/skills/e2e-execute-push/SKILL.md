# E2E Execute and Push (Stage 4)

Execute E2E tests locally and optionally push to PR branch.

## Design Mode Gate

If running in **Design Mode** (ADR/EP only, no PR):
- Run implementation presence check
- ASK: "Run E2E tests locally on your cluster? (Yes / No)"
- If No: show Design Mode completion banner, skip push
- If Yes: run cluster readiness + execution, skip push (no PR branch)

## PR Mode / Combined Mode

### Step 1 — Local Execution Prompt

ASK: "Run E2E tests locally on your cluster? (Yes / No)"
Do NOT auto-execute. Do NOT assume.
- No: skip to step 5 (push/stop decision)
- Yes: proceed to step 2

### Step 2 — Cluster Readiness Gate

1. Read `config.yaml → credentials.cluster.kubeconfig_path` (ask if empty)
2. Export KUBECONFIG
3. Read OPERATOR_NAMESPACE from Makefile or `test/e2e/utils/constants.go`
4. Run pre-flight checks:
   ```bash
   oc whoami --show-server
   oc whoami
   oc get ns <OPERATOR_NAMESPACE>
   oc get csv -n <OPERATOR_NAMESPACE> -o jsonpath='{.items[0].status.phase}'
   ```
5. If any fails: STOP with checklist. Do NOT proceed.
6. If all pass: output "Cluster readiness: OK". Proceed.

### Step 3 — Execute Tests

```bash
OPERATOR_NAMESPACE=<ns> make test-e2e 2>&1 | tee /tmp/opsx-e2e-output.log
```

Parse Go test / Ginkgo output for per-test pass/fail.

Emit telemetry: `e2e_execution`, `e2e_bug_found` per failure.

Generate QE metrics:
```bash
python -m openspec.telemetry.qe_metrics --change <name>
```

Verify metrics completeness (tests_executed not null, bug count matches failures).

### Step 4 — E2E Evaluation Report (on failures)

Write `openspec/changes/<name>/e2e/e2e-evaluation-report.md` with per-failure root cause analysis.

Present to user: "Fix and re-run? / Push as-is? / Stop?"
- Fix: apply fixes, re-run (attempt 2+)
- Push as-is: proceed to step 5
- Stop: STOP

### Step 5 — Push / Stop Decision

ASK: "Push generated E2E test code to the PR branch? (Yes / No)"

If Yes:
```bash
cp -r openspec/changes/<name>/e2e/generated/* <target-repo>/test/e2e/
cd <target-repo> && git add test/e2e/ && git commit -m "Add E2E tests from /opsx-e2e" && git push
```

Output: "E2E code pushed to PR branch. CI will re-run."

### Step 6 — Final Summary

Present execution summary with test results, artifacts, PR status.
