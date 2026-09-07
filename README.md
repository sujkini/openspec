# OpenSpec Agile Workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema for **gated, Jira-driven, spec-first development** with AI-assisted planning and implementation. Supports two execution strategies (**phase-iterative** and **one-shot**), two code-generation modes (**ai-helpers** and **direct**), per-phase Jira traceability, and a post-CI E2E test generation pipeline.

> **After completing a change (and E2E, if applicable), run `/opsx-archive` to capture your feedback and time savings.** This is the single, mandatory place all feedback is collected — `/opsx-apply` and `/opsx-e2e` never prompt for it. Run `/opsx-e2e` *before* archiving if this change needs E2E coverage; once archived, the change moves out of the live directory. See [Telemetry & Metrics](#telemetry--metrics).

---

## Quick Start

### 1. Clone & Install

```bash
rm -rf /tmp/openspec-workflow
git clone -b openspec-v1-restructured https://github.com/sujkini/openspec.git /tmp/openspec-workflow
/tmp/openspec-workflow/install.sh /path/to/your-operator-repo
```

This copies `openspec/`, `.cursor/`, `eval-generation/`, and `dashboard/` into your project, installs the OpenSpec CLI, and sets up dependencies. Use `--no-dashboard` to skip the dashboard.

### 2. Configure execution mode (`openspec/config.yaml`)

```yaml
# openspec/config.yaml
flags:
  codegen_mode: ai-helpers        # or: direct
  task_execution_mode: phase-iterative  # or: one-shot
  auto_approve: true              # auto-approve artifacts + per-task code; phase/PR/Jira gates always prompted
```

| Flag | Options | Purpose |
|------|---------|---------|
| `codegen_mode` | `ai-helpers` / `direct` | Code generation strategy |
| `task_execution_mode` | `phase-iterative` / `one-shot` | How tasks are grouped and PRs raised |
| `auto_approve` | `true` / `false` | Auto-approve artifacts and per-task code approval. Phase approval, PR creation, and Jira creation are NEVER auto-approved. |

### 3. Add operator documentation

**a) `agents.md` at repo root:**

Create `agents.md` at your operator repo root with your agent routing, architecture patterns, and test exemplar.

**b) Harness docs in `harness-evals/harness-docs/`:**

```bash
cp /path/to/your-docs/*.md harness-evals/harness-docs/
```

These docs (architecture guides, coding conventions, testing patterns) are used by `/opsx-constitute` to generate your constitution.

**c) Generate constitution:**

```
/opsx-constitute
```

This reads `harness-evals/harness-docs/` and generates `harness-evals/constitution.md`.

**d) Set up E2E context in `qe-e2e/` (recommended for E2E test generation):**

Create a `qe-e2e/` directory at your operator repo root with operator-specific E2E context:

```bash
mkdir -p qe-e2e
```

Copy and fill in the template from `openspec/openspec/schemas/openspec-agile-workflow/e2e-workflow/qe-behaviour.md` Sections 3a/3b:

```bash
# Create your operator-specific qe-behaviour.md
cp openspec/openspec/schemas/openspec-agile-workflow/e2e-workflow/qe-behaviour.md qe-e2e/qe-behaviour.md
# Then edit qe-e2e/qe-behaviour.md — fill in Sections 3a and 3b with your operator's details
```

See `docs/qe-behaviour-example-ztwim.md` for a complete filled-in example. If `qe-e2e/` is not present, `/opsx-e2e` will still work but will derive context from `agents.md` with reduced accuracy.

### 4. Start the Dashboard

```bash
cd /path/to/your-operator-repo
./dashboard/start.sh
```

Installs deps on first run, starts the FastAPI backend (port 8000) and React frontend (port 5173). Open http://localhost:5173. The backend polls `openspec/changes/` for telemetry data written by `/opsx-*` commands. See `dashboard/README.md` for details.

### 5. Restart Cursor

Restart Cursor so slash commands load from `.cursor/commands/`.

### 6. Run your first change

```
/opsx-new PROJ-123
```

### 7. Archive and capture feedback

After implementation is complete (and `/opsx-e2e` has run, if this change needs E2E coverage), run:

```
/opsx-archive
```

