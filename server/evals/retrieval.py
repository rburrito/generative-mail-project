"""Retrieval eval — deterministic quality check on the RAG search layer.

For a curated set of queries we know which thread(s) *should* be retrieved, then
measure:
  - recall@k : fraction of the expected threads that appear in the top-k hits
  - MRR      : 1 / rank of the first expected thread (0 if it never appears)

No LLM judge — this is exact and reliable, which is what you want for retrieval
at this scale. Run from the server/ directory:

    uv run python -m evals.retrieval
"""

from __future__ import annotations

from main import app
from models import Email
from agents.embeddings import reindex_all
from agents.retrieval import search_emails

# query -> the thread_ids a good retriever should surface for it.
CASES = [
    {"query": "Phoenix launch timeline and status",
     "expected": {"phoenix-timeline-001", "design-review-003", "marketing-launch-007"}},
    {"query": "mobile offline sync storage decision", "expected": {"mobile-offline-002"}},
    {"query": "Globex enterprise dashboard requirements", "expected": {"enterprise-dash-004"}},
    {"query": "data sync issue affecting Initech", "expected": {"bug-escalation-010"}},
    {"query": "competitor launched AI analytics", "expected": {"competitive-011"}},
    {"query": "activation funnel and retention analysis", "expected": {"data-insights-006"}},
    {"query": "support tickets navigation confusion", "expected": {"support-feedback-005"}},
    {"query": "analytics SDK partnership with vendor", "expected": {"vendor-013"}},
]


def _score(query: str, expected: set[str], k: int) -> tuple[float, float, list[str]]:
    """Return (recall@k, reciprocal_rank, ordered distinct thread_ids) for one query."""
    hits = search_emails(query, k=k)

    ordered_threads: list[str] = []
    for hit in hits:  # keep rank order, dedupe threads
        if hit["thread_id"] not in ordered_threads:
            ordered_threads.append(hit["thread_id"])

    found = expected & set(ordered_threads)
    recall = len(found) / len(expected)

    rr = 0.0
    for rank, thread_id in enumerate(ordered_threads, 1):
        if thread_id in expected:
            rr = 1.0 / rank
            break

    return recall, rr, ordered_threads


def evaluate(k: int = 5) -> dict:
    """Run the retrieval eval and print a report. Returns the summary metrics."""
    # Rebuild the index from the current DB so the eval reflects live data.
    with app.app_context():
        reindex_all(Email.query.all())

    print(f"Retrieval eval (k={k}), {len(CASES)} queries")
    print("=" * 64)
    print(f"{'query':<44}{'recall':>8}{'rank':>6}")
    print("-" * 64)

    total_recall = total_rr = 0.0
    for case in CASES:
        recall, rr, _ = _score(case["query"], case["expected"], k)
        total_recall += recall
        total_rr += rr
        rank = f"{int(1 / rr)}" if rr else "-"
        print(f"{case['query'][:43]:<44}{recall:>8.2f}{rank:>6}")

    n = len(CASES)
    mean_recall = total_recall / n
    mrr = total_rr / n
    print("-" * 64)
    print(f"mean recall@{k}: {mean_recall:.2f}    MRR: {mrr:.2f}")

    return {"mean_recall": mean_recall, "mrr": mrr, "k": k, "n": n}


if __name__ == "__main__":
    evaluate()
