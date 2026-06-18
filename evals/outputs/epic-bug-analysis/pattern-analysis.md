# Pattern Analysis — Istio CSR integration (CM-463 / OCPSTRAT-1974)

**Round:** 3 | **Feature:** Istio CSR integration | **Baseline:** Rounds 1–2 (Istio CSR + Network Policy)

## Baseline cross-check (round 1 evals — same feature, round 1)

| Round 1 eval | Would catch bug? | Bug |
|--------------|------------------|-----|
| eval-r001-const-002, eval-r001-impl-001 (unified manager) | **Yes** | CM-735 |
| eval-r001-tasks-001, eval-r001-impl-002 (Ready + e2e) | **Yes** | CM-546 |
| eval-r001-plan-002 (OLM upgrade) | **Yes** | CM-770 |
| eval-r001-plan-003 (version skew matrix) | **Yes** | CM-521 |
| eval-r001-tasks-003 (docs placeholders) | **Yes** | OCPBUGS-57841 |

**Conclusion:** Round 1 artifact evals cover all five bugs at the workflow level. Round 3 gap is **code-generation evals** (empty after rounds 1–2) — retrospective patterns were not enforced at `/opsx-apply` per-task gate.

## 1. Requirement → ARD layout

EP ([istio-csr-controller.md](https://github.com/openshift/enhancements/blob/master/enhancements/cert-manager/istio-csr-controller.md)):

| Section | Content |
|---------|---------|
| Summary | cert-manager-operator manages istio-csr via dedicated controller + IstioCSR CR |
| Motivation | Customer CA via cert-manager for OSSM mTLS |
| Goals | Extend operator; new `istiocsrs.operator.openshift.io` CR |
| Non-goals | Limited CR delete teardown; no auto ConfigMap cleanup; version skew bounds |
| Proposal | Static manifests, labels, singleton CR, status subresource, GA API fields |
| Risks | ConfigMap conflicts, OLM upgrade, operand version skew, status completeness |

**ARD strength:** Detailed API types, CEL immutability, manifest examples, operational commands, version skew table.

**ARD gaps:** No explicit requirement for unified manager cache; OLM upgrade test plan implicit; Ready condition lifecycle not spelled out in test plan.

## 2. Epic → Stories carving

```
OCPSTRAT-1974 (GA strategy)
    └── CM-463 (TP epic)
            ├── CM-418/419 — CRD + controller
            ├── CM-423 — E2E + gRPC
            ├── CM-521/675/826 — operand version bumps
            ├── CM-679/680/681/706 — GA API fields
            ├── CM-639 — metrics
            └── CM-1043 — Service Mesh smoke tests
```

| Carving pattern | Observation |
|-----------------|-------------|
| TP → GA strat | Same AC text; GA adds API revisit stories |
| Verification | E2E stories added after controller (CM-423) — Ready assertion gap found in QA (CM-546) |
| Packaging | OLM/CRD stories implicit in controller epic — upgrade break found post-release (CM-770) |

## 3. Gaps: EP → stories

- No story for **OLM N-1→N upgrade** when adding `istiocsrs` CRD (CM-770)
- No story for **controller cache wiring** in setup_manager (CM-735)
- Operand version story (CM-521) came from **OSSM integration feedback**, not EP verification matrix
- Docs placeholder consistency not in story AC (OCPBUGS-57841)

## 4. Pattern recurrence (round 3)

All Istio CSR patterns from round 1 are **recurring** — same feature bundle re-run with code-generation eval gap as primary new work.

| ID | Pattern | Recurrence |
|----|---------|------------|
| PAT-001 | Namespaced singleton `default` CR | recurring (round 1) |
| PAT-002 | Limited teardown on CR delete | recurring |
| PAT-003 | Unified ctrl.Manager cache for addons | recurring |
| PAT-004 | Ready condition when operand healthy | recurring |
| PAT-005 | OLM upgrade for new owned CRD | recurring |
| PAT-006 | Operand version skew vs OSSM/Istio | recurring |
| PAT-007 | Docs placeholder naming consistency | recurring |
| PAT-008 | GA API fields (selector, CA cert, clusterID) | recurring |

**New pattern (round 3):** PAT-015 — Code-generation eval gate missing for addon controller tasks (retrospective evals did not flow to `/opsx-apply`).
