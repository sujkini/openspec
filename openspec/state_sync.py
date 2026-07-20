"""State synchronisation to a dedicated git repository.

Commits and pushes ``openspec/changes/<change>/`` artifacts to a remote
branch after each phase completes.  This enables multi-owner handover:
the next phase owner runs ``/opsx-resume`` to pull the branch and
continue from where the previous owner left off.

Configuration lives in ``openspec/config.yaml`` under ``state_sync``.
The remote URL and auth token are read from environment variables
(defaults: ``OPENSPEC_STATE_REPO`` and ``GIT_TOKEN``).

All operations are **best-effort** — a push failure logs a warning but
never blocks the workflow.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

CHANGES_DIR = Path("openspec/changes")
_CACHE_ROOT = Path(tempfile.gettempdir()) / "openspec-state-cache"


def _load_sync_config() -> dict[str, Any]:
    """Read ``state_sync`` block from ``openspec/config.yaml``."""
    cfg_path = Path("openspec/config.yaml")
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text()) or {}
        return data.get("state_sync", {})
    except Exception:
        return {}


def _repo_url(config: dict[str, Any]) -> str:
    env_var = config.get("repo_env_var", "OPENSPEC_STATE_REPO")
    return os.environ.get(env_var, "").strip()


def _auth_token(config: dict[str, Any]) -> str:
    env_var = config.get("token_env_var", "GIT_TOKEN")
    return os.environ.get(env_var, "").strip()


def _authenticated_url(repo_url: str, token: str) -> str:
    """Inject a token into an HTTPS repo URL for git operations."""
    if not token or not repo_url.startswith("https://"):
        return repo_url
    return repo_url.replace("https://", f"https://x-access-token:{token}@", 1)


def _normalize_repo_url(url: str) -> str:
    """Normalize repo URLs for comparison (strip auth, trailing .git)."""
    if "@" in url and "://" in url:
        url = url.split("://", 1)[1]
        url = url.split("@", 1)[1]
    else:
        url = url.split("://", 1)[-1]
    return url.rstrip("/").removesuffix(".git").lower()


def _run(cmd: list[str], cwd: str | Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=cwd, check=check)


def _ensure_clone(repo_url: str, token: str) -> Path:
    """Clone (or re-use) the state repo into a local cache directory."""
    _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    clone_dir = _CACHE_ROOT / "repo"

    auth_url = _authenticated_url(repo_url, token)
    expected = _normalize_repo_url(repo_url)

    if (clone_dir / ".git").exists():
        current = _run(["git", "remote", "get-url", "origin"], cwd=clone_dir, check=False)
        current_url = current.stdout.strip() if current.returncode == 0 else ""
        if current_url and _normalize_repo_url(current_url) != expected:
            logger.info(
                "state_sync: remote changed (%s -> %s), re-cloning cache",
                current_url,
                repo_url,
            )
            shutil.rmtree(clone_dir)
        else:
            _run(["git", "remote", "set-url", "origin", auth_url], cwd=clone_dir, check=False)
            _run(["git", "fetch", "--all", "--prune"], cwd=clone_dir, check=False)
            return clone_dir

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    _run(["git", "clone", "--no-checkout", auth_url, str(clone_dir)])
    return clone_dir


def _branch_name(jira_key: str, change_slug: str, config: dict[str, Any]) -> str:
    pattern = config.get("branch_pattern", "{jira_key}/{change_slug}")
    return pattern.format(jira_key=jira_key, change_slug=change_slug)


def _checkout_branch(clone_dir: Path, branch: str) -> None:
    """Checkout the branch, creating it from the default branch if needed."""
    remote_ref = f"refs/remotes/origin/{branch}"
    local_ref = f"refs/heads/{branch}"

    remote = _run(["git", "rev-parse", "--verify", remote_ref], cwd=clone_dir, check=False)
    if remote.returncode == 0:
        _run(["git", "checkout", "-B", branch, remote_ref], cwd=clone_dir)
        return

    local = _run(["git", "rev-parse", "--verify", local_ref], cwd=clone_dir, check=False)
    if local.returncode == 0:
        _run(["git", "checkout", branch], cwd=clone_dir)
        return

    default = _run(
        ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
        cwd=clone_dir,
        check=False,
    )
    base = default.stdout.strip().replace("origin/", "") if default.returncode == 0 else "main"
    base_ref = f"refs/remotes/origin/{base}"
    base_exists = _run(["git", "rev-parse", "--verify", base_ref], cwd=clone_dir, check=False)
    if base_exists.returncode == 0:
        _run(["git", "checkout", "-B", branch, base_ref], cwd=clone_dir)
        return

    _run(["git", "checkout", "--orphan", branch], cwd=clone_dir)
    _run(["git", "rm", "-rf", "--ignore-unmatch", "."], cwd=clone_dir, check=False)


def _copy_artifacts(change_dir: Path, clone_dir: Path) -> None:
    """Copy all change artifacts into the clone working tree."""
    target = clone_dir / "openspec" / "changes" / change_dir.name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        change_dir,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".dashboard.json"),
    )


def _commit_and_push(clone_dir: Path, branch: str, message: str, token: str, repo_url: str) -> str:
    """Stage, commit, and push.  Returns the commit SHA or empty string."""
    _run(["git", "add", "-A"], cwd=clone_dir)

    status = _run(["git", "status", "--porcelain"], cwd=clone_dir)
    if not status.stdout.strip():
        logger.info("state_sync: nothing to commit")
        return ""

    _run(["git", "-c", "user.name=openspec-bot", "-c", "user.email=openspec-bot@noreply",
          "commit", "-m", message], cwd=clone_dir)

    auth_url = _authenticated_url(repo_url, token)
    _run(["git", "push", auth_url, f"HEAD:{branch}"], cwd=clone_dir)

    sha = _run(["git", "rev-parse", "HEAD"], cwd=clone_dir)
    return sha.stdout.strip()


def sync_state(change: str, phase_name: str, jira_key: str) -> str:
    """Commit and push change artifacts to the state repo.

    Returns the commit SHA on success, empty string otherwise.
    Best-effort: logs warnings on failure but never raises.
    """
    config = _load_sync_config()
    if not config.get("enabled", False):
        logger.debug("state_sync: disabled in config")
        return ""

    repo_url = _repo_url(config)
    if not repo_url:
        logger.warning("state_sync: no repo URL configured (env var %s)", config.get("repo_env_var", "OPENSPEC_STATE_REPO"))
        return ""

    token = _auth_token(config)
    change_dir = CHANGES_DIR / change

    if not change_dir.exists():
        logger.warning("state_sync: change dir %s does not exist", change_dir)
        return ""

    change_slug = change
    branch = _branch_name(jira_key, change_slug, config)
    message = f"[openspec] {phase_name} complete - {jira_key}"

    try:
        clone_dir = _ensure_clone(repo_url, token)
        _checkout_branch(clone_dir, branch)
        _copy_artifacts(change_dir, clone_dir)
        sha = _commit_and_push(clone_dir, branch, message, token, repo_url)
        if sha:
            logger.info("state_sync: pushed %s to %s (branch %s)", sha[:8], repo_url, branch)
        return sha
    except Exception as exc:
        logger.warning("state_sync: failed to push state: %s", exc, exc_info=True)
        return ""


def pull_state(jira_key: str, change_slug: str | None = None) -> tuple[str, Path]:
    """Pull state from the state repo for ``/opsx-resume``.

    Returns ``(branch_name, temp_dir)`` where *temp_dir* contains the
    pulled ``openspec/changes/<change>/`` tree.

    Raises ``RuntimeError`` on failure.
    """
    config = _load_sync_config()
    repo_url = _repo_url(config)
    if not repo_url:
        raise RuntimeError("OPENSPEC_STATE_REPO not configured")

    token = _auth_token(config)
    clone_dir = _ensure_clone(repo_url, token)

    _run(["git", "fetch", "--all", "--prune"], cwd=clone_dir, check=False)

    result = _run(["git", "branch", "-r"], cwd=clone_dir)
    branches = [b.strip().removeprefix("origin/") for b in result.stdout.splitlines()]
    matching = [b for b in branches if b.startswith(f"{jira_key}/")]

    if not matching:
        raise RuntimeError(f"No state branches found for {jira_key}")

    if change_slug:
        exact = [b for b in matching if b == f"{jira_key}/{change_slug}"]
        branch = exact[0] if exact else matching[0]
    else:
        branch = matching[0]

    _run(["git", "checkout", "-B", branch, f"refs/remotes/origin/{branch}"], cwd=clone_dir)

    changes_root = clone_dir / "openspec" / "changes"
    if not changes_root.exists():
        raise RuntimeError(f"Branch {branch} has no openspec/changes/ directory")

    change_dirs = [d for d in changes_root.iterdir() if d.is_dir()]
    if not change_dirs:
        raise RuntimeError(f"Branch {branch} has no change directories")

    return branch, change_dirs[0]


def list_branches(jira_key: str) -> list[str]:
    """List state repo branches matching a Jira key prefix."""
    config = _load_sync_config()
    repo_url = _repo_url(config)
    if not repo_url:
        return []

    token = _auth_token(config)
    try:
        clone_dir = _ensure_clone(repo_url, token)
        _run(["git", "fetch", "--all", "--prune"], cwd=clone_dir, check=False)
        result = _run(["git", "branch", "-r"], cwd=clone_dir)
        branches = [b.strip().removeprefix("origin/") for b in result.stdout.splitlines()]
        return [b for b in branches if b.startswith(f"{jira_key}/")]
    except Exception:
        return []