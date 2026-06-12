# Bug: OCPBUGS-57841

**Link:** https://issues.redhat.com/browse/OCPBUGS-57841

**Summary:** `<istio_project_name>` should be used in issuer.yaml example

**Symptom:** OpenShift documentation for Istio-CSR integration uses inconsistent placeholders (`istio-system` vs `<istio_csr_project_name>` vs `<istio_project_name>`) in Example IstioCSR CR, issuer.yaml, and verification steps.

**Root cause:** Documentation not aligned with parameterized namespace guidance.

**Fix:** Doc updates across 4.14+ branches — unify on `<istio_project_name>`.

**Doc:** https://docs.redhat.com/en/documentation/openshift_container_platform/4.14/html/security_and_compliance/cert-manager-operator-for-red-hat-openshift#cert-manager-operator-integrating-istio

**Type:** ops_docs — documentation
