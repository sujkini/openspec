# OpenSpec Agile Workflow

**Schema:** `openspec-agile-workflow`
**Version:** 1

Gated spec-driven workflow: Spec Understanding → Repo Understanding → Planning → Task Creation → Implementation. Produces `validation.json`, `specs.md`, `repo-assessment.md`, `constitution.md`, `plan.md`, `tasks.md`, and (during implementation) `implementation-report.md`, `implementation-checklist.md`, and optional `adrs.md`. Implementation uses OAPE command orchestration (`/opsx:apply`).

---

## 1. The System Prompt & Agent Personas

The workflow uses seven distinct agent personas, each defined in a template under `schemas/openspec-agile-workflow/templates/`. Each persona is activated at a specific stage and receives a tailored system prompt.

### 1.1 Specification Validator

- **Template:** `templates/validation.md`
- **Role/Context:** *"You are the 'Specification Validator': a quality gate for software specs before engineering or agentic codegen."*
- **Objectives:** Evaluate a Jira ticket's specification for completeness (60% weight) and quality (40% weight). Score each dimension 0–100. Emit a single JSON object (`validation.json`) with scores, missing elements, quality issues, cert-manager ecosystem gaps, blockers, and an overall status.
- **Guardrails:**
  - Do not fabricate repositories, APIs, ports, behaviors, timelines, or dependencies not stated in the spec.
  - If any core completeness pillar (Context & Motivation, User Personas, Acceptance Criteria, Scope Boundaries, Impacted Repositories) is absent, cap `completeness_score` at 60.
  - Set `overall_status` to BLOCKED on severe contradictions — even if scores are high.

### 1.2 Specification Analyst

- **Template:** `templates/spec.md`
- **Role/Context:** *"You are the 'Specification Analyst': a requirements transformation agent for a spec-driven development pipeline."*
- **Objectives:** Transform a raw Jira ticket (plus optional validation context) into a clean, technology-agnostic feature specification (`specs.md`). Produce user stories with priorities (P1/P2/P3), Given/When/Then acceptance scenarios, functional requirements (FR-001...), success criteria (SC-001...), and assumptions (A-001...).
- **Guardrails:**
  - No implementation details — no language names, framework names, file paths, or API endpoints.
  - Requirements must be testable: each FR maps to at least one Given/When/Then scenario.
  - Success criteria must be measurable: quantified outcomes, not adjectives.
  - Maximum 3 `[NEEDS CLARIFICATION]` markers.

### 1.3 Repository Assessment Agent

- **Template:** `templates/repo-assessment.md`
- **Role/Context:** *"You are the Repository Assessment Agent (Principal Software Engineer)."*
- **Objectives:** Produce a grounded, repo-evidenced assessment — a "how to work in this repo" playbook — across 12 mandatory sections (§0 Inputs & Tooling through §12 Quick Reference Card). Every section answers: *"What does a Planning AI Agent need to know about this to produce a safe, accurate, and complete implementation plan?"*
- **Guardrails:**
  - Only assert file paths and symbols supported by repository evidence from tools.
  - Read actual source files to understand behavior — do not guess from file names alone.
  - No draft/meta prose (e.g., "I will now read...").
  - Completeness target: ≥90%. Output must reach §12 in full.
  - Branch verification before feature claims — never assume main/master has code that the pinned branch lacks.

### 1.4 Constitution Agent

- **Template:** `templates/constitution.md`
- **Role/Context:** *"You are the 'Constitution Agent': a repository governance analyst for a spec-driven development pipeline."*
- **Objectives:** Derive core principles, coding conventions, development workflow, and governance rules from the codebase itself (`constitution.md`). Set `AgentRoutingMode` to PROVIDED (if AGENTS.md found) or PROVISIONAL (if not). This artifact is injected into all downstream agents as non-negotiable guardrails.
- **Guardrails:**
  - Every principle must be repo-evidence-backed — no generic best-practice platitudes.
  - No implementation decisions (those belong in `plan.md`).
  - No file inventories or risk analysis (those belong in `repo-assessment.md`).

### 1.5 Technical Planning Agent

