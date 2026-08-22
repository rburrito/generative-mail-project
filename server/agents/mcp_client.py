"""MCP client — runs Claude's tool-use loop against the GenMail MCP server.

This is the bridge between Flask and the MCP layer. It keeps ONE long-lived MCP
session (the server subprocess is spawned once and reused), so the embedding
model and DB connection load a single time instead of on every request.

How the persistence works:
  - A background thread runs a dedicated asyncio event loop forever.
  - On first use, that loop opens the stdio session, initializes it, and lists
    the server's tools — then keeps the session open.
  - Each synchronous run_agent() call dispatches its agentic-loop coroutine onto
    that loop (run_coroutine_threadsafe) and blocks for the result. Calls are
    serialized with a lock — a single MCP session can't safely interleave
    concurrent requests (fine for the dev server and the eval harness).

Features call run_agent(); the Flask routes are thin wrappers over it.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

from anthropic import AsyncAnthropic
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from constants import PRIMARY_USER
from agents.llm import DEFAULT_MODEL
from agents.guard import SECURITY_NOTICE, fence

logger = logging.getLogger("genmail.mcp")

_SERVER_DIR = Path(__file__).resolve().parent.parent  # the server/ directory
_MAX_TURNS = 6  # safety cap on the tool-use loop

SYSTEM = (
    f"You are an assistant to {PRIMARY_USER}, a product manager at Acme Corp. "
    "Answer questions about their email using the provided tools. "
    "Ground every answer in actual emails — call the tools to look things up "
    "rather than guessing, and refer to specific senders and subjects. "
    "If the tools turn up nothing relevant, say so plainly."
)

# Launch the server as a module from the server/ dir so its absolute imports
# resolve. Also put server/ on PYTHONPATH as a belt-and-suspenders measure.
_server_params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "agents.mcp_server"],
    cwd=str(_SERVER_DIR),
    env={**os.environ, "PYTHONPATH": str(_SERVER_DIR) + os.pathsep + os.environ.get("PYTHONPATH", "")},
)


# --- Token instrumentation (for evals) -------------------------------------
# Reset before a feature call and read after to get that call's token cost.
_usage = {"input_tokens": 0, "output_tokens": 0}


def reset_usage() -> None:
    _usage["input_tokens"] = 0
    _usage["output_tokens"] = 0


def get_usage() -> dict:
    return dict(_usage)


def _track(response) -> None:
    _usage["input_tokens"] += response.usage.input_tokens
    _usage["output_tokens"] += response.usage.output_tokens


def _tool_result_text(result) -> str:
    """Flatten an MCP CallToolResult's content blocks into a string."""
    parts = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


def _loads_lenient(text: str):
    """Parse a JSON object from model output; return None if none is parseable.

    Structured-output responses are almost always clean JSON, but a model can
    occasionally wrap them in a ```json fence or emit a line of prose alongside
    them. This tolerates those; it does NOT recover truncated JSON (the caller
    retries for that).
    """
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        # Drop the ``` fence (and any ```json language tag) around the JSON.
        text = text.strip("`")
        if "{" in text:
            text = text[text.find("{"):]
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # Fall back to the outermost {...} span in case prose surrounds the object.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


# --- Persistent MCP session ------------------------------------------------

class _McpSession:
    """Owns a background event loop + one long-lived MCP session."""

    def __init__(self):
        self._loop = None
        self._session = None
        self._tools = None
        self._anthropic = None
        self._stdio_cm = None
        self._session_cm = None
        self._start_lock = threading.Lock()  # guards one-time startup
        self._call_lock = threading.Lock()   # serializes calls on the session

    def _ensure_started(self):
        if self._loop is not None:
            return
        with self._start_lock:
            if self._loop is not None:
                return
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, daemon=True).start()
            asyncio.run_coroutine_threadsafe(self._open(), loop).result()
            self._loop = loop
            atexit.register(self._close)

    async def _open(self):
        # Enter the context managers manually and keep them open for the process
        # lifetime (they're bound to this loop, so all calls must use this loop).
        self._stdio_cm = stdio_client(_server_params)
        read, write = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()
        self._tools = (await self._session.list_tools()).tools
        self._anthropic = AsyncAnthropic()  # one client, bound to this loop
        logger.info("MCP session started (%d tools available)", len(self._tools))

    def run(self, prompt, system, schema, model, allowed_tools) -> dict:
        self._ensure_started()
        with self._call_lock:  # one agentic loop at a time on the shared session
            future = asyncio.run_coroutine_threadsafe(
                _run_async(self._anthropic, self._session, self._tools, prompt, system, schema, model, allowed_tools),
                self._loop,
            )
            return future.result()

    def call_tool(self, name, arguments) -> str:
        """Invoke one MCP tool directly and return its result text (no LLM)."""
        self._ensure_started()
        with self._call_lock:
            future = asyncio.run_coroutine_threadsafe(
                self._call_tool_async(name, arguments), self._loop
            )
            return future.result()

    async def _call_tool_async(self, name, arguments) -> str:
        result = await self._session.call_tool(name, arguments)
        return _tool_result_text(result)

    def _close(self):
        if self._loop is None:
            return
        async def _shutdown():
            try:
                await self._session_cm.__aexit__(None, None, None)
                await self._stdio_cm.__aexit__(None, None, None)
            except Exception:
                pass  # best-effort; the subprocess also exits on stdin EOF
        try:
            asyncio.run_coroutine_threadsafe(_shutdown(), self._loop).result(timeout=5)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)


