# OpenSpec Agile Workflow


|     |
| --- |
|     |


## User Guide

**Start here.** This section covers installation, editor setup, and the commands you need to run a change end to end.

### Install

Run this single command in your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- /path/to/workplace
```

This installs everything — workflow files, commands, skills, and dependencies for Cursor and Codex.

### Setup

#### Cursor

1. Run the install command above
2. Restart Cursor


|                                                                  |
| ---------------------------------------------------------------- |
| **That's it. You're ready.**                                     |
| Restart Cursor, then run `/opsx-new` to start your first change. |


#### Codex

1. Run the install command above
2. Install Codex CLI:
  ```bash
   npm install -g @codex/cli
  ```
   Or install the Codex extension in your editor (Extensions → search "Codex" → Install).
3. Set your OpenAI API key (request this from your team):
  ```bash
   export OPENAI_API_KEY="sk-YOUR_KEY_HERE"
  ```
4. Restart Codex (or reopen your editor)


|                                                                 |
| --------------------------------------------------------------- |
| **That's it. You're ready.**                                    |
| Restart Codex, then run `/opsx-new` to start your first change. |


### Commands

#### Development

**Input:** an Epic or Task/Story Jira ticket link, upstream repo URL, and local clone path.


| Step | Command                                            | What it does                                                                            |
| ---- | -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 1    | `/opsx-new <JIRA-KEY> <upstream-url> <clone-path>` | Starts a change: forks upstream (or reuses existing fork clone), creates feature branch |
| 2    | `/opsx-continue`                                   | Moves through each stage (validation → specs → repo-assessment → plan → tasks)          |
| 3    | `/opsx-apply`                                      | Implements code in the fork clone on the feature branch                                 |


You will be prompted to approve at each stage before moving to the next. After code implementation, you will be prompted to raise a PR to upstream.

**Example:**

```
/opsx-new CM-830 https://github.com/org/my-operator /home/you/code/my-operator-fork
```

If you already have a fork cloned at the path, OpenSpec reuses it (validates `origin` is your fork, not upstream).

#### QE (E2E Tests)


| Step | Command                   | What it does                                   |
| ---- | ------------------------- | ---------------------------------------------- |
| 1    | `/opsx-e2e --pr <PR-URL>` | Generates E2E tests from a PR                  |
| 1    | `/opsx-e2e --adr <path>`  | Generates E2E tests from an ADR (no PR needed) |


After test generation, you will be prompted to raise a PR.

#### After your run is complete


| Step | Command                                                                                                               | Required?                                                                               |
| ---- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 1    | `/opsx-archive`                                                                                                       | **Mandatory** — collects your feedback (time saved, story points) and finalizes metrics |
| 2    | `/opsx-publish-metrics`                                                                                               | **Recommended** — publishes metrics to the shared dashboard via PR                      |
| 3    | [Feedback Form](https://docs.google.com/spreadsheets/d/1lBhSpvjtceexzHGc-dF37F6ho2y4msUnXm5hg52gMus/edit?usp=sharing) | **Mandatory** — submit the external agent feedback form                                 |


## **You are set to begin!**



---

## Additional Workflow Details (Optional)

Installation and setup are covered in the **User Guide** above. The sections below provide a detailed overview of the OpenSpec agile workflow — configuration, execution modes, pipeline stages, Jira integration, telemetry, and agent compliance.

## Configuration

### Execution mode (`openspec/config.yaml`)

```yaml
# openspec/config.yaml
flags:
  codegen_mode: direct            # or: ai-helpers
  task_execution_mode: phase-iterative  # or: one-shot
  auto_approve: true              # auto-approve artifacts + per-task code; phase/PR/Jira gates always prompted
