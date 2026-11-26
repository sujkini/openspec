# OpenSpec agent worker — runs the openspec agile/QE workflows end to end
# with the OpenAI Codex CLI on OpenShift CI.
#
# Built by the sujkini/openspec ci-operator config and promoted to
# oape/openspec-agent:openspec-agent-worker. Consumed by the
# openspec-agile-workflow and openspec-qe-workflow step-registry refs.
FROM registry.access.redhat.com/ubi9/go-toolset

USER 0

# System dependencies: git/make for operator builds, gh for GitHub operations,
# nodejs+npm for the Codex and openspec CLIs, python3.11 for telemetry.
RUN dnf install -y \
        git \
        make \
        curl \
        tar \
        gzip \
        python3.11 \
        python3.11-pip && \
    dnf install -y 'dnf-command(config-manager)' && \
    dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo && \
    dnf install -y gh && \
    dnf install -y nodejs npm && \
    dnf clean all

# OpenAI Codex CLI (non-interactive `codex exec` drives the workflows) and
# the openspec CLI (`openspec new change`, `openspec status`, ...).
RUN npm install -g @openai/codex @fission-ai/openspec

# oc + kubectl for the QE workflow cluster readiness gate and E2E execution.
RUN curl -fsSL https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/openshift-client-linux.tar.gz \
        -o /tmp/openshift-client-linux.tar.gz && \
    tar -C /usr/local/bin -xzf /tmp/openshift-client-linux.tar.gz oc kubectl && \
    rm -f /tmp/openshift-client-linux.tar.gz

# Python dependencies for the openspec telemetry modules
# (python -m openspec.telemetry.*).
RUN python3.11 -m pip install --no-cache-dir pyyaml tiktoken

# Bundle the openspec repo content needed at runtime. The runner
# (scripts/ci/run-openspec-workflow.sh) copies the scaffolding into the
# workspace repo it creates per run:
#   /opt/openspec-src/openspec/          -> workflow config, schemas, telemetry
#   /opt/openspec-src/commands/          -> /opsx-* command prompts
#   /opt/openspec-src/scripts/ci/        -> the CI runner itself
COPY openspec /opt/openspec-src/openspec
COPY .cursor/commands /opt/openspec-src/commands
COPY scripts/ci /opt/openspec-src/scripts/ci

# Configure git globally while still root, and ensure the home directory is
# writable for arbitrary UIDs (OpenShift runs containers as random UID).
RUN git config --global user.name "openshift-app-platform-shift-bot" && \
    git config --global user.email "267347085+openshift-app-platform-shift-bot@users.noreply.github.com" && \
    git config --global --add safe.directory '*' && \
    chmod -R g=u /opt/app-root/src && \
    chmod -R g=u /opt/openspec-src && \
    mkdir -p /workspace && chown 1001:0 /workspace && chmod g=u /workspace

ENV HOME=/opt/app-root/src \
    OPENSPEC_SRC=/opt/openspec-src

USER 1001

WORKDIR /workspace

CMD ["/opt/openspec-src/scripts/ci/run-openspec-workflow.sh"]