- **Template:** `templates/plan.md`
- **Role/Context:** *"You are the Technical Planning Agent for the cert-manager ecosystem."*
- **Objectives:** Produce `plan.md` — the architectural and sequencing blueprint for implementation (§0–§8). Explains HOW work should proceed and in what order, using implementation phases with Goal, Dependencies, Target files, Required capabilities, and Verification hooks.
- **Guardrails:**
  - Do NOT write code, patches, or diffs.
  - Do NOT create Jira tickets, checklists with assignees, sprint plans, or granular "tasks."
  - Do NOT invent file paths, APIs, ports, feature gates, or behaviors not evidenced by the inputs.
  - Input precedence: constitution.md > specs.md > repo-assessment.md > AGENTS.md > validation.json.
  - Completeness target: ≥80–85%. All sections §0 through §8 in full.
  - Mandatory repo-grounded reality check in §1: if repo-assessment says a feature is absent on the pinned branch, plan greenfield work — not "verify existing implementation."

### 1.6 Sub-Task Creation Agent

- **Template:** `templates/tasks.md` (base) + `templates/tasks-modes/` (pass-specific instructions)
- **Role/Context:** *"You are the Sub-Task Creation Agent (Technical Project Manager mode)."*
- **Objectives:** Convert validated requirements + technical plan into an ordered execution backlog (`tasks.md`) with 6 sections (§0–§5): input coverage checklist, task dependency DAG (Mermaid), linear execution order, task execution manifest, per-task payloads, and orchestration notes.
- **Guardrails:**
  - No source code, patch hunks, or shell commands that mutate systems.
  - No inventing file paths not present in inputs.
  - Complexity uses Fibonacci integers: 1, 2, 3, 5, 8.
  - Assigned Agent must match AGENTS.md IDs exactly (if PROVIDED) or use provisional IDs (`API_Agent`, `OperatorController_Agent`, `ManifestsBindata_Agent`, `WebhookTLS_Agent`, `RBACSecurity_Agent`, `OLMRelease_Agent`, `Testing_Agent`, `Docs_Agent`).
  - Input precedence: constitution.md > specs.md > plan.md > repo-assessment.md > agents.md.

### 1.7 Code Generation Agent (OAPE Implementation Orchestrator)

- **Templates:** `templates/code-generation.md` (code generation rules), `templates/design-bundle.md` (per-task context bundle), `templates/implementation.md` (phase log format)
- **Role/Context:** *"You are the Code Generation Agent (Robotic Engineer Role)"* and the OAPE Implementation Orchestrator.
- **Objectives:** Execute approved tasks from `tasks.md` task-by-task in linear execution order. For each task: compose a design bundle, resolve and invoke one OAPE command (or implement manually for manual agents), verify acceptance criteria, run code-generation eval gate, refine code, then present results for user approval.
- **Guardrails:**
  - One OAPE command per task — never invoke multiple commands for the same task.
  - Forbidden commands during implementation: `predict-regressions`, `review`, `implement-review-fixes`, `analyze-rfe`, `init`.
  - Never skip the task approval gate.
  - Never ask user approval before the code eval refinement loop completes.
  - Do not implement the next task in the same pass — each invocation covers one Task ID only.
  - Follow constitution.md conventions exactly. Match existing patterns in the repository.

---

## 2. Orchestration Configuration (The State Machine)

### 2.1 Triggers

| Trigger | What it starts | Skill |
|---------|---------------|-------|
| `/opsx-new <JIRA_KEY> [change-name]` | Creates a new change from a Jira ticket. Writes `inputs/jira.yaml` and `inputs/jira-spec.md`. Does not create artifacts. | `openspec-new-change` |
| `/opsx-continue [change-name]` | Advances to the next artifact in the workflow. Creates one artifact per invocation (including eval gate + approval). | `openspec-continue-change` |
| `/opsx:apply [change-name]` | Starts or continues the Implementation Stage (Stage 5). Drives task-by-task OAPE execution. | `openspec-apply-change` |
| `/opsx:explore [change-name]` | Enters explore mode — a thinking partner for investigating problems and clarifying requirements. Read-only; does not create artifacts. | `openspec-explore` |

### 2.2 Sequential Steps (The Five Stages)