```


| Flag                  | Options                        | Purpose                                                                                                                    |
| --------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `codegen_mode`        | `ai-helpers` / `direct`        | Code generation strategy                                                                                                   |
| `task_execution_mode` | `phase-iterative` / `one-shot` | How tasks are grouped and PRs raised                                                                                       |
| `auto_approve`        | `true` / `false`               | Auto-approve artifacts and per-task code approval. Phase approval, PR creation, and Jira creation are NEVER auto-approved. |


### Operator documentation

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

Fill in Sections 3a and 3b in `qe-e2e/qe-behaviour.md` using the template as reference. If `qe-e2e/` is not present, `/opsx-e2e` will still work but will derive context from `agents.md` with reduced accuracy.

### Dashboard

```bash
cd /path/to/your-operator-repo
./dashboard/start.sh
```

Installs deps on first run, starts the FastAPI backend (port 8000) and React frontend (port 5173). Open [http://localhost:5173](http://localhost:5173). The backend polls `openspec/changes/` for telemetry data written by `/opsx-*` commands. See `dashboard/README.md` for details.

---

## Task Execution Modes

### Phase-Iterative (default)

Tasks are executed one phase at a time. After each phase completes:

- A PR is raised scoped to that phase
- A Jira Story ticket is created for the phase (linked to the epic)
- The user can trigger `/opsx-e2e --phase N` to generate E2E tests
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


| Input              | Mode          | Pipeline                                                             |
| ------------------ | ------------- | -------------------------------------------------------------------- |
| **PR only**        | PR Mode       | Full: pre-analysis → plan → consolidation → codegen → execute → push |
| **ADR or EP only** | Design Mode   | Plan-only: pre-analysis → plan → consolidation → codegen → STOP      |
| **ADR/EP + PR**    | Combined Mode | Full pipeline with enriched design context                           |
| **Change name**    | Change Mode   | Resolves PR from `state.yaml`, then runs Full                        |


**Design Mode** generates the test plan and code but does NOT execute or push — there is no branch to push to. Use this to review E2E coverage before a PR exists.

### Pipeline Stages

The pipeline runs five stages, each with a user approval gate:


| Stage              | Output                 | Description                                                            |
| ------------------ | ---------------------- | ---------------------------------------------------------------------- |
| 1. Pre-analysis    | `e2e-analysis.md`      | Scoping analysis from PR diff / ADR + operator context                 |
| 2. Test plan       | `test-plan.md`         | Full tiered plan with traceability                                     |
| 3. Consolidation   | `revised-test-plan.md` | Journey consolidation to configured limit                              |
| 4. Code generation | `*_test.go`            | Executable Ginkgo/Go test code                                         |
| 5. Execute         | Push + run             | Commit tests to PR branch, optionally execute (skipped in Design Mode) |


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

`**qe-e2e/qe-behaviour.md**` must contain two sections filled in by the operator team:

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


| Category               | What to define                                          |
| ---------------------- | ------------------------------------------------------- |
| Operator Lifecycle     | Installation, health, recovery observables              |
| Operand Health         | One row per operand CR with ready conditions            |
| Core Functionality     | Domain-specific behavior gates (operator team fills in) |
| Security               | RBAC boundaries, SCC/PSA, privilege constraints         |
| Deployment Integration | OLM Upgradeable, Helm hooks, etc.                       |
| Resilience             | Pod recovery, config reconciliation behavior            |
| Error Paths (optional) | Expected behavior on dependency/config failures         |
| Performance (optional) | Numeric thresholds (restart windows, SLAs)              |


A generic template with placeholders is shipped with OpenSpec at `openspec/openspec/schemas/openspec-agile-workflow/e2e-workflow/qe-behaviour.md`. Copy Sections 3a/3b from there into your `qe-e2e/qe-behaviour.md` and fill in operator-specific values.

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


| Location                                 | What to provide                                                                               |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- |
| `**agents.md`** (repo root)              | Agent routing, repository architecture, test patterns, verification matrix                    |
| `**qe-e2e/qe-behaviour.md`** (repo root) | Operator-specific E2E context: deployment model + quality gates (recommended for `/opsx-e2e`) |
| `**harness-evals/harness-docs/**`        | Operator documentation (used by `/opsx-constitute` to generate constitution)                  |
| `**harness-evals/constitution.md**`      | Coding guardrails, CI gates, governance rules (generated by `/opsx-constitute`)               |
| `**harness-evals/evals/**`               | Stage eval cases — quality gates (populated by `/eval-loop` or manually)                      |


And populate the `harness-evals/` directory:


| Directory                         | What to place                                                                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `**harness-evals/harness-docs/**` | Operator documentation (architecture guides, coding conventions, testing patterns). Used by `/opsx-constitute` to generate constitution.md |
| `**harness-evals/evals/**`        | Stage eval cases (populated by `/eval-loop` or placed manually). Used as quality gates during `/opsx-continue` and `/opsx-apply`           |


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
- `**/eval-loop` auto-syncs** generated evals to `harness-evals/evals/`.
- `**agents.md`** lives at the operator repo root (not inside harness-evals).

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
3. Run in local_clone_path (fork checkout on feature_branch)
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


|                          | Development                                                            | QE / E2E                                             |
| ------------------------ | ---------------------------------------------------------------------- | ---------------------------------------------------- |
| Events                   | `openspec/changes/<name>/telemetry/events.jsonl`                       | `openspec/changes/<name>/telemetry/e2e-events.jsonl` |
| Report                   | `openspec/changes/<name>/telemetry/metrics-report.json`                | `openspec/changes/<name>/telemetry/qe-metrics.json`  |
| Own tokens-in/out + cost | ✓                                                                      | ✓                                                    |
| Generated by             | `/opsx-new`, `/opsx-continue`, `/opsx-apply` (throughout the workflow) | `/opsx-e2e` (throughout the E2E pipeline)            |
| Completeness flag        | `report_status.complete`                                               | `qe_report_status.complete`                          |


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

### Cost optimization: single-shot `tasks.md`

Only the `**tasks`** artifact uses a same-session, single-turn generation path
(no tool calls during generation). Validation, specs, repo-assessment, plan, and
implementation remain agentic. After `tasks.md` is written, a deterministic
structural validator runs (no LLM):

```bash
python -m openspec.validators.tasks_structural --change "<name>"
```

Compare token usage before/after by running the same Jira ticket twice and
diffing `metrics-report.json` → `global_health.total_tokens_consumed` and the
`tasks` phase row in `phases[]`.

### Publishing metrics to the cross-operator dashboard

```
/opsx-publish-metrics [change-name]
```

Standalone command (not auto-triggered by `/opsx-archive`) that forks
[anandkuma77/open-spec-mado](https://github.com/anandkuma77/open-spec-mado)
via the `user-github` MCP server, branches, and opens a PR adding this change's
`metrics-report.json` (and `qe-metrics.json`, if this change ran `/opsx-e2e`) under
`data/open-spec-matrics/operators/<operator>/`. The operator folder is derived
automatically from `metrics-report.json → operator_name`. Publishing doesn't require
`report_status.complete`/`qe_report_status.complete` to be `true` — it warns on
incomplete data but doesn't block. Note that merging the resulting PR does not
automatically update the live dashboard; the dashboard repo owner must separately
re-run its `Generate Processed Metrics` GitHub Action.

---

## Repo setup (single mode)

At `/opsx-new`, provide:

- **Jira ticket key or URL**
- **Target repo URL** (upstream)
- **Local clone path** (where your fork checkout lives)

The agent either **reuses** an existing fork clone at that path or **forks + clones** upstream, then creates a **feature branch**. All implementation edits happen in `local_clone_path`. PRs target upstream when you approve at phase boundary.

```
/opsx-new CM-830 https://github.com/org/my-operator /home/you/code/my-operator-fork
```

---

## Cursor Commands

### Forward workflow


| Command                 | Purpose                                                                 |
| ----------------------- | ----------------------------------------------------------------------- |
| `/opsx-constitute`      | Generate constitution.md from harness-docs                              |
| `/opsx-new PROJ-123`    | Start a change from a Jira key                                          |
| `/opsx-continue`        | Create next artifact; eval gate; approval                               |
| `/opsx-apply`           | Implement tasks — one at a time, approval after each                    |
| `/opsx-e2e`             | Generate E2E tests for a phase/final PR                                 |
| `/opsx-archive`         | Archive a completed change                                              |
| `/opsx-publish-metrics` | Publish metrics-report.json / qe-metrics.json to open-spec-mado as a PR |


### OAPE commands (ai-helpers mode only, during `/opsx-apply`)


| Command                    | When                          |
| -------------------------- | ----------------------------- |
| `/oape:api-generate`       | API_Agent task                |
| `/oape:api-generate-tests` | API_Agent verification task   |
| `/oape:api-implement`      | OperatorController_Agent task |


These commands are **not used** when `codegen_mode: direct`.

### Retrospective eval loop


| Command      | Purpose                                       |
| ------------ | --------------------------------------------- |
| `/eval-loop` | Improve evals from a completed feature bundle |


---

## Configuration (`openspec/config.yaml`)

Key flags you can tune:

```yaml
flags:
  codegen_mode: direct                  # "direct" or "ai-helpers"
  task_execution_mode: phase-iterative  # "phase-iterative" or "one-shot"
  auto_approve: true                    # auto-approve artifacts + per-task code; phase/PR/Jira gates always prompted
  max_feedback_rounds: 3
  exit_on_all_tasks_complete: true
