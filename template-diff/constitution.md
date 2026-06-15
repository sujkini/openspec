# Template diff: `constitution.md`

| Side | Path |
|------|------|
| Schema (upstream) | `schemas/openspec-agile-workflow/templates/constitution.md` |
| Refined (eval workflow) | `evals/refined-templates/constitution.md` |

## Status

**Changed** — +26 / -0 lines (approx.)

## Unified diff

```diff
--- schemas/openspec-agile-workflow/templates/constitution.md
+++ evals/refined-templates/constitution.md
@@ -58,6 +58,32 @@
 - **[Constraint category]:** [Rule derived from repo] — **Evidence:** `[path]`

 - **[Constraint category]:** [Rule derived from repo] — **Evidence:** `[path]`

 

+### cert-manager-operator supplements (include when repo/spec warrants)

+

+**Addon controllers:**

+- Unified `ctrl.Manager` in `setup_manager.go` — no separate per-addon manager or isolated cache.

+- Addon CRs use controller-runtime + SSA; core cert-manager uses library-go — do not mix patterns.

+- **Singleton semantics:** addon CRs are namespaced with singleton name `default` (CEL-enforced) — NOT

+  cluster-scoped `cluster` like core `CertManager`. Cite exemplar (e.g. `istiocsrs.operator.openshift.io`).

+- **CR delete / teardown:** limited teardown only — stop reconciling + warning event; document manual

+  cleanup as non-goal unless EP explicitly requires full resource deletion (TechPreview may defer).

+- **Status conditions:** `Ready` and `Degraded` lifecycle via `SetCondition()` / `HandleReconcileResult()` —

+  `Ready` MUST be set when operand is healthy (not only `Degraded` on failure).

+- **OLM upgrade:** when a new owned CRD joins the bundle, N-1 → N operator upgrade MUST be testable;

+  avoid CSV/CRD changes that break in-place upgrades (e.g. shortname additions without migration plan).

+- **Operand version matrix:** bindata/operand image pins MUST align with platform dependencies

+  (OSSM/Istio minimum versions) — document compatibility in constraints, not only in plan.

+- **Documentation placeholders:** integration examples MUST use consistent parameter names across docs

+  (e.g. `<istio_project_name>` — not mixed namespace/project placeholders).

+

+**Network policy (when spec touches NetworkPolicy / defaultNetworkPolicy / networkPolicies[]):**

+- Static/library-go managed NPs: operator-owned field drift MUST be reverted on reconcile.

+- User-defined runtime NPs: compare desired vs current before patch — no hot-loop on unchanged spec.

+- User-defined NP delete MUST trigger prompt recreate (watch/informer required).

+- Distinguish operator-namespace NP (OLM bundle) from operand NPs (CR-driven).

+- **Opt-in security defaults:** `defaultNetworkPolicy` and similar features default `false` for backward

+  compatibility — constitution must not assume enabled-by-default without EP evidence.

+

 ## Development Workflow

 

 <!-- How work actually flows in this repo: review, CI, local verify, bundle generation -->

```
