# Input: Jira Epics — CM-463 (TP) + OCPSTRAT-1974 (GA)

## CM-463 — [TP] istio-csr integration for cert-manager

**Link:** https://redhat.atlassian.net/browse/CM-463

**Summary:** Integration of service mesh and cert-manager requires istio-csr agent to facilitate certificate management. Istio-csr agent needs to be productized and supported by Red Hat as an add-on component.

**Scope:** Dev-preview of productization and integration istio-csr with cert-manager operator for service-mesh integration testing and customer feedback.

**Acceptance criteria:**

1. Documentation of architecture and configuration
2. Documentation of use cases of integration with service mesh
3. CPaaS productization of istio-csr with cert-manager operator
4. UT test cases for updates to cert-manager operator
5. Dev-preview release for service mesh integration

## OCPSTRAT-1974 — [GA] istio-csr integration for cert-manager

**Link:** https://redhat.atlassian.net/browse/OCPSTRAT-1974

**Summary:** GA strategy epic for istio-csr integration (same functional scope as TP, graduation to GA).

**Linked development stories:** Stories linked directly under GA strat (implementation traceability via PRs):

| Key | Theme |
|-----|-------|
| CM-418, CM-419 | IstioCSR CRD + controller lifecycle |
| CM-423 | E2E istio-csr controller + gRPC CreateCertificate |
| CM-521 | Upstream istio-csr version bump (OSSM v3 compatibility) |
| CM-639 | Metrics Service for istio-csr |
| CM-675 / CM-826 | Rebase bindata to v0.14.2 / v0.15.0 |
| CM-679 | User-configurable CA certificate (`istioCACertificate`) |
| CM-680 | Configure istio clusterID |
| CM-681 | `istioDataPlaneNamespaceSelector` |
| CM-706 | GA API revisit |
| CM-1043 | IstioCSR e2e + Service Mesh smoke tests |

**EP link:** https://github.com/openshift/enhancements/blob/master/enhancements/cert-manager/istio-csr-controller.md