```


| Flag                         | Default           | What it does                                                                                                                                                  |
| ---------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `codegen_mode`               | `direct`          | Code generation strategy: `direct` (plain agent, no OAPE, no eval gate) or `ai-helpers` (OAPE commands + code eval gate)                                      |
| `task_execution_mode`        | `phase-iterative` | `phase-iterative`: one phase at a time with per-phase PRs and Jira tickets. `one-shot`: all tasks in one run, single PR                                       |
| `auto_approve`               | `true`            | Auto-approve artifacts (`/opsx-continue`) and per-task code approval (`/opsx-apply`). Phase approval, PR creation, and Jira creation are NEVER auto-approved. |
| `max_feedback_rounds`        | `3`               | Max rejection + refinement loops per artifact before halting                                                                                                  |
| `exit_on_all_tasks_complete` | `true`            | Auto-exit implementation when all tasks marked `[x]`                                                                                                          |


### Code generation modes

`**ai-helpers**` — For each task, composes a `design-bundle.md`, routes to specialized OAPE Cursor commands (`api-generate`, `api-implement`), scores generated code via a code-generation eval gate, refines until evals pass, then asks for user approval. E2E tasks are handled separately via `/opsx-e2e`.

`**direct**` — The Cursor agent reads context files directly, implements code via FILE OPERATIONS, verifies against acceptance criteria, and asks for user approval. No OAPE commands, no design bundles, no code eval gate. Simpler and faster for straightforward tasks.

### Task execution modes

`**phase-iterative**` — Tasks are grouped by plan phase. After each phase completes: a PR is raised (fork → upstream), a Jira Story ticket is created for the phase, and `/opsx-continue` generates next-phase tasks. E2E tests can be triggered per phase.

`**one-shot**` — All tasks execute sequentially across all phases. A single PR is raised at the end (fork → upstream). E2E tests are triggered once after implementation is complete.

---

## Eval Loop (Optional, Recommended)

The eval loop is a **retrospective improvement** tool. After a feature is fully completed, feed its history into `/eval-loop` to generate eval cases that improve the quality of future runs.

### Step 1: Provide inputs

Fill `eval-generation/input/feature-bundle.yaml` with data from a **completed feature**:


| Field                  | What to paste                   |
| ---------------------- | ------------------------------- |
| `feature_name`         | Feature name                    |
| `epic_key`             | Jira epic key                   |
| `target_repo`          | Target repository URL           |
| `enhancement_proposal` | Full EP/ARD content             |
| `jira_epic`            | Jira epic export                |
| `repo_state`           | Pre-feature repo state          |
| `user_stories`         | User stories linked to the epic |
| `repo_prs`             | PR links and key diffs          |
| `bugs`                 | Bug list with root causes       |


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


| Stage                    | Artifacts                                      | Purpose                                                   |
| ------------------------ | ---------------------------------------------- | --------------------------------------------------------- |
| **Spec understanding**   | `validation.json`, `specs.md`                  | Validate Jira spec before repo work                       |
| **Repo understanding**   | `repo-assessment.md`                           | Ground planning in the target repository                  |
| **Constitution (input)** | `constitution.md` (from `harness-evals/`)      | Non-negotiable guardrails                                 |
| **Planning**             | `plan.md`                                      | Phased implementation plan (e2e phases excluded)          |
| **Task creation**        | `tasks.md` + Jira phase ticket                 | Executable task manifest with agents (e2e tasks excluded) |
| **Implementation**       | code + `implementation-report.md`              | Task-by-task execution with per-task approval             |
| **E2E (post-CI)**        | `e2e-analysis.md`, `test-plan.md`, `*_test.go` | E2E test generation triggered by `/opsx-e2e`              |
| **Archive**              | archived change                                | Close out                                                 |


---

## Prerequisites


| Requirement                                            | Notes                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------- |
| [Node.js](https://nodejs.org/)                         | For OpenSpec CLI installation                                 |
| [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) | Installed by `install.sh`                                     |
| [Cursor](https://cursor.com)                           | Slash commands load from `.cursor/commands/`                  |
| Jira access                                            | Ticket key at `/opsx-new`; spec via MCP or paste              |
| Target GitHub repo (upstream)                          | URL at `/opsx-new`                                            |
| Local clone path                                       | Absolute path at `/opsx-new` — fork cloned or reused here     |
| GitHub MCP / `gh`                                      | Fork upstream at `/opsx-new`; PR to upstream at `/opsx-apply` |


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
- **Goals:** Validate Jira specifications, generate phased implementation plans, produce and verify code task-by-task, raise PRs (fork → upstream), and create Jira traceability tickets.
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


| Command                 | Type                                  | Description                                          |
| ----------------------- | ------------------------------------- | ---------------------------------------------------- |
| `/opsx-new`             | Write                                 | Start a new change from a Jira ticket key            |
| `/opsx-continue`        | Write                                 | Generate next artifact, run eval gate, approve       |
| `/opsx-apply`           | Write                                 | Implement tasks one at a time with per-task approval |
| `/opsx-e2e`             | Write                                 | Generate E2E tests from a PR or ADR                  |
| `/opsx-archive`         | Write                                 | Archive a completed change                           |
| `/opsx-publish-metrics` | Write (external repo, via GitHub MCP) | Fork/branch/PR metrics files to open-spec-mado       |
| `/opsx-constitute`      | Write                                 | Generate constitution.md from harness-docs           |


**OAPE Commands (ai-helpers mode only, during `/opsx-apply`):**


| Command                    | Type  | Description                                                   |
| -------------------------- | ----- | ------------------------------------------------------------- |
| `/oape:api-generate`       | Write | Generate API types for API_Agent tasks                        |
| `/oape:api-generate-tests` | Write | Generate tests for API_Agent verification tasks               |
| `/oape:api-implement`      | Write | Implement controller logic for OperatorController_Agent tasks |


**Retrospective:**


| Command      | Type  | Description                                   |
| ------------ | ----- | --------------------------------------------- |
| `/eval-loop` | Write | Improve evals from a completed feature bundle |


**MCP Integrations:**


| Integration | Operations                                  | Credentials                                     |
| ----------- | ------------------------------------------- | ----------------------------------------------- |
| Jira MCP    | Read tickets, create Stories under Epic     | `config.yaml → credentials.jira` (user's PAT)   |
| GitHub MCP  | Fork at `/opsx-new`, read repos, create PRs | `config.yaml → credentials.github` (user's PAT) |


**Data Sources:**


| Source                            | Access     | Description                                         |
| --------------------------------- | ---------- | --------------------------------------------------- |
| `inputs/jira.yaml`                | Read/Write | Jira ticket metadata, fork URL, target repo         |
| `agents.md`                       | Read       | Agent routing, architecture patterns, test exemplar |
| `harness-evals/constitution.md`   | Read       | Coding guardrails and governance rules              |
| `harness-evals/evals/*.yaml`      | Read       | Stage eval cases for quality gates                  |
| `specs.md`, `plan.md`, `tasks.md` | Read/Write | Workflow artifacts (immutable once approved)        |
| `implementation/state.yaml`       | Read/Write | State machine for crash recovery                    |
| Fork working copy                 | Read/Write | Source code in the user's fork                      |


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
`anandkuma77/open-spec-mado`, and only as a PR — it never merges. It is a standalone,
user-invoked command (never triggered autonomously by another command).

- Launch background sub-agents during `/opsx-apply` or `/opsx-continue`
- Auto-approve phase gates, PR creation, or Jira ticket creation regardless of configuration

### Best Practices

- **Manual review:** Set `auto_approve: false` in `config.yaml` if you want to approve each artifact and task individually. Default is `true`.
- **Repo setup at `/opsx-new`:** Provide upstream URL + local clone path. The agent forks (or reuses your existing fork clone), creates a feature branch, and records paths in `inputs/jira.yaml`. `/opsx-apply` edits only that clone.
- **Reuse existing fork:** If you already cloned your fork to the path, OpenSpec validates `origin` is your fork and continues — no second clone.
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
4. **PR creation:** The agent always asks: "Would you like to raise a PR to the upstream repo?" The user can decline. All PRs are created from the auto-forked repo to upstream, requiring normal review and merge.
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


| Scenario                                    | Command                                              |
| ------------------------------------------- | ---------------------------------------------------- |
| Undo a task's code changes                  | `git checkout -- <files>` in the fork working copy   |
| Undo the last commit                        | `git reset HEAD~1` in the fork                       |
| Undo an entire phase                        | `git reset --hard <commit-before-phase>` in the fork |
| Remove all generated artifacts for a change | Delete `openspec/changes/<name>/` directory          |
| Close a PR                                  | `gh pr close <URL>` or close via GitHub UI           |
| Delete the fork feature branch              | `git push origin --delete <branch>`                  |


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
- `**/opsx-publish-metrics`:** uses the `user-github` Cursor MCP server (the developer's own
authenticated GitHub identity via Cursor), separate from `config.yaml → credentials.github.token`

The agent cannot access any repository, Jira project, or API the user is not already authorized to access. No service accounts are used. All operations run under the developer's identity with their existing RBAC permissions.

**To verify your access levels:**

- GitHub: check token scopes at [https://github.com/settings/tokens](https://github.com/settings/tokens)
- Jira: verify your PAT permissions in your Jira profile settings
- Git: confirm SSH key access with `ssh -T git@github.com`

---

### Troubleshooting


| Issue                                    | Cause                                                   | Fix                                                                                                        |
| ---------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Commands not showing up                  | Cursor or Codex not restarted after install             | Restart Cursor or Codex                                                                                    |
| Cursor commands missing                  | Install incomplete                                      | Run `ls .cursor/commands/opsx-*.md` — if empty, re-run the install command                                 |
| Codex commands missing                   | Install incomplete                                      | Run `ls ~/.codex/prompts/opsx-*.md` — if empty, re-run the install command                                 |
| API key not working                      | `OPENAI_API_KEY` not set                                | Run `echo $OPENAI_API_KEY` — if empty, set it and reload your shell                                        |
| "Repo setup incomplete" at `/opsx-apply` | Missing fork/clone metadata                             | Re-run `/opsx-new` or complete `fork_repo_url`, `local_clone_path`, `feature_branch` in `inputs/jira.yaml` |
| Fork reuse rejected                      | `origin` points to upstream, not fork                   | Ensure `origin` is your fork and the path is a fork of the target repo                                     |
| "constitution.md required"               | Missing `harness-evals/constitution.md`                 | Run `/opsx-constitute` or place the file manually                                                          |
| "target_repo not set"                    | Missing repo URL before repo-assessment                 | Provide the URL when prompted; it persists to `inputs/jira.yaml`                                           |
| "fork failed"                            | Auto-fork of target repo failed                         | Check GitHub MCP auth and permissions, ensure you have fork rights on the target repo                      |
| Jira Story creation skipped              | Input ticket is not an Epic, or Jira credentials empty  | Fill `credentials.jira` in `config.yaml` and use an Epic ticket                                            |
| Eval scoring skipped                     | No eval file at `harness-evals/evals/<stage>_eval.yaml` | Add evals via `/eval-loop` or place YAML files manually                                                    |
| Agent stuck or in infinite loop          | LLM context issue or tool execution hang                | Press `Ctrl+C` (CLI) or Stop button (IDE), then re-run the command                                         |
| Duplicate `package` errors in Go build   | Agent appended to a source file instead of editing      | Reset file with `git checkout -- <file>`, then re-run `/opsx-apply`                                        |
| State recovery after crash               | `state.yaml` persists the last transition               | Re-run `/opsx-apply` — it reads `state.yaml` and resumes from last state                                   |
| Preflight log not printed                | Agent skipped mandatory config read                     | Re-run the command; if repeated, check that `openspec/config.yaml` exists                                  |


### Feedback Mechanism

We actively monitor the performance and helpfulness of the OpenSpec agent. If you encounter poor quality output, hallucinations, or unexpected behavior, please report it using our feedback form:

- **[Submit Agent Feedback Here](https://docs.google.com/document/d/19vAlSNyY-HyG3WrjnpwNs7r1RaDvZGkw7YRZx-WK4sM/edit?usp=sharing)**

### Point of Contact

For questions, access requests, or to report security concerns, please contact the OpenSpec maintainers at: `<INSERT_TEAM_ALIAS_HERE>@redhat.com`