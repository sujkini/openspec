# openspec-agile-workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema for **gated, Jira-driven, spec-first development** with AI-assisted planning and implementation.

This repo is the **distribution package**: schema, templates, Cursor commands, and optional eval tooling. Designed to work across **any operator** — each team clones this repo, customizes `agents.md` for their operator, and runs the workflow.

---

## Getting Started for New Operators

### 1. Clone and install

```bash
git clone -b openspec-operator-generic https://github.com/sujkini/openspec.git /tmp/openspec-workflow
cd /path/to/your-operator-project
/tmp/openspec-workflow/install.sh .
```

This installs the schema, Cursor commands, skills, and evals into your project. **Restart Cursor** after install so slash commands load.

### 2. Customize `agents.md` for your operator

Edit **one file**: `openspec/schemas/openspec-agile-workflow/agents.md`

This is the **only operator-specific file** in the workflow. Everything else (templates, stage-gate prompts, evals) is generic. Your `agents.md` should define:

- **Repository layout** — directory structure, key packages
- **Architecture patterns** — controller frameworks, reconciliation flow, how your operator works
- **Shared utilities** — common packages, helper functions, test mocking patterns
- **Test exemplar** — how tests are structured (mocks, table-driven patterns, file naming)
- **Execution agent routing** — agent IDs and which paths/packages they own
- **Per-task verification matrix** — which `make` targets and `go test` commands to run per task type
- **Stage-specific hints** — operator-specific guidance for repo-assessment, planning, validation stages

The bundled `agents.md` in this repo is for **cert-manager-operator** as an example. Replace it entirely with your operator's documentation.

### 3. Start a change

You have **two modes** of operation:

#### Mode A: Working-folder mode (code changes in your local checkout)

Use this when your Cursor workspace IS the operator repo you want to work in.

```
/opsx-new PROJ-123
```

When prompted for the target repo, tell the agent: **"use this as the working directory"**

This sets `use_working_folder_as_repo: true` — the agent will:
- Assess YOUR current checkout for repo-assessment
- Implement code changes directly in your working directory
- No fork URL needed, no clone, no draft PR

#### Mode B: Fork mode (generate a draft PR)

Use this when you want the agent to clone your fork and open a draft PR.

```
/opsx-new PROJ-123
```

When prompted, provide:
- **Target repo URL** (e.g. `https://github.com/openshift/my-operator`) — needed before repo-assessment
- **Fork repo URL** (e.g. `https://github.com/youruser/my-operator`) — needed before `/opsx-apply`

The agent will clone your fork, create a feature branch, implement task-by-task, and open a draft PR.

### 4. Run the workflow

```
/opsx-new PROJ-123          → start change from Jira ticket
/opsx-continue              → validation.json      [approve]
/opsx-continue              → specs.md             [approve]
/opsx-continue              → repo-assessment.md + constitution.md  [approve]
/opsx-continue              → plan.md             [approve]
/opsx-continue              → tasks.md            [approve]
/opsx-apply                 → task T1 [approve] → task T2 [approve] → … → done
/opsx-archive               → archive the change
```

You can also start from an **Enhancement Proposal** file in your working directory instead of a Jira key — just tell the agent the path.

---

## How the eval loop works (`/eval-loop`)

The eval loop is a **retrospective improvement** tool. After a feature is fully completed (EP written, code merged, bugs found), you feed that history into `/eval-loop` to generate eval cases that improve future workflow runs.

### What to provide

Fill the files under `evals/inputs/` with data from **one completed feature**:

| File | What to paste |
|------|---------------|
| `evals/inputs/feature-meta.yaml` | Feature name, epic key, target repo URL |
| `evals/inputs/01-ep-ard.md` | The Enhancement Proposal or ARD document |
| `evals/inputs/02-jira-epic.md` | Jira epic export (summary, description, acceptance criteria, linked stories) |
| `evals/inputs/03-original-repo.md` | Pre-feature repo state: commit SHA, branch, key file listings |
| `evals/inputs/04-user-stories.md` | All user stories / sub-tasks linked to the epic |
| `evals/inputs/05-repo-prs.md` | PR links, summaries, and key diffs from the completed implementation |
| `evals/inputs/bugs/index.yaml` | List of bug keys related to this feature |
| `evals/inputs/bugs/<KEY>.md` | One file per bug with details |

### Running it

```
/eval-loop
```

