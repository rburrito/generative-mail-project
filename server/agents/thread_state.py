"""Thread state — classify where a thread stands and why.

Input:  a thread id.
Output: a state classification + explanation.

An LLM feature: judging whether a thread is blocked, waiting on the PM, resolved,
etc. is reasoning over the conversation, so it runs through the MCP agent
(get_thread). But the last-activity date and its relative time are exact facts,
so those are computed deterministically from the model's returned date rather
than trusting the model to do date math. Renders as:

    Thread: enterprise-dash-004 (Enterprise dashboard - Globex)

    State: BLOCKED - Waiting on Jennifer
    Last activity: Jan 14 (13 days ago)

    Context:
    - Jennifer said "I'll send over their full requirements doc tomorrow" (Jan 14)
    - Document hasn't arrived
    - You're blocked on scoping until you see their requirements
"""

from __future__ import annotations

from datetime import datetime

from constants import PRIMARY_USER
from agents.mcp_client import run_agent
from analytics import _relative_time  # reuse the deterministic "X ago" helper

SYSTEM = (
    f"You are an assistant to {PRIMARY_USER}, a product manager at Acme Corp. "
    "Determine the current state of an email thread from the PM's point of view. "
    "Read it with get_thread first. Choose one state:\n"
    "- WAITING_ON_ME: the PM owes the next substantive reply or decision (a "
    "routine 'I'll notify people' follow-up does not count).\n"
    "- BLOCKED: the thread is waiting on a specific person to deliver something "
    "they said they would; name that person in state_detail (e.g. 'Waiting on "
    "Jennifer').\n"
    "- ACTIVE: a healthy recent back-and-forth with no one clearly blocking.\n"
    "- RESOLVED: the substantive decision was made or the ask was fulfilled. "
    "Routine follow-ups the PM mentioned in passing (e.g. 'I'll update the "
    "roadmap', 'I'll let stakeholders know') do NOT keep it open — if the core "
    "question is settled, it's RESOLVED.\n"
    "- STALE: dormant, with no clear pending item and no recent activity; may just "
    "need a nudge or to be closed.\n"
    "Prefer BLOCKED or WAITING_ON_ME over STALE whenever there is a specific "
    "outstanding item, even if the thread is old. Put a short qualifier in "
    "state_detail (who/what it's waiting on); it may be empty for RESOLVED/ACTIVE. "
    "last_activity is the ISO date (YYYY-MM-DD) of the most recent email in the "
    "thread. context is 2-4 short bullet strings explaining the state, citing "
    "quotes and dates from the emails. Ground everything in the emails."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "state": {
            "type": "string",
            "enum": ["WAITING_ON_ME", "BLOCKED", "ACTIVE", "RESOLVED", "STALE"],
        },
        "state_detail": {"type": "string"},
        "last_activity": {"type": "string"},
        "context": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["subject", "state", "state_detail", "last_activity", "context"],
    "additionalProperties": False,
}


def _pretty_date(iso: str) -> tuple[str, str | None]:
    """Return ('Jan 14', '13 days ago') from an ISO date/datetime string."""
    try:
        when = datetime.fromisoformat(iso)
    except ValueError:
        return iso, None
    return f"{when:%b} {when.day}", _relative_time(when, datetime.now())


def _format(thread_id: str, data: dict) -> str:
    state_line = f"State: {data['state']}"
    detail = data["state_detail"].strip()
    if detail:
        state_line += f" - {detail}"

    pretty, relative = _pretty_date(data["last_activity"])
    last_line = f"Last activity: {pretty}"
    if relative:
        last_line += f" ({relative})"

    lines = [
        f"Thread: {thread_id} ({data['subject']})",
        "",
        state_line,
        last_line,
        "",
        "Context:",
    ]
    lines += [f"- {point}" for point in data["context"]]
    return "\n".join(lines)


def determine_state(thread_id: str) -> dict:
    """Classify a thread's current state. Returns structured data, text, + tools."""
    today = datetime.now().strftime("%B %d, %Y")
    prompt = (
        f"Today is {today}. Determine the current state of the thread with "
        f"thread_id '{thread_id}'. Read it with get_thread first."
    )
    result = run_agent(prompt, system=SYSTEM, schema=SCHEMA, tools=["get_thread"])
    data = result["data"]
    return {
        "thread_id": thread_id,
        **data,
        "formatted": _format(thread_id, data),
        "tool_calls": result["tool_calls"],
    }
