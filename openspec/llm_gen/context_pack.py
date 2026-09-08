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


# ============================================================================
# Phase-Scoped Context Bundling (Cost Optimization)
# ============================================================================


def extract_phase_from_plan(plan_text: str, phase_number: int) -> str:
    """Extract only Phase N section from plan.md.

    Returns the specified phase's content (Goal, Dependencies, Target files,
    Verification) while excluding all other phases. This reduces token count
    by 70-80% when generating tasks for phase-iterative mode.

    Args:
        plan_text: Full plan.md content
        phase_number: Phase to extract (1-based)

    Returns:
        Phase N section only, or full plan if extraction fails
    """
    import re

    if not plan_text or plan_text == "NOT_PROVIDED":
        return plan_text

    # Look for phase markers like "## Phase 1", "### Phase 1", etc.
    # Common patterns: "## Phase N", "### Phase N:", "## §N Phase N"
    phase_pattern = rf"^(#{2,3})\s*(?:§{phase_number}\s+)?Phase\s+{phase_number}\b"

    lines = plan_text.split("\n")
    phase_start = None
    phase_end = None
    header_level = None

    for i, line in enumerate(lines):
        match = re.match(phase_pattern, line, re.IGNORECASE)
        if match:
            phase_start = i
            header_level = len(match.group(1))  # Number of # symbols
            break

    if phase_start is None:
        # Phase not found, return full plan to avoid breaking generation
        return plan_text

    # Find where this phase ends (next same-level or higher header)
    for i in range(phase_start + 1, len(lines)):
        # Match any header at the same or higher level
        header_match = re.match(r"^(#{1,6})\s+", lines[i])
        if header_match:
            next_level = len(header_match.group(1))
            if next_level <= header_level:
                phase_end = i
                break

    # Extract the phase section
    if phase_end is None:
        phase_section = "\n".join(lines[phase_start:])
    else:
        phase_section = "\n".join(lines[phase_start:phase_end])

    # Add minimal header context (document title + phase section)
    header_lines = []
    for i, line in enumerate(lines[:phase_start]):
        if line.startswith("#"):
            header_lines.append(line)
            if i > 5:  # Only keep first few headers
                break

    if header_lines:
        context = "\n".join(header_lines[:3]) + "\n\n" + phase_section
    else:
        context = phase_section

    return context.strip()


def extract_target_files_from_plan(plan_phase_text: str) -> list[str]:
    """Extract target file paths from a plan phase section.

    Looks for file paths mentioned in the plan (typically in 'Target files'
    or 'Implementation' sections). Used to filter repo-assessment.

    Args:
        plan_phase_text: Plan phase section content

    Returns:
        List of file paths found in the plan
    """
    import re

    if not plan_phase_text:
        return []

    # Common file path patterns in Go projects
    # - pkg/controllers/foo_controller.go
    # - api/v1/types.go
    # - internal/webhooks/validation.go
    file_pattern = r'\b[\w/.-]+\.(?:go|yaml|yml|md|json|txt|sh)\b'

    files = set()
    for match in re.finditer(file_pattern, plan_phase_text):
        file_path = match.group(0)
        # Filter out common false positives
        if not any(skip in file_path.lower() for skip in ['http', 'example.', 'foo.', 'test.']):
            files.add(file_path)

    return sorted(list(files))


def filter_assessment_by_files(assessment_text: str, target_files: list[str]) -> str:
    """Filter repo-assessment.md to only include relevant files for current phase.

    Reduces assessment context by keeping only the files mentioned in the plan's
    target files list, plus their immediate dependencies.

    Args:
        assessment_text: Full repo-assessment.md content
        target_files: List of target file paths from plan

    Returns:
        Filtered assessment with only relevant files
    """
    if not assessment_text or assessment_text == "NOT_PROVIDED":
        return assessment_text

    if not target_files:
        # No target files specified, return full assessment
        return assessment_text

    # Extract file entries from assessment
    # Typical format: "### path/to/file.go" or "#### path/to/file.go"
    import re

    lines = assessment_text.split("\n")
    filtered_lines = []
    current_file_relevant = False
    header_lines = []

    # Keep document header (title, summary, etc.)
    for i, line in enumerate(lines):
        if line.startswith("###"):
            break
        header_lines.append(line)

    filtered_lines.extend(header_lines)

    # Process file sections
    for line in lines[len(header_lines):]:
        # Check if this is a file header
        file_header_match = re.match(r"^#{3,4}\s+(.+)$", line)

        if file_header_match:
            file_path = file_header_match.group(1).strip()
            # Check if this file is in target files or matches pattern
            current_file_relevant = any(
                target in file_path or file_path in target
                for target in target_files
            )

        if current_file_relevant or line.startswith("#"):
            filtered_lines.append(line)

    # If filtering resulted in just headers, return full assessment
    # (better to have too much context than too little)
    filtered_text = "\n".join(filtered_lines).strip()
    if len(filtered_text) < len(assessment_text) * 0.1:
        return assessment_text

    return filtered_text


def get_prior_phase_task_ids(tasks_text: str, current_phase: int) -> list[str]:
    """Extract task IDs from prior phases (for dependency references).

    When generating Phase N tasks, we need to know completed task IDs from
    Phases 1..N-1 for DAG dependencies, but we don't need full task payloads.
    This extracts just the IDs.

    Args:
        tasks_text: Full tasks.md content from prior phases
        current_phase: Current phase number (1-based)

    Returns:
        List of task IDs from phases 1..current_phase-1 (e.g., ["T1_1", "T1_2", "T2_1"])
    """
    import re

    if not tasks_text or current_phase <= 1:
        return []

    # Match task IDs like T1_1, T2_3, etc.
    # Typically found in task manifest tables or headers
    task_id_pattern = r'\bT(\d+)_(\d+)\b'

    task_ids = []
    for match in re.finditer(task_id_pattern, tasks_text):
        phase_num = int(match.group(1))
        if phase_num < current_phase:
            task_ids.append(match.group(0))

    return sorted(list(set(task_ids)))
