"""Unread digest — "what needs my attention", grouped by sender or by thread.

Thin caller of the MCP agent. Claude calls list_unread to see everything
outstanding, groups it (by sender or by thread), and writes a short description
per email. Sender grouping renders as:

    Unread Digest (7 emails):

    From Sarah Chen (2):
    - Sprint planning Thursday at 10am
    - Needs decision on Mobile v2.0 offline sync

Thread grouping uses "Thread: <subject> (n):" headers instead.
"""

from __future__ import annotations

from constants import PRIMARY_USER
from agents.mcp_client import run_agent

# Per-mode instruction for what each group's label/key should be.
_GROUPING = {
    "sender": (
        "Group the unread emails by sender. For each group, `label` is a human "
        "display name derived from the sender's address "
        "(e.g. sarah.chen@acme.com -> 'Sarah Chen') and `key` is the sender's "
        "email address."
    ),
    "thread": (
        "Group the unread emails by thread. For each group, `label` is a short, "
        "readable version of the thread's subject and `key` is the thread_id."
    ),
}

_SYSTEM_BASE = (
    f"You are an assistant to {PRIMARY_USER}, a product manager at Acme Corp. "
    "Build a digest of their unread email. Use the list_unread tool to see what's "
    "outstanding."
)

_SYSTEM_TAIL = (
    "For each email give one short description (a few words capturing the gist; "
    "prefix it with 'URGENT:' when the email is genuinely urgent). List the most "
    "pressing groups first. total_unread is the total count of unread emails. "
    "Ground everything in the actual emails."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "total_unread": {"type": "integer"},
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "key": {"type": "string"},
                    "count": {"type": "integer"},
                    "emails": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"description": {"type": "string"}},
                            "required": ["description"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["label", "key", "count", "emails"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["total_unread", "groups"],
    "additionalProperties": False,
}


def _format(total_unread: int, groups: list[dict], group_by: str) -> str:
    """Render the digest as a grouped text block."""
    header_prefix = "From " if group_by == "sender" else "Thread: "
    lines = [f"Unread Digest ({total_unread} emails):", ""]
    for group in groups:
        lines.append(f"{header_prefix}{group['label']} ({group['count']}):")
        for email in group["emails"]:
            lines.append(f"- {email['description']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_digest(group_by: str = "sender") -> dict:
    """Build the unread digest, grouped by 'sender' or 'thread'.

    Returns structured data, the formatted text, and the MCP tool trace.
    """
    if group_by not in _GROUPING:
        group_by = "sender"

    system = f"{_SYSTEM_BASE} {_GROUPING[group_by]} {_SYSTEM_TAIL}"
    prompt = f"Build my unread email digest, grouped by {group_by}."
    result = run_agent(
        prompt, system=system, schema=SCHEMA,
        tools=["list_unread", "search_emails"],
    )
    data = result["data"]
    return {
        "group_by": group_by,
        **data,
        "formatted": _format(data["total_unread"], data["groups"], group_by),
        "tool_calls": result["tool_calls"],
    }