This runs:
1. **Epic Bug Analysis** — analyzes PRs and bugs for patterns
2. **Eval Generation** — creates eval cases, refines templates and `agents.md`, updates baseline

### Where outputs go

| Location | What |
|----------|------|
| `evals/baseline/evals/<stage>/<stage>_eval.yaml` | Eval cases per stage (cumulative) |
| `evals/refined-templates/` | Improved template variants (eval-specific) |
| `evals/refined-templates/agents.md` | Refined `agents.md` with learnings from bugs/PRs |
| `evals/outputs/epic-bug-analysis/` | Pattern analysis, RCA summaries |
| `schemas/.../evals/*_eval.yaml` | Synced stage evals for forward workflow |

### Syncing evals to the forward workflow

After `/eval-loop` completes, the generated eval cases must be present in `schemas/openspec-agile-workflow/evals/` so the forward workflow (`/opsx-continue` and `/opsx-apply`) can use them as quality gates. The pipeline does this automatically — it writes each stage's eval file to **both** locations:

| Retrospective (eval loop) | Forward workflow (used by `/opsx-continue`) |
|---------------------------|---------------------------------------------|
| `evals/baseline/evals/repo-assessment/repo-assessment_eval.yaml` | `schemas/openspec-agile-workflow/evals/repo-assessment_eval.yaml` |
| `evals/baseline/evals/constitution/constitution_eval.yaml` | `schemas/openspec-agile-workflow/evals/constitution_eval.yaml` |
| `evals/baseline/evals/plan/plan_eval.yaml` | `schemas/openspec-agile-workflow/evals/plan_eval.yaml` |
| `evals/baseline/evals/tasks/tasks_eval.yaml` | `schemas/openspec-agile-workflow/evals/tasks_eval.yaml` |
| `evals/baseline/evals/implementation/implementation_eval.yaml` | `schemas/openspec-agile-workflow/evals/implementation_eval.yaml` |
| `evals/baseline/evals/code-generation/code-generation_eval.yaml` | `schemas/openspec-agile-workflow/evals/code-generation_eval.yaml` |

If you run `install.sh` after running `/eval-loop`, the synced eval files under `schemas/.../evals/` will be copied into your project at `openspec/schemas/openspec-agile-workflow/evals/` — making the new eval cases active in your next `/opsx-continue` or `/opsx-apply` run.

### Repeating

After reviewing outputs, replace `evals/inputs/` with data from your **next** completed feature and run `/eval-loop` again. Prior evals accumulate — each round builds on the last.

---

## What is openspec-agile-workflow?

