"""Sender topic clustering.

Input:  a sender's email address.
Output: that sender's emails grouped into topic clusters, each with examples.

Renders as:

    Sender: sarah.chen@acme.com (8 emails)

    Topics:
    1. Technical decisions (4 emails)
       - Mobile offline sync architecture
       - API refactor results

    2. Sprint planning (3 emails)
       - Phoenix punch list prioritization
       - Thursday planning invite

Thin caller of the MCP agent: it fetches all of the sender's emails via the
emails_from_sender tool, then groups them into topic clusters. Clustering is done
by the model (not k-means) — at this scale that yields clean, labeled clusters in
a single structured call, which embedding clustering would still need an LLM to
label anyway.
"""

from __future__ import annotations

from constants import PRIMARY_USER
from agents.mcp_client import run_agent

SYSTEM = (
    f"You are an assistant to {PRIMARY_USER}, a product manager at Acme Corp. "
    "Given a sender's address, fetch all of their emails with the "
    "emails_from_sender tool, then group those emails into topic clusters by "
    "subject matter. Aim for 2-5 meaningful clusters. total_emails is the total "
    "number of emails from that sender. For each cluster give a short topic label, "
    "a one-line summary, how many emails it contains (email_count), and a few "
    "short example labels (a few words each describing an email). Every example "
    "must correspond to a real email from that sender — do not invent."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "sender": {"type": "string"},
        "total_emails": {"type": "integer"},
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "summary": {"type": "string"},
                    "email_count": {"type": "integer"},
                    "examples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "thread_id": {"type": "string"},
                            },
                            "required": ["label", "thread_id"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["topic", "summary", "email_count", "examples"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["sender", "total_emails", "clusters"],
    "additionalProperties": False,
}


def _format(sender: str, total_emails: int, clusters: list[dict]) -> str:
    """Render the clusters as the numbered-topics text block."""
    lines = [f"Sender: {sender} ({total_emails} emails)", "", "Topics:"]
    for i, cluster in enumerate(clusters, 1):
        lines.append(f"{i}. {cluster['topic']} ({cluster['email_count']} emails)")
        for example in cluster["examples"]:
            lines.append(f"   - {example['label']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def cluster_by_sender(sender: str) -> dict:
    """Cluster a sender's emails by topic. Returns structured data, text, + tool trace."""
    prompt = (
        f"Analyze all emails from {sender} and group them into topic clusters. "
        "Fetch them first with the emails_from_sender tool."
    )
    result = run_agent(prompt, system=SYSTEM, schema=SCHEMA, tools=["emails_from_sender"])
    data = result["data"]
    return {
        **data,
        "formatted": _format(sender, data["total_emails"], data["clusters"]),
        "tool_calls": result["tool_calls"],
    }
