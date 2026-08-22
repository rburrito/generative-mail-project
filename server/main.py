import hmac
import logging
import os
import time
import uuid
from datetime import datetime
from flask import Flask, request, Response, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest
from logging_config import setup_logging
from models import db, Email
from seeds import SEED_EMAILS
from validation import (
    json_object,
    required_str,
    optional_str,
    email_address,
    id_list,
    MAX_FIELD,
    MAX_BODY,
    MAX_QUESTION,
)
from agents.embeddings import index_email, reindex_all
from agents.mcp_client import ask
from agents.summarizer import summarize_thread
from agents.classifier import classify_thread
from agents.digest import build_digest
from agents.clusterer import cluster_by_sender
from analytics import compute_analytics, format_analytics
from agents.tracker import track_commitments
from agents.urgency import score_urgency
from agents.thread_state import determine_state
from agents.reply_drafter import draft_reply

setup_logging()
logger = logging.getLogger("genmail.api")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///emails.db"
app.config["MAX_CONTENT_LENGTH"] = 1_000_000  # cap request bodies at ~1 MB

# Restrict CORS to the client origin(s); override with CORS_ORIGINS (comma-separated).
_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173")
CORS(app, origins=[o.strip() for o in _origins.split(",") if o.strip()])

db.init_app(app)

with app.app_context():
    db.create_all()


@app.errorhandler(BadRequest)
def _handle_bad_request(e):
    """Return validation failures as JSON 400s instead of HTML error pages."""
    return {"error": e.description}, 400


@app.before_request
def _limit_input_sizes():
    """Bound query and path parameters globally (identifiers, senders, topics)."""
    for value in request.args.values():
        if len(value) > 2_000:
            raise BadRequest("Query parameter is too long.")
    for value in (request.view_args or {}).values():
        if isinstance(value, str) and len(value) > MAX_FIELD:
            raise BadRequest("Path parameter is too long.")


# --- Rate limiting -------------------------------------------------------
# Generous global cap (anti-flood); a tighter per-endpoint limit is applied to
# the paid /ai/* routes below. In-memory storage is fine for a single process;
# use a shared store (e.g. redis) if you run multiple workers.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["120 per minute", "2000 per hour"],
    storage_uri="memory://",
)


# --- Auth (opt-in via APP_API_KEY) ---------------------------------------
# When APP_API_KEY is set, the sensitive routes (/ai/* and /reset) require a
# matching X-API-Key header. When unset, auth is disabled for local dev.
_APP_API_KEY = os.environ.get("APP_API_KEY")
if not _APP_API_KEY:
    logger.warning("APP_API_KEY not set - auth is DISABLED (dev mode).")

_PROTECTED_PREFIXES = ("/ai/",)
_PROTECTED_PATHS = {"/reset"}


@app.before_request
def _require_api_key():
    if request.method == "OPTIONS":
        return  # let CORS preflight through
    if not _APP_API_KEY:
        return  # auth disabled in dev
    path = request.path
    if path.startswith(_PROTECTED_PREFIXES) or path in _PROTECTED_PATHS:
        provided = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided, _APP_API_KEY):
            logger.warning("unauthorized request to %s from %s", path, get_remote_address())
            return {"error": "unauthorized"}, 401


@app.before_request
def _start_timer():
    g._start = time.perf_counter()


@app.after_request
def _log_request(response):
    duration_ms = (time.perf_counter() - getattr(g, "_start", time.perf_counter())) * 1000
    logger.info(
        "%s %s -> %s (%.0f ms)",
        request.method, request.path, response.status_code, duration_ms,
    )
    return response


@app.route("/ping")
def ping():
    return {"message": "pong"}


@app.route("/ai/ask", methods=["POST"])
def ai_ask():
    """Answer a natural-language question about the mailbox.

    Runs Claude's tool-use loop against the MCP server (which exposes the RAG
    search + thread/stats tools). Returns the answer plus the trace of which
    tools Claude called.
    """
    data = json_object()
    question = required_str(data, "question", MAX_QUESTION)
    return ask(question)


@app.route("/ai/summarize/<thread_id>", methods=["GET"])
def ai_summarize(thread_id):
    """Summarize a single thread via the MCP agent (uses the get_thread tool).

    Returns the formatted two-line text. Add ?format=json for the structured
    payload (summary + tool_calls).
    """
    result = summarize_thread(thread_id)
    if request.args.get("format") == "json":
        return result
    return Response(result["formatted"], mimetype="text/plain")


