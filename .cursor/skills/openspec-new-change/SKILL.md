---
name: openspec-new-change
description: Start openspec-agile-workflow change from Jira ticket. Use for /opsx-new.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.2"
---

Jira key required at `/opsx-new`. Write `inputs/jira.yaml`. Obtain spec via Jira MCP or user paste into `inputs/jira-spec.md`. Do not create artifacts. Next: `/opsx-continue`.

Syntax: `/opsx-new CM-830` or `/opsx-new CM-830 change-name`

Repo URL optional now; required before repo-assessment stage.

## Steps

1. Parse Jira key (required), optional change name, optional repo URL.
2. Create the change:
   ```bash
   python -m src.telemetry.openspec_wrapper new change "<name>"
   ```
3. Write `openspec/changes/<name>/inputs/jira.yaml` with `jira_key`, `target_repo`, `created_at`.
4. Fetch ticket → `inputs/jira-spec.md`:
   - Use Jira MCP if configured, **or**
   - Ask the user to paste ticket content into `inputs/jira-spec.md`.
5. Get status and instructions:
   ```bash
   python -m src.telemetry.openspec_wrapper status --change "<name>" --json
   python -m src.telemetry.openspec_wrapper instructions validation --change "<name>"
   ```
6. **STOP** — do not create artifacts yet. Prompt: `/opsx-continue` to create `validation.json`.
