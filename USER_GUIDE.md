# OpenSpec User Guide

Mandatory Post Run Procedure (After Your Openspec Run):

- Run /opsx-arcive at the end of every run to capture additional metrics.
- Run /opsx-publish-metrics next to create a pr to the metrics Dasboard 
- Add your feedback here: [https://docs.google.com/spreadsheets/d/1lBhSpvjtceexzHGc-dF37F6ho2y4msUnXm5hg52gMus/edit?usp=sharing](url)

Complete step-by-step guide for using OpenSpec with either **Cursor** or **Codex**.

---

## Table of Contents

1. [Installation & Setup](#installation--setup)
   - Cursor Setup
   - Codex Setup
2. [Using OpenSpec Commands](#using-openspec-commands)
3. [Running Your First Change](#running-your-first-change)
4. [Common Commands](#common-commands)
5. [Troubleshooting](#troubleshooting)

---

## Installation & Setup

### ⭐ Choose Your Editor

You'll use **either Cursor or Codex** — pick one:

| Feature | Cursor | Codex |
|---------|--------|-------|
| Setup Time | 5 minutes | 10 minutes |
| Commands | Built-in (`.cursor/commands/`) | Manual install (via script) |
| Price | Free | Free |
| IDE Support | Cursor app | VS Code extension or CLI |

---

## Step 1: Install OpenSpec (one command)

Run **one command** in your terminal and you're ready to go.

**For Cursor users:**

```bash
curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- /path/to/your/project
```

**For Codex users** (also installs slash commands globally):

```bash
curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- --codex /path/to/your/project
```

**Skip the dashboard** (optional):

```bash
curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- --no-dashboard /path/to/your/project
```

This installs:
- `openspec/` — OpenSpec workflow files
- `.cursor/` — Cursor commands and skills
- `.codex/` — Codex skills and setup script
- `scripts/` — Codex command installer and helpers
- `eval-generation/` — Evaluation generation workflows
- `dashboard/` — Metrics dashboard (unless `--no-dashboard`)
- *(with `--codex`)* Codex slash commands installed globally to `~/.codex/prompts/`

**Expected output:**
```
==> Downloading OpenSpec from https://github.com/sujkini/openspec.git (main)...
==> Running installer...
==> Installing OpenSpec CLI...
==> Copying openspec/ into /path/to/your/project...
==> Copying .cursor/ into /path/to/your/project...
==> Copying .codex/ into /path/to/your/project...
==> Copying scripts/ into /path/to/your/project...
=== Installation complete ===
```

---

## Step 2: Editor Setup

### If Using **Cursor**

**Option A: With Codex Extension in Cursor**

Codex can run inside Cursor as an extension. Follow these steps:

**Step 1: Open Cursor Command Palette**
1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type: `Codex: New Agent Setup`
3. Press Enter

**Step 2: Set Up Codex Agent**
1. Select **"New Agent"**
2. When prompted, enter your OpenAI API key (you'll receive this separately):
   ```
   sk-YOUR_KEY_HERE
   ```
3. Choose a model (e.g., `gpt-5.6-luna`, `gpt-4-turbo`, or `gpt-4`)
4. Complete the setup

**Step 3: Codex Commands**

If you installed with `--codex` in Step 1, Codex commands are already installed globally. Skip to Step 4.

If you used the Cursor install (without `--codex`), install them now:
```bash
cd /path/to/your/project
./scripts/install-codex-commands.sh
```

**Step 4: Restart Cursor**
Close and reopen Cursor completely to load the new Codex commands.

**Step 5: Track Token Usage (Important for Feedback)**
```bash
npx ccusage@latest session
```

This starts tracking your API usage. Keep this terminal tab open while working.

**Step 6: Start Using OpenSpec!**
```
/opsx-new PROJ-123
```

---

**Option B: Standalone Cursor with .cursor/commands**

Simply **restart Cursor** (close and reopen) — it automatically loads commands from `.cursor/commands/`. You're ready to go!

(You can skip this if using Option A with Codex extension.)

### If Using **Codex** (VS Code)

**Step A: Install Codex in VS Code**

Choose one installation method:

**Method 1: VS Code Extension (Easiest)**
1. Open VS Code
2. Press `Ctrl+Shift+X` (Windows/Linux) or `Cmd+Shift+X` (Mac)
3. Search for `"Codex"`
4. Click the blue **Install** button
5. Restart VS Code

**Method 2: Command-line CLI**
```bash
npm install -g @codex/cli
codex --version  # verify installation
```

**Step B: Set Up Codex Agent**

1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type: `Codex: New Agent Setup`
3. Enter your OpenAI API key (you'll receive this separately):
   ```
   sk-YOUR_KEY_HERE
   ```
4. Choose a model (e.g., `gpt-5.6-luna`, `gpt-4-turbo`, or `gpt-4`)
5. Complete the setup

**Step C: Install OpenSpec Commands**

If you installed with `--codex` in Step 1, commands are already installed globally. Skip to Step D.

Otherwise, install them manually:
```bash
cd /path/to/your/project
./scripts/install-codex-commands.sh
```

**Step D: Track Token Usage (Important for Feedback)**

```bash
npx ccusage@latest session
```

This starts tracking your API token usage and costs. Keep this terminal tab open while working.

**Step E: Restart Codex**

Close and reopen VS Code to load the new commands.

**Step F: Ready to Use**

You can now use OpenSpec commands:
```
/opsx-new PROJ-123
```

---

### 📊 Recording Token Usage & Costs

After your work session, record your API usage:

1. **Stop the token tracking:**
   ```bash
   # In the terminal where you ran ccusage@latest session
   # Press Ctrl+C to stop tracking
   ```

2. **Get your usage report:**
   ```bash
   npx ccusage@latest report
   ```
   This shows:
   - Total tokens used
   - Estimated cost
   - Cost breakdown by model

3. **Record in Feedback Sheet:**
   - Open the feedback sheet (link will be provided)
   - Add your session data:
     - **Change ID**: `PROJ-123` (or your ticket ID)
     - **Tokens Used**: From ccusage report
     - **Estimated Cost**: From ccusage report
     - **Time Spent**: Duration of your session
     - **Satisfaction**: Rate the experience

This data helps track efficiency and costs.

---

## Using OpenSpec Commands

### Cursor

Use slash commands directly in Cursor:

```
/opsx-new PROJ-123
/opsx-explore
/opsx-apply
/opsx-archive
```

### Codex

Use slash commands in Codex (same as Cursor):

```
/opsx-new PROJ-123
/opsx-explore
/opsx-apply
/opsx-archive
```

Both work identically!

---

## OpenAI API Key Setup

Your OpenAI API key will be shared separately via:
- Direct message
- Email
- Secure channel (1Password, etc.)

### Verify Your Key is Set

```bash
# Test in Codex:
/opsx-new TEST-001
# If the key is set up, it will work
# If not, you'll see an API error

# Or check the environment:
echo $OPENAI_API_KEY
# Should output: sk-...
```

### Troubleshooting

**"No API key found" error:**
1. Check your shell profile:
   ```bash
   cat ~/.bashrc | grep OPENAI_API_KEY
   ```
2. If it's there, reload your shell:
   ```bash
   source ~/.bashrc
   ```
3. If it's not there, add it manually

**"Permission denied" or "Invalid key" error:**
1. Verify the key format starts with `sk-`
2. Check there are no extra spaces:
   ```bash
   export OPENAI_API_KEY="sk-abc123..."  # ✓ Correct
   export OPENAI_API_KEY=" sk-abc123..." # ✗ Wrong (space at start)
   ```

---

## Running Your First Change

Both Cursor and Codex users follow the same workflow:

### 1. Start a New Change

```
/opsx-new PROJ-123
```

Replace `PROJ-123` with your actual Jira ticket ID.

### 2. Explore the Specification

The command generates a detailed specification. Read it and interact:

```
/opsx-explore
```

### 3. Implement the Change

Follow the generated spec and implement the required changes.

### 4. Apply & Test

Apply the changes:

```
/opsx-apply
```

Run tests and verify your implementation.

### 5. Archive Your Work (Mandatory)

When complete, archive and capture feedback:

```
/opsx-archive
```

This is required for compliance tracking.

### 6. Publish Metrics (Recommended)

Share your results to the dashboard:

```
/opsx-publish-metrics PROJ-123
```

---

## Common Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `/opsx-new` | Start a new OpenSpec change | `/opsx-new PROJ-123` |
| `/opsx-explore` | Review the spec | `/opsx-explore` |
| `/opsx-apply` | Apply changes from the spec | `/opsx-apply` |
| `/opsx-archive` | Complete & archive (mandatory) | `/opsx-archive` |
| `/opsx-continue` | Continue to next phase | `/opsx-continue` |
| `/opsx-e2e` | Generate E2E tests | `/opsx-e2e` |
| `/opsx-publish-metrics` | Publish to dashboard | `/opsx-publish-metrics PROJ-123` |
| `/opsx-cve-analyze` | Analyze security impacts | `/opsx-cve-analyze` | (Stand Alone Command)


---

## Troubleshooting

### Commands Not Showing Up

**Cursor:**
1. Did you restart Cursor? (Close and reopen completely)
2. Check `.cursor/commands/` exists:
   ```bash
   ls -la .cursor/commands/ | grep opsx
   ```

**Codex:**
1. Did you run the installer?
   ```bash
   ./scripts/install-codex-commands.sh
   ```
2. Did you restart Codex? (Close and reopen VS Code)
3. Check commands were installed:
   ```bash
   ls -la ~/.codex/prompts/ | grep opsx
   ```

### API Key Not Working

```bash
# 1. Verify the key is set:
echo $OPENAI_API_KEY

# 2. If empty, add to your shell profile and reload:
export OPENAI_API_KEY="sk-YOUR_KEY_HERE"
source ~/.bashrc  # or ~/.zshrc

# 3. Test a command:
/opsx-new TEST-001
```

### Installation Script Failed

```bash
# 1. Check script exists:
ls -la ./scripts/install-codex-commands.sh

# 2. Make it executable:
chmod +x ./scripts/install-codex-commands.sh

# 3. Run with explicit bash:
bash ./scripts/install-codex-commands.sh

# 4. Check destination directory:
mkdir -p ~/.codex/prompts
ls -la ~/.codex/prompts/
```

### Codex Not Finding Commands After Install

1. **Restart Codex completely** (not just reload, but close and reopen)
2. Check the commands are in the right place:
   ```bash
   ls ~/.codex/prompts/opsx-*.md
   ```
3. Check your Codex version is up to date:
   ```bash
   codex --version
   ```

---

## Need Help?

If you encounter issues:

1. **Check this guide** — scroll to [Troubleshooting](#troubleshooting)
2. **Verify your setup:**
   ```bash
   # Cursor users:
   ls -la .cursor/commands/opsx-*.md
   
   # Codex users:
   ls -la ~/.codex/prompts/opsx-*.md
   echo $OPENAI_API_KEY
   ```
3. **Contact your team** with:
   - Which editor you're using (Cursor or Codex)
   - The exact error message
   - The command you ran
   - Output of the setup verification above

---

## Quick Reference

### Setup Checklist

- [ ] Ran the one-liner install (`curl ... | bash -s -- /path/to/project`)
- [ ] Set `OPENAI_API_KEY` environment variable
- [ ] **Cursor users:** Restarted Cursor
- [ ] **Codex users:** Used `--codex` flag (or ran `./scripts/install-codex-commands.sh`) and restarted Codex
- [ ] Verified commands work: `/opsx-new TEST-001`

### First Change Workflow

```bash
/opsx-new PROJ-123      # Create
/opsx-explore           # Review spec
# ... implement changes ...
/opsx-apply             # Apply changes
/opsx-archive           # Archive (mandatory)
/opsx-publish-metrics   # Share results (optional)
```




---

**Last Updated:** 2026-09-23
