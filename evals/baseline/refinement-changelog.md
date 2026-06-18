# Refinement changelog — append-only

**Template location:** `evals/refined-templates/` (eval workflow). Do not log changes under `schemas/` — upstream defaults stay unchanged.

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

## Full bundle backfill — Rounds 1 & 2 (Istio CSR + Network Policy) — 2026-06-10

Comprehensive in-place template refinement for all PAT-001–PAT-014 patchable gaps.

### constitution.md (round 1 + 2)

Expanded cert-manager-operator supplements: singleton `default`, limited teardown, Ready/Degraded,
OLM upgrade, operand version matrix, doc placeholders, opt-in `defaultNetworkPolicy`.

### repo-assessment.md

Added addon operand assessment block (singleton, GA API fields, bindata version); §10.2 per-component
traffic matrix table (6443, 10250, 9402, DNS, istio-csr).

### plan.md

Addon supplements: teardown phase, version compatibility, documentation phase; NP traffic matrix §6 rows;
self-check for OLM upgrade and traffic matrix.

### tasks.md

OLM upgrade verification pairing, bindata platform compatibility, documentation placeholder AC,
controller Watches tasks; expanded quality self-check.

### implementation.md

Unified manager wiring, status conditions, limited teardown, static drift revert, NetworkPolicy Watches.

### tasks-modes/single.md

OLM upgrade, documentation, and Watches tasks in completeness rules and self-check.

**Driver patterns:** PAT-001–PAT-014 | **Driver bugs:** all 8 input bugs across both bundles

## Round 3 — Istio CSR re-run / code-generation (CM-463) — 2026-06-18

### validation.md

Added `### Code-generation eval bridge` section — flag specs whose tasks would not map to
`code-generation_eval.yaml` per-task gates at `/opsx-apply`.

**Driver:** PAT-015 — empty codegen evals after rounds 1–2

### tasks.md

Added `### OAPE command tagging` section — every task payload must include OAPE Command for
code-generation eval filtering.

**Driver:** PAT-015

### baseline/evals/code-generation/code-generation_eval.yaml

Populated **13 code-generation cases** (was empty): api-implement (3), api-generate (2),
api-generate-tests (2), manual (3), e2e-generate (2), any (1).

**Driver bugs:** CM-735, CM-546, CM-770, CM-521, OCPBUGS-57841

### baseline/agents.md

Added Round 3 code-generation eval bridge routing notes.

**Eval cases added:** 28 (15 artifact bridge + 13 code-generation)
