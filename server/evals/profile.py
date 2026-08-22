"""Per-feature profile — latency and token cost for each AI feature.

Runs one representative call of every agentic feature and tabulates wall-clock
latency and token usage (input/output). This covers the latency and cost metrics
across the whole feature suite. (The deterministic /analytics endpoint is excluded
— it makes no LLM calls.)

This is the most expensive eval — it invokes every feature once, and each is an
agentic loop of several LLM calls. Run from server/:

    uv run python -m evals.profile
"""

from __future__ import annotations

import time

from main import app
from models import Email
from agents.embeddings import reindex_all
from agents.mcp_client import ask, reset_usage, get_usage
from agents.summarizer import summarize_thread
from agents.classifier import classify_thread
from agents.thread_state import determine_state
from agents.urgency import score_urgency
from agents.digest import build_digest
from agents.clusterer import cluster_by_sender
from agents.tracker import track_commitments
from agents.reply_drafter import draft_reply

# (label, callable) — one representative invocation per feature.
FEATURES = [
    ("summarize", lambda: summarize_thread("phoenix-timeline-001")),
    ("classify", lambda: classify_thread("bug-escalation-010")),
    ("state", lambda: determine_state("enterprise-dash-004")),
    ("urgency", lambda: score_urgency(thread_id="bug-escalation-010")),
    ("digest", lambda: build_digest()),
    ("clusters", lambda: cluster_by_sender("sarah.chen@acme.com")),
    ("commitments", lambda: track_commitments()),
    ("draft", lambda: draft_reply(thread_id="mobile-offline-002")),
    ("ask", lambda: ask("What is the current status of the Phoenix launch?")),
]


def evaluate() -> list[dict]:
    """Profile every feature once and print a latency/cost table."""
    # Ensure the vector index is fresh (features that use search_emails need it).
    with app.app_context():
        reindex_all(Email.query.all())

    print("Per-feature profile (latency + cost)")
    print("=" * 56)
    print(f"{'feature':<14}{'latency':>9}{'in':>8}{'out':>7}{'total':>8}")
    print("-" * 56)

    rows = []
    for label, call in FEATURES:
        reset_usage()
        start = time.perf_counter()
        call()
        latency = time.perf_counter() - start
        usage = get_usage()
        total = usage["input_tokens"] + usage["output_tokens"]
        rows.append({"feature": label, "latency_s": latency, **usage, "total": total})
        print(
            f"{label:<14}{latency:>8.1f}s{usage['input_tokens']:>8}"
            f"{usage['output_tokens']:>7}{total:>8}"
        )

    print("-" * 56)
    n = len(rows)
    print(
        f"{'mean':<14}{sum(r['latency_s'] for r in rows)/n:>8.1f}s"
        f"{sum(r['input_tokens'] for r in rows)//n:>8}"
        f"{sum(r['output_tokens'] for r in rows)//n:>7}"
        f"{sum(r['total'] for r in rows)//n:>8}"
    )
    return rows


if __name__ == "__main__":
    evaluate()
