"""Inbox analytics — deterministic email-pattern statistics.

Unlike the /ai/* features, this does NOT go through the LLM/MCP layer. Analytics
is exact counting and aggregation, which SQL/Python does perfectly and an LLM
does unreliably. This is an extension of /stats, computed directly from the DB.

compute_analytics(start, end) -> structured dict
format_analytics(data)        -> the "Inbox Intelligence" text block
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from constants import PRIMARY_USER
from models import Email


def _display_name(email: str) -> str:
    """jennifer.walsh@acme.com -> 'Jennifer Walsh'."""
    local = email.split("@")[0]
    return " ".join(part.capitalize() for part in local.replace("_", ".").split("."))


def _relative_time(then: datetime, now: datetime) -> str:
    """Human 'X ago' string."""
    seconds = (now - then).total_seconds()
    if seconds < 0:
        return "just now"
    minutes, hours, days = seconds / 60, seconds / 3600, seconds / 86400
    if seconds < 60:
        return "just now"
    if minutes < 60:
        return f"{int(minutes)} minutes ago"
    if hours < 24:
        return f"{int(hours)} hours ago"
    if days < 30:
        return f"{int(days)} days ago"
    if days < 365:
        return f"{int(days / 30)} months ago"
    return f"{int(days / 365)} years ago"


def _thread_subject(emails: list[Email]) -> str:
    """The thread's originating subject (earliest email), minus any 'Re:' prefix."""
    first = min(emails, key=lambda e: e.created_at)
    subject = first.subject
    while subject.lower().startswith("re:"):
        subject = subject[3:].strip()
    return subject


def compute_analytics(start: datetime | None = None, end: datetime | None = None) -> dict:
    """Compute inbox statistics over an optional [start, end] date range."""
    query = Email.query
    if start:
        query = query.filter(Email.created_at >= start)
    if end:
        query = query.filter(Email.created_at <= end)
    emails = query.all()

    now = datetime.now()

    if not emails:
        return {
            "volume": {"total_emails": 0, "unread": 0, "threads_active": 0, "busiest_day": None},
            "people": {"most_frequent": None, "awaiting_reply": []},
            "threads": {"longest": None, "most_recent": None},
        }

    # Group into threads.
    threads: dict[str, list[Email]] = {}
    for email in emails:
        threads.setdefault(email.thread_id, []).append(email)

    # --- Volume ---
    total = len(emails)
    unread = sum(1 for e in emails if not e.is_read)
    day_counts = Counter(e.created_at.date() for e in emails)
    busiest_day, busiest_count = day_counts.most_common(1)[0]

    # --- People ---
    inbound = Counter(e.sender for e in emails if e.sender != PRIMARY_USER)
    most_frequent = None
    if inbound:
        email_addr, count = inbound.most_common(1)[0]
        most_frequent = {"name": _display_name(email_addr), "email": email_addr, "count": count}

    # Awaiting reply: threads whose most recent email isn't from the PM.
    awaiting = set()
    for thread_emails in threads.values():
        last = max(thread_emails, key=lambda e: e.created_at)
        if last.sender != PRIMARY_USER:
            awaiting.add(_display_name(last.sender))

    # --- Threads ---
    longest_id = max(threads, key=lambda t: len(threads[t]))
    longest = threads[longest_id]
    span_days = (
        max(e.created_at for e in longest) - min(e.created_at for e in longest)
    ).days

    recent_id = max(threads, key=lambda t: max(e.created_at for e in threads[t]))
    recent = threads[recent_id]
    recent_last = max(e.created_at for e in recent)

    return {
        "volume": {
            "total_emails": total,
            "unread": unread,
            "threads_active": len(threads),
            "busiest_day": {"date": busiest_day.isoformat(), "count": busiest_count},
        },
        "people": {
            "most_frequent": most_frequent,
            "awaiting_reply": sorted(awaiting),
        },
        "threads": {
            "longest": {
                "subject": _thread_subject(longest),
                "count": len(longest),
                "span_days": span_days,
            },
            "most_recent": {
                "subject": _thread_subject(recent),
                "relative": _relative_time(recent_last, now),
            },
        },
    }


def format_analytics(data: dict) -> str:
    """Render the analytics dict as the 'Inbox Intelligence' text block."""
    v, p, t = data["volume"], data["people"], data["threads"]
    lines = ["Inbox Intelligence:", ""]

    lines.append("Volume:")
    lines.append(f"- {v['total_emails']} total emails ({v['unread']} unread)")
    lines.append(f"- {v['threads_active']} threads active")
    if v["busiest_day"]:
        day = datetime.fromisoformat(v["busiest_day"]["date"])
        lines.append(f"- Busiest day: {day:%b} {day.day} ({v['busiest_day']['count']} emails)")
    lines.append("")

    lines.append("People:")
    if p["most_frequent"]:
        mf = p["most_frequent"]
        lines.append(f"- Most frequent: {mf['name']} ({mf['count']} emails)")
    awaiting = ", ".join(p["awaiting_reply"]) if p["awaiting_reply"] else "nobody"
    lines.append(f"- Awaiting reply: {awaiting}")
    lines.append("")

    lines.append("Threads:")
    if t["longest"]:
        ln = t["longest"]
        lines.append(f"- Longest: {ln['subject']} ({ln['count']} emails over {ln['span_days']} days)")
    if t["most_recent"]:
        mr = t["most_recent"]
        lines.append(f"- Most recent: {mr['subject']} ({mr['relative']})")

    return "\n".join(lines).rstrip()
