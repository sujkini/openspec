# RCA Summary — Network Policy bugs (Round 2)

**Baseline consulted:** `evals/baseline/evals/` round 1 — no direct NP coverage.

---

## CM-758 — Static NP spec drift not reconciled

| Field | Value |
|-------|-------|
| Symptom | Patched static NP port not reverted after 10+ min |
| Fix | PR #338 — library-go bump with enhanced ApplyNetworkPolicy |
| Category | **coding** (static controller integration) + **story_formation** (no tamper-test story) |
| Type | functional |
| Stage | plan, tasks, implementation |
| Round 1 eval gap | eval-r001-tasks-001 would catch if NP tamper e2e added |

---

## CM-763 — Infinite NetworkPolicy update loop

| Field | Value |
|-------|-------|
| Symptom | NetworkPolicyUpdated every 400–800ms for 1+ hour |
| Fix | PR #339 — fix unconditional update in user-defined reconciler |
| Category | **coding** |
| Type | non_functional |
| Stage | implementation, tasks |
| Pattern | Compare-before-update / semantic equality missing |

---

## CM-764 — Slow recreate after user-defined NP delete

| Field | Value |
|-------|-------|
| Symptom | Deleted user NP recreated after ~8 min (static NP immediate) |
| Fix | PR #342 — NetworkPolicy informer on user-defined controller |
| Category | **coding** + **design** (EP didn't distinguish watch requirements per controller) |
| Type | functional |
| Stage | plan, tasks, implementation |
| Pattern | Missing Watches() on NetworkPolicy for user-defined path |

---

## Code approach analysis

### Functional

| Approach | Bug | Issue |
|----------|-----|-------|
| Rely on library-go without verifying drift reconcile | CM-758 | Static NP tamper persists |
| No informer on user-defined NP resources | CM-764 | Delete not observed promptly |

### Non-functional

| Approach | Bug | Issue |
|----------|-----|-------|
| Unconditional client.Update in reconcile | CM-763 | Hot loop, API load |

### Architectural insight

Network policy feature spans **two reconcile paths** with different semantics — round 1 addon evals assumed single controller-runtime SSA pattern. NP feature requires evals for **library-go static** vs **runtime user-defined** controllers separately.
