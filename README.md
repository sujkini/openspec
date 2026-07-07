# openspec-agile-workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema for **gated, Jira-driven, spec-first development** with AI-assisted planning and implementation.

This repo is the **distribution package**: schema, templates, Cursor commands, and optional eval tooling. You install it into your own project with `install.sh`.

For the **Agentic AI Observability Dashboard** (pipeline metrics, token burn, SSE logs), see [DASHBOARD_README.md](DASHBOARD_README.md).

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
generate v1 → run stage evals → refine artifact → user approve → next stage
```

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
| `AGENTS.md` in target repo | **Expected in production** — see [agents.md](#agentsmd-testing-only) below |

### Required after install (forward workflow)

These are installed by `install.sh` and are **required** for `/opsx-new` through `/opsx-apply`:

```
openspec/
├── config.yaml                              # selects openspec-agile-workflow schema
├── changes/                                 # one folder per change
│   └── <change>/feedback_stage_artifacts/   # round summaries (per rejection loop)
└── schemas/openspec-agile-workflow/
    ├── schema.yaml                          # workflow definition
    ├── templates/                           # artifact + agent templates
    │   └── code-generation.md              # Code Generation Agent (implementation)
    ├── evals/                               # stage evals for /opsx-continue
    ├── stage-gate/                          # eval + feedback prompts
    ├── feedback_stage_artifacts/            # format spec (README only — data in changes/)
    └── agents.md                            # bundled roster (testing only — see below)