_manager = _McpSession()


# --- Agentic loop ----------------------------------------------------------

async def _run_async(client, session, mcp_tools, prompt, system, schema, model, allowed_tools) -> dict:
    extra = (
        {"output_config": {"format": {"type": "json_schema", "schema": schema}}}
        if schema
        else {}
    )

    # Only expose the tools this feature asked for — fewer schemas, fewer tokens.
    anthropic_tools = [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        }
        for t in mcp_tools
        if allowed_tools is None or t.name in allowed_tools
    ]

    messages = [{"role": "user", "content": prompt}]
    tool_calls = []  # record what Claude called, for transparency

    for _ in range(_MAX_TURNS):
        tool_kwargs = {"tools": anthropic_tools} if anthropic_tools else {}
        response = await client.messages.create(
            model=model or DEFAULT_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
            **tool_kwargs,
            **extra,
        )
        _track(response)

        if response.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": response.content})

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_calls.append({"tool": block.name, "input": block.input})
            mcp_result = await session.call_tool(block.name, block.input)
            # Tool results carry attacker-controllable email content. Fence it so
            # the model treats it as untrusted data, not instructions (see guard.py).
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": fence(_tool_result_text(mcp_result)),
            })
        messages.append({"role": "user", "content": results})

    # If we hit the turn cap while Claude still wanted a tool, force a final
    # answer with no tools so it must produce the answer now.
    if response.stop_reason == "tool_use":
        response = await client.messages.create(
            model=model or DEFAULT_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
            **extra,
        )
        _track(response)

    text = "".join(block.text for block in response.content if block.type == "text")
    result = {"tool_calls": tool_calls}
    if not schema:
        result["answer"] = text.strip()
        return result

    # Structured output: the model must return JSON matching the schema. It very
    # occasionally returns prose, a fenced block, or a truncated/empty response
    # (e.g. after flagging an injection attempt). Parse leniently, and if that
    # fails, retry once with a corrective nudge before giving up — so a transient
    # bad response degrades to one clear error, not a raw JSONDecodeError.
    data = _loads_lenient(text)
    if data is None:
        response = await client.messages.create(
            model=model or DEFAULT_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages + [
                {"role": "assistant", "content": text or "(no output)"},
                {"role": "user", "content": (
                    "Your previous reply was not valid JSON. Reply with ONLY the "
                    "JSON object required by the schema — no prose, no code fences."
                )},
            ],
            **extra,
        )
        _track(response)
        text = "".join(block.text for block in response.content if block.type == "text")
        data = _loads_lenient(text)
    if data is None:
        raise ValueError(
            f"structured output was not valid JSON after one retry: {text[:200]!r}"
        )
    result["data"] = data
    return result


def run_agent(
    prompt: str,
    *,
    system: str = SYSTEM,
    schema: dict | None = None,
    model: str | None = None,
    tools: list[str] | None = None,
) -> dict:
    """Run Claude's MCP tool-use loop. Returns {tool_calls, answer|data}.

    This is the shared engine for every AI feature. Pass a `schema` to get a
    validated dict back under `data`; otherwise you get text under `answer`.
    Pass `tools` (a list of tool names) to expose only those MCP tools to the
    model — trims input tokens by not sending unused tool schemas each turn.
    """
    # Every feature's task is fixed by its own system prompt; append the shared
    # injection guard here so no feature can forget it (see guard.py).
    system = f"{system}\n\n{SECURITY_NOTICE}"

    before_in, before_out = _usage["input_tokens"], _usage["output_tokens"]
    start = time.perf_counter()
    result = _manager.run(prompt, system, schema, model, tools)
    logger.info(
        "agent run: tools=%s tool_calls=%d tokens=%d in/%d out latency=%.0fms",
        tools if tools is not None else "all",
        len(result["tool_calls"]),
        _usage["input_tokens"] - before_in,
        _usage["output_tokens"] - before_out,
        (time.perf_counter() - start) * 1000,
    )
    return result


def call_tool(name: str, arguments: dict) -> str:
    """Invoke a single MCP tool directly (no LLM). Returns the tool's result text.

    Used by features that know exactly what data they need — fetch it once, then
    make a single no-tools run_agent() call — instead of paying for the agentic
    loop's growing tool-result history.
    """
    return _manager.call_tool(name, arguments)


def ask(question: str, model: str | None = None) -> dict:
    """Generic Q&A entry point for the /ai/ask route."""
    result = run_agent(question, model=model)
    return {"question": question, **result}