This archives the change and **collects mandatory feedback**: estimated manual hours (time saved), a satisfaction rating, comments, and story points delivered — written to `user-feedback.md` and `metrics-report.json` inside the archived change directory. If this change ran `/opsx-e2e`, it also collects **QE feedback** (QE time saved, QE story points, QE feedback) into `qe-metrics.json` — skipped automatically if E2E was never run. This data is used for continuous monitoring and performance review (MON-01 compliance). See [Telemetry & Metrics](#telemetry--metrics) for details.

---

## Task Execution Modes

### Phase-Iterative (default)

Tasks are executed one phase at a time. After each phase completes:
- A draft PR is raised scoped to that phase
- A Jira Story ticket is created for the phase (linked to the epic)
- The user can trigger `/opsx-e2e --phase N` after CI passes
- `/opsx-continue` generates next-phase tasks

### One-Shot

All tasks across all phases are executed sequentially in a single run. A single PR is raised at the end covering the entire implementation. After CI passes, trigger `/opsx-e2e` for the final PR.

---

## E2E Exclusion Policy

E2E phases and tasks are **excluded from OAPE planning, task generation, and code generation**. They are handled separately by the `/opsx-e2e` post-CI pipeline instead.

A phase or task is classified as e2e when any of these match:
- Assigned Agent is `Testing_Agent`
- Title/objective contains "e2e" or "end-to-end"
- Target files are under `test/` (e2e, ginkgo, integration paths)
- Acceptance criteria references `make test-e2e`

E2e coverage is still documented in `plan.md` §6 (Verification matrix) for reference but is never generated during `/opsx-apply`.

---

## E2E Test Generation (Post-CI)

After a phase or final PR is raised and CI passes, trigger the E2E pipeline:

```
/opsx-e2e <change-name> --phase N    # phase-iterative: specific phase
/opsx-e2e <change-name>              # one-shot: final PR
/opsx-e2e --pr <URL>                 # direct PR URL
/opsx-e2e --adr <path-or-URL>        # design mode (plan only, no execute/push)
/opsx-e2e --ep <path-or-URL>         # enhancement proposal (same as ADR)
/opsx-e2e --pr <URL> --adr <path>    # combined mode (full pipeline + design context)
```

### Input Modes

| Input | Mode | Pipeline |
|-------|------|----------|
| **PR only** | PR Mode | Full: pre-analysis → plan → consolidation → codegen → execute → push |
| **ADR or EP only** | Design Mode | Plan-only: pre-analysis → plan → consolidation → codegen → STOP |
| **ADR/EP + PR** | Combined Mode | Full pipeline with enriched design context |
| **Change name** | Change Mode | Resolves PR from `state.yaml`, then runs Full |

**Design Mode** generates the test plan and code but does NOT execute or push — there is no branch to push to. Use this to review E2E coverage before a PR exists.

### Pipeline Stages

The pipeline runs five stages, each with a user approval gate:

| Stage | Output | Description |
|-------|--------|-------------|
| 1. Pre-analysis | `e2e-analysis.md` | Scoping analysis from PR diff / ADR + operator context |
| 2. Test plan | `test-plan.md` | Full tiered plan with traceability |
| 3. Consolidation | `revised-test-plan.md` | Journey consolidation to configured limit |
| 4. Code generation | `*_test.go` | Executable Ginkgo/Go test code |
| 5. Execute | Push + run | Commit tests to PR branch, optionally execute (skipped in Design Mode) |

All artifacts are written to `openspec/changes/<name>/e2e/`.

### Context-Narrowing Architecture

The E2E pipeline uses a **context-narrowing** approach to optimize token usage and avoid redundant context:

```
Stage 1 (Pre-Analysis) — READS ALL CONTEXT:
  - agents.md (full)
  - constitution.md (full)
  - qe-e2e/qe-behaviour.md (operator-specific deployment + quality gates)
  - harness-docs/*.md
  - ADR/PR diff
  → PRODUCES: e2e-analysis.md (embeds deployment context, quality gates, constraints)

Stage 2 (Test Plan) — NARROW CONTEXT:
  - e2e-analysis.md (carries all scoping decisions + embedded operator context)
  - Generic QE writing rules (Sections 1-5)
  → PRODUCES: test-plan.md

Stage 3 (Consolidation) — MINIMAL CONTEXT:
  - test-plan.md + config.yaml max_test_cases
  → PRODUCES: revised-test-plan.md

Stage 4 (Code Generation) — TARGETED CONTEXT:
  - revised-test-plan.md
  - agents.md (helpers + code style sections ONLY)
  - Target repo test/e2e/ patterns
  → PRODUCES: *_test.go files
```

All operator context is consumed once in Stage 1 and compressed into `e2e-analysis.md`. Downstream stages read the compressed output instead of re-reading raw operator files.

### What each operator repo must have for E2E (`qe-e2e/`)

Each operator repo should maintain a `qe-e2e/` directory at the repo root (alongside `agents.md`) containing operator-specific E2E context:

```
<operator-repo>/
├── agents.md                        # Agent routing, architecture (required)
├── qe-e2e/                          # Operator-specific E2E context (recommended)
│   └── qe-behaviour.md             # Deployment context + quality gates
└── harness-evals/
    ├── constitution.md              # Governance guardrails (required)
    └── ...
```

**`qe-e2e/qe-behaviour.md`** must contain two sections filled in by the operator team:

**Section 3a — Operator Deployment Context:**
- Deployment method (OLM / Helm / Manual)
- Operator namespace
- CSV/Deployment name pattern
- Operand CR kinds and default names
- Config patching method (how to change operator config at runtime)
- Scaling method
- Things the agent must NEVER do (e.g., "Never use `oc scale deployment` — OLM will revert it")

**Section 3b — Operator Quality Gates:**

A table of domain-specific quality gates that E2E tests must cover, organized by category:

| Category | What to define |
|----------|---------------|
| Operator Lifecycle | Installation, health, recovery observables |
| Operand Health | One row per operand CR with ready conditions |
| Core Functionality | Domain-specific behavior gates (operator team fills in) |
| Security | RBAC boundaries, SCC/PSA, privilege constraints |
| Deployment Integration | OLM Upgradeable, Helm hooks, etc. |
| Resilience | Pod recovery, config reconciliation behavior |
| Error Paths (optional) | Expected behavior on dependency/config failures |
| Performance (optional) | Numeric thresholds (restart windows, SLAs) |

A generic template with placeholders is shipped with OpenSpec at `openspec/openspec/schemas/openspec-agile-workflow/e2e-workflow/qe-behaviour.md`. Copy Sections 3a/3b from there into your `qe-e2e/qe-behaviour.md` and fill in. See `docs/qe-behaviour-example-ztwim.md` for a complete filled-in example.

**If `qe-e2e/` is not present:** `/opsx-e2e` still works — it derives deployment context from `agents.md` and quality gates from `constitution.md`. The test plan will be less precise but functional.

### Generic QE Rules (shipped with OpenSpec)

The generic QE behavioural rules (Sections 1-5) ship with OpenSpec at `{schema_root}/e2e-workflow/qe-behaviour.md` and apply to all operators:

1. **Ask Before Assuming** — surface ambiguity early, don't fabricate requirements
2. **Precision Over Volume** — one test per observable behavior, no padding
3. **Surgical Scope** — test only what the change covers, nothing speculative
4. **Traceability Always** — every test traces to an ADR section or PR diff location
5. **Self-Verify Before Outputting** — run quality gates before returning any plan

---

## Jira Integration

### Per-Phase Jira Tickets (phase-iterative mode)

After tasks for a phase are approved, a Jira Story ticket is created:
- Linked to the epic from `inputs/jira.yaml`
- Summary: `[Phase N] <phase title>`
- Description includes phase goal, dependencies, target files, task manifest, and acceptance criteria
- Stored in `inputs/jira.yaml` → `plan_phases[]`

If Jira creation fails, the phase is marked `PENDING` and retried once at `/opsx-apply` start.

---

## Configuration

After installation, set up the following:

| Location | What to provide |
|----------|----------------|
| **`agents.md`** (repo root) | Agent routing, repository architecture, test patterns, verification matrix |
| **`qe-e2e/qe-behaviour.md`** (repo root) | Operator-specific E2E context: deployment model + quality gates (recommended for `/opsx-e2e`) |
| **`harness-evals/harness-docs/`** | Operator documentation (used by `/opsx-constitute` to generate constitution) |
| **`harness-evals/constitution.md`** | Coding guardrails, CI gates, governance rules (generated by `/opsx-constitute`) |
| **`harness-evals/evals/`** | Stage eval cases — quality gates (populated by `/eval-loop` or manually) |

And populate the `harness-evals/` directory:

| Directory | What to place |
|-----------|---------------|
| **`harness-evals/harness-docs/`** | Operator documentation (architecture guides, coding conventions, testing patterns). Used by `/opsx-constitute` to generate constitution.md |
| **`harness-evals/evals/`** | Stage eval cases (populated by `/eval-loop` or placed manually). Used as quality gates during `/opsx-continue` and `/opsx-apply` |

These are the **only operator-specific files**. Everything else is generic.

### Harness-Evals Structure

```
harness-evals/
├── harness-docs/                    # Operator documentation (sole source for /opsx-constitute)
│   ├── architecture.md              # System design, component relationships
│   ├── coding-conventions.md        # Style guides, patterns, naming
│   ├── testing-patterns.md          # Test strategies, exemplars, fixtures
│   └── ...                          # Any .md files — all are read
│
├── constitution.md                  # Generated by /opsx-constitute (governance guardrails)
│
└── evals/                           # Stage eval cases (quality gates)
    ├── repo-assessment_eval.yaml    # Repo assessment scoring
    ├── plan_eval.yaml               # Plan quality scoring
    ├── tasks_eval.yaml              # Task breakdown scoring
    └── code-generation_eval.yaml    # Per-task code quality scoring
```

- **Evals are optional.** If not present, eval scoring is skipped and the workflow proceeds with verification/tests and user approval only.
- **Harness-docs are required for `/opsx-constitute`.** The command will stop if no documentation is found.
- **`/eval-loop` auto-syncs** generated evals to `harness-evals/evals/`.
- **`agents.md`** lives at the operator repo root (not inside harness-evals).

Your `agents.md` (at repo root) should define:
- **Repository layout** — directory structure, key packages
- **Architecture patterns** — controller frameworks, reconciliation flow
- **Test exemplar** — how tests are structured (mocks, table-driven patterns, file naming)
- **Execution agent routing** — agent IDs and which paths/packages they own
- **Per-task verification matrix** — `make` targets and `go test` commands per task type

---

## Running the Workflow

### Start a change

```
/opsx-new PROJ-123
```

### Progress through artifacts

```
/opsx-continue              → validation.json      [approve]
/opsx-continue              → specs.md             [approve]
/opsx-continue              → repo-assessment.md   [approve]
/opsx-continue              → plan.md              [approve] (requires harness-evals/constitution.md)
/opsx-continue              → tasks.md             [approve] (+ Jira phase ticket in phase-iterative)
```

Each artifact is:
1. Generated from the template
2. Evaluated against stage evals (skipped if `harness-evals/evals/` has no eval file for that stage)
3. Refined if needed
4. Presented for your approval

If you **reject**, the agent refines and re-runs evals until you approve. Previously approved artifacts stay immutable.

### Implement tasks

```
/opsx-apply                 → task T1 [approve] → task T2 [approve] → … → phase PR → next phase
```

The implementation flow depends on `codegen_mode` in `openspec/config.yaml`:

**ai-helpers mode** (`codegen_mode: ai-helpers`):
1. Compose `design-bundle.md` scoped to that task
2. Resolve one OAPE command (or manual work)
3. Run in fork working copy (or project cwd in working-folder mode)
4. Verify against acceptance criteria
5. Run code-generation evals → refine code (max 2 passes)
6. Present task summary + scorecard → user approval
7. On approve: mark task complete, next task

**direct mode** (`codegen_mode: direct`):
1. Read context files (agents.md, constitution.md, specs, plan, repo-assessment)
2. Implement code directly via FILE OPERATIONS
3. Verify against acceptance criteria
4. Present task summary → user approval
5. On approve: mark task complete, next task

### Generate E2E tests (post-CI)

```
/opsx-e2e <change-name> --phase N
```

### Archive

```
/opsx-archive               → archive the change
```

---

## Telemetry & Metrics

OpenSpec keeps **development metrics** and **QE/E2E metrics** in two separate,
file-based reports — no database, no server. Both are regenerated automatically
after every relevant hook fires.

| | Development | QE / E2E |
|---|---|---|
| Events | `openspec/changes/<name>/telemetry/events.jsonl` | `openspec/changes/<name>/telemetry/e2e-events.jsonl` |
| Report | `openspec/changes/<name>/telemetry/metrics-report.json` | `openspec/changes/<name>/telemetry/qe-metrics.json` |
| Own tokens-in/out + cost | ✓ | ✓ |
| Generated by | `/opsx-new`, `/opsx-continue`, `/opsx-apply` (throughout the workflow) | `/opsx-e2e` (throughout the E2E pipeline) |
| Completeness flag | `report_status.complete` | `qe_report_status.complete` |

**Feedback is collected exactly once, centrally, by `/opsx-archive`** — not
mid-workflow. Neither `/opsx-apply` nor `/opsx-e2e` ever prompts for
time-saved, satisfaction, or story points; `/opsx-archive` is the single
source of truth for that data, asked right before the change directory is
moved into `openspec/changes/archive/`.

`/opsx-archive` always asks the **development** questions (mandatory, every
archive):
- Estimated manual effort (time savings)
- Satisfaction rating (1–5)
- Comments
- **Story points delivered** — mandatory; `metrics-report.json` is marked
  `report_status.complete: false` until it's recorded

`/opsx-archive` additionally asks the **QE** questions, but **only if this
change ran `/opsx-e2e` at least once** (detected by the presence of
`telemetry/e2e-events.jsonl`; skipped silently otherwise):
- QE time saved (%)
- **QE story points delivered** — mandatory when E2E ran; `qe-metrics.json`
  is marked `qe_report_status.complete: false` until it's recorded
- QE feedback

Both reports also carry IST-formatted timestamps for when the work started
and finished: `run.started_at_display` / `run.archived_at_display` in
`metrics-report.json`, and `qe_started_at_display` / `qe_completed_at_display`
in `qe-metrics.json` (the latter spans the earliest `/opsx-e2e` run to the
latest, since phase-iterative changes may run E2E once per phase).

The dashboard (`./dashboard/start.sh`) polls `openspec/changes/` and reads
`metrics-report.json` for its live view — see `dashboard/README.md` for details.

### Cost optimization: non-agentic generation via `openspec.llm_gen`

`validation`, `specs`, `plan`, and `tasks` can each generate **outside** the
Cursor agent session — a plain Python script (`openspec.llm_gen`) reads the
exact same closed bundle the agent would have read, calls an LLM API directly
with your own API key, writes the artifact, and runs a deterministic
structural gate before handing back a one-line JSON verdict for the agent to
resume on. `repo-assessment` and `implementation` are **never** eligible —
they require real repository discovery/tool use and always stay agentic.

**Why this saves tokens without a quality trade-off:** the savings come from
removing the *agent-loop overhead* (system prompt, tool schemas,
chain-of-thought, repeated context reloads across turns) — not from
downgrading the model. Configure the same (or an even stronger) model for
generation in `credentials.llm.model`.

**Enabled by default, per stage** in `openspec/config.yaml` (each flag is
independently reversible — set a stage to `agent` any time, with zero code
change, to opt just that one stage back into the agent session):

```yaml
credentials:
  llm:
    provider: anthropic              # anthropic | openai | vertex | anthropic_vertex
    model: ""                        # generation model (validation/specs/plan/tasks) — keep as strong as the agent
    judge_model: ""                  # scoring/report model (stage_eval/code_eval_score/reports) — may be cheaper
    api_key_env: OPENSPEC_LLM_API_KEY  # set this env var — never put the raw key in this file (unused for vertex/anthropic_vertex)
    project_id: ""                    # vertex and anthropic_vertex only
    location: "us-central1"           # vertex and anthropic_vertex only
    max_output_tokens: 8000
    temperature: 0.2
    max_retries: 2

flags:
  generation_runtime:
    validation: script       # -> agent to fall back to in-agent generation for this stage
    specs: script
    plan: script
    tasks: script
    stage_eval: script       # scoring+refinement for repo-assessment/plan/tasks
    code_eval_score: script  # code-generation eval scoring only (build/test/verify always run for real)
    reports: script          # implementation-report / deviation-observed / <artifact>_evaluation_report
    feedback: script         # regeneration on user-rejection feedback (validation/plan/tasks)
```

| `provider` | Auth | Notes |
|---|---|---|
| `anthropic` | API key (`api_key_env`) | Direct Anthropic API |
| `openai` | API key (`api_key_env`) | Direct OpenAI API |
| `vertex` | ADC (`gcloud auth application-default login`, no API key) | Gemini models via Vertex AI; needs `project_id` + `location` |
| `anthropic_vertex` | ADC (`gcloud auth application-default login`, no API key) | Claude models on Vertex AI Model Garden; needs `project_id` + `location`, and **`model`/`judge_model` set explicitly** to the model ID enabled in your Vertex deployment (current-generation models use dateless IDs, e.g. `claude-opus-5` / `claude-sonnet-5`; older models need a dated suffix like `claude-3-5-sonnet-v2@20241022`) — there's no safe generic default to guess for this provider |

Install the SDK matching your chosen provider (see
`openspec/llm_gen/requirements.txt`): `pip install anthropic` (covers both
`anthropic` and `anthropic_vertex`), `pip install openai`, or
`pip install google-cloud-aiplatform` (`vertex` only).

`/opsx-continue` and `/opsx-apply` dispatch to `openspec.llm_gen` automatically
for any stage whose flag is `script` (the default) — see the
"Generation-runtime dispatch" notes in `.cursor/commands/opsx-continue.md`
and `.cursor/commands/opsx-apply.md`. **Set `OPENSPEC_LLM_API_KEY` (or your
configured `api_key_env`) before starting the workflow** — if it's missing,
every script call fails closed (`ok: false`) and the workflow automatically
escalates that stage to in-agent generation instead, so nothing breaks, but
you also won't get the token savings until the key is set. You can also
invoke the script directly:

```bash
python -m openspec.llm_gen.run --stage validation --change "<name>"
python -m openspec.llm_gen.run --stage plan --change "<name>"
```

**Fail-closed, always:** on invalid output or a failed structural gate, the
script retries the same call (up to `credentials.llm.max_retries`) with the
failures fed back into the prompt. If still failing, it returns `ok: false`
with a `reason` — the workflow escalates that one artifact to the agent or
halts; it never silently accepts a broken artifact.

**New deterministic structural gates** (parity with the existing
`tasks_structural.py`, now applied to every generated artifact):

```bash
python -m openspec.validators.validation_schema --change "<name>"
python -m openspec.validators.specs_structural --change "<name>"
python -m openspec.validators.plan_structural --change "<name>"
python -m openspec.validators.tasks_structural --change "<name>"
```

**Real token accounting:** direct API calls report exact `tokens_in`/`tokens_out`
from the provider response, written to
`openspec/changes/<name>/telemetry/llm-usage/<artifact-id>.json`.
`openspec.telemetry.tokens` prefers this exact figure over the tiktoken
estimate whenever it is present, so `metrics-report.json` totals are exact
for script-generated artifacts and estimated (as before) for agent-generated
ones.

**Compare before/after:** run the same Jira ticket once with a stage's flag
set to `agent` and once set to `script`, then diff
`eval-results/<artifact-id>.yaml` scores and `metrics-report.json` →
`global_health.total_tokens_consumed` (plus the artifact's row in
`phases[]`). The acceptance bar for keeping a stage on `script` is eval-score
parity or better versus the agentic baseline — not just a lower token count.
See `cost-optimization-stratergy.md` for the full design rationale.

### Publishing metrics to the cross-operator dashboard

```
/opsx-publish-metrics [change-name]
```

Standalone command (not auto-triggered by `/opsx-archive`) that forks
[anandkuma77/open-spec-dashboard](https://github.com/anandkuma77/open-spec-dashboard)
via the `user-github` MCP server, branches, and opens a PR adding this change's
`metrics-report.json` (and `qe-metrics.json`, if this change ran `/opsx-e2e`) under
`data/open-spec-matrics/operators/<operator>/`. The operator folder is derived
automatically from `metrics-report.json → operator_name`. Publishing doesn't require
`report_status.complete`/`qe_report_status.complete` to be `true` — it warns on
incomplete data but doesn't block. Note that merging the resulting PR does not
automatically update the live dashboard; the dashboard repo owner must separately
re-run its `Generate Processed Metrics` GitHub Action.

---

## Working Modes

### Mode A: Working-folder mode (local code changes)

Use when your Cursor workspace IS the operator repo.

When prompted for target repo, tell the agent: **"use this as the working directory"**
- Code changes happen directly in your working directory
- No fork URL needed, no draft PR

### Mode B: Fork mode (draft PR)

When prompted, provide:
- **Target repo URL** — before repo-assessment
- **Fork repo URL** — before `/opsx-apply`

The agent clones your fork, implements task-by-task, and opens a draft PR.

---

## Cursor Commands

### Forward workflow

| Command | Purpose |
|---------|---------|
| `/opsx-constitute` | Generate constitution.md from harness-docs |
| `/opsx-new PROJ-123` | Start a change from a Jira key |
| `/opsx-continue` | Create next artifact; eval gate; approval |
| `/opsx-apply` | Implement tasks — one at a time, approval after each |
| `/opsx-e2e` | Generate E2E tests for a phase/final PR after CI passes |
| `/opsx-archive` | Archive a completed change |
| `/opsx-publish-metrics` | Publish metrics-report.json / qe-metrics.json to open-spec-dashboard as a PR |
| `/opsx-explore` | Explore ideas without creating artifacts |

### OAPE commands (ai-helpers mode only, during `/opsx-apply`)

| Command | When |
|---------|------|
| `/oape:api-generate` | API_Agent task |
| `/oape:api-generate-tests` | API_Agent verification task |
| `/oape:api-implement` | OperatorController_Agent task |

These commands are **not used** when `codegen_mode: direct`.

### Retrospective eval loop

| Command | Purpose |
|---------|---------|
| `/eval-loop` | Improve evals from a completed feature bundle |

---

## Configuration (`openspec/config.yaml`)

Key flags you can tune:

```yaml
flags:
  codegen_mode: ai-helpers              # "ai-helpers" or "direct"
  task_execution_mode: phase-iterative  # "phase-iterative" or "one-shot"
  auto_approve: true                    # auto-approve artifacts + per-task code; phase/PR/Jira gates always prompted
  max_feedback_rounds: 3
  exit_on_all_tasks_complete: true
  generation_runtime:                   # per-stage agent | script — see "Cost optimization" below
    validation: script
    specs: script
    plan: script
    tasks: script
    stage_eval: script
    code_eval_score: script
    reports: script
    feedback: script

credentials:
  llm:                                  # only used when a generation_runtime flag above is "script"
    provider: anthropic                 # anthropic | openai | vertex
    api_key_env: OPENSPEC_LLM_API_KEY
```

| Flag | Default | What it does |
|------|---------|--------------|
| `codegen_mode` | `ai-helpers` | Code generation strategy: `ai-helpers` (OAPE commands + code eval gate) or `direct` (plain agent, no OAPE, no eval gate) |
| `task_execution_mode` | `phase-iterative` | `phase-iterative`: one phase at a time with per-phase PRs and Jira tickets. `one-shot`: all tasks in one run, single PR |
| `auto_approve` | `true` | Auto-approve artifacts (`/opsx-continue`) and per-task code approval (`/opsx-apply`). Phase approval, PR creation, and Jira creation are NEVER auto-approved. |
| `max_feedback_rounds` | `3` | Max rejection + refinement loops per artifact before halting |
| `exit_on_all_tasks_complete` | `true` | Auto-exit implementation when all tasks marked `[x]` |
| `generation_runtime.*` | `script` (every key) | Per-stage switch to run that stage as an external script + direct LLM API call instead of in the Cursor agent session. Set a key to `agent` to opt that stage back into the agent session. See [Cost optimization](#cost-optimization-non-agentic-generation-via-openspecllm_gen). |
| `credentials.llm.*` | unset | Provider/model/API-key-env for `openspec.llm_gen` — must be configured (API key exported) for the `script` default to actually run non-agentically; falls back to `agent` per stage on `ok: false` otherwise. |

### Code generation modes

**`ai-helpers`** — For each task, composes a `design-bundle.md`, routes to specialized OAPE Cursor commands (`api-generate`, `api-implement`), scores generated code via a code-generation eval gate, refines until evals pass, then asks for user approval. E2E tasks are handled separately via `/opsx-e2e`.

**`direct`** — The Cursor agent reads context files directly, implements code via FILE OPERATIONS, verifies against acceptance criteria, and asks for user approval. No OAPE commands, no design bundles, no code eval gate. Simpler and faster for straightforward tasks.

### Task execution modes

**`phase-iterative`** — Tasks are grouped by plan phase. After each phase completes: a draft PR is raised, a Jira Story ticket is created for the phase, and `/opsx-continue` generates next-phase tasks. E2E tests can be triggered per phase after CI passes.

**`one-shot`** — All tasks execute sequentially across all phases. A single draft PR is raised at the end. E2E tests are triggered once after the final CI passes.

---

## Eval Loop (Optional, Recommended)

The eval loop is a **retrospective improvement** tool. After a feature is fully completed, feed its history into `/eval-loop` to generate eval cases that improve the quality of future runs.

### Step 1: Provide inputs

Fill `eval-generation/input/feature-bundle.yaml` with data from a **completed feature**:

| Field | What to paste |
|-------|---------------|
| `feature_name` | Feature name |
| `epic_key` | Jira epic key |
| `target_repo` | Target repository URL |
| `enhancement_proposal` | Full EP/ARD content |
| `jira_epic` | Jira epic export |
| `repo_state` | Pre-feature repo state |
| `user_stories` | User stories linked to the epic |
| `repo_prs` | PR links and key diffs |
| `bugs` | Bug list with root causes |

### Step 2: Run the eval loop

```
/eval-loop
```

### Step 3: Review template gaps

Review the gap reports generated in:

```
eval-generation/eval-generation-workflow/template-gaps/
```

Each file (`repo-assessment-gaps.md`, `plan-gaps.md`, `tasks-gaps.md`, etc.) describes generic template deficiencies discovered from the analyzed feature — what classes of information the templates should require but currently don't.

### Step 4: Review refined templates

Find refined templates in:

```
eval-generation/output-refined-templates/
```

These are patched versions of the templates with the patchable gaps addressed.

### Step 5: Apply approved refinements

If you approve the refined templates, copy them into the active workflow:

```bash
cp eval-generation/output-refined-templates/*.md openspec/schemas/openspec-agile-workflow/templates/
```

These are the templates used by the OpenSpec workflow for all future artifact generation.

### Step 6: Evals are auto-synced

The generated evals in `eval-generation/output-evals/` are automatically synced to:

```
harness-evals/evals/
```

These evals run as quality gates during `/opsx-continue` for every future artifact.

### Repeating

Update `eval-generation/input/feature-bundle.yaml` with the next completed feature and run `/eval-loop` again. Prior evals accumulate — each round improves coverage.

---

## Pipeline Overview

```
validation → specs → repo-assessment → [constitution.md required] → plan → tasks → implementation → [E2E] → archive
```

| Stage | Artifacts | Purpose |
|-------|-----------|---------|
| **Spec understanding** | `validation.json`, `specs.md` | Validate Jira spec before repo work |
| **Repo understanding** | `repo-assessment.md` | Ground planning in the target repository |
| **Constitution (input)** | `constitution.md` (from `harness-evals/`) | Non-negotiable guardrails |
| **Planning** | `plan.md` | Phased implementation plan (e2e phases excluded) |
| **Task creation** | `tasks.md` + Jira phase ticket | Executable task manifest with agents (e2e tasks excluded) |
| **Implementation** | code + `implementation-report.md` | Task-by-task execution with per-task approval |
| **E2E (post-CI)** | `e2e-analysis.md`, `test-plan.md`, `*_test.go` | E2E test generation triggered by `/opsx-e2e` |
| **Archive** | archived change | Close out |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| [Node.js](https://nodejs.org/) | For OpenSpec CLI installation |
| [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) | Installed by `install.sh` |
| [Cursor](https://cursor.com) | Slash commands load from `.cursor/commands/` |
| Jira access | Ticket key at `/opsx-new`; spec via MCP or paste |
| Target GitHub repo | URL before **repo-assessment**; or use working-folder mode |
| Fork GitHub repo | URL before `/opsx-apply`; skip in working-folder mode |

---

## Repository Layout

```
.
├── agents.md                                 # Operator-owned agent routing (at repo root)
├── qe-e2e/                                   # Operator-owned E2E context (at repo root)
│   └── qe-behaviour.md                      # Deployment context (3a) + quality gates (3b)
├── harness-evals/                            # Operator-owned (constitution + evals + docs)
│   ├── constitution.md                       # Generated by /opsx-constitute
│   ├── harness-docs/                         # Operator docs (read by /opsx-constitute)
│   └── evals/                                # Stage eval YAMLs (quality gates)
├── openspec/                                 # Pre-built — ready to use after install
│   ├── config.yaml                           # Workflow configuration and flags
│   ├── schemas/openspec-agile-workflow/      # Schema, templates, stage-gate
│   │   ├── schema.yaml                       # Workflow definition
│   │   ├── templates/                        # Generic artifact templates (*-template.md)
│   │   ├── e2e-workflow/                     # E2E test generation pipeline templates
│   │   │   ├── pre-analysis-gate.md          # PR scoping and approval gate
│   │   │   ├── test-plan-generation.md       # Tiered test plan + consolidation + code gen
│   │   │   └── qe-behaviour.md              # Generic QE rules (Sections 1-5) + templates for 3a/3b
│   │   ├── stage-gate/                       # Eval gate prompts and artifact map
│   │   └── feedback_stage_artifacts/         # Format spec for rejection rounds
│   ├── validators/                           # Deterministic (no-LLM) structural gates per artifact
│   ├── llm_gen/                              # Non-agentic stage execution — direct LLM API calls
│   │   ├── run.py                            # CLI dispatcher: python -m openspec.llm_gen.run --stage ...
│   │   ├── provider.py                       # Multi-provider LLM client (anthropic/openai/vertex)
│   │   ├── context_pack.py                   # Closed-bundle dependency-file reader
│   │   └── stages/                           # validation, specs, plan, tasks, stage_eval, code_eval, report, feedback
│   ├── telemetry/                            # Telemetry collection: metrics-report.json (dev) + qe-metrics.json (QE)
│   └── changes/                              # Active changes (created per /opsx-new)
├── .cursor/                                  # Pre-built — Cursor loads immediately
│   ├── commands/                             # opsx-new, opsx-continue, opsx-apply, opsx-e2e, eval-loop
│   └── skills/                               # openspec-*, effective-go
├── eval-generation/                          # Retrospective eval loop
│   ├── input/                                # feature-bundle.yaml (your input)
│   ├── output-evals/                         # Generated evals per stage (auto-synced to harness-evals/)
│   ├── output-refined-templates/             # Refined templates (review before applying)
│   └── eval-generation-workflow/             # Internal workflow machinery
│       ├── template-gaps/                    # Gap reports per template
│       ├── outputs/                          # Epic-bug-analysis + patches
│       ├── rounds/                           # Round snapshots
│       └── generation-phase/                 # SYSTEM_PROMPT, template-inventory
├── dashboard/                                # Observability dashboard (optional)
│   ├── config.json                           # Dashboard configuration
│   ├── start.sh                              # One-command launcher
│   ├── src/                                  # FastAPI backend (ingest + UI)
│   └── web/                                  # React + TypeScript SPA
├── install.sh                                # Installer script
└── README.md
```

---

## agents.md Resolution

`agents.md` is read from the operator repo root (working directory):

```
./agents.md
./AGENTS.md
```

If not found, the workflow asks the user once to provide it. If declined, the workflow proceeds with `AgentRoutingMode: PROVISIONAL`.

Your `agents.md` should define:
- **Repository layout** — directory structure, key packages
- **Architecture patterns** — controller frameworks, reconciliation flow
- **Test exemplar** — how tests are structured (mocks, table-driven patterns, file naming)
- **Execution agent routing** — agent IDs and which paths/packages they own
- **Per-task verification matrix** — `make` targets and `go test` commands per task type

## constitution.md Resolution

`constitution.md` is read from a single location:

```
harness-evals/constitution.md
```

If this file does not exist or is empty, the workflow **stops before planning** and prompts you to provide it.

**How to create it:**
- Run `/opsx-constitute` — reads documentation from `harness-evals/harness-docs/` and generates a constitution based on your operator's governance rules
- Or place a pre-existing `constitution.md` directly in `harness-evals/`

**Important:** `/opsx-constitute` requires documentation in `harness-evals/harness-docs/`. If that directory is empty, the command will stop and ask you to add your operator docs first.

The workflow will **never** auto-generate a constitution from a template.

---

## Validate Schema

```bash
openspec schema validate openspec-agile-workflow
```

---

## License

MIT (schema and templates). OpenSpec CLI is separate — see [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec).

---

## AI Agent User Guide & Compliance

This section outlines the operational boundaries, limitations, safety mechanisms, and compliance information for the OpenSpec AI Agent, in accordance with Red Hat AI compliance policies.

### Agent's Persona and Purpose

The OpenSpec AI Agent is a **spec-first, gated development assistant** for Kubernetes/OpenShift operator repositories. It operates within the Cursor IDE or Cursor CLI on the developer's local workstation.

- **Role:** AI-assisted software engineer that plans, implements, and tests operator code changes under strict human oversight.
- **Goals:** Validate Jira specifications, generate phased implementation plans, produce and verify code task-by-task, raise draft PRs, and create Jira traceability tickets.
- **Operational context:** Runs locally in the developer's terminal or IDE session. Never deployed as a hosted service. All actions are scoped to the local workspace, the user's GitHub fork, and authorized Jira/GitHub APIs.

### Limitations

- **Hallucinations:** The agent may occasionally hallucinate complex Kubernetes API versions, CRD field names, or internal Red Hat-specific libraries. Always verify generated code against official documentation.
- **Scope:** The agent is restricted to the local working directory and cannot access external Red Hat networks beyond authorized APIs (GitHub, Jira).
- **Go-operator focus:** The agent is designed for Go-based Kubernetes operator repositories. It is not suitable for non-Go projects, frontend applications, or non-operator workloads.
- **OpenShift API drift:** The agent may generate incorrect API group/version strings for OpenShift-specific resources (e.g. `security.openshift.io/v1` vs `v1beta1`). Always verify against the target cluster version.
- **File splitting:** The agent may over-split code across multiple files for a single controller. This is mitigated by the file colocation guardrail but should be reviewed.
- **Large changes:** Changes spanning 10+ files may exceed the LLM context window, leading to incomplete implementations or missed dependencies across packages.

### Capabilities and Inventory: Tools

**Cursor Commands (workflow):**

| Command | Type | Description |
|---------|------|-------------|
| `/opsx-new` | Write | Start a new change from a Jira ticket key |
| `/opsx-continue` | Write | Generate next artifact, run eval gate, approve |
| `/opsx-apply` | Write | Implement tasks one at a time with per-task approval |
| `/opsx-e2e` | Write | Generate E2E tests after CI passes |
| `/opsx-archive` | Write | Archive a completed change |
| `/opsx-publish-metrics` | Write (external repo, via GitHub MCP) | Fork/branch/PR metrics files to open-spec-dashboard |
| `/opsx-constitute` | Write | Generate constitution.md from harness-docs |
| `/opsx-explore` | Read | Explore ideas without creating artifacts |

**OAPE Commands (ai-helpers mode only, during `/opsx-apply`):**

| Command | Type | Description |
|---------|------|-------------|
| `/oape:api-generate` | Write | Generate API types for API_Agent tasks |
| `/oape:api-generate-tests` | Write | Generate tests for API_Agent verification tasks |
| `/oape:api-implement` | Write | Implement controller logic for OperatorController_Agent tasks |

**Retrospective:**

| Command | Type | Description |
|---------|------|-------------|
| `/eval-loop` | Write | Improve evals from a completed feature bundle |

**MCP Integrations:**

| Integration | Operations | Credentials |
|-------------|------------|-------------|
| Jira MCP | Read tickets, create Stories under Epic | `config.yaml → credentials.jira` (user's PAT) |
| GitHub MCP | Read repos, create draft PRs | `config.yaml → credentials.github` (user's PAT) |

**Direct LLM API calls (`openspec.llm_gen`, default for validation/specs/plan/tasks/stage-eval/code-eval/reports/feedback):**

| Integration | Operations | Credentials |
|-------------|------------|-------------|
| Anthropic / OpenAI / Vertex AI API | Generate or score `validation.json`, `specs.md`, `plan.md`, `tasks.md`, stage-eval scores, code-eval scores, reports | `config.yaml → credentials.llm.api_key_env` (user's own provider API key, read from an environment variable — never stored in `config.yaml`) |

This path is exercised whenever `config.yaml → flags.generation_runtime.<stage>` is `script`
(the default for every stage listed above — set a stage's flag to `agent` to opt it back into
the Cursor agent session). It runs as a plain local Python script — not a hosted service — and
reads only the same declared dependency files the agent would otherwise have read. It calls the
provider's API directly with the user's own key, billed to the user's own provider account
(separate from any Cursor/Claude Code subscription). `repo-assessment` and `implementation` are
never eligible for this path and always run agentically.

**Data Sources:**

| Source | Access | Description |
|--------|--------|-------------|
| `inputs/jira.yaml` | Read/Write | Jira ticket metadata, fork URL, target repo |
| `agents.md` | Read | Agent routing, architecture patterns, test exemplar |
| `harness-evals/constitution.md` | Read | Coding guardrails and governance rules |
| `harness-evals/evals/*.yaml` | Read | Stage eval cases for quality gates |
| `specs.md`, `plan.md`, `tasks.md` | Read/Write | Workflow artifacts (immutable once approved) |
| `implementation/state.yaml` | Read/Write | State machine for crash recovery |
| Fork working copy | Read/Write | Source code in the user's fork |

### Authorized and Prohibited Actions

**Autonomous actions (with `auto_approve: true`):**
- Generate and refine artifacts (validation.json, specs.md, repo-assessment.md, plan.md, tasks.md)
- Generate and refine code per task after eval/verification passes
- Run `go build`, `go vet`, `go test`, `make verify` in fork working directory
- Write telemetry data to `openspec/changes/`
- Mark tasks complete and advance to the next task

**Actions requiring human approval (never auto-approved):**
- Phase implementation approval — always prompted after all phase tasks complete
- PR creation to upstream repository — always prompted; user can decline
- Jira Story creation — always prompted; only offered when input ticket is an Epic with configured credentials
- Specs rejection — always requires explicit user action

**Prohibited actions:**
- Push to protected branches or merge to main/master
- Access files outside the working directory or fork checkout
- Execute arbitrary network requests beyond GitHub and Jira APIs
- Modify previously approved artifacts (specs, plan, repo-assessment are immutable once approved)
- Append to source files using `>>` or `tee -a` (in-place edits only)

**Explicit exception — `/opsx-publish-metrics`:** the one command permitted to write outside
the operator working directory/fork. It only ever writes the two local telemetry JSON files
(`metrics-report.json`, `qe-metrics.json`) verbatim, only to a fork of
`anandkuma77/open-spec-dashboard`, and only as a PR — it never merges. It is a standalone,
user-invoked command (never triggered autonomously by another command).
- Launch background sub-agents during `/opsx-apply` or `/opsx-continue`
- Auto-approve phase gates, PR creation, or Jira ticket creation regardless of configuration

### Best Practices

- **First run:** Set `auto_approve: false` in `config.yaml` to review each artifact and task individually. Switch to `true` once comfortable with the workflow.
- **Working-folder mode:** When your Cursor workspace IS the operator repo, tell the agent "use this as the working directory" when prompted for target repo. This avoids fork overhead and is faster for iteration.
- **Fork mode:** Use when you want the agent to raise a draft PR to the upstream repository. Provide fork URL before `/opsx-apply`.
- **Code generation mode:** Start with `codegen_mode: direct` for simple or few-file changes. Use `ai-helpers` for complex multi-package work that benefits from design bundles and code eval scoring.
- **agents.md quality matters:** The agent relies heavily on `agents.md` for code patterns, test exemplars, and package routing. Invest time in making it detailed and accurate.
- **Run `/eval-loop` after features:** After completing a feature, feed its history into `/eval-loop` to generate eval cases that improve quality for future runs.
- **Edge cases:** The agent may struggle with cross-CRD dependencies, non-standard project layouts, repositories without `make` targets, or monorepo structures with multiple operators.

### Human-in-the-Loop (HITL) and Accountability Workflow

> **Always review AI-generated output or actions prior to use.** Standard code review and compliance processes still apply to all AI-generated code.

The OpenSpec workflow enforces multi-layered human oversight:

1. **Artifact approval:** Each artifact (validation, specs, plan, tasks) is evaluated against stage evals, refined if needed, and presented for explicit user approval before the next stage begins.
2. **Task approval:** Each code task is verified (build, test, eval gate) and presented for approval. When `auto_approve` is `false`, the agent yields after every task. When `true`, tasks auto-approve after passing verification but phase/PR/Jira gates still require human input.
3. **Phase approval:** After all tasks in a phase complete, the agent always prompts: "Phase {N} development complete. Approve the phase implementation?" This gate is never auto-approved.
4. **PR creation:** The agent always asks: "Would you like to raise a draft PR to the upstream repo?" The user can decline. All PRs are created as drafts requiring normal upstream review and merge.
5. **Jira Story creation:** The agent always asks before creating Jira Stories. Skipped entirely if the input ticket is not an Epic or if Jira credentials are not configured.
6. **Override recording:** If a user approves a task despite failing eval cases, the decision and eval results are recorded in `implementation/task-reports/<task-id>.md` for audit purposes.
7. **Rejection handling:** When a user rejects with feedback, the agent re-runs only the current task/artifact. Up to 3 rejection rounds are allowed before the workflow halts.

### Rollback and Emergency Stop (Kill Switch)

**Emergency Stop:**

If the agent exhibits unexpected behavior, infinite loops, or attempts unauthorized actions, immediately terminate the session:

- **Cursor IDE (Chat/Composer):** Click the **Stop/Cancel button** in the AI panel, or use `Ctrl+Backspace` (Windows/Linux) / `Cmd+Backspace` (Mac). This halts the LLM stream and terminates active tool executions.
- **Cursor CLI (Terminal):** Press `Ctrl+C`. This sends a `SIGINT` signal, immediately halting all agent processes at the operating system level.

Both mechanisms function independently of the agent's logic and cannot be bypassed by the AI model.

**Rollback procedures:**

| Scenario | Command |
|----------|---------|
| Undo a task's code changes | `git checkout -- <files>` in the fork working copy |
| Undo the last commit | `git reset HEAD~1` in the fork |
| Undo an entire phase | `git reset --hard <commit-before-phase>` in the fork |
| Remove all generated artifacts for a change | Delete `openspec/changes/<name>/` directory |
| Close a draft PR | `gh pr close <URL>` or close via GitHub UI |
| Delete the fork feature branch | `git push origin --delete <branch>` |

The agent never merges to protected branches. All PRs are created as drafts and require human merge through the normal upstream review process.

### Data Handling

> **Do not add unapproved personal information or customer data to any agent input or configuration file.**

The agent processes the following data types:
- Jira ticket keys, summaries, and acceptance criteria
- GitHub repository URLs and source code
- Operator documentation from `agents.md` and `harness-evals/harness-docs/`

The agent does **not** process:
- Personally identifiable information (PII)
- Customer data or customer environment details
- Production cluster credentials or secrets

All data remains local to the developer's workstation and the authorized GitHub/Jira APIs. Credentials in `config.yaml` (PATs, API tokens) are the user's own personal tokens and must not be committed to version control. The `config.yaml` file should be added to `.gitignore` or have credentials managed via environment variables.

### RBAC Enforcement

The agent operates under the executing developer's identity and inherits their exact permissions:

- **Git operations:** Uses the developer's local SSH keys or configured Git credentials
- **GitHub API:** Uses the personal access token from `config.yaml → credentials.github.token`
- **Jira API:** Uses the personal API token from `config.yaml → credentials.jira.api_token`
- **`/opsx-publish-metrics`:** uses the `user-github` Cursor MCP server (the developer's own
  authenticated GitHub identity via Cursor), separate from `config.yaml → credentials.github.token`

The agent cannot access any repository, Jira project, or API the user is not already authorized to access. No service accounts are used. All operations run under the developer's identity with their existing RBAC permissions.

**To verify your access levels:**
- GitHub: check token scopes at https://github.com/settings/tokens
- Jira: verify your PAT permissions in your Jira profile settings
- Git: confirm SSH key access with `ssh -T git@github.com`

### Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "constitution.md required" | Missing `harness-evals/constitution.md` | Run `/opsx-constitute` or place the file manually |
| "target_repo not set" | Missing repo URL before repo-assessment | Provide the URL when prompted; it persists to `inputs/jira.yaml` |
| "fork_repo_url not set" | Missing fork URL before `/opsx-apply` | Provide fork URL, or say "use this as the working directory" |
| Jira Story creation skipped | Input ticket is not an Epic, or Jira credentials empty | Fill `credentials.jira` in `config.yaml` and use an Epic ticket |
| Eval scoring skipped | No eval file at `harness-evals/evals/<stage>_eval.yaml` | Add evals via `/eval-loop` or place YAML files manually |
| Agent stuck or in infinite loop | LLM context issue or tool execution hang | Press `Ctrl+C` (CLI) or Stop button (IDE), then re-run the command |
| Duplicate `package` errors in Go build | Agent appended to a source file instead of editing | Reset file with `git checkout -- <file>`, then re-run `/opsx-apply` |
| State recovery after crash | `state.yaml` persists the last transition | Re-run `/opsx-apply` — it reads `state.yaml` and resumes from last state |
| Preflight log not printed | Agent skipped mandatory config read | Re-run the command; if repeated, check that `openspec/config.yaml` exists |
| `openspec.llm_gen` returns `"No API key found..."` | `generation_runtime.<stage>` is `script` (the default) but the env var named by `credentials.llm.api_key_env` isn't exported | `export OPENSPEC_LLM_API_KEY=...` (or your configured var name) — the workflow already fell back to `agent` for this run automatically |
| `openspec.llm_gen` returns `ok: false` after retries | Structural gate kept failing, or the LLM API call errored | Read `reason` in the printed JSON; the workflow escalates that one artifact to the agent — no manual action usually needed |

### Feedback Mechanism

We actively monitor the performance and helpfulness of the OpenSpec agent. If you encounter poor quality output, hallucinations, or unexpected behavior, please report it using our feedback form:
- **[Submit Agent Feedback Here](https://docs.google.com/document/d/19vAlSNyY-HyG3WrjnpwNs7r1RaDvZGkw7YRZx-WK4sM/edit?usp=sharing)**

### Point of Contact

For questions, access requests, or to report security concerns, please contact the OpenSpec maintainers at: `<INSERT_TEAM_ALIAS_HERE>@redhat.com`
