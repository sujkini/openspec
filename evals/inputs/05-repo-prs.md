# Input: Repo PRs — Istio CSR (CM-463 / OCPSTRAT-1974)

**Repository:** https://github.com/openshift/cert-manager-operator

## Feature PRs

| PR | Title | Merged |
|----|-------|--------|
| #220, #245 | CM-418, CM-419: Adds new istio-csr CRD and controller | 2025-02-12 |
| #226, #248, #250 | CM-423: E2E istio-csr controller + gRPC tests | 2025-02-25 – 2025-03-06 |
| #252, #254 | CM-521: Rebase with istio-csr v0.14 | 2025-03-11 |
| #303 | CM-680: Provision to configure istio clusterID | 2025-08-20 |
| #304 | CM-675: Rebase istio-csr with upstream v0.14.2 | 2025-08-14 |
| #305, #323 | CM-681: istioDataPlaneNamespaceSelector | 2025-10-09 |
| #310, #319 | CM-706: Revisits istiocsr API for GA release | 2025-10-07 |
| #312, #332 | CM-679: User-configurable CA certificate for Istio CSR | 2025-10-22 |
| #317, #322 | CM-639: Metrics service for istio-csr | 2025-10-08 |
| #363 | CM-826: Rebase istio-csr with upstream v0.15.0 | 2026-01-08 |
| #381 | CM-973: Fix SA label reconciliation and exist/update/event logic | 2026-04-01 |
| #427 | CM-1043: IstioCSR e2e + Service Mesh smoke tests | 2026-06-17 |

## Bug-fix PRs

| Bug | PR | Title |
|-----|-----|-------|
| CM-546 | #241 | Fix missing Ready condition despite successful deployment |
| CM-735 | #324, #330 | Fix IstioCSR cache sync race — unified manager cache |
| CM-769 | #345, #346 | Remove `format` library from IstioCSR CEL validation |
| CM-770 | #344, #347 | Revert shortname addition in istiocsr CRD (OLM upgrade) |
| CM-521 | #304 | Rebase istio-csr v0.14.2 (OSSM v3 integration) |