@app.route("/ai/classify/<thread_id>", methods=["GET"])
def ai_classify(thread_id):
    """Classify a thread (urgency / state / category) as structured JSON."""
    return classify_thread(thread_id)


@app.route("/ai/digest", methods=["GET"])
def ai_digest():
    """Unread digest grouped by sender (default) or thread.

    ?group_by=sender|thread, ?format=json for the structured payload.
    """
    result = build_digest(request.args.get("group_by", "sender"))
    if request.args.get("format") == "json":
        return result
    return Response(result["formatted"], mimetype="text/plain")


@app.route("/ai/clusters", methods=["GET"])
def ai_clusters():
    """Group a sender's emails into topic clusters. Pass ?sender=<address>."""
    sender = request.args.get("sender")
    if not sender:
        return {"error": "missing 'sender' query parameter"}, 400
    result = cluster_by_sender(sender)
    if request.args.get("format") == "json":
        return result
    return Response(result["formatted"], mimetype="text/plain")


@app.route("/ai/commitments", methods=["GET"])
def ai_commitments():
    """Extract the PM's commitments from their sent email. ?format=json for data."""
    result = track_commitments()
    if request.args.get("format") == "json":
        return result
    return Response(result["formatted"], mimetype="text/plain")


@app.route("/ai/urgency", methods=["GET"])
def ai_urgency():
    """Score an email's urgency. Pass ?email_id=<int> or ?thread_id=<id>.

    ?format=json for the structured payload (score, level, reasoning, tool_calls).
    """
    email_id = request.args.get("email_id", type=int)
    thread_id = request.args.get("thread_id")
    if email_id is None and not thread_id:
        return {"error": "provide 'email_id' or 'thread_id'"}, 400
    result = score_urgency(email_id=email_id, thread_id=thread_id)
    if request.args.get("format") == "json":
        return result
    return Response(result["formatted"], mimetype="text/plain")


@app.route("/ai/state/<thread_id>", methods=["GET"])
def ai_state(thread_id):
    """Classify a thread's current state. ?format=json for the structured payload."""
    result = determine_state(thread_id)
    if request.args.get("format") == "json":
        return result
    return Response(result["formatted"], mimetype="text/plain")


@app.route("/ai/draft", methods=["GET"])
def ai_draft():
    """Draft a reply. Pass ?thread_id=<id> or ?email_id=<int>.

    ?format=json for the structured payload (subject, body, tool_calls).
    """
    email_id = request.args.get("email_id", type=int)
    thread_id = request.args.get("thread_id")
    if email_id is None and not thread_id:
        return {"error": "provide 'thread_id' or 'email_id'"}, 400
    result = draft_reply(email_id=email_id, thread_id=thread_id)
    if request.args.get("format") == "json":
        return result
    return Response(result["formatted"], mimetype="text/plain")


@app.route("/emails", methods=["POST"])
def create_email():
    data = json_object()
    email = Email(
        thread_id=optional_str(data, "thread_id") or str(uuid.uuid4()),
        sender=email_address(data, "sender"),
        recipient=email_address(data, "recipient"),
        subject=required_str(data, "subject"),
        body=required_str(data, "body", MAX_BODY),
    )
    db.session.add(email)
    db.session.commit()
    index_email(email)  # keep the RAG vector store in sync
    return email.to_dict(), 201


@app.route("/emails", methods=["GET"])
def get_emails():
    query = Email.query

    thread_id = request.args.get("thread_id")
    if thread_id:
        query = query.filter_by(thread_id=thread_id)

    is_read = request.args.get("is_read")
    if is_read is not None:
        query = query.filter_by(is_read=is_read.lower() == "true")

    sender = request.args.get("sender")
    if sender:
        query = query.filter_by(sender=sender)

    recipient = request.args.get("recipient")
    if recipient:
        query = query.filter_by(recipient=recipient)

    emails = query.order_by(Email.created_at.desc()).all()
    return [email.to_dict() for email in emails]


@app.route("/emails/<int:email_id>", methods=["GET"])
def get_email(email_id):
    email = Email.query.get_or_404(email_id)
    return email.to_dict()


