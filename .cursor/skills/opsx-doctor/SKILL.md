# OpenSpec Doctor

Verify all prerequisites for the OpenSpec workflow. Run this before starting a new change to catch configuration issues early.

## Checks

Run each check and report pass/fail. Present a summary checklist at the end.

### 1. Python 3

```bash
python3 --version
```
Require Python 3.9+. Report version.

### 2. OpenSpec CLI

```bash
openspec --version 2>/dev/null || python -m openspec --version 2>/dev/null
```
Report version or "NOT FOUND".

### 3. Config File

Check `openspec/config.yaml` exists and is valid YAML.
Report key flags: `codegen_mode`, `task_execution_mode`, `auto_approve`.

### 4. Jira Credentials

Read `openspec/config.yaml → credentials.jira`:
- `base_url`: non-empty?
- `api_token`: non-empty?
Report "configured" or "missing".

### 5. Jira MCP Reachable

If Jira credentials configured, test MCP connectivity:
- Check if `user-jira` MCP server is available
Report "reachable", "unreachable", or "skipped (no credentials)".

### 6. GitHub MCP / CLI

```bash
gh auth status
```
Report authenticated user and scopes, or "NOT AUTHENTICATED".

### 7. Constitution

Check `harness-evals/constitution.md` exists and is non-empty.
Report "found (N lines)" or "MISSING".

### 8. Agents.md

Check for `agents.md` or `AGENTS.md` at workspace root.
Report "found (N lines)" or "MISSING".

### 9. Telemetry Dependencies

```bash
python -c "from openspec.telemetry.auto import build_parser; print('ok')"
```
Report "installed" or "MISSING — run pip install".

### 10. Go Toolchain (optional)

```bash
go version
make --version
```
Report versions or "not found (optional for non-Go projects)".

## Summary Output

```
======================================================================
/opsx-doctor — Environment Health Check
======================================================================
  [✓] Python 3:          3.11.5
  [✓] OpenSpec CLI:      0.4.2
  [✓] Config file:       openspec/config.yaml (auto_approve: true, codegen: direct)
  [✓] Jira credentials:  configured
  [✓] Jira MCP:          reachable
  [✓] GitHub CLI:         authenticated (user@example.com)
  [✓] Constitution:      found (142 lines)
  [✓] Agents.md:         found (85 lines)
  [✓] Telemetry:         installed
  [✓] Go toolchain:      go1.21.5, make 4.3
======================================================================
  Result: 10/10 checks passed — ready to go!
======================================================================
```

If any check fails, show `[✗]` with a brief fix instruction.
If optional checks fail, show `[—]` (informational only).
