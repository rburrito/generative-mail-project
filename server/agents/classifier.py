"""Thread classification — structured output over the MCP agent.

Same thin-caller pattern as the summarizer, but passes a JSON schema to
run_agent() so Claude's answer comes back as a validated dict instead of prose.
This is the structured-output building block the digest and synthesizer reuse.

Fields:
    urgency       - how soon it needs attention
    thread_state  - who the ball is with, from the PM's point of view
    category      - rough topic bucket
    reason        - one-line justification (keeps the labels auditable)
"""

from __future__ import annotations

from constants import PRIMARY_USER
from agents.mcp_client import run_agent

SYSTEM = (
    f"You are an assistant to {PRIMARY_USER}, a product manager at Acme Corp. "
    "You triage email threads. Read the thread with the get_thread tool, then "
    "classify it from the PM's point of view. thread_state values:\n"
    "- waiting_on_me: the PM owes the next substantive reply or action.\n"
    "- waiting_on_them: someone else owes the next substantive action.\n"
    "- resolved: the substantive decision was made or the ask was fulfilled; "
    "routine trailing follow-ups (e.g. 'I'll update the roadmap') do not keep it "
    "open.\n"
    "- fyi: an informational message — a report or heads-up that doesn't request a "
    "reply or a decision (it may still include recommendations).\n"
    "Base every label on what the emails actually say."
)

# JSON Schema for the structured output. additionalProperties:false and an
# explicit required list are mandatory for structured outputs.
SCHEMA = {
    "type": "object",
    "properties": {
        "urgency": {
            "type": "string",
            "enum": ["urgent", "high", "normal", "low"],
        },
        "thread_state": {
            "type": "string",
            "enum": ["waiting_on_me", "waiting_on_them", "resolved", "fyi"],
        },
        "category": {
            "type": "string",
            "enum": [
                "launch",
                "product_decision",
                "customer_issue",
                "sales",
                "internal_update",
                "recognition",
                "other",
            ],
        },
        "reason": {"type": "string"},
    },
    "required": ["urgency", "thread_state", "category", "reason"],
    "additionalProperties": False,
}


def classify_thread(thread_id: str) -> dict:
    """Classify one thread. Returns the labels plus the MCP tool trace."""
    prompt = (
        f"Classify the email thread with thread_id '{thread_id}'. "
        "Read it first with the get_thread tool."
    )
    result = run_agent(prompt, system=SYSTEM, schema=SCHEMA, tools=["get_thread"])
    return {
        "thread_id": thread_id,
        **result["data"],
        "tool_calls": result["tool_calls"],
    }
