# Input: User stories — Istio CSR (CM-463 / OCPSTRAT-1974)

**Strategy:** OCPSTRAT-1974 | **TP Epic:** CM-463

## EP user stories (selected)

- Administrator: deploy istio-csr as day-2 operation
- Administrator: configure istio-csr features selectively
- Administrator: uninstall without disrupting cert-manager (limited teardown)
- Security engineer: identify all artefacts via labels
- SRE: status conditions and messages for failure diagnosis
- Service mesh admin: use istio-csr endpoint with pre-installed mesh
- SRE: collect istio-csr metrics
- Security engineer: restrict ConfigMap provisioning via namespace selector
- Administrator: configure cluster ID for CSR verification

## Implementation stories (from GA strat / PR traceability)

| Key / PR | Story theme |
|----------|-------------|
| CM-418, CM-419 / PR #220, #245 | IstioCSR CRD + controller lifecycle |
| CM-423 / PR #226, #248, #250 | E2E istio-csr + gRPC certificate flow |
| CM-521 / PR #252, #254, #304 | Operand version bump for OSSM compatibility |
| CM-639 / PR #317, #322 | Metrics Service for istio-csr |
| CM-679 / PR #312, #332 | `istioCACertificate` ConfigMap support |
| CM-680 / PR #303 | `server.clusterID` configuration |
| CM-681 / PR #305, #323 | `istioDataPlaneNamespaceSelector` |
| CM-706 / PR #310, #319 | GA API revisit |
| CM-1043 / PR #427 | IstioCSR e2e + Service Mesh smoke tests |

## EP → story gaps (from bugs)

| Gap | Bug |
|-----|-----|
| Unified manager cache for addon controller | CM-735 |
| Ready condition when deployment healthy | CM-546 |
| OLM upgrade path for new CRD | CM-770 |
| Operand bindata version vs OSSM minimum | CM-521 |
| Docs placeholder consistency | OCPBUGS-57841 |