A structured workflow that turns a Jira ticket into reviewed artifacts, then implements them **task-by-task** on your fork using [OAPE](https://github.com/openshift-eng/oape-ai-e2e) commands.

### Pipeline

```
validation → specs → repo-assessment + constitution → plan → tasks → implementation → archive
```

| Stage | Artifacts | Purpose |
|-------|-----------|---------|
| **Spec understanding** | `validation.json`, `specs.md` | Validate and refine the Jira spec before any repo work |
| **Repo understanding** | `repo-assessment.md`, `constitution.md` | Ground planning in the target repository |
| **Planning** | `plan.md` | Phased implementation plan (§0–§8) |
| **Task creation** | `tasks.md` | Executable task manifest with assigned agents |
| **Implementation** | code on fork + `implementation-report.md` | Task-by-task OAPE execution with per-task approval |
| **Archive** | archived change | Close out the change |

### Gates on every artifact

After each artifact is generated:

```
generate v1 → run stage evals → refine artifact → generate evaluation report → user approve → next stage
```

Every artifact gets an **evaluation report** (`<artifact-id>_evaluation_report.md`) written alongside it. The report presents:

- How many evals passed/failed with scores
- Gap analysis — what's missing or inconsistent with input artifacts and `agents.md`
- Quality assessment — completeness, consistency, grounding
- Recommendations for review

The evaluation report is presented to you together with the artifact for approval.

If you **reject** with feedback, the agent:

1. Loads prior approved artifacts (read-only), current artifact, and the **current template**
2. **Updates the template** if your feedback requires structural changes (minimal patch)
3. **Regenerates** only the current artifact
4. Writes a **round summary** to `openspec/changes/<change>/feedback_stage_artifacts/<artifact-id>/round-<N>.yaml`
5. Re-runs evals → asks for approval again (loops until you approve)

Previously approved artifacts stay **immutable**. No `prompts/<artifact-id>.yaml` snapshots are used.

**Exception:** Rejecting **`specs.md`** **exits the workflow** — no regeneration, no repo-assessment or later stages until you start fresh or re-run specs.

During **implementation**, approval happens **after every task** (not per artifact).

---

## What you need to run it

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) | `npm install -g @fission-ai/openspec` |
| [Cursor](https://cursor.com) | Slash commands and skills install to `.cursor/` |
| Jira access | Ticket key at `/opsx-new`; spec via MCP or paste into `inputs/jira-spec.md` |
| Target GitHub repo | URL before **repo-assessment** (`inputs/jira.yaml` → `target_repo`); **or** use working-folder mode |
| Fork GitHub repo | URL before **`/opsx-apply`** (`inputs/jira.yaml` → `fork_repo_url`); **skip in working-folder mode** |

---

## Configuration (`config.yaml`)

After install, `openspec/config.yaml` controls workflow behavior. Key flags you can tune:

```yaml
flags:
  max_feedback_rounds: 3          # Max user rejection + refinement loops per artifact before halting
  exit_on_all_tasks_complete: true # Auto-exit implementation stage when all tasks in tasks.md are marked [x]
```

| Flag | Default | What it does |
|------|---------|--------------|
| `max_feedback_rounds` | 3 | Limits how many times you can reject and refine an artifact before the workflow halts and asks you to restart |
| `exit_on_all_tasks_complete` | true | When all tasks in `tasks.md` are checked off, the implementation stage ends automatically (writes report, opens PR) |

The `rules:` section in `config.yaml` defines per-stage constraints the agent follows (validation scoring, spec format, implementation mode). You generally don't need to edit these unless you want to change workflow behavior.

---

## Install with `install.sh`

`install.sh` copies everything needed to run **openspec-agile-workflow** into a target project. It is the supported install path — **`openspec init` alone** installs the default `spec-driven` schema, not this workflow.

```bash
git clone https://github.com/sujkini/openspec.git /tmp/openspec-workflow
/tmp/openspec-workflow/install.sh /path/to/your-project
```

Or install into the current directory:

```bash
./install.sh .
```

**Restart Cursor** after install so slash commands load.

### What `install.sh` does (step by step)

1. **Checks** that the `openspec` CLI is installed.
2. **Runs `openspec init --tools cursor`** if `openspec/` does not exist (creates the OpenSpec skeleton).
3. **Creates** `openspec/changes/` if missing.
4. **Copies the full schema package** from `schemas/openspec-agile-workflow/` → `openspec/schemas/openspec-agile-workflow/` (schema, templates, stage evals, stage-gate prompts).
5. **Copies `agents.md`** from this repo root into `openspec/schemas/openspec-agile-workflow/agents.md`.
6. **Copies `config.yaml.example`** → `openspec/config.yaml` (selects this schema and artifact rules).
7. **Copies all Cursor commands** from `tooling/cursor/commands/` → `.cursor/commands/` (opsx-new, opsx-continue, opsx-apply, OAPE commands, eval-loop, etc.).
8. **Copies all Cursor skills** from `tooling/cursor/skills/` → `.cursor/skills/` (openspec workflow skills plus OAPE `effective-go` and `e2e-test-generator`).
9. **Copies OAPE e2e fixtures** from `tooling/cursor/e2e-test-generator/` → `.cursor/e2e-test-generator/` (used by `/oape:e2e-generate`).
10. **Copies `evals/`** → project `evals/` (optional retrospective pipeline for `/eval-loop`; preserves existing baseline if re-run).
11. **Validates** the schema with `openspec schema validate openspec-agile-workflow`.

### Install map

| Source (this repo) | Target (your project) |
|--------------------|-------------------------|
| `schemas/openspec-agile-workflow/` | `openspec/schemas/openspec-agile-workflow/` |
| `agents.md` | `openspec/schemas/openspec-agile-workflow/agents.md` |
| `config.yaml.example` | `openspec/config.yaml` |
| `tooling/cursor/commands/` | `.cursor/commands/` (all command files) |
| `tooling/cursor/skills/` | `.cursor/skills/` (openspec-* + OAPE `effective-go`, `e2e-test-generator`) |
| `tooling/cursor/e2e-test-generator/` | `.cursor/e2e-test-generator/` (e2e fixtures for `/oape:e2e-generate`) |
| `evals/` | `evals/` (optional — `/eval-loop` only) |

### Re-installing

- **`openspec update`** overwrites `.cursor/` with stock OpenSpec commands. Re-run `install.sh` to restore this workflow's commands.
- Re-running `install.sh` is safe: it refreshes the schema and commands; existing changes under `openspec/changes/` are preserved.

---

## agents.md — operator-specific customization

This distribution repo ships `agents.md` for **cert-manager-operator** as a reference example. **Each operator team must replace it** with their own operator-specific documentation.

Your `agents.md` defines:
- Agent IDs (e.g. `API_Agent`, `OperatorController_Agent`, `Testing_Agent`)
- Execution routing to OAPE commands
- Repo-specific conventions, architecture, and test patterns

### Where agents are resolved (lookup order)

When the workflow needs agent routing (repo-assessment onward):

1. `openspec/changes/<change>/inputs/AGENTS.md` (change-local override)
2. `openspec/changes/<change>/inputs/agents.md`
3. `{target_repo}/AGENTS.md` ← **expected long-term location**
4. `{target_repo}/agents.md`
5. `{schema_root}/agents.md` ← bundled copy from install

If none are found, the agent asks you once to provide `AGENTS.md`. If you decline, the workflow continues in **PROVISIONAL** mode (documented in constitution, plan, and tasks).

**Production expectation:** your target repository should own its `AGENTS.md`. The bundled copy is a fallback so you can run the workflow end-to-end before the target repo has one.

---

## Cursor commands

### Forward workflow (required)

| Command | Purpose |
|---------|---------|
| `/opsx-new PROJ-123` | Start a change from a Jira key; writes `inputs/jira.yaml` |
| `/opsx-continue` | Create the next artifact; runs stage evals; asks for approval |
| `/opsx-apply` | Implement tasks on your fork — **one task at a time**, user approval after each |
| `/opsx-archive` | Archive a completed change |
| `/opsx-explore` | Explore ideas without creating artifacts |

### OAPE commands (used during `/opsx-apply`)

Only these OAPE commands are invoked during implementation (one per task):

| Command | When |
|---------|------|
| `/oape:api-generate` | API_Agent task (non-verification) |
| `/oape:api-generate-tests` | API_Agent verification-only task |
| `/oape:api-implement` | OperatorController_Agent task |
| `/oape:e2e-generate` | E2E / Testing_Agent task |

Other OAPE commands (`review`, `predict-regressions`, etc.) are **not** used during `/opsx-apply`.

**OAPE skills** (installed to `.cursor/skills/`):

| Skill | Used by |
|-------|---------|
| `effective-go` | `/oape:api-generate`, `/oape:api-generate-tests`, `/oape:api-implement` |
| `e2e-test-generator` | `/oape:e2e-generate` (fixtures in `.cursor/e2e-test-generator/fixtures/`) |

### Retrospective eval loop (optional)

| Command | Purpose |
|---------|---------|
| `/eval-loop` | Improve evals and templates from a **completed** feature bundle |

---

## Implementation (`/opsx-apply`)

Implementation follows **`tasks.md`** in linear execution order, respecting task dependencies.

For **each pending task**:

1. Compose `implementation/design-bundle.md` scoped to **that task only**
2. Resolve **exactly one** allowed OAPE command (or manual work per `templates/code-generation.md` for non-OAPE agents)
3. Run the command in your **fork** working copy (or project cwd in working-folder mode)
4. Verify against the task's acceptance criteria
5. Run **code-generation evals** → refine code until evals pass (max 2 passes)
6. Present task summary + code eval scorecard; ask for **user approval of the code**
7. On approve: write **`implementation/task-reports/<task-id>.md`**, mark task `- [x]`, log progress, next task
8. On reject: add revision feedback, re-run **current task only**

When all tasks are done: write **`implementation-report.md`** (aggregates all task reports), commit, push feature branch, open a **draft PR** on your fork. In **working-folder mode**, no push/PR — summarize local changes instead.

---

## Template architecture

Each artifact template in `schemas/.../templates/` follows a consistent structure:

```
Agent preamble (system prompt: role, mission, inputs, quality rules)
---
## Output Template
<markdown skeleton for the artifact>
```

| Template | Agent role |
|----------|------------|
| `validation.md` | Specification Validator |
| `spec.md` | Specification Analyst |
| `repo-assessment.md` | Repository Assessment Agent |
| `constitution.md` | Constitution Agent |
| `plan.md` | Technical Planning Agent |
| `tasks.md` + `tasks-modes/*.md` | Sub-Task Creation Agent (multipass) |
| `code-generation.md` | Code Generation Agent (implementation) |
| `design-bundle.md` | User message template for codegen |
| `implementation-report.md` | Closing documentation agent |

Templates are **generic** — they work for any operator. Operator-specific depth comes from `agents.md`.

---

## Three eval systems

Do not confuse these — they serve different purposes.

### 1. Forward workflow eval gate (`/opsx-continue`)

**When:** After each artifact is generated during a live change.

**Where:** Stage evals in `openspec/schemas/openspec-agile-workflow/evals/*_eval.yaml`

**What happens:**

```
generate artifact → score against stage evals → refine artifact → user approve
```

Templates under `openspec/schemas/.../templates/` are **not** modified during eval-gate refinement. Only the change artifact is refined. However, during the **user rejection feedback loop**, templates **may be patched** if your feedback requires structural changes (see `stage-gate/USER_FEEDBACK_PROMPT.md`).

### 2. Code generation eval gate (`/opsx-apply`)

**When:** After each task's OAPE command (or manual work) during implementation.

**Where:** `openspec/schemas/openspec-agile-workflow/evals/code-generation_eval.yaml`

**What happens:**

```
OAPE command → verify task → score fork code (filtered by oape_command) → refine code until evals pass → user approves code → task report → next task
```

Each approved task writes **`implementation/task-reports/<task-id>.md`**. The final **`implementation-report.md`** aggregates all task reports.

Cases are **authored by `/eval-loop`** from PR diffs and bugs, tagged with `oape_command` (`api-generate`, `api-implement`, etc.).

### 3. Retrospective eval loop (`/eval-loop`)

**When:** After a feature is **fully completed** (EP, epic, stories, PRs, bugs). Used to improve the workflow itself over time.

**Where:** Project-root `evals/` directory (installed optionally by `install.sh`)

**What happens:**

```
Paste feature bundle into evals/inputs/ → /eval-loop → baseline updated → repeat with next bundle
```

See the [eval loop section](#how-the-eval-loop-works-eval-loop) above for detailed input format.

---

## Repository layout (this distribution repo)

```
schemas/openspec-agile-workflow/
├── schema.yaml                    # workflow definition
├── agents.md                      # operator-specific (customize per operator)
├── templates/                     # artifact + agent templates (generic)
│   ├── code-generation.md        # Code Generation Agent prompt
│   └── tasks-modes/              # multipass mode templates for tasks.md
├── evals/                         # stage evals (forward workflow gate)
├── stage-gate/                    # SYSTEM_PROMPT, USER_FEEDBACK_PROMPT, artifact map
└── feedback_stage_artifacts/      # format spec for rejection round summaries
evals/                             # retrospective eval loop (/eval-loop)
├── inputs/                        # paste one feature bundle at a time
├── baseline/                      # cumulative evals + changelog
├── epic-bug-analysis/             # SYSTEM_PROMPT for analysis
├── eval-generation/               # SYSTEM_PROMPT + stage samples
├── stages/                        # eval-spec.yaml rubrics per stage
└── refined-templates/             # improved templates (eval workflow output)
tooling/cursor/
├── commands/                      # opsx-new, opsx-continue, opsx-apply, OAPE, eval-loop
├── skills/                        # openspec-* + OAPE effective-go, e2e-test-generator
└── e2e-test-generator/            # fixtures + docs for /oape:e2e-generate
config.yaml.example                # → openspec/config.yaml
install.sh                         # install into another project
```

---

## Important notes

- Use **`install.sh`**, not `openspec init` alone, to get this workflow.
- **`openspec update`** overwrites `.cursor/` — re-run `install.sh` afterward.
- **`agents.md`** is the only operator-specific file — customize it for your operator.
- All templates are **generic** and work for any operator without modification.
- Implementation edits go to your **fork** (default) or **working folder** (`use_working_folder_as_repo: true`) — not the upstream target repo.
- Rejecting an artifact regenerates **only that artifact** (except **specs.md** — rejection exits the workflow); the agent may also **patch the template** if feedback requires structural changes.
- Feedback round summaries are written to `openspec/changes/<change>/feedback_stage_artifacts/` — they persist across schema reinstalls.

---

## Validate schema

```bash
openspec schema validate openspec-agile-workflow
```

Run from a project where the schema is installed under `openspec/schemas/`.

---

## License

MIT (schema and templates). OpenSpec CLI is separate — see [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec).