```
                            /opsx-new
                               │
                               ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 1: SPEC UNDERSTANDING                         │
│                                                      │
│  ┌────────────────┐    ┌────────────────┐            │
│  │ validation.json│───▶│   specs.md     │            │
│  │ (threshold     │    │ (approval gate │            │
│  │  gate)         │    │  — reject =    │            │
│  └────────────────┘    │  EXIT workflow)│            │
│                        └───────┬────────┘            │
└────────────────────────────────┼──────────────────────┘
                /opsx-continue   │  user approves
                                 ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 2: REPO UNDERSTANDING                         │
│                                                      │
│  ┌────────────────────┐  ┌────────────────────┐      │
│  │ repo-assessment.md │  │  constitution.md   │      │
│  │ (co-generated;     │  │  (co-generated;    │      │
│  │  joint approval    │◀▶│   joint approval   │      │
│  │  gate)             │  │   gate)            │      │
│  └─────────┬──────────┘  └────────┬───────────┘      │
│            └──────────┬───────────┘                   │
└───────────────────────┼──────────────────────────────┘
                /opsx-continue   │  user approves
                                 ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 3: PLANNING                                   │
│                                                      │
│  ┌────────────────┐                                  │
│  │   plan.md      │                                  │
│  │ (approval gate)│                                  │
│  └───────┬────────┘                                  │
└──────────┼───────────────────────────────────────────┘
                /opsx-continue   │  user approves
                                 ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 4: TASK CREATION                              │
│                                                      │
│  ┌────────────────┐                                  │
│  │   tasks.md     │                                  │
│  │ (approval gate)│                                  │
│  └───────┬────────┘                                  │
└──────────┼───────────────────────────────────────────┘
                /opsx:apply      │  user approves
                                 ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 5: IMPLEMENTATION                             │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │  FOR EACH pending task (§2 order):           │    │
│  │    1. Compose design-bundle.md               │    │
│  │    2. Resolve & invoke ONE OAPE command      │    │
│  │    3. Verify acceptance criteria             │    │
│  │    4. Code eval gate (refine ≤2 passes)      │    │
│  │    5. Present summary + scorecard            │    │
│  │    6. User approves CODE ──┐                 │    │
│  │       ├─ approve: task report → next task    │    │
│  │       └─ reject: REVISION FEEDBACK → retry   │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  POST-LOOP:                                          │
│    → implementation-report.md                        │
│    → implementation-checklist.md                     │
│    → adrs.md (if deviations)                         │
│    → push + draft PR (default mode)                  │
└──────────────────────────────────────────────────────┘
```

### 2.3 Branching / Conditional Logic

**Eval gate (every artifact except specs):**

After generating an artifact (v1), the agent scores it against stage-specific eval cases (`evals/<stage>_eval.yaml`). If cases fail, the agent refines the artifact and re-scores. This loop runs before the user ever sees the artifact. The eval gate never modifies schema templates — only the change artifact.

```
generate_v1 → run_stage_evals → refine_artifact → re_score → present_to_user
```

**User approval (every artifact):**

After the eval gate, the agent presents the artifact + eval scorecard and asks: *"Approve this artifact? (Approve / Reject with feedback)"*

- **Approve:** Lock artifact as immutable. Unlock next stage.
- **Reject (specs.md only):** EXIT the entire workflow. No feedback loop. No regeneration.
- **Reject (all other artifacts):** Enter the user approval feedback gate:
  1. Capture user feedback verbatim.
  2. Load revision context (prior approved artifacts read-only, current artifact, current template, eval results, openspec instructions).
  3. Patch the schema template if feedback requires structural changes.
  4. Regenerate the current artifact only.
  5. Write round summary to `feedback_stage_artifacts/`.
  6. Re-run eval gate.
  7. Re-present for approval. Loop until approved.

**Working-folder mode vs default mode (implementation):**

| Concern | Default mode | Working-folder mode |
|---------|-------------|-------------------|
| Repo source | Clone fork from `fork_repo_url` | Use current project checkout (cwd) |
| Feature branch | Created from fork default branch | Not created unless user requests |
| Code edits | Applied in cloned fork | Applied in cwd |
| Draft PR | Pushed and opened on fork | Skipped entirely |
| Activation | Default when `use_working_folder_as_repo` is false or absent | When `use_working_folder_as_repo` is true in `inputs/jira.yaml`, or user directs it |

