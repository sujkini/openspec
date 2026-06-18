# Input: Original repo version (before Istio CSR feature)

**Repository:** https://github.com/openshift/cert-manager-operator

**Pre-feature reference:** `master` before IstioCSR CRD and controller (CM-418 / CM-419).

**Enhancement tracking:** CM-234 (EP), CM-463 (TP epic)

**Suggested pin:** Commit before merge of PR #220 / #245 (CM-418, CM-419: Adds new istio-csr CRD and controller) — 2025-02-12.

**Pre-feature state:**

- No `pkg/controller/istiocsr/` package
- No `istiocsrs.operator.openshift.io` CRD in bundle
- No `bindata/istio-csr/` static manifests
- No `EnableIstioCSR` in `setup_manager.go`

**Post-implementation paths:**

- `pkg/controller/istiocsr/` — controller-runtime reconcilers
- `pkg/operator/setup_manager.go` — unified manager registration
- `bindata/istio-csr/` — operand manifests (version via `hack/update-istio-csr-manifests.sh`)
- `api/v1alpha1/istiocsr_types.go` — IstioCSR API
- `test/e2e/istio_csr_test.go` — e2e coverage
