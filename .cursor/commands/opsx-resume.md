---
name: /opsx-resume
id: opsx-resume
category: Workflow
description: Resume a change from the state repo — pull artifacts from previous owner for handover (OPSX)
---

Resume working on a change that was handed over by a previous phase owner.  Pulls state from the dedicated state repository and reconstructs `openspec/changes/<change>/` locally so `/opsx-continue` can pick up the next phase.

**Input**: Jira key (required), optional change name.

## Command syntax

```
/opsx-resume OAPE-850
/opsx-resume OAPE-850 my-change-name
```

Jira key pattern: `[A-Z][A-Z0-9]+-\d+`.

## Prerequisites

- `OPENSPEC_STATE_REPO` environment variable set (or configured in `openspec/config.yaml` → `state_sync.repo_env_var`)
- `GIT_TOKEN` environment variable set with repo access
- The previous owner must have completed their phase (state was pushed to the state repo)

## Steps

1. Parse Jira key (required), optional change name.
2. Read `OPENSPEC_STATE_REPO` from env (or `openspec/config.yaml` → `state_sync.repo_env_var`). If not set, error: "OPENSPEC_STATE_REPO not configured. Set it in your environment or .devcontainer/.env."
3. List remote branches matching `<jira-key>/*` in the state repo:
   ```bash
   python -c "from openspec.state_sync import list_branches; print(list_branches('<JIRA_KEY>'))"
   ```
   - If one match: use it automatically.
   - If multiple matches: present choices to user, ask which to resume.
   - If none: error — "No state found for Jira key `<JIRA_KEY>` in the state repo."
4. Pull the state branch:
   ```bash
   python -c "from openspec.state_sync import pull_state; branch, path = pull_state('<JIRA_KEY>', '<change_slug>'); print(f'branch={branch} path={path}')"
   ```
5. **Divergence check**: If `openspec/changes/<change>/` already exists locally:
   - Compare local file list with the pulled state.
   - If files differ, ASK:
     ```
     Local state at openspec/changes/<change>/ diverges from the state repo.
     Overwrite local with remote? (Yes / No / Show diff)
     ```
   - On "No": abort resume. STOP.
   - On "Show diff": list files that differ (added, modified, removed), then re-ask.
   - On "Yes": back up local to `openspec/changes/<change>.backup-<timestamp>/`, then overwrite.
   - If local does not exist: proceed directly (no conflict).
6. Copy the pulled state into `openspec/changes/<change>/` in the local workspace.
7. Verify state is valid:
   ```bash
   openspec status --change "<change>" --json
   ```
8. **RBAC identity check** (only if `inputs/rbac.yaml` exists):
   - Determine the last completed phase from `openspec status --change "<change>" --json` and the
     next phase name via `openspec.rbac.get_next_phase_name()`.
   - Resolve the current user email and verify they are the assigned owner for the **next** phase:
     ```python
     from pathlib import Path
     from openspec.rbac import (
         load_rbac_config,
         get_next_phase_name,
         resolve_current_user_email,
         verify_user_is_phase_owner,
         get_phase_owner,
     )
     config = load_rbac_config(Path("openspec/changes/<change>"))
     next_phase = get_next_phase_name("<last_completed_phase>")
     user_email = resolve_current_user_email()
     ok, err = verify_user_is_phase_owner(config, next_phase, user_email)
     ```
   - If `ok` is False: output the error message and **STOP** — do not show "assigned to you".
   - If `ok` is True and RBAC is enabled: display the phase ownership summary (assigned owner
     email for the next phase must match `user_email`).
9. Display resume summary:
   ```
   ═══════════════════════════════════════════════
   RESUMED: <change-name>
   Jira: <jira-key>
   State branch: <branch>
   Last completed phase: <phase_name> (by <previous_owner>)
   Next phase: <next_phase_name> (assigned to you)
   ═══════════════════════════════════════════════

   Run /opsx-continue to start the next phase.
   ```
10. **STOP** — do not auto-start the next phase.

## Guardrails

- Jira key required
- When RBAC is enabled, refuse resume if the current user is not the assigned owner for the next phase
- Never auto-start a phase — always require explicit `/opsx-continue`
- Back up local state before overwriting (never silently destroy work)
- If the state repo is unreachable, provide actionable error with steps to fix
- Do not modify the state repo — this command is read-only (pull only)
