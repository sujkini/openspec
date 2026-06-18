# Input: EP / ARD — Istio CSR integration

**Link:** https://github.com/openshift/enhancements/blob/master/enhancements/cert-manager/istio-csr-controller.md

**Tracking:** CM-234 | **Authors:** @bhb | **Last updated:** 2025-09-24

## Summary

Extend cert-manager-operator to deploy and manage the `istio-csr` agent via a dedicated controller. New CR `istiocsrs.operator.openshift.io` (namespaced singleton `default`) configures the operand. cert-manager signs Istio workload and control-plane CSRs; istio-csr bridges OSSM to cert-manager.

## Key design points

- **New controller:** `istio-csr-controller` in cert-manager-operator manages static manifests (Certificate, Issuer, RBAC, Deployment, Service, ServiceMonitor, etc.)
- **Singleton CR:** namespaced `IstioCSR` named `default` with CEL enforcement
- **Immutable fields:** issuerRef, privateKeySize, certificateKeySize, signatureAlgorithm, istio.revisions, istio.namespace (CEL)
- **Limited delete:** CR delete stops reconciliation only — manual cleanup (GA non-goal for full auto-uninstall)
- **GA API additions:** `istioDataPlaneNamespaceSelector`, `certManager.istioCACertificate`, `server.clusterID`
- **Labels:** `app.kubernetes.io/managed-by: cert-manager-operator`, part-of cert-manager-operator
- **Version skew:** OSSM 2.4+, Istio v1.10+, cert-manager Operator v1.3+
- **Downstream fork:** openshift/cert-manager-istio-csr (bindata in operator)

## Non-goals (selected)

- istio-csr only with supported OSSM versions
- CR delete does not remove deployment (re-evaluate post-GA)
- Automatic cleanup of `istio-ca-root-cert` ConfigMaps in deselected namespaces
- Namespace validation against service mesh config
- Hardened RBAC restricting ConfigMap creation to selected namespaces only

## Risks

- ConfigMap `istio-ca-root-cert` conflict when multiple Istio instances — mitigate via `istioDataPlaneNamespaceSelector`
- OLM upgrade when adding new owned CRD
- Operand version skew with OSSM v3 / Istio v1.24+
- Status conditions must reflect deployment readiness for operability

## Test plan (EP)

- Default and permuted IstioCSR configurations
- Upgrade/downgrade scenarios
- QE feedback window
