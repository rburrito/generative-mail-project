"""FastMCP server — exposes GenMail's data as MCP tools.

This is the *integration layer*. Instead of features calling the database and the
LLM directly, the email operations are published here as MCP tools, and Claude
calls them agentically through the MCP client (see mcp_client.py). That's how
objective #2 (integrate the LLM with the REST/data layer) is satisfied, and it's
where RAG plugs in: `search_emails` wraps the Phase 1 retrieval layer.

Run standalone over stdio:
    uv run python agents/mcp_server.py

It runs as its own process, so it builds a minimal Flask app bound to the same
emails.db just to get a SQLAlchemy app context. It deliberately does NOT import
main.py (which would re-register routes and rebuild the index).
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask
from fastmcp import FastMCP

from logging_config import setup_logging
from models import db, Email
from agents.retrieval import search_emails as _search_emails
from agents.retrieval import get_thread as _get_thread

# Logs go to stderr (safe — the stdio transport uses stdout for the protocol).
setup_logging()
logger = logging.getLogger("genmail.tools")

# Minimal app: just enough to give the tools a SQLAlchemy context. As its own
# process, Flask(__name__) would resolve the instance folder relative to agents/,
# so we pin an absolute path to the real DB instead.
_DB_PATH = Path(__file__).resolve().parent.parent / "instance" / "emails.db"
_app = Flask(__name__)
_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_DB_PATH}"
db.init_app(_app)

mcp = FastMCP("genmail")


@mcp.tool()
def search_emails(query: str, k: int = 5) -> list[dict]:
    """Semantically search the mailbox and return the k most relevant emails.

    Use this to gather emails related to a topic, person, or question when you
    don't already know which thread they're in (e.g. "everything about the
    Phoenix launch"). Returns each email's metadata, body, and a distance score
    (lower = more relevant).
    """
    # search_emails only touches Chroma (a file on disk) — no app context needed.
    results = _search_emails(query, k=k)
    logger.info("tool search_emails(%r, k=%d) -> %d hits", query, k, len(results))
    return results


@mcp.tool()
def get_thread(thread_id: str) -> list[dict]:
    """Return every email in a thread, oldest first.

    Use this when you already know the thread_id and need the full, ordered
    conversation (e.g. to summarize one thread).
    """
    with _app.app_context():
        emails = _get_thread(thread_id)
    logger.info("tool get_thread(%s) -> %d emails", thread_id, len(emails))
    return emails


@mcp.tool()
def get_email(email_id: int) -> dict:
    """Return a single email by its numeric id, or {} if it doesn't exist.

    Useful when you need to inspect one specific email (e.g. to score its
    urgency). The returned dict includes its thread_id so you can fetch the rest
    of the thread for context.
    """
    with _app.app_context():
        email = db.session.get(Email, email_id)
        result = email.to_dict() if email else {}
    logger.info("tool get_email(id=%s) -> %s", email_id, "found" if result else "not found")
    return result


@mcp.tool()
def emails_from_sender(sender: str) -> list[dict]:
    """Return every email sent by a given address, oldest first.

    Use this to analyze everything one person has sent — e.g. to group their
    emails into topic clusters. This is an exact match on the sender address,
    not a semantic search.
    """
    with _app.app_context():
        emails = (
            Email.query.filter_by(sender=sender)
            .order_by(Email.created_at.asc())
            .all()
        )
        result = [email.to_dict() for email in emails]
    logger.info("tool emails_from_sender(%s) -> %d emails", sender, len(result))
    return result


@mcp.tool()
def list_unread() -> list[dict]:
    """Return all unread emails, newest first.

    Use this to figure out what needs the user's attention right now.
    """
    with _app.app_context():
        emails = (
            Email.query.filter_by(is_read=False)
            .order_by(Email.created_at.desc())
            .all()
        )
        result = [email.to_dict() for email in emails]
    logger.info("tool list_unread -> %d emails", len(result))
    return result


@mcp.tool()
def get_stats() -> dict:
    """Return mailbox counts: total, unread, read, and number of threads."""
    with _app.app_context():
        total = Email.query.count()
        unread = Email.query.filter_by(is_read=False).count()
        threads = db.session.query(Email.thread_id).distinct().count()
    logger.info("tool get_stats -> total=%d unread=%d threads=%d", total, unread, threads)
    return {
        "total_emails": total,
        "unread_count": unread,
        "read_count": total - unread,
        "thread_count": threads,
    }


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
