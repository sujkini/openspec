# Edit the ARG defaults below and open a PR to trigger the openspec QE
# workflow run (/opsx-e2e) on OpenShift CI. CI will extract these values
# and pass them to the Codex CLI agent.
#
# The job provisions a temporary OpenShift cluster on AWS (ipi-aws), has the
# agent generate E2E tests, deploys the operator and runs the generated
# tests against the cluster, then raises a PR with the generated tests from
# the openshift-app-platform-shift-github-bot fork.
#
# The job only runs when this file changes: /test qe-workflow
FROM registry.access.redhat.com/ubi9/ubi-micro:9.6

# Upstream PR to generate E2E tests for (PR Mode), e.g.
# https://github.com/openshift/cert-manager-operator/pull/123
ARG PR_URL=""
# Optional ADR document (path-or-URL). PR + ADR/EP => Combined Mode.
ARG ADR_URL=""
# Optional Enhancement Proposal (path-or-URL). PR + ADR/EP => Combined Mode.
ARG EP_URL=""
# Without PR_URL: Design Mode (plan + code only, no execution/push).
# Optional kebab-case change name for the artifacts directory
ARG CHANGE_NAME=""
# Optional phase number for phase-iterative changes
ARG PHASE=""
# Optional Codex model / reasoning effort overrides (defaults come from CI config)
ARG MODEL=""
ARG EFFORT=""

RUN echo "PR_URL=${PR_URL}" > /params.env && \
    echo "ADR_URL=${ADR_URL}" >> /params.env && \
    echo "EP_URL=${EP_URL}" >> /params.env && \
    echo "CHANGE_NAME=${CHANGE_NAME}" >> /params.env && \
    echo "PHASE=${PHASE}" >> /params.env && \
    echo "MODEL=${MODEL}" >> /params.env && \
    echo "EFFORT=${EFFORT}" >> /params.env
