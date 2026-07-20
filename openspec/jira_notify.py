"""Jira comment notification templates for the RBAC handover flow.

This module formats comment bodies that the Cursor commands post via the
Atlassian MCP ``jira_add_comment`` tool.  It does **not** call Jira
directly — it only produces the text.

Red Hat uses Jira Cloud (``redhat.atlassian.net``).  User mentions use
the ``[~accountid:<id>]`` shorthand which Jira Cloud renders as a
clickable @mention and triggers an email notification.
"""
from __future__ import annotations


def _mention(jira_account_id: str, display_name: str = "") -> str:
    """Format an @mention for Jira Cloud."""
    if jira_account_id:
        return f"[~accountid:{jira_account_id}]"
    if display_name:
        return f"@{display_name}"
    return ""


def format_phase_complete_comment(
    *,
    phase_name: str,
    status: str,
    quality_score: float = 0,
    iteration_count: int = 1,
    artifact_list: str = "",
    state_repo_branch: str = "",
    owner_account_id: str = "",
    owner_display_name: str = "",
) -> str:
    score_str = f"{quality_score:.0f}%" if quality_score else "N/A"
    owner_mention = _mention(owner_account_id, owner_display_name)

    lines = [
        f'*[OpenSpec]* Phase "{phase_name}" completed successfully.',
        "",
        f"||Status|{status}||Quality|{score_str}||Iterations|{iteration_count}||",
    ]
    if artifact_list:
        lines.append(f"Artifacts: {artifact_list}")
    if state_repo_branch:
        lines.append(f"State branch: {{noformat}}{state_repo_branch}{{noformat}}")
    if owner_mention:
        lines.append(f"Phase owner: {owner_mention}")

    return "\n".join(lines)


def format_handover_comment(
    *,
    completed_phase: str,
    next_phase: str,
    current_owner_account_id: str = "",
    current_owner_display: str = "",
    next_owner_account_id: str = "",
    next_owner_display: str = "",
    artifact_list: str = "",
    state_repo_url: str = "",
    state_branch: str = "",
    jira_key: str = "",
) -> str:
    current_mention = _mention(current_owner_account_id, current_owner_display)
    next_mention = _mention(next_owner_account_id, next_owner_display)

    lines = [
        f'*[OpenSpec]* Phase handover: "{completed_phase}" → "{next_phase}"',
        "",
        f'"{completed_phase}" has been completed by {current_mention}.',
        f'The next phase "{next_phase}" is assigned to {next_mention}.',
        "",
        f"*Action required:* {next_mention} please run {{noformat}}/opsx-resume {jira_key}{{noformat}} then {{noformat}}/opsx-continue{{noformat}} in your Cursor workspace to proceed.",
    ]
    if artifact_list:
        lines.extend(["", "Artifacts from completed phase:", artifact_list])
    if state_repo_url and state_branch:
        lines.append(f"State branch: [{state_branch}|{state_repo_url}/tree/{state_branch}]")

    return "\n".join(lines)


def format_run_complete_comment(
    *,
    jira_key: str,
    phases_summary: str = "",
    state_repo_url: str = "",
    state_branch: str = "",
    epic_owner_account_id: str = "",
    epic_owner_display: str = "",
) -> str:
    epic_mention = _mention(epic_owner_account_id, epic_owner_display)

    lines = [
        f"*[OpenSpec]* All phases complete for {jira_key}.",
    ]
    if epic_mention:
        lines.append(f"cc {epic_mention}")
    if phases_summary:
        lines.extend(["", "Summary:", phases_summary])
    if state_repo_url and state_branch:
        lines.append(f"\nAll artifacts: [{state_branch}|{state_repo_url}/tree/{state_branch}]")

    return "\n".join(lines)


def format_phase_failed_comment(
    *,
    phase_name: str,
    error_summary: str = "",
    owner_account_id: str = "",
    owner_display_name: str = "",
    epic_owner_account_id: str = "",
    epic_owner_display: str = "",
) -> str:
    owner_mention = _mention(owner_account_id, owner_display_name)
    epic_mention = _mention(epic_owner_account_id, epic_owner_display)

    lines = [
        f'*[OpenSpec]* Phase "{phase_name}" *failed*.',
    ]
    if owner_mention:
        lines.append(f"Phase owner: {owner_mention}")
    if epic_mention:
        lines.append(f"Epic owner: {epic_mention}")
    if error_summary:
        lines.extend(["", f"Error: {error_summary}"])

    return "\n".join(lines)
