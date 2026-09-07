"""Closed-bundle context reader for openspec.llm_gen stages.

Reads ONLY the exact dependency files a stage declares — never greps or globs
the repository. This is the same "pack a closed bundle... fail closed"
discipline already documented in cost-optimization-stratergy.md, now enforced
in code instead of by agent instruction-following.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CHANGES_DIR = Path("openspec/changes")
SCHEMA_ROOT = Path("openspec/schemas/openspec-agile-workflow")
TEMPLATES_DIR = SCHEMA_ROOT / "templates"


def change_dir(change: str) -> Path:
    return CHANGES_DIR / change


def read_text(path: Path, default: str = "") -> str:
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    return default


def read_or_not_provided(path: Path) -> tuple[str, bool]:
    """Returns (content, provided). When absent/empty, content is the literal
    'NOT_PROVIDED' marker string the templates' own User Message Template
    sections expect for optional inputs."""
    text = read_text(path, "")
    if text.strip():
        return text, True
    return "NOT_PROVIDED", False


def read_template(template_name: str) -> str:
    """Read a schema template file, e.g. 'validation-template.md' or
    'tasks-modes/single-template.md'."""
    path = TEMPLATES_DIR / template_name
    text = read_text(path, "")
    if not text:
        raise FileNotFoundError(f"Schema template not found: {path}")
    return text


def read_agents_md(repo_root: Path) -> tuple[str, bool]:
    """agents.md is resolved via lookup order: target repo root → change
    inputs/ → schema inputs/ (per schema.yaml). Only the repo-root location is
    read here since that's the only one populated for non-agentic stages."""
    for name in ("agents.md", "AGENTS.md"):
        p = repo_root / name
        text = read_text(p, "")
        if text.strip():
            return text, True
    return "NOT_PROVIDED", False


def read_constitution_md(repo_root: Path) -> tuple[str, bool]:
    text = read_text(repo_root / "harness-evals" / "constitution.md", "")
    return (text, True) if text.strip() else ("", False)


@dataclass
class ChangeInputs:
    jira_yaml: dict[str, Any] = field(default_factory=dict)
    jira_key: str = ""
    jira_spec_text: str = ""


def read_change_inputs(cdir: Path) -> ChangeInputs:
    import yaml

    jira_yaml_path = cdir / "inputs" / "jira.yaml"
    data: dict[str, Any] = {}
    if jira_yaml_path.exists():
        try:
            loaded = yaml.safe_load(jira_yaml_path.read_text(encoding="utf-8"))
            data = loaded if isinstance(loaded, dict) else {}
        except Exception:
            data = {}
    jira_spec = read_text(cdir / "inputs" / "jira-spec.md")
    return ChangeInputs(jira_yaml=data, jira_key=data.get("jira_key", ""), jira_spec_text=jira_spec)