@app.route("/emails/<int:email_id>", methods=["PUT"])
def update_email(email_id):
    email = Email.query.get_or_404(email_id)
    data = json_object()
    sender = optional_str(data, "sender")
    recipient = optional_str(data, "recipient")
    subject = optional_str(data, "subject")
    body = optional_str(data, "body", MAX_BODY)
    if sender is not None:
        email.sender = sender
    if recipient is not None:
        email.recipient = recipient
    if subject is not None:
        email.subject = subject
    if body is not None:
        email.body = body
    if "is_read" in data:
        if not isinstance(data["is_read"], bool):
            raise BadRequest("'is_read' must be a boolean.")
        email.is_read = data["is_read"]
    db.session.commit()
    return email.to_dict()


@app.route("/emails/<int:email_id>/read", methods=["PATCH"])
def mark_email_read(email_id):
    email = Email.query.get_or_404(email_id)
    email.is_read = True
    db.session.commit()
    return email.to_dict()


@app.route("/emails/<int:email_id>", methods=["DELETE"])
def delete_email(email_id):
    email = Email.query.get_or_404(email_id)
    db.session.delete(email)
    db.session.commit()
    return "", 204


@app.route("/threads", methods=["GET"])
def get_threads():
    threads = db.session.query(
        Email.thread_id,
        db.func.min(Email.subject).label("subject"),
        db.func.count(Email.id).label("message_count"),
        db.func.min(Email.created_at).label("first_message_at"),
        db.func.max(Email.created_at).label("last_message_at"),
        db.func.sum(db.case((Email.is_read == False, 1), else_=0)).label("unread_count")
    ).group_by(Email.thread_id).all()

    return [
        {
            "thread_id": t.thread_id,
            "subject": t.subject,
            "message_count": t.message_count,
            "first_message_at": t.first_message_at.isoformat(),
            "last_message_at": t.last_message_at.isoformat(),
            "unread_count": t.unread_count or 0
        }
        for t in threads
    ]


@app.route("/stats", methods=["GET"])
def get_stats():
    total_emails = Email.query.count()
    unread_count = Email.query.filter_by(is_read=False).count()
    thread_count = db.session.query(Email.thread_id).distinct().count()

    return {
        "total_emails": total_emails,
        "unread_count": unread_count,
        "read_count": total_emails - unread_count,
        "thread_count": thread_count
    }


@app.route("/analytics", methods=["GET"])
def analytics():
    """Inbox analytics (deterministic). Optional ?start=&end= (ISO dates).

    Returns the 'Inbox Intelligence' text; add ?format=json for structured data.
    """
    start = request.args.get("start")
    end = request.args.get("end")
    try:
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None
    except ValueError:
        raise BadRequest("'start' and 'end' must be ISO dates (e.g. 2026-01-01).")
    data = compute_analytics(start_dt, end_dt)
    if request.args.get("format") == "json":
        return data
    return Response(format_analytics(data), mimetype="text/plain")


@app.route("/emails", methods=["DELETE"])
def delete_emails():
    data = json_object()
    ids = id_list(data, "ids")
    Email.query.filter(Email.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return "", 204


@app.route("/reset", methods=["POST"])
def reset_database():
    db.drop_all()
    db.create_all()
    for seed in SEED_EMAILS:
        email = Email(
            thread_id=seed.get("thread_id") or str(uuid.uuid4()),
            sender=seed["sender"],
            recipient=seed["recipient"],
            subject=seed["subject"],
            body=seed["body"],
            created_at=datetime.fromisoformat(seed["created_at"]) if seed.get("created_at") else None,
            is_read=seed.get("is_read", False)
        )
        db.session.add(email)
    db.session.commit()
    indexed = reindex_all(Email.query.all())  # rebuild the RAG vector store
    logger.info("database reset: %d emails seeded, %d indexed", len(SEED_EMAILS), indexed)
    return {
        "message": "database reset",
        "emails_created": len(SEED_EMAILS),
        "emails_indexed": indexed,
    }


# Tighter rate limit on the paid AI endpoints (cost control), applied on top of
# the global default. Done in a loop to avoid decorating each route by hand.
for _endpoint in (
    "ai_ask", "ai_summarize", "ai_classify", "ai_digest", "ai_clusters",
    "ai_commitments", "ai_urgency", "ai_state", "ai_draft",
):
    app.view_functions[_endpoint] = limiter.limit("15 per minute")(
        app.view_functions[_endpoint]
    )


if __name__ == "__main__":
    # Debug is OFF by default — the Werkzeug debugger allows code execution.
    # Enable explicitly for local dev with FLASK_DEBUG=1.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
