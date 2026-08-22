"""RAG vector store — Chroma + local sentence-transformers embeddings.

This is the *retrieval layer* of GenMail. Every email is embedded and stored in
a local Chroma collection so features can find relevant emails by meaning, not
just keyword match. Embeddings run locally (all-MiniLM-L6-v2) — no embedding API
key, fully offline. The first run downloads the model (~80MB).

NOTE on scale: with only ~24 seed emails the entire mailbox fits in one context
window, so strictly speaking we could skip retrieval and stuff everything into
the prompt. RAG is built here anyway to demonstrate the retrieve-then-pack
pattern that becomes necessary at thousands of emails. `search_emails` in
retrieval.py is where that pattern pays off.

The Chroma collection is persisted next to the SQLite DB, under instance/chroma.
"""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("genmail.rag")

_CHROMA_PATH = Path(__file__).resolve().parent.parent / "instance" / "chroma"
_COLLECTION_NAME = "emails"
_EMBED_MODEL = "all-MiniLM-L6-v2"

# Lazily initialized so importing this module doesn't load the model.
_collection = None


def get_collection():
    """Return the Chroma collection, creating it (and the client) on first use."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(_CHROMA_PATH))
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=_EMBED_MODEL
        )
        _collection = client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=embed_fn,
        )
    return _collection


def _to_document(email) -> str:
    """The text we embed for an email: subject + body."""
    return f"{email.subject}\n\n{email.body}"


def _to_metadata(email) -> dict:
    """Scalar fields Chroma can filter on and return alongside hits."""
    return {
        "email_id": email.id,
        "thread_id": email.thread_id,
        "sender": email.sender,
        "recipient": email.recipient,
        "subject": email.subject,
        "created_at": email.created_at.isoformat(),
        "is_read": email.is_read,
    }


def index_email(email) -> None:
    """Add or update a single email in the vector store."""
    get_collection().upsert(
        ids=[str(email.id)],
        documents=[_to_document(email)],
        metadatas=[_to_metadata(email)],
    )
    logger.debug("indexed email id=%s into vector store", email.id)


def reindex_all(emails) -> int:
    """Rebuild the whole index from scratch. Call this after a DB reset.

    Returns the number of emails indexed.
    """
    collection = get_collection()
    # Drop everything, then re-add. Simplest correct approach at this scale.
    existing = collection.get()["ids"]
    if existing:
        collection.delete(ids=existing)

    if not emails:
        return 0

    collection.add(
        ids=[str(e.id) for e in emails],
        documents=[_to_document(e) for e in emails],
        metadatas=[_to_metadata(e) for e in emails],
    )
    logger.info("reindexed %d emails into the vector store", len(emails))
    return len(emails)
