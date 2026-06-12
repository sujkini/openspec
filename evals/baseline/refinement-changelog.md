# Refinement changelog — append-only

## Round 1 — Istio CSR (CM-463) — 2026-06-10

### validation.md

Added `### Addon-operator supplements` section under Completeness rubric:
- Singleton semantics (namespaced default vs cluster)
- CR delete / teardown behavior
- Status conditions lifecycle
- Unified ctrl.Manager requirement
- OLM upgrade path for new owned CRDs
- Operand version compatibility matrix
- Documentation placeholder consistency

**Driver bugs:** CM-735, CM-770, CM-521, CM-546, OCPBUGS-57841

### baseline/agents.md

Added Round 1 addon routing notes: unified manager, IstioCSR singleton convention, status conditions, OLM upgrade, operand versions.

**Eval cases added:** 15 (3 per stage: repo-assessment, constitution, plan, tasks, implementation)

## Round 2 — Network Policy (CM-802 / CM-525) — 2026-06-10

### validation.md

Added `### Network policy supplements` section:
- Dual controller paths (static library-go vs user-defined runtime)
- Opt-in `defaultNetworkPolicy` backward compatibility
- Traffic matrix per component
- Drift reconciliation, idempotent reconcile, delete/recreate watch
- Operator OLM vs operand NP split

**Driver bugs:** CM-758, CM-763, CM-764

### baseline/agents.md

Added Round 2: library-go static NP vs user-defined runtime; compare-before-update; NetworkPolicy watches.

**Eval cases added:** 15 (`eval-r002-*`)
**Eval cases updated:** `eval-r001-tasks-001` (NP drift/delete verification pairing)

## Backfill — Template patches (rounds 1–2 gaps) — 2026-06-10

Applied in-place refinements to schema templates (previously eval-only). Driver patterns: PAT-003–PAT-012, CM-463, CM-758, CM-763, CM-764.

### repo-assessment.md

Added **Network policy dual-path** under §4.2: library-go static vs user-defined runtime paths with package paths, OLM vs operand split, branch verification.

### constitution.md

Added **cert-manager-operator supplements**: unified manager, addon vs library-go split; NP drift revert, compare-before-update, delete-recreate.

### plan.md

Added **Addon operand planning supplements** and **Network policy planning supplements**; quality self-check rows for NP verification and GA API field coverage.

### tasks.md

Added **Verification pairing**, **Operand reconcile features**, output mode pointer, quality self-check.

### implementation.md

Added **Reconciler guardrails**: compare-before-update, static drift revert, delete-recreate, deviation logging.

### tasks-modes/single.md

Added drift/delete/idempotent reconcile pairing in completeness rules and quality self-check.
