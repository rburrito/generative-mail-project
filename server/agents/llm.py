"""Thin wrapper around the Anthropic Claude API.

This is the single place every GenMail AI feature talks to the LLM. Keeping the
client and model choices here means the feature modules (summarizer, classifier,
synthesizer, ...) stay focused on *what* to ask, not *how* to call the API.

Model tiers (chosen for this project):
    - MODEL_HAIKU  : cheap / fast  -> classification, simple labels
    - MODEL_SONNET : the workhorse -> summaries, digests (default)
    - MODEL_OPUS   : hardest       -> cross-thread synthesis, multi-email reasoning

Two entry points:
    complete(...)       -> returns the model's text answer as a string
    complete_json(...)  -> constrains the answer to a JSON schema and returns a dict

Auth: set ANTHROPIC_API_KEY in a .env file (searched upward from this file) or
in the environment. Nothing else is required.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic

# --- Model tiers -----------------------------------------------------------

MODEL_HAIKU = "claude-haiku-4-5"
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_OPUS = "claude-opus-4-8"

# Workhorse default. Override per call, or globally via the ANTHROPIC_MODEL env var.
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", MODEL_SONNET)

# Summaries/digests are short; bump per call for long syntheses.
DEFAULT_MAX_TOKENS = 4096


# --- .env loading (dependency-free) ----------------------------------------

def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from the nearest .env, searching upward from here.

    Only sets variables that aren't already in the environment, so a real
    environment variable always wins over the file. Silently does nothing if no
    .env is found.
    """
    for directory in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        candidate = directory / ".env" if directory.is_dir() else directory.parent / ".env"
        if candidate.is_file():
            for raw in candidate.read_text().splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
            return


_load_dotenv()

# Reused across calls; reads ANTHROPIC_API_KEY from the environment.
_client = anthropic.Anthropic()


# --- Public API ------------------------------------------------------------

def complete(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Send a single prompt and return Claude's text answer.

    Args:
        prompt: The user message.
        system: Optional system prompt to set the model's role/behavior.
        model: One of the MODEL_* constants. Defaults to DEFAULT_MODEL.
        max_tokens: Output cap. Raise for long outputs.
    """
    kwargs = {
        "model": model or DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    response = _client.messages.create(**kwargs)
    return "".join(block.text for block in response.content if block.type == "text")


def complete_json(
    prompt: str,
    schema: dict,
    *,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict:
    """Send a prompt and get back a dict validated against a JSON schema.

    Use this for any feature that needs structured data (urgency labels, thread
    state, extracted commitments) rather than prose. `schema` is a JSON Schema
    object; it must set `"additionalProperties": false` and list `"required"`.
    """
    kwargs = {
        "model": model or DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }
    if system:
        kwargs["system"] = system

    response = _client.messages.create(**kwargs)
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)


if __name__ == "__main__":
    # Smoke test: `python agents/llm.py` (or `uv run agents/llm.py`) from server/.
    print("Model:", DEFAULT_MODEL)
    print(complete("Reply with exactly: pong"))
