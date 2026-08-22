# Security Notes

Security posture for GenMail and how to run the checks. This is a local
demo/dev app; the "Before exposing publicly" section lists what must be added
before it faces untrusted traffic.

## Input validation

Request validation lives in `server/validation.py` and is applied in
`server/main.py`. It rejects malformed input with a JSON `400` (not a `500`):

- **Write endpoints** (`POST/PUT/DELETE /emails`): JSON body must be an object;
  `sender`/`recipient` must be email-shaped; `subject`/`body` required with length
  caps (255 / 50 000); `is_read` must be boolean; bulk-delete `ids` must be a
  non-empty list of integers.
- **AI/analytics endpoints**: `question` is required and capped (2 000 chars);
  malformed `start`/`end` dates return 400; a global `before_request` hook caps
  every query parameter (≤ 2 000) and path parameter (≤ 255).
- **Request size**: `MAX_CONTENT_LENGTH` caps bodies at ~1 MB.

Note: all DB access goes through the SQLAlchemy ORM, which parameterizes queries —
so these checks are about well-formedness, size, and type safety, not SQL
injection (which the ORM already prevents).

## Infrastructure hardening

- **CORS** is restricted to the client origin(s); override with the
  `CORS_ORIGINS` env var (comma-separated). It is no longer wide-open.
- **Debug mode is off by default.** The Werkzeug debugger allows code execution,
  so it must never run in production. Enable locally with `FLASK_DEBUG=1`.
- **Secrets**: `server/.env` (holds `ANTHROPIC_API_KEY`) is gitignored, along
  with `instance/` and `emails.db`. Never commit the key.

## Authentication (opt-in)

Set `APP_API_KEY` on the server to require a matching `X-API-Key` header on the
sensitive routes (`/ai/*` and `/reset`). When unset, auth is disabled for local
dev and the server prints a warning at startup. The key is compared in constant
time (`hmac.compare_digest`). To authenticate the client, set `VITE_API_KEY`
(client env) to the same value — the client sends it automatically on those
routes.

Scope note: the `/emails` read/write routes are intentionally left open for the
demo. To protect everything, add their prefixes to `_PROTECTED_PREFIXES` /
`_PROTECTED_PATHS` in `main.py` (and send the header from those client calls).

## Rate limiting

Flask-Limiter enforces a generous global cap (120/min, 2000/hour per IP) plus a
tighter limit on the paid `/ai/*` routes (15/min per IP) for cost control.
Storage is in-memory — fine for a single process; use a shared store (redis via
`storage_uri`) if you run multiple workers, so limits hold across processes.

## Dependency checks

Run all checks:

```bash
./security_check.sh
```

It runs `pip-audit` (Python deps), `bandit` (Python static analysis), and
`npm audit` (client deps).

Current status:

- **Fixed**: Flask (→ 3.1.3, CVE-2026-27205) and Werkzeug (→ 3.1.8,
  CVE-2026-27199) were upgraded.
- **Client**: `npm audit` reports 0 vulnerabilities.
- **Monitored (no upstream fix yet)**: `chromadb`, `diskcache` (transitive),
  `torch` (transitive via sentence-transformers), and `ragas` (used only by the
  eval harness, not the running app). Re-run `pip-audit` periodically and bump
  when patched releases land.

## LLM-specific considerations

- **Prompt injection.** Email subjects and bodies are attacker-controllable
  (anyone can send mail into the inbox) and flow into LLM prompts — both as MCP
  tool results in the agentic loop and inlined into hand-built prompts. A crafted
  email could try to steer the model ("ignore previous instructions…"). Layered
  mitigations, centralized in `server/agents/guard.py`:
  - **Data fencing (spotlighting).** Every piece of email content sent to the
    model is wrapped in `fence()` — delimiter markers carrying a **per-process
    random nonce** so email content can't forge the boundary and "break out" of
    the data region. Applied to every MCP tool result (`mcp_client._run_async`)
    and to the hand-built prompts in `urgency.py` / `tracker.py`.
  - **Content neutralization.** `neutralize()` strips invisible/bidi/control
    characters (zero-width joiners, RTL overrides, C0 controls) that hide
    injected instructions from a human reviewer while the model still reads them.
  - **System-prompt guard.** A shared `SECURITY_NOTICE` is appended to *every*
    feature's system prompt in `run_agent()`, instructing the model that fenced
    content and tool results are data only, never instructions — regardless of
    what the content claims. `reply_drafter.py` additionally forbids carrying
    instructions, links, or addresses from an email into a generated draft.
  - **Structured output** schemas constrain most responses to enumerated fields.
  - **Read-only tools.** The MCP tools are search/get/list only — the model
    cannot send mail, delete data, or take destructive action, so even a
    successful injection can at worst produce a misleading analysis, not a
    harmful side effect.
  Residual risk: these are defense-in-depth, not a guarantee — a determined
  injection could still bias free-text output. Treat AI output as advisory, not
  authoritative.
- **Cost/DoS.** AI endpoints call a paid LLM. Inputs are length-capped, but there
  is no rate limiting — add it before public exposure (see below).

## Before exposing publicly

Opt-in auth and rate limiting now exist (see above). Before public exposure, also:

- **Set `APP_API_KEY`** (and the client's `VITE_API_KEY`) — auth is off until you do,
  which leaves `/ai/*` and `/reset` open.
- **Extend auth** to the `/emails` read/write routes if they shouldn't be public.
- **Use a shared rate-limit store** (redis) if running multiple workers, so limits
  are enforced across processes rather than per-process.
- **Run a production WSGI server** (gunicorn/uwsgi), not the Flask dev server.
