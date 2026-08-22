"""RAG retrieval — the read side of the vector store.

Two ways to pull emails for the LLM:

    search_emails(query, k)  -> semantic search (RAG). Finds emails by meaning.
                                This is what cross-thread/synthesis features use
                                to gather everything related to a topic.
    get_thread(thread_id)    -> exact lookup of one thread, ordered oldest->newest.
                                A precise SQL fetch, not semantic.

Both become MCP tools in Phase 2, so Claude can call them agentically.

Retrieval unit is the whole email (no chunking) — see embeddings.py for why.
"""

from __future__ import annotations

from models import Email

from agents.embeddings import get_collection


def search_emails(query: str, k: int = 5) -> list[dict]:
    """Semantic search over the mailbox. Returns up to k emails, most relevant first.

    Each result carries the email's metadata plus a `distance` (lower = closer).
    """
    results = get_collection().query(query_texts=[query], n_results=k)

    # Chroma returns parallel lists wrapped one level deep (one per query).
    metadatas = results.get("metadatas", [[]])[0]
    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    hits = []
    for metadata, document, distance in zip(metadatas, documents, distances):
        hits.append({**metadata, "body": document, "distance": distance})
    return hits


def get_thread(thread_id: str) -> list[dict]:
    """Return every email in a thread, oldest first. Empty list if none."""
    emails = (
        Email.query.filter_by(thread_id=thread_id)
        .order_by(Email.created_at.asc())
        .all()
    )
    return [email.to_dict() for email in emails]
