"""RBAC phase-ownership module for multi-owner handover.

Loads ``inputs/rbac.yaml`` from a change directory and provides helpers
to look up phase owners, determine handover needs, and validate the
configuration.

Phase ordering follows the openspec-agile-workflow schema:
  spec_understanding → repo_assessment → arch_planning →
  subtask_creation → code_generation
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PHASE_ORDER: list[str] = [
    "spec_understanding",
    "repo_assessment",
    "arch_planning",
    "subtask_creation",
    "code_generation",
]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class PhaseOwner:
    owner: str
    display_name: str = ""
    jira_account_id: str = ""


@dataclass
class RBACConfig:
    epic_owner: str = ""
    phase_owners: dict[str, PhaseOwner] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return bool(self.phase_owners)


def load_rbac_config(change_dir: Path) -> RBACConfig:
    """Load and parse ``inputs/rbac.yaml`` from a change directory.

    Returns an empty (disabled) config if the file does not exist.
    """
    rbac_path = change_dir / "inputs" / "rbac.yaml"
    if not rbac_path.exists():
        return RBACConfig()

    data: dict[str, Any] = yaml.safe_load(rbac_path.read_text()) or {}
    config = RBACConfig(epic_owner=data.get("epic_owner", ""))

    for phase_name, info in (data.get("phase_owners") or {}).items():
        if isinstance(info, dict):
            config.phase_owners[phase_name] = PhaseOwner(
                owner=info.get("owner", ""),
                display_name=info.get("display_name", ""),
                jira_account_id=info.get("jira_account_id", ""),
            )
        elif isinstance(info, str):
            config.phase_owners[phase_name] = PhaseOwner(owner=info)

    return config


def save_rbac_config(change_dir: Path, config: RBACConfig) -> None:
    """Persist the RBAC config (including cached Jira account IDs)."""
    rbac_path = change_dir / "inputs" / "rbac.yaml"
    rbac_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {"epic_owner": config.epic_owner, "phase_owners": {}}
    for phase_name, po in config.phase_owners.items():
        entry: dict[str, str] = {"owner": po.owner}
        if po.display_name:
            entry["display_name"] = po.display_name
        if po.jira_account_id:
            entry["jira_account_id"] = po.jira_account_id
        data["phase_owners"][phase_name] = entry

    rbac_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def get_phase_owner(config: RBACConfig, phase_name: str) -> PhaseOwner | None:
    """Return the assigned owner for a phase, or ``None``."""
    return config.phase_owners.get(phase_name)


def get_next_phase_owner(config: RBACConfig, current_phase: str) -> PhaseOwner | None:
    """Return the owner of the phase that follows *current_phase*."""
    try:
        idx = PHASE_ORDER.index(current_phase)
    except ValueError:
        return None
    if idx + 1 >= len(PHASE_ORDER):
        return None
    return config.phase_owners.get(PHASE_ORDER[idx + 1])


def get_next_phase_name(current_phase: str) -> str | None:
    """Return the name of the phase that follows *current_phase*."""
    try:
        idx = PHASE_ORDER.index(current_phase)
    except ValueError:
        return None
    if idx + 1 >= len(PHASE_ORDER):
        return None
    return PHASE_ORDER[idx + 1]


def is_handover_needed(config: RBACConfig, current_phase: str) -> bool:
    """True if the current and next phase have *different* owners."""
    if not config.enabled:
        return False
    current = get_phase_owner(config, current_phase)
    nxt = get_next_phase_owner(config, current_phase)
    if not current or not nxt:
        return False
    return current.owner.lower() != nxt.owner.lower()


def validate_rbac_config(config: RBACConfig) -> list[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors: list[str] = []

    if config.epic_owner and not _EMAIL_RE.match(config.epic_owner):
        errors.append(f"Invalid epic_owner email: {config.epic_owner}")

    for phase_name in PHASE_ORDER:
        owner = config.phase_owners.get(phase_name)
        if not owner:
            continue
        if not _EMAIL_RE.match(owner.owner):
            errors.append(f"Invalid email for {phase_name}: {owner.owner}")

    unknown = set(config.phase_owners.keys()) - set(PHASE_ORDER)
    if unknown:
        errors.append(f"Unknown phase names: {', '.join(sorted(unknown))}")

    return errors
