"""Thread summarization — the first Phase 3 feature.

A thin caller of the MCP agent. It does NOT touch the database directly; it asks
Claude to summarize a thread and lets Claude pull the emails through the MCP
`get_thread` tool. Every other feature follows this same shape: a system prompt,
a task prompt, and run_agent().
"""

from __future__ import annotations

from constants import PRIMARY_USER
from agents.mcp_client import run_agent

SYSTEM = (
    f"You are an assistant to {PRIMARY_USER}, a product manager at Acme Corp. "
    "You summarize email threads so they can catch up in seconds. Be concise and "
    "factual: lead with the current state of the thread, then any decision reached, "
    "then anything still outstanding. Use the get_thread tool to read the thread. "
    "Stick to what the emails state: do not add roles, team names, or "
    "characterizations that aren't in the source (e.g. don't call a group the "
    "'engineering team' unless an email does), and do not overstate or reframe what "
    "the emails say (don't call something 'on hold' or 'blocked', and don't add "
    "conditions such as a feature being wanted 'before committing', unless an email "
    "states it). Keep time references exactly as the emails phrase them (e.g. 'by "
    "Friday', 'Thursday afternoon') — do not convert them into specific calendar "
    "dates. You MAY note that a question has no reply yet, or that a promised item "
    "hasn't been delivered, within the thread. Do not invent details."
)


def summarize_thread(thread_id: str) -> dict:
    """Summarize one thread. Returns the summary plus the MCP tool trace."""
    prompt = (
        f"Summarize the email thread with thread_id '{thread_id}' in 2-4 sentences. "
        "Read it first with the get_thread tool. If the thread has no emails, say so."
    )
    result = run_agent(prompt, system=SYSTEM, tools=["get_thread"])
    summary = result["answer"]
    return {
        "thread_id": thread_id,
        "summary": summary,
        "formatted": f'Thread: {thread_id}\nSummary: "{summary}"',
        "tool_calls": result["tool_calls"],
    }