**OAPE command resolution (per task):**

Exactly one command per task, resolved in this order:

1. If e2e task → `e2e-generate`
2. Else if API_Agent and verification-only → `api-generate-tests`
3. Else if API_Agent → `api-generate`
4. Else if OperatorController_Agent → `api-implement`
5. Else if manual agent (ManifestsBindata, WebhookTLS, RBACSecurity, OLMRelease, Docs) → no OAPE command; implement task payload directly
6. Else → halt and ask user

---

## 3. Tool & Building Block Integration

### 3.1 Read Tools

| Tool | Purpose | Used in |
|------|---------|---------|
| `openspec list --json` | List available changes with status and last-modified timestamps | `/opsx-continue`, `/opsx:explore` |
| `openspec status --change "<name>" --json` | Get artifact statuses (done/ready/blocked), completion state | `/opsx-continue`, `/opsx:apply` |
| `openspec instructions <artifact-id> --change "<name>" --json` | Get generation instructions: template, rules, context, dependencies, output path | `/opsx-continue` |
| `openspec instructions apply --change "<name>" --json` | Get implementation instructions and context file paths | `/opsx:apply` |
| Jira MCP (`user-jira`) | Read Jira ticket content: summary, description, linked issues, subtasks, comments | `/opsx-new` |
| GitHub MCP (`user-github`) | Read repository tree, file contents, git metadata from target repo | Stage 2 (Repo Understanding) |
| Local file reads | Read dependency artifacts, `inputs/jira.yaml`, AGENTS.md, repo source files | All stages |
| `git remote get-url origin` | Derive `target_repo` in working-folder mode | Stage 2 |

### 3.2 Write / Action Tools

| Tool | Purpose | Used in |
|------|---------|---------|
| `openspec new --jira "<KEY>" --schema openspec-agile-workflow [--name "<name>"]` | Create a new change directory structure with `inputs/jira.yaml` | `/opsx-new` |
| `/oape:api-generate --design-doc <path>` | OAPE command: generate API types and code from design bundle | Stage 5 (API_Agent implementation tasks) |
| `/oape:api-generate-tests <api-path>` | OAPE command: generate API tests | Stage 5 (API_Agent verification-only tasks) |
| `/oape:api-implement --design-doc <path>` | OAPE command: implement operator/controller logic from design bundle | Stage 5 (OperatorController_Agent tasks) |
| `/oape:e2e-generate <fork-default-branch>` | OAPE command: generate end-to-end tests | Stage 5 (e2e / Testing_Agent tasks) |
| `gh pr create --draft` | Open a draft pull request on the user's fork | Stage 5 post-loop (default mode only) |
| `git clone`, `git checkout -b`, `git push` | Fork setup, feature branch creation, push to remote | Stage 5 (default mode only) |
| `make` targets (`make test`, `make verify`, `make generate`, `make manifests`, `make build`) | Build, test, and verify code changes | Stage 5 (verification after each task) |
| File write operations (CREATE / EDIT / DELETE) | Direct code changes for manual-agent tasks | Stage 5 (manual agent tasks) |

---

## 4. Input/Output Schema & Variables

### 4.1 Inputs

**Change-level inputs** (persisted at `openspec/changes/<change>/inputs/`):

| Variable | Source | Stored in | Required at |
|----------|--------|-----------|-------------|
| `jira_key` | User provides at `/opsx-new` | `inputs/jira.yaml` | `/opsx-new` |
| `jira_spec` | Jira MCP or user paste | `inputs/jira-spec.md` | `/opsx-new` |
| `target_repo` | User provides or derived from `git remote` | `inputs/jira.yaml` | Stage 2 (before repo-assessment) |
| `fork_repo_url` | User provides | `inputs/jira.yaml` | Stage 5 (default mode only) |
| `use_working_folder_as_repo` | User directs | `inputs/jira.yaml` | Stage 2+ (when active) |
| `working_folder_path` | Derived from cwd | `inputs/jira.yaml` | Stage 2+ (working-folder mode) |

