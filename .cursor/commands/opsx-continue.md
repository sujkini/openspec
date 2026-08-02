---
name: /opsx-continue
id: opsx-continue
category: Workflow
description: Continue agile-workflow change - create next artifact, eval gate, refine, approve (OPSX)
---

Continue working on a change by creating the **next** artifact, then **eval → refine artifact → approval**. When `config.yaml → flags.auto_approve` is `true`, auto-loops through **all** remaining artifacts without prompting (see "Auto-approve loop" section). When `false`, processes one artifact per invocation.

**Input**: Optional change name after `/opsx-continue` (e.g. `/opsx-continue cm-830`).

## Schema package (resolve first existing path)

| Role | Installed | Distribution |
|------|-----------|--------------|
| Schema root | `openspec/schemas/openspec-agile-workflow/` |
| Stage gate | `{schema_root}/stage-gate/` | same |
| Stage evals | `{schema_root}/evals/<stage>_eval.yaml` | same |
| Templates | `{schema_root}/templates/` | same |

## Steps

1. Select change (`openspec list --json` if name not given).
2. `openspec status --change "<name>" --json`
3. Read `openspec/changes/<name>/inputs/jira.yaml` (required).
4. **Resolve repo target before repo-assessment** (see schema `target_repo` and `working_folder_repo`):
   - **Working-folder mode:** If the user directs using the working folder as the repo,
     set `use_working_folder_as_repo: true` in `inputs/jira.yaml`, record
     `working_folder_path`, analyze cwd — do not ask for GitHub URL or clone separately.
   - **Default mode:** If the next ready artifact is `repo-assessment` and
     `target_repo` is absent or empty in `jira.yaml`:
     - Ask the user once: "Provide the URL of the target GitHub repository
       (e.g. https://github.com/org/repo)."
     - Persist `target_repo` to `inputs/jira.yaml`.
     - Verify the repository is accessible before creating repo-assessment.
     - **Do not** create repo-assessment until `target_repo` is recorded.
   - For earlier artifacts (`validation`, `specs`), `target_repo` is not required.

4b. **Constitution check before planning** (ONLY when next ready artifact is `plan`):
    - Read `openspec/inputs/constitution.md`.
    - If the file does NOT exist or is EMPTY:
      STOP and output:
      **"constitution.md is required before planning but was not found (or is empty) at
      `openspec/inputs/constitution.md`. Please provide it using one of these options:
      1. Run `/opsx-constitute <repo-url>` to bootstrap it from the target repo
      2. Place your constitution.md manually in `openspec/inputs/constitution.md`
      Then re-run `/opsx-continue`."**
      Do NOT proceed. Do NOT auto-generate from a template.
    - If the file exists and has content: proceed to step 5.

5. Pick first artifact with `status: "ready"`.

5b. **Task execution mode check** (ONLY when next ready artifact is `tasks`):
    - Read `config.yaml → flags.task_execution_mode` (default: `phase-iterative`).

    **IF task_execution_mode = "phase-iterative":**
      - Read `implementation/state.yaml` (or initialize if missing) to get
        `current_plan_phase` (default: 1), `total_plan_phases`, and
        `discarded_e2e_phases` (default: []).
      - **E2e phase filtering:** Read `plan.md` §5 phases. Classify each phase
        using schema `e2e_exclusion.phase_criteria`. Phases matching e2e criteria
        are added to `discarded_e2e_phases` in state.yaml and skipped.
        `total_plan_phases` counts only NON-e2e phases.
      - If `current_plan_phase` is a discarded e2e phase, advance past it
        until a non-e2e phase is reached (or all phases done).
      - If `current_plan_phase > total_plan_phases` (counting non-e2e only):
        all phases done — skip task generation; proceed to archive. STOP.
      - Read `plan.md` and extract Phase N details (goal, target files,
        dependencies, verification hooks).
      - Set `phase_scope: N` in generation context metadata.
      - If Phase N > 1: existing tasks.md contains prior phases marked `[x]` —
        new tasks will be appended.

    **IF task_execution_mode = "one-shot":**
      - Do NOT set `phase_scope` metadata (generate all phases at once).
      - tasks.md is generated once covering ALL plan phases.
      - No state.yaml phase tracking needed at this stage.

5c. **Task sizing prompt** (ONLY when next ready artifact is `tasks`):
    - Read `config.yaml → flags.task_sizing`.
    - If `prompt_user` is true:

      **IF task_execution_mode = "phase-iterative":**
        - ASK the user ONCE:
          ```
          Phase {N} of plan.md: {phase_goal}.
          How many tasks for this phase?
          Enter a range: min max (e.g. "3 8")
          Press Enter to use defaults ({default_min}–{default_max}).
          ```

      **IF task_execution_mode = "one-shot":**
        - Read the approved `plan.md` and count §5 implementation phases.
        - ASK the user ONCE:
          ```
          plan.md has {N} implementation phases.
          How many total tasks should this change produce?
          Enter a range: min max (e.g. "6 12")
          Press Enter to use defaults ({default_min}–{default_max}).
          ```

    - Parse response. Empty → defaults from config.
    - Inject into generation context as metadata field:
      `task_sizing: { min: X, max: Y, consolidation_threshold: Z }`
    - If `prompt_user` is false: inject defaults silently (no prompt).
    - **Do NOT re-prompt during eval gate, feedback loop, or regeneration.**
      The task_sizing metadata persists for the lifetime of this artifact generation.
6. **Telemetry — signal artifact start** (silent, non-blocking; starts phase clock on dashboard):
   ```bash
   python -m openspec.telemetry.auto on-artifact-start --change "<name>" --artifact "<artifact-id>" --phase <N>
   ```
   Include `--phase <N>` only when task_execution_mode = "phase-iterative" AND artifact is `tasks`.
   Omit `--phase` for one-shot mode and non-task artifacts.
7. `openspec instructions <artifact-id> --change "<name>" --json` → create artifact at `outputPath` (**v1**).
   - Generation uses **`{schema_root}/templates/`** (from openspec instructions).
   - **phase-iterative**: pass `phase_scope` and `task_sizing` metadata to the template.
     If Phase N > 1: append new phase tasks to existing tasks.md.
   - **one-shot**: pass `task_sizing` metadata only (no `phase_scope`). Generate all
     phases in a single tasks.md.
8. **Telemetry — signal artifact written** (silent, non-blocking; emits `phase_progress` with partial tokens):
   ```bash
   python -m openspec.telemetry.auto on-artifact-created --change "<name>" --artifact "<artifact-id>" --phase <N>
   ```
   Include `--phase` only for phase-iterative mode tasks artifact.
9. **Stage eval gate** — read and follow **`{schema_root}/stage-gate/STAGE_EVAL_GATE_PROMPT.md`** Steps 1–5 exactly.
   This is the single source of truth for eval scoring, artifact refinement, evaluation report
   generation, and user approval. Read `config.yaml → flags.auto_approve`; if `true`,
   STAGE_EVAL_GATE_PROMPT Step 5 auto-approves (no user prompt). Key paths used by the prompt:
   - Artifact-to-eval mapping: `{schema_root}/stage-gate/artifact-eval-map.yaml`
   - Stage eval cases: `{schema_root}/evals/<stage>_eval.yaml`
   - Eval results output: `openspec/changes/<name>/eval-results/<artifact-id>.yaml`
   - Evaluation report output: `openspec/changes/<name>/eval-results/<artifact-id>_evaluation_report.md`
   - On user rejection: follow **`{schema_root}/stage-gate/USER_FEEDBACK_PROMPT.md`**
   - On `specs` rejection: **exit workflow** (schema `exit_on_reject.specs`) — do NOT regenerate; STOP
10. **Telemetry — signal waiting for approval** (silent, non-blocking; emits `phase_progress` with eval score):
    ```bash
    python -m openspec.telemetry.auto on-waiting-approval --change "<name>" --artifact "<artifact-id>" --score <eval_score>
    ```
    Add `--phase <N>` only for phase-iterative mode tasks artifact.
11. **After user approves or rejects**, signal the outcome (finalizes phase metrics):
    ```bash
    python -m openspec.telemetry.auto on-artifact-complete --change "<name>" --artifact "<artifact-id>" --status passed --score <eval_score> --label "<quality_label>"
    ```
    Use `--status failed` if the user rejects the artifact.
    Add `--phase <N>` only for phase-iterative mode tasks artifact.

12. **Post-approve: create Jira Phase ticket** (ONLY when artifact is `tasks` AND `task_execution_mode = phase-iterative` AND `--status passed`):
    - Read `current_plan_phase` from `implementation/state.yaml` (or `phase_scope` from context).
    - Phase N should already be non-e2e (e2e phases are skipped in step 5b).
    - Parse `plan.md` Phase N section (Goal, Dependencies, Target files, Required capabilities, Verification hooks).
    - Parse `tasks.md` §3/§4 for Phase N task IDs and covered user stories.
    - Read `config.yaml → flags.auto_approve`. If `true`, treat as "Yes" (skip prompt).
      Otherwise ask:
      > "Phase {N} tasks approved. Create Jira Story ticket for Phase {N} under [epic_key/jira_key]? (Yes / No)"
    - **No** → write `plan_phases[]` entry with `jira_key: SKIPPED`. Proceed.
    - **Yes** →
      - Read `inputs/jira.yaml` for `epic_key` / `jira_key`.
      - Call Jira MCP `create_ticket`:
        - `project`: prefix of parent key (e.g. `CM` from `CM-800`)
        - `issuetype`: `Story`
        - `parent`: `epic_key` if present, else `jira_key`
        - `summary`: `[Phase N] <phase title from plan.md>`
        - `description`: developer-style phase ticket assembled from plan.md Phase N
          (Goal, Dependencies, Target files, Verification hooks) plus tasks.md §3/§4
          for Phase N (task list, acceptance criteria, covered US-xx / FR-xx, OpenSpec
          change path, parent epic reference).
      - Persist to `inputs/jira.yaml` → `plan_phases[]` (see schema `phases_jira_sync`).
      - If Jira MCP is unavailable, set `jira_key: PENDING`; surface the error but
        do NOT block the workflow. PENDING entries are retried once at /opsx-apply start.
    - Report created / PENDING / SKIPPED key in the approval summary.
    - Skip this step entirely for non-`tasks` artifacts and for one-shot mode.

## Artifact order (openspec-agile-workflow)

validation.json → specs.md → repo-assessment.md → [constitution.md check] → plan.md → tasks.md → …

**Note:** constitution.md is NOT a generated artifact. It is checked as a prerequisite before
plan.md. If `openspec/inputs/constitution.md` does not exist or is empty, the workflow stops
and prompts the user to provide it (via `/opsx-constitute` or manually).

## Eval gate by artifact

| Artifact | Stage eval file (under `{schema_root}/`) |
|----------|------------------------------------------|
| validation | Rubric in `templates/validation-template.md` only |
| specs | Skip (no stage eval) |
| repo-assessment | `evals/repo-assessment_eval.yaml` |
| plan | `evals/plan_eval.yaml` |
| tasks | `evals/tasks_eval.yaml` |


## Auto-approve loop

Read `config.yaml → flags.auto_approve` at the start of execution.

**When `auto_approve` is `true`:**

After step 11 completes with `--status passed`, **do NOT stop**. Instead:

1. Re-run `openspec status --change "<name>" --json` to refresh artifact statuses.
2. If another artifact has `status: "ready"`, loop back to **step 5** and process it.
   Use `--batch` flags on all telemetry hooks (see "Batch / Continue-All Telemetry" below).
3. Continue looping until **no more artifacts** have `status: "ready"` (all approved or
   the final artifact `tasks.md` is approved).
4. When the loop ends, print a summary of all artifacts processed and their eval scores.

This means a single `/opsx-continue` invocation with `auto_approve: true` will process
**all** remaining artifacts (validation → specs → repo-assessment → plan → tasks)
in sequence, stopping only after the last one is approved.

**When `auto_approve` is `false`:**

Process ONE artifact per invocation (original behavior). Stop after user approval/rejection
of the current artifact.

## Guardrails

- When `auto_approve` is `false`: ONE artifact per invocation (includes eval + refine + approval)
- When `auto_approve` is `true`: loop through ALL ready artifacts in a single invocation
- Do not skip eval gate for artifacts with `gate: stage_evals`
- Do not skip user approval (unless `config.yaml → flags.auto_approve` is `true`)
- Do not refine **templates** during eval gate — refine the **change artifact** only
- User rejection feedback loop **may** patch `{schema_root}/templates/` when required; write summaries to `feedback_stage_artifacts/`
- `target_repo` required before repo-assessment — **not** at `/opsx-new`
- Do not create the next artifact until the current one passes eval (auto_approve bypasses the prompt, not the eval gate)
- **No background sub-agents** — Do NOT launch background sub-agents, background shells, or Task-tool agents with `run_in_background=true` during `/opsx-continue`. Telemetry hooks execute in the main agent session only; background work cannot be metered and produces missing or incorrect metrics.

## Batch / Continue-All Telemetry

When the user requests "continue all" or approves multiple artifacts in a single session, use `--batch` flags on telemetry hooks so tokens are attributed at the phase level only:

- `python -m openspec.telemetry.auto on-artifact-start --change "<name>" --artifact "<artifact-id>" --batch`
- `python -m openspec.telemetry.auto on-artifact-created --change "<name>" --artifact "<artifact-id>" --batch`
- `python -m openspec.telemetry.auto on-artifact-complete --change "<name>" --artifact "<artifact-id>" --status passed --score <eval_score> --label "<quality_label>" --batch`

Add `--phase <N>` to all batch hooks when task_execution_mode = "phase-iterative" AND artifact is `tasks`.

In batch mode, per-artifact `phase_progress` token updates are skipped. The final `on-artifact-complete --batch` for the last artifact in a phase uses `estimate_artifact_phase_tokens()` to compute a single honest phase total.
