# Template diff: `validation.md`

| Side | Path |
|------|------|
| Schema (upstream) | `schemas/openspec-agile-workflow/templates/validation.md` |
| Refined (eval workflow) | `evals/refined-templates/validation.md` |

## Status

**Changed** — +20 / -0 lines (approx.)

## Unified diff

```diff
--- schemas/openspec-agile-workflow/templates/validation.md
+++ evals/refined-templates/validation.md
@@ -40,6 +40,26 @@
 - Platform matrix (OpenShift vs MicroShift; FeatureGates/FeatureSets if relevant; Hypershift/hosted notes)

 - Observability (metrics/readiness/status conditions if relevant)

 - Upgrade / downgrade / version skew

+

+### Addon-operator supplements (when spec describes cert-manager-operator addon operands)

+Penalize if absent from spec or untestable; add to `missing_elements` and `cert_manager_ecosystem.gaps`:

+- **Singleton semantics:** namespaced `default` vs cluster `cluster` — flag contradiction with cert-manager core patterns

+- **CR delete / teardown:** explicit behavior (stop reconcile only vs full cleanup); manual cleanup steps if limited teardown

+- **Status conditions:** Ready and Degraded lifecycle — when each is set; observable e2e criteria

+- **Unified manager:** addon controllers share one `ctrl.Manager` / cache (no separate per-addon cache)

+- **OLM upgrade path:** when a new owned CRD joins the bundle, upgrade from N-1 operator version must be testable

+- **Operand version matrix:** minimum istio-csr (or addon) version vs platform dependency (e.g. OSSM / Istio)

+- **Documentation placeholders:** consistent parameter names in examples (`<istio_project_name>` etc.)

+

+### Network policy supplements (when spec touches NetworkPolicy / defaultNetworkPolicy / networkPolicies[])

+Penalize if absent or untestable; add to `missing_elements` and `cert_manager_ecosystem.gaps`:

+- **Dual controller paths:** static library-go managed vs user-defined runtime — both documented

+- **Opt-in default:** `defaultNetworkPolicy` default false and backward-compat impact stated

+- **Traffic matrix:** per-component ingress/egress ports (API 6443, metrics 9402, webhook 10250, DNS, istio gRPC)

+- **Drift reconciliation:** tampered static NP spec must be reverted — test scenario required

+- **Idempotent reconcile:** user-defined NP must not hot-loop on unchanged spec

+- **Delete/recreate SLA:** user-defined NP delete must trigger prompt recreate (watch/informer)

+- **Operator vs operand:** OLM bundle NP for operator namespace vs CR-driven operand NPs

 

 ## Rubric — B) QUALITY (Clarity & Actionability; INVEST-style)

 Flag with quotes + concrete rewrite guidance:

```
