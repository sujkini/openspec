# OpenSpec User Guide

## Install

Run this single command in your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- /path/to/your/project
```

This installs everything — workflow files, commands, skills, and dependencies for both Cursor and Codex.

---

## Setup

### Cursor

1. Run the install command above
2. Restart Cursor

That's it. You're ready.

### Codex

1. Run the install command above
2. Install Codex in VS Code (Extensions > search "Codex" > Install) or CLI (`npm install -g @codex/cli`)
3. Set your OpenAI API key (request this from your team):
   ```bash
   export OPENAI_API_KEY="sk-YOUR_KEY_HERE"
   ```
4. Restart VS Code

That's it. You're ready.

---

## Commands

### Development

**Input:** an Epic or Task/Story Jira ticket link.

| Step | Command | What it does |
|------|---------|-------------|
| 1 | `/opsx-new <JIRA-KEY>` or `/opsx-new <JIRA-LINK>` | Starts a new change from a Jira ticket key or link |
| 2 | `/opsx-continue` | Moves through each stage (validation > specs > repo-assessment > plan > tasks) |
| 3 | `/opsx-apply` | Implements the code after tasks are generated |

You will be prompted to approve at each stage before moving to the next. After code implementation, you will be prompted to raise a PR.

### QE (E2E Tests)

| Step | Command | What it does |
|------|---------|-------------|
| 1 | `/opsx-e2e --pr <PR-URL>` | Generates E2E tests from a PR |
| 1 | `/opsx-e2e --adr <path>` | Generates E2E tests from an ADR (no PR needed) |

After test generation, you will be prompted to raise a PR.

### After Your Run is Complete

| Step | Command | Required? |
|------|---------|-----------|
| 1 | `/opsx-archive` | **Mandatory** — collects your feedback (time saved, story points) and finalizes metrics |
| 2 | `/opsx-publish-metrics` | **Recommended** — publishes metrics to the shared dashboard via PR |
| 3 | [Feedback Form](https://docs.google.com/spreadsheets/d/1lBhSpvjtceexzHGc-dF37F6ho2y4msUnXm5hg52gMus/edit?usp=sharing) | **Mandatory** — submit the external agent feedback form |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Commands not showing up | Restart Cursor or VS Code |
| API key not working | Run `echo $OPENAI_API_KEY` — if empty, set it and reload your shell |
| Codex commands missing | Run `ls ~/.codex/prompts/opsx-*.md` — if empty, re-run the install command |
| Cursor commands missing | Run `ls .cursor/commands/opsx-*.md` — if empty, re-run the install command |

---

**Last Updated:** 2026-09-24
