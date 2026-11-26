# Edit the ARG defaults below and open a PR to trigger the openspec agile
# workflow run (/opsx-new -> /opsx-continue -> /opsx-apply) on OpenShift CI.
# CI will extract these values and pass them to the Codex CLI agent.
#
# You MUST also replace prow-workflow/jira-spec.md with the content of the
# Jira ticket referenced by JIRA_KEY — the CI agent has no Jira MCP access.
#
# The job only runs when this file changes: /test agile-workflow
FROM registry.access.redhat.com/ubi9/ubi-micro:9.6

# Jira ticket key (e.g. CM-830) or full URL (https://issues.redhat.com/browse/CM-830)
ARG JIRA_KEY="CM-830"
# Upstream repository the workflow plans against and raises the PR on
ARG TARGET_REPO="https://github.com/openshift/cert-manager-operator.git"
# Optional kebab-case change name (defaults to the lowercase ticket slug)
ARG CHANGE_NAME=""
# Set to "true" to skip validation/specs/repo-assessment/plan (lightweight tasks)
ARG FAST_TRACK="false"
# Optional Codex model / reasoning effort overrides (defaults come from CI config)
ARG MODEL=""
ARG EFFORT=""

RUN echo "JIRA_KEY=${JIRA_KEY}" > /params.env && \
    echo "TARGET_REPO=${TARGET_REPO}" >> /params.env && \
    echo "CHANGE_NAME=${CHANGE_NAME}" >> /params.env && \
    echo "FAST_TRACK=${FAST_TRACK}" >> /params.env && \
    echo "MODEL=${MODEL}" >> /params.env && \
    echo "EFFORT=${EFFORT}" >> /params.env

# The pasted Jira ticket content (required — replace the placeholder before
# opening the PR). The runner copies this into inputs/jira-spec.md.
COPY prow-workflow/jira-spec.md /jira-spec.md
