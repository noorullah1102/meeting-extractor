"""
Formatter
Converts extracted meeting data into plain text and HTML email bodies.
"""

import os
from collections import defaultdict

from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))


def _group_by_owner(action_items: list[dict]) -> dict[str, list[dict]]:
    """Group action items by owner, preserving order of first appearance."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in action_items:
        owner = item.get("owner", "Unassigned")
        groups[owner].append(item)
    return groups


def format_plain(data: dict) -> str:
    """Format extracted data as plain text for quick reading."""
    lines = []
    title = data.get("meeting_title") or "Meeting Notes"
    date = data.get("meeting_date") or "Unknown date"
    time = data.get("meeting_time") or ""
    lines.append(f"{title} — {date}")
    if time:
        lines.append(f"Time: {time}")
    lines.append("=" * 50)

    summary = data.get("summary")
    if summary:
        lines.append("")
        lines.append(f"Summary: {summary}")

    items = data.get("action_items", [])
    if items:
        lines.append("")
        lines.append("Action Items (by owner):")
        groups = _group_by_owner(items)
        for owner, tasks in groups.items():
            lines.append(f"\n  {owner}:")
            for task in tasks:
                due = task.get("due", "TBD")
                priority = task.get("priority", "Low")
                lines.append(f"    - {task['task']} (Due: {due}, Priority: {priority})")

    next_meeting = data.get("next_meeting")
    if next_meeting:
        lines.append("")
        lines.append(f"Next Meeting: {next_meeting}")

    return "\n".join(lines)


def format_html(data: dict) -> str:
    """Render the extracted data into an HTML email using Jinja2 template."""
    template = _env.get_template("email.html")
    items = data.get("action_items", [])
    return template.render(
        meeting_title=data.get("meeting_title"),
        meeting_date=data.get("meeting_date"),
        meeting_time=data.get("meeting_time"),
        next_meeting=data.get("next_meeting"),
        summary=data.get("summary"),
        attendees=data.get("attendees", []),
        action_items=items,
        grouped_items=_group_by_owner(items),
    )
