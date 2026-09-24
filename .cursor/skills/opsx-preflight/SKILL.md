# Preflight Check

Shared preflight logic for all OpenSpec commands. Read and execute on every `/opsx-*` invocation before any domain work.

## Steps

1. **Read config flags**
   ```bash
   cat openspec/config.yaml
   ```
   Extract:
   - `flags.codegen_mode` (default: `direct`)
   - `flags.task_execution_mode` (default: `phase-iterative`)
   - `flags.auto_approve` (default: `true`)
   - `credentials.jira.base_url`, `credentials.jira.api_token`

2. **Resolve change directory**
   - If change name was provided: `openspec/changes/<name>/`
   - If not provided: run `openspec list --json`, pick the active change, or ask user.
   - Verify the directory exists.

3. **Read `inputs/jira.yaml`** (required for all commands)
   ```
   openspec/changes/<name>/inputs/jira.yaml
   ```
   Extract: `jira_key`, `jira_issuetype`, `target_repo`, `plan_phases[]`.

4. **Read `implementation/state.yaml`** (if exists — required for `/opsx-apply`)
   ```
   openspec/changes/<name>/implementation/state.yaml
   ```
   If missing and command is `/opsx-apply`: initialize from template
   `openspec/schemas/openspec-agile-workflow/templates/implementation-state-template.yaml`.

5. **Check blockers**
   - If next command needs `target_repo` and it is absent: STOP — ask user for repo URL.
   - If next command is plan generation and `harness-evals/constitution.md` is missing/empty:
     STOP — tell user to run `/opsx-constitute` or place `constitution.md` manually.
   - If `state.yaml` shows `EXECUTING_TASK`, `RUNNING_TESTS`, or `EVAL_GATE`:
     delegate to `opsx-recovery` skill before proceeding.

6. **Print preflight block** (mandatory — if not printed, the run is non-compliant):
   ```
   Preflight:
     change: <name>
     auto_approve: {true|false}
     codegen_mode: {direct|ai-helpers}
     task_execution_mode: {phase-iterative|one-shot}
     state: {IDLE|EXECUTING_TASK|...|COMPLETE|N/A}
     current_task: {task_id|null|N/A}
     jira_key: {key}
     jira_issuetype: {type}
     jira_creds_configured: {true|false}
   ```
