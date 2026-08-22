"""Request validation helpers.

Reject malformed input with a clean 400 instead of a 500 (or worse). Note the
DB access is via SQLAlchemy's ORM everywhere, so these checks are about
well-formedness, size limits, and type safety — not SQL injection, which the ORM
already parameterizes away.
"""

from __future__ import annotations

from flask import request
from werkzeug.exceptions import BadRequest

MAX_FIELD = 255       # matches the Email String(255) columns
MAX_BODY = 50_000     # email body cap
MAX_QUESTION = 2_000  # free-text question sent to the LLM
MAX_IDS = 1_000       # bulk-delete cap


def json_object() -> dict:
    """Return the request's JSON body, or 400 if it isn't a JSON object."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object.")
    return data


def required_str(data: dict, field: str, max_len: int = MAX_FIELD) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BadRequest(f"'{field}' is required and must be a non-empty string.")
    if len(value) > max_len:
        raise BadRequest(f"'{field}' must be at most {max_len} characters.")
    return value


def optional_str(data: dict, field: str, max_len: int = MAX_FIELD) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise BadRequest(f"'{field}' must be a string.")
    if len(value) > max_len:
        raise BadRequest(f"'{field}' must be at most {max_len} characters.")
    return value


def email_address(data: dict, field: str) -> str:
    """A required string with a lightweight email-shape check (not full RFC)."""
    value = required_str(data, field)
    if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
        raise BadRequest(f"'{field}' must look like an email address.")
    return value


def id_list(data: dict, field: str) -> list[int]:
    value = data.get(field)
    ok = (
        isinstance(value, list)
        and 0 < len(value) <= MAX_IDS
        # bool is a subclass of int — exclude True/False from "integer ids"
        and all(isinstance(x, int) and not isinstance(x, bool) for x in value)
    )
    if not ok:
        raise BadRequest(f"'{field}' must be a non-empty list of integers.")
    return value


def bounded(value: str | None, name: str, max_len: int = MAX_FIELD) -> str | None:
    """Length-cap a query-string value (identifiers, senders, topics)."""
    if value is not None and len(value) > max_len:
        raise BadRequest(f"'{name}' must be at most {max_len} characters.")
    return value
