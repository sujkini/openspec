# Template diff: `repo-assessment.md`

| Side | Path |
|------|------|
| Schema (upstream) | `schemas/openspec-agile-workflow/templates/repo-assessment.md` |
| Refined (eval workflow) | `evals/refined-templates/repo-assessment.md` |

## Status

**Changed** — +27 / -1 lines (approx.)

## Unified diff

```diff
--- schemas/openspec-agile-workflow/templates/repo-assessment.md
+++ evals/refined-templates/repo-assessment.md
@@ -139,6 +139,24 @@
 - If TrustManager exists on branch: document its install sequence and SSA field owner

   `trust-manager-controller` — otherwise state "Not on this branch" in §4.2.

 

+**Addon operand assessment (when spec describes IstioCSR / TrustManager / similar addon):**

+- Document **namespaced singleton** `metadata.name: default` vs core `CertManager` cluster singleton

+  `metadata.name: cluster` — cite CRD path (e.g. `istiocsrs.operator.openshift.io`) and CEL validation.

+- List **GA API fields** from spec in §4.1 table (e.g. `istioCACertificate`, `istioDataPlaneNamespaceSelector`,

+  `server.clusterID`) with immutability/default notes from CRD markers.

+- Cross-reference exemplar package (`pkg/controller/istiocsr/`) for greenfield or delta assessment.

+- Document **operand image/bindata version** pin and platform compatibility (OSSM/Istio minimums) in §4.3.

+

+**Network policy dual-path (when spec touches NetworkPolicy / defaultNetworkPolicy / networkPolicies[]):**

+- Document **both** reconciliation paths with package paths — do not collapse into a single controller:

+  1. **Static / default NPs (library-go):** `StaticResourceController` / static-resources path under

+     `pkg/controller/certmanager/` — operator-managed defaults; spec drift must be reverted on reconcile.

+  2. **User-defined NPs (controller-runtime):** CR `networkPolicies[]` entries reconciled by a runtime

+     controller — compare desired vs current before patch; delete must trigger recreate (watch/informer).

+- State which path owns operator-namespace NP (OLM bundle) vs operand-namespace NPs (CR-driven).

+- For pre-feature repo pins: document what exists on the branch vs greenfield work required.

+- Cross-reference §10.2 Network policy patterns with the dual-path table in §4.2.

+

 **Configuration Surface (§4.1):**

 - List ALL fields for `CertManager` spec in a table: managementState, logLevel,

   operatorLogLevel, unsupportedConfigOverrides (controller.args/webhook.args/cainjector.args),

@@ -444,7 +462,15 @@
 ### 10.2 Proxy & Network Configuration

 * How proxy settings propagate (e.g., OLM → operator → operands)

 * Trusted CA bundle injection mechanism

-* Network policy patterns

+* Network policy patterns — when spec touches NPs, include a **per-component traffic matrix** table:

+  | Component | Ingress/Egress | Ports / peers | Notes |

+  |-----------|----------------|---------------|-------|

+  | API server | egress | 6443 | Kubernetes API |

+  | Webhook | ingress | 10250 | Admission webhook |

+  | Metrics | ingress | 9402 | Prometheus scrape |

+  | DNS | egress | 53/udp,tcp | CoreDNS |

+  | istio-csr (if applicable) | ingress/egress | gRPC per EP | Operand-specific |

+  Cross-reference §4.2 dual-path (static library-go vs user-defined runtime) and `defaultNetworkPolicy` opt-in.

 

 ### 10.3 Cloud Provider Integration

 * Credential provisioning (CCO, CredentialsRequest, workload identity, etc.)

```
