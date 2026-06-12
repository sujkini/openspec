# Pattern Analysis — Network Policy hardening (CM-802 / CM-525)

**Round:** 2 | **Feature:** Network Policy hardening | **Baseline:** Round 1 (Istio CSR)

## Baseline cross-check (round 1 evals)

| Round 1 eval | Would catch NP bugs? |
|--------------|---------------------|
| eval-r001-impl-001 (unified manager) | Partial — NP uses library-go static controller + separate runtime controller |
| eval-r001-tasks-001 (verify pairing) | **Yes** — if extended to NP tamper/delete scenarios |
| eval-r001-plan-002 (OLM upgrade) | No |
| eval-r001-const-002 (unified manager) | No — different controller split |

**Conclusion:** Round 1 evals insufficient for network policy reconcile/watch patterns → **new_pattern** for PAT-009 through PAT-012.

## 1. Requirement → ARD layout

EP ([cert-manager-network-policies.md](https://github.com/openshift/enhancements/blob/master/enhancements/cert-manager/cert-manager-network-policies.md)):

| Section | Content |
|---------|---------|
| Summary | Operator OLM NPs + operand NPs via CertManager CR |
| Motivation | Product Security mandate, least privilege |
| Goals | opt-in `defaultNetworkPolicy`, deny-all + allows, user `networkPolicies[]`, istio-csr auto-managed |
| Non-goals | No AdminNetworkPolicy; no istio-csr user NP config |
| Proposal | Dual path: OLM for operator NS, operator for operand NS |
| Implementation | Traffic matrix per component; YAML examples |

**ARD strength:** Clear traffic flows, opt-in default, separation operator vs operand.

**ARD gaps:** Two-controller architecture (static library-go vs user-defined runtime) not explicit; watch/reconcile semantics for NP drift not specified; no SLA for recreate-after-delete latency.

## 2. Epic → Stories carving

```
OCPSTRAT-819 (platform mandate)
    ├── CM-802 (operator epic)
    └── CM-525 (operand epic)
            ├── CM-577 / PR #320 — core NP implementation
            ├── CM-525 / PR #348 — CoreController scope
            └── Bug fixes: CM-758, CM-763, CM-764
```

| Carving pattern | Observation |
|-----------------|-------------|
| Operator vs operand split | CM-802 vs CM-525 mirrors EP OLM vs operator-managed |
| Static vs user-defined | EP describes both; **no separate story** for watch semantics per controller type |
| Verification | Bugs found in QA — tamper, loop, delete latency not in initial AC |

## 3. Gaps: EP → stories

- No story for **static NP spec drift reconciliation** (CM-758)
- No story for **idempotent user-defined NP updates** (CM-763)
- No story for **immediate recreate on user-defined NP delete** (CM-764)
- Deployment scenario table in Jira epic left empty (Hypershift, SNO, etc.)

## 4. New patterns (round 2)

| ID | Pattern | Recurrence |
|----|---------|------------|
| PAT-009 | Dual NP controller architecture (static library-go vs user-defined runtime) | new |
| PAT-010 | Static-managed NP must reconcile spec drift (tamper correction) | new |
| PAT-011 | User-defined NP reconciler must skip no-op updates (avoid hot loop) | new |
| PAT-012 | User-defined NP controller must watch NP delete events for prompt recreate | new |
| PAT-013 | Opt-in `defaultNetworkPolicy` backward compatibility | new |
| PAT-014 | Traffic matrix per component (webhook, metrics, DNS, API server) | new |
