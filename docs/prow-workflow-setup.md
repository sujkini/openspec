# OpenSpec Prow Workflow Setup

Reference documentation for the `agile-workflow` and `qe-workflow` CI jobs.
This file is **not consumed by CI directly** — it describes how the pipelines
are built and how end users trigger them.

## Overview

The openspec repo ships two on-demand Prow presubmits that run the openspec
agile workflow (`/opsx-new → /opsx-continue → /opsx-apply`) and the QE
workflow (`/opsx-e2e`) end to end on OpenShift CI, driven by the **OpenAI
Codex CLI** instead of an interactive editor:

| Job | Prow context | Trigger | Runs |
| --- | --- | --- | --- |
| `pull-ci-sujkini-openspec-main-agile-workflow` | `ci/prow/agile-workflow` | `/test agile-workflow` | Codex plans and implements a Jira change on a target operator repo, then raises a PR |
| `pull-ci-sujkini-openspec-main-qe-workflow` | `ci/prow/qe-workflow` | `/test qe-workflow` | Codex generates E2E tests for a PR, provisions an AWS cluster, deploys + runs the tests, then raises a PR with the tests |

## User flow

1. Create a branch on `sujkini/openspec`.
2. Edit the ARG defaults in `prow-workflow/agile-workflow.Dockerfile` or
   `prow-workflow/qe-workflow.Dockerfile`.
3. For the agile workflow, replace `prow-workflow/jira-spec.md` with the
   content of the Jira ticket referenced by `JIRA_KEY` (there is no Jira MCP
   on CI — this file is the spec source).
4. Open a PR. The matching job triggers automatically because of
   `run_if_changed: ^prow-workflow/(agile|qe)-workflow`. Re-run manually with
   `/test agile-workflow` or `/test qe-workflow`.
5. Watch the job on Prow. The log streams the Codex session; artifacts
   (`openspec-changes-<name>.tar.gz`, telemetry reports, codex session logs)
   are attached to the job. The job log prints `PR_CREATED: <url>` lines for
   every PR the workflow raised on the target repo.

### Agile workflow inputs (`prow-workflow/agile-workflow.Dockerfile`)

| ARG | Required | Description |
| --- | --- | --- |
| `JIRA_KEY` | yes | Jira ticket key or URL |
| `TARGET_REPO` | yes | Upstream repo the workflow implements against and PRs to |
| `CHANGE_NAME` | no | Kebab-case change name (defaults to the ticket slug) |
| `FAST_TRACK` | no | `true` skips validation/specs/repo-assessment/plan |
| `MODEL` / `EFFORT` | no | Codex model / reasoning-effort overrides |

Plus `prow-workflow/jira-spec.md` with the pasted ticket content.

### QE workflow inputs (`prow-workflow/qe-workflow.Dockerfile`)

| ARG | Required | Description |
| --- | --- | --- |
| `PR_URL` | one of PR_URL/ADR_URL/EP_URL | PR to generate E2E tests for (PR/Combined Mode) |
| `ADR_URL` / `EP_URL` | see above | Design documents (Design or Combined Mode) |
| `CHANGE_NAME` | no | Artifacts directory name (defaults to `pr-<n>-e2e`) |
| `PHASE` | no | Phase number for phase-iterative changes |
| `MODEL` / `EFFORT` | no | Codex model / reasoning-effort overrides |

Design Mode (ADR/EP without PR) generates the plan and test code but performs
no execution and raises no PR.

## Architecture

1. **Input images** — `prow-workflow/agile-workflow.Dockerfile` and
   `prow-workflow/qe-workflow.Dockerfile` are dummy images that bake the
   user's ARGs into `/params.env` (plus `/jira-spec.md` for agile). They are
   built from the PR, never promoted.
2. **Worker image** — `images/openspec-agent-worker.Dockerfile` (go-toolset
   base + Codex CLI + openspec CLI + gh + oc) bundles the openspec
   scaffolding and the runner. Promoted to `oape/openspec-agent:openspec-agent-worker`
   by the postsubmit images job on merge.
3. **Step registry refs** (in `openshift/release`):
   - `openspec-mint-gh-token` — mints a GitHub App installation token for
     `openshift-app-platform-shift-github-bot` (reuses the gh-token-minter
     image promoted from `openshift-eng/oape-ai-e2e`).
   - `openspec-agile-workflow` — runs
     `scripts/ci/run-openspec-workflow.sh agile` with the
     `oap-lts-codex-sa` OpenAI API key.
   - `openspec-qe-workflow` — runs `scripts/ci/run-openspec-workflow.sh qe`;
     expects a cluster kubeconfig at `${SHARED_DIR}/kubeconfig`.
4. **Job steps** —
   - agile: `extract-params` → `openspec-mint-gh-token` → `openspec-agile-workflow`
   - qe: `extract-params` → `openspec-mint-gh-token` → `ipi-aws-pre`
     (provisions a cluster) → `openspec-qe-workflow` → `ipi-aws-post`
     (deprovisions).

## Runner behaviour (`scripts/ci/run-openspec-workflow.sh`)

- Loads the OpenAI API key from `/var/run/codex-openai-api-key/openai_api_key`
  (`oap-lts-codex-sa` secret) and the GitHub App token from
  `${SHARED_DIR}/gh-token`.
- Forks + clones the target repo (agile) or checks out the PR (qe), installs
  the bundled openspec scaffolding into the clone, and seeds
  `openspec/config.yaml`.
- Builds the initial prompt from `.cursor/commands/opsx-new.md` /
  `opsx-e2e.md` (frontmatter stripped) plus a non-interactive CI context that
  pre-answers the approval gates (PR creation approved, Jira Story creation
  skipped, QE local execution yes on the provided cluster).
- Drives `codex exec --sandbox danger-full-access` and resumes the session
  (`codex exec resume --last`) for a bounded number of rounds until the
  workflow completes (a created PR verifies via `gh pr view`).
- Archives `openspec/changes/<name>/`, telemetry reports, and Codex session
  logs to the job artifacts and writes `junit_openspec.xml`.

## Prerequisites for target repos

- `agents.md` and `harness-evals/constitution.md` at the repo root (hard
  guardrails in the openspec workflow — the run stops if missing).
- `qe-e2e/qe-behaviour.md` recommended for QE (Sections 3a/3b).
- The `openshift-app-platform-shift-github-bot` GitHub App installed with
  write access so it can fork and raise PRs.

## Notes

- Jobs are pinned to the `build13` build cluster, where the
  `oap-lts-codex-sa` and `openshift-app-platform-shift-github-bot` secrets
  live.
- The worker image used by a run is the latest **promoted** one, so changes
  to the runner or prompts land on `main` (postsubmit promotion) before user
  workflow PRs pick them up. Use `/pj-rehearse` to test in-flight changes.
- The QE job provisions an AWS cluster via the `ipi-aws` chain; the OCP
  version pinned in the ci-operator config (`releases.latest`) controls the
  installed payload.
