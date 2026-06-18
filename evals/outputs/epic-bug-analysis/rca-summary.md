# Root Cause Analysis — Istio CSR integration bugs

**Round:** 3 | **Epic:** CM-463 | **GA Strat:** OCPSTRAT-1974 | **Bugs:** 5

## CM-735 — Reconcile skip / empty status on CR creation

| Field | Detail |
|-------|--------|
| Symptom | IstioCSR CR created; `.status` empty; deployment missing; log: object not found in cache |
| Fix | PR #324 — register istiocsr in unified manager cache (`setup_manager.go`) |
| Root cause category | **coding** |
| Type | functional |
| Workflow stage | **implementation** |
| Pattern | PAT-003 (recurring) |
| Round 1 eval would catch? | **Yes** — eval-r001-const-002, eval-r001-impl-001 |
| Round 3 gap | No **code-generation** eval enforced unified cache at apply time |

## CM-546 — Missing Ready condition

| Field | Detail |
|-------|--------|
| Symptom | Deployment ready; IstioCSR lacks `Ready` condition; e2e timeout at istio_csr_test.go:118 |
| Fix | PR #241 — status update conflict / state machine fix; PR #381 area for broader resource logic |
| Root cause category | **coding** |
| Type | functional |
| Workflow stage | **tasks** |
| Pattern | PAT-004 (recurring) |
| Round 1 eval would catch? | **Yes** — eval-r001-tasks-001, eval-r001-impl-002 |
| Round 3 gap | No codegen eval for `HandleReconcileResult` + Ready |

## CM-770 — OLM upgrade CRD conflict

| Field | Detail |
|-------|--------|
| Symptom | CSV Pending; `istiocsrs.operator.openshift.io` PresentNotSatisfied; 1.17→1.18 upgrade |
| Fix | PR #344 — revert CRD shortname addition |
| Root cause category | **design** |
| Type | non_functional |
| Workflow stage | **validation** |
| Pattern | PAT-005 (recurring) |
| Round 1 eval would catch? | **Yes** — eval-r001-plan-002 |
| Round 3 gap | No **manual** codegen eval for OLM bundle CRD immutability |

## CM-521 — Operand version below OSSM minimum

| Field | Detail |
|-------|--------|
| Symptom | OSSM v3 integration testing failed — istio-csr version incompatible |
| Fix | PR #304 — rebase bindata to v0.14.2+ |
| Root cause category | **story_formation** |
| Type | functional |
| Workflow stage | **plan** |
| Pattern | PAT-006 (recurring) |
| Round 1 eval would catch? | **Yes** — eval-r001-plan-003, eval-r001-repo-003 |
| Round 3 gap | No **manual** codegen eval for bindata version pin |

## OCPBUGS-57841 — Docs placeholder inconsistency

| Field | Detail |
|-------|--------|
| Symptom | Docs use mixed `istio-system` / `<istio_csr_project_name>` / `<istio_project_name>` |
| Fix | Doc updates — unify on `<istio_project_name>` |
| Root cause category | **ops_docs** |
| Type | non_functional |
| Workflow stage | **tasks** |
| Pattern | PAT-007 (recurring) |
| Round 1 eval would catch? | **Yes** — eval-r001-tasks-003 |
| Round 3 gap | No **manual** docs task codegen eval |

---

## Code approach

### Functional issues

| Approach | Bug | Lesson |
|----------|-----|--------|
| Separate controller cache / Manager | CM-735 | Addon controllers must share unified manager from `setup_manager.go` |
| Incomplete status state machine | CM-546 | Use `HandleReconcileResult`; set Ready when deployment available |
| Stale bindata operand version | CM-521 | Pin bindata via `hack/update-istio-csr-manifests.sh`; verify OSSM matrix |

### Non-functional issues

| Approach | Bug | Lesson |
|----------|-----|--------|
| CRD schema change without upgrade test | CM-770 | Treat CRD shortnames/ownership as immutable across N-1 bundle |
| Docs without parameterized placeholders | OCPBUGS-57841 | Single placeholder convention in all examples |

### Code-generation implication (round 3)

Retrospective artifact evals (round 1) did not translate to per-task `/opsx-apply` gates. Round 3 adds `code-generation_eval.yaml` cases tagged by `oape_command` for each bug pattern.