**Schema-level inputs** (shipped with the schema at `schemas/openspec-agile-workflow/`):

| Input | Path | Purpose |
|-------|------|---------|
| Templates | `templates/*.md` | Structure and prompt for each artifact |
| Task mode templates | `templates/tasks-modes/*.md` | Pass-specific instructions for multipass task generation |
| Stage eval files | `evals/<stage>_eval.yaml` | Eval cases for scoring each artifact |
| Eval spec definitions | `evals/stages/<stage>/eval-spec.yaml` | Eval specifications per stage |
| Stage gate system prompt | `stage-gate/SYSTEM_PROMPT.md` | System prompt for the eval gate agent |
| Code generation eval prompt | `stage-gate/CODE_GENERATION_EVAL_PROMPT.md` | System prompt for code eval scoring |
| User feedback prompt | `stage-gate/USER_FEEDBACK_PROMPT.md` | System prompt for the feedback revision agent |
| Artifact-eval mapping | `stage-gate/artifact-eval-map.yaml` | Maps artifacts to their eval files and templates |
| AGENTS.md | `agents.md` (schema package) or target repo | Agent roster and routing rules |

### 4.2 Expected Outputs

Each artifact has a defined format and output path:

| Artifact | Format | Output path | Gate type |
|----------|--------|-------------|-----------|
| `validation.json` | JSON (strict schema — see `templates/validation.md`) | `openspec/changes/<change>/validation.json` | Threshold (score ≥ `pass_threshold`, default 80) |
| `specs.md` | Markdown (output template in `templates/spec.md`) | `openspec/changes/<change>/specs.md` | Approval (reject = exit workflow) |
| `repo-assessment.md` | Markdown (12-section output template in `templates/repo-assessment.md`) | `openspec/changes/<change>/repo-assessment.md` | Approval (joint with constitution) |
| `constitution.md` | Markdown (output template in `templates/constitution.md`) | `openspec/changes/<change>/constitution.md` | Approval (joint with repo-assessment) |
| `plan.md` | Markdown (§0–§8 output schema in `templates/plan.md`) | `openspec/changes/<change>/plan.md` | Approval |
| `tasks.md` | Markdown (§0–§5 output schema in `templates/tasks.md`) | `openspec/changes/<change>/tasks.md` | Approval |
| `implementation-phase-log.md` | Markdown (append-only log, template: `templates/implementation.md`) | `openspec/changes/<change>/implementation-phase-log.md` | Per-task approval |
| Task reports | Markdown (template: `templates/implementation-task-report.md`) | `openspec/changes/<change>/implementation/task-reports/<task-id>.md` | Written on task approval |
| Design bundle | Markdown (template: `templates/design-bundle.md`) | `openspec/changes/<change>/implementation/design-bundle.md` | Regenerated per task |
| `implementation-report.md` | Markdown (template: `templates/implementation-report.md`) | `openspec/changes/<change>/implementation-report.md` | Informational (post-loop) |
| `implementation-checklist.md` | Markdown (template: `templates/implementation-checklist.md`) | `openspec/changes/<change>/implementation-checklist.md` | Informational (post-loop) |
| `adrs.md` | Markdown (template: `templates/adrs.md`) | `openspec/changes/<change>/adrs.md` | Informational (only if deviations logged) |
| Eval results | YAML | `openspec/changes/<change>/eval-results/<artifact-id>.yaml` | Written by eval gate |
| Code eval results | YAML | `openspec/changes/<change>/eval-results/code-generation-<task-id>.yaml` | Written by code eval gate |
| Feedback round summaries | YAML | `openspec/changes/<change>/feedback_stage_artifacts/<artifact-id>/round-<N>.yaml` | Written on user rejection |

---

## 5. Version History & Evolution

| Version | Changes |
|---------|---------|
| **v1** | Initial workflow: 5 stages (Spec Understanding → Repo Understanding → Planning → Task Creation → Implementation). 7 agent personas. Gated artifact pipeline with eval scoring and user approval at each stage. OAPE command orchestration for implementation. Multipass task generation. Working-folder mode. Exit-on-reject for specs.md. Joint approval gate for repo-assessment + constitution. Code-generation eval gate with per-task refinement. |