.cursor/
├── commands/                                # opsx-*, OAPE commands
└── skills/                                  # workflow skills
```

### Optional (retrospective eval loop)

```
evals/                                       # only needed for /eval-loop
```

The forward workflow does **not** require `evals/` at project root. Stage evals for `/opsx-continue` ship inside the schema package.

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
5. **Copies `agents.md`** from this repo root into `openspec/schemas/openspec-agile-workflow/agents.md` (cert-manager-operator roster for testing — see below).
6. **Copies `config.yaml.example`** → `openspec/config.yaml` (selects this schema and artifact rules).
7. **Copies all Cursor commands** from `tooling/cursor/commands/` → `.cursor/commands/` (15 files: opsx-new, opsx-continue, opsx-apply, OAPE commands, eval-loop, etc.).
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

## agents.md (testing only)

This distribution repo ships **`agents.md`** inside the schema package for **testing and development** against the [cert-manager-operator](https://github.com/openshift/cert-manager-operator) repository. It defines:

- Agent IDs (e.g. `API_Agent`, `OperatorController_Agent`, `Testing_Agent`)
- Execution routing to OAPE commands
- Repo-specific conventions for that operator

**It is cert-manager-operator specific.** Do not treat it as a generic agent roster for other projects.

### Where agents are resolved (lookup order)

When the workflow needs agent routing (repo-assessment onward):

1. `openspec/changes/<change>/inputs/AGENTS.md` (change-local override)
2. `openspec/changes/<change>/inputs/agents.md`
3. `{target_repo}/AGENTS.md` ← **expected long-term location**
4. `{target_repo}/agents.md`
5. `{schema_root}/agents.md` ← bundled testing copy from install

If none are found, the agent asks you once to provide `AGENTS.md`. If you decline, the workflow continues in **PROVISIONAL** mode (documented in constitution, plan, and tasks).

**Production expectation:** your target repository should own its `AGENTS.md`. The bundled copy is a fallback so you can run the workflow end-to-end before the target repo has one.

---

## Cursor commands

### Forward workflow (required)

| Command | Purpose |
|---------|---------|
| `/opsx-new CM-830` | Start a change from a Jira key; writes `inputs/jira.yaml` |
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

## Step-by-step example (forward workflow)

```
/opsx-new CM-830
/opsx-continue    → validation.json              [approve]
/opsx-continue    → specs.md                     [approve]
/opsx-continue    → repo-assessment + constitution [approve]
/opsx-continue    → plan.md                      [approve]
/opsx-continue    → tasks.md                     [approve]
/opsx-apply       → task T1 [approve] → task T2 [approve] → … → draft PR
/opsx-archive
```

### Inputs during a change

| Input | When required |
|-------|----------------|
| Jira ticket key | `/opsx-new` |
| Jira spec content | Paste into `inputs/jira-spec.md` or use Jira MCP |
| Target repo URL | Before **repo-assessment** — agent prompts if empty (`inputs/jira.yaml` → `target_repo`); **skip if using working-folder mode** |
| Fork repo URL | Before **`/opsx-apply`** (`inputs/jira.yaml` → `fork_repo_url`); **skip in working-folder mode** |
| `AGENTS.md` | Before repo-assessment/plan/tasks if not in target repo — see [agents.md](#agentsmd-testing-only) |

### Working-folder mode

If you tell the agent to **"use the working folder as the repo"** (or similar), it activates local-checkout mode:

- Sets `use_working_folder_as_repo: true` in `inputs/jira.yaml`
- Uses your **current project checkout** for repo-assessment, constitution, plan, tasks, and implementation
- **No fork URL** required, **no clone**, **no feature branch** (unless you ask), **no draft PR**
- Implementation edits apply directly in your working directory

This is useful when your project checkout is the same repo you want to assess and implement in.

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

Typical task chain for a full feature:

```
T1  api-generate        → API types / CRD scaffolding
T2  api-generate-tests  → .testsuite.yaml integration tests
T3  api-implement       → controller / operator logic
T4  e2e-generate        → end-to-end tests (when applicable)
```

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

Templates serve as both the **system prompt** (how to generate) and the **output schema** (what to produce).

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

One command runs the full loop:

1. Validate `evals/inputs/` (no placeholder files)
2. Load prior baseline and refined templates (round 2+)
3. **Epic Bug Analysis** → `evals/outputs/epic-bug-analysis/`
4. **Eval Generation** → merge artifact eval cases, **author code-generation evals**, refine templates, sync stage evals
5. Update `evals/baseline/` and round state

| Step | You do |
|------|--------|
| 1 | Fill all files under `evals/inputs/` with one completed feature (EP, epic, stories, PRs, bugs) |
| 2 | Run **`/eval-loop`** in Cursor |
| 3 | Review `evals/baseline/` and `evals/refined-templates/` |
| 4 | Replace `evals/inputs/` with the next feature bundle |
| 5 | Run **`/eval-loop`** again — prior evals and refined templates feed the next round |

Eval workflow templates are read/written at `evals/refined-templates/` — **not** `schemas/.../templates/`. See `evals/README.md` for file layout and input format.

---

## Validate schema

```bash
openspec schema validate openspec-agile-workflow
```

Run from a project where the schema is installed under `openspec/schemas/`.

---

## Repository layout (this distribution repo)

```
agents.md                          # cert-manager-operator roster (copied into schema on install)
config.yaml.example                # → openspec/config.yaml
install.sh                         # install into another project
schemas/openspec-agile-workflow/
├── schema.yaml                    # workflow definition
├── agents.md                      # synced copy for schema package
├── templates/                     # artifact + agent templates (forward workflow)
│   ├── code-generation.md        # Code Generation Agent prompt
│   └── tasks-modes/              # multipass mode templates for tasks.md
├── evals/                         # stage evals (forward workflow gate)
├── stage-gate/                    # SYSTEM_PROMPT, USER_FEEDBACK_PROMPT, artifact map
└── feedback_stage_artifacts/      # format spec for rejection round summaries
evals/                             # retrospective eval loop (/eval-loop)
├── inputs/                        # paste one feature bundle at a time
├── baseline/                      # cumulative evals + changelog
├── epic-bug-analysis/
└── eval-generation/
tooling/cursor/
├── commands/                      # opsx-new, opsx-continue, opsx-apply, OAPE, eval-loop
├── skills/                        # openspec-* + OAPE effective-go, e2e-test-generator
└── e2e-test-generator/            # fixtures + docs for /oape:e2e-generate
oape-ai-e2e/                       # upstream OAPE plugin (source for OAPE skills/commands)
```

---

## Important notes

- Use **`install.sh`**, not `openspec init` alone, to get this workflow.
- **`openspec update`** overwrites `.cursor/` — re-run `install.sh` afterward.
- Bundled **`agents.md`** is for **testing** cert-manager-operator; production repos should provide their own `AGENTS.md`.
- Implementation edits go to your **fork** (default) or **working folder** (`use_working_folder_as_repo: true`) — not the upstream target repo.
- Rejecting an artifact regenerates **only that artifact** (except **specs.md** — rejection exits the workflow); the agent may also **patch the template** if feedback requires structural changes.
- Feedback round summaries are written to `openspec/changes/<change>/feedback_stage_artifacts/` — they persist across schema reinstalls.

---

## License

MIT (schema and templates). OpenSpec CLI is separate — see [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec).
