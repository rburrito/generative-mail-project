# GenMail — LLM-Powered Email Intelligence
A product manager's email client (`pm@acme.com`) augmented with an LLM
intelligence layer. Ten AI features analyze and act on email — summaries,
triage, drafting, cross-inbox reasoning — built on a **RAG + MCP**
architecture with a full evaluation suite, a React UI, and
production-minded security.

### Personal Notes
I used Claude (Sonnet) to build this project so I could get a hands-on feel for how it approaches development and learn major concepts along the way. Just a heads-up: the wordy write-up and presentation below are in Claude’s own words. Here are a few major lessons I learned from relying on Claude and using evals for a end-to-end build instead of writing it myself:
1. Claude is generally good with individual pieces of code.
2. The more code Claude inserts, the messier the architecture gets, which really hurts the project's long-term scalability.
3. Lacking deep familiarity with the inherited codebase, a seemingly minor edit broke 15 tests. I ultimately relied on Claude to quickly debug the failure modes and fix the suite.
4. My role shifted toward interface and integration testing to ensure the system actually delivered what it was designed to build.
5. If I hadn't set up tests and evals with Claude 4.8 Opus as the LLM judge, I probably would've missed most of these edge cases.
6. You can't completely rely on LLM evals at face value. Fine-tuning a judge's prompt is a balancing act; it's easy to accidentally make it overly strict or completely lenient. In practice, chasing higher scores often yielded worse results, making it obvious that further tuning was just overfitting to the eval harness rather than solving the real problem.

## Architecture

```
React client ──HTTP──▶ Flask REST API ──▶ MCP client ──▶ MCP server (tools)
                            │                                   │
                            ├─ /analytics (deterministic)       ├─ RAG: Chroma + local embeddings
                            └─ Claude (Anthropic)                └─ SQLite (emails)
```

- **Data layer** — Flask + SQLAlchemy + SQLite; REST CRUD over an `Email` model.
- **RAG retrieval layer** — Chroma vector store + local `sentence-transformers`
  embeddings (offline, no embedding-API key). One vector per email.
- **MCP integration layer** — a FastMCP server exposes email operations as
  tools (`search_emails`, `get_thread`, `get_email`, `emails_from_sender`,
  `list_unread`, `get_stats`); a persistent-session MCP client runs Claude's
  tool-use loop.
- **LLM** — Anthropic Claude (Sonnet workhorse; Haiku/Opus tiers), with
  structured outputs for typed results.
- **Client** — React + shadcn UI.

Design rule: LLM features reach data *only* through MCP tools, never direct
DB calls. Pure counting (`/analytics`) stays deterministic — LLMs miscount.

## Features

| Feature | What it does |
|---|---|
| Ask | Free-form Q&A over the inbox (agentic) |
| Summarize | Thread → concise summary |
| Classify | Urgency / thread-state / category (structured) |
| State | Where a thread stands + why |
| Urgency | 1–10 score from content, sender history, context |
| Digest | "Needs attention," grouped by sender/thread |
| Clusters | A sender's mail → topic clusters |
| Commitments | Promises the PM made + Done/Overdue/Open |
| Draft | Contextual reply in the PM's voice |
| Analytics | Deterministic inbox stats (volume/people/threads) |

## Evaluation

Six runnable harnesses under `server/evals/`:

- **Retrieval** — recall@k + MRR (deterministic).
- **Faithfulness** — LLM-as-judge grounding score (Opus judges Sonnet).
- **Classification** — accuracy / precision / recall / F1 + latency + cost.
- **Hallucination rate** — % of verifiable claims that are wrong.
- **Per-feature profile** — latency + token cost across the suite.
- **Prompt-injection red-team** — seeds crafted attack emails, runs the real
  features, and a judge scores resisted vs. compromised.

## Security

- Input validation (`server/validation.py`): JSON-shape checks, length/type
  caps, 1 MB request cap.
- Opt-in API key auth on `/ai/*` and `/reset` (`APP_API_KEY` / `VITE_API_KEY`).
- Rate limiting: 120/min global, 15/min on `/ai/*`.
- CORS restricted to the client origin; debug mode off by default; secrets
  gitignored.
- Dependency scanning via `security_check.sh` (pip-audit + bandit + npm audit).
- Layered prompt-injection defenses (`server/agents/guard.py`): untrusted
  content fencing, invisible-character stripping, system-prompt guard,
  structured outputs, read-only MCP tools. Red-teamed 6/6 resisted.

See [SECURITY.md](SECURITY.md) for details, and
[PRESENTATION.md](PRESENTATION.md) for the full technical writeup.

## Run it locally

Two terminals:

```bash
# Terminal 1 — server (API at http://localhost:5000)
cd server
uv run flask --app main run

# Terminal 2 — client (app at http://localhost:5173)
cd client
npm install        # first time only
npm run dev
```

Then open **http://localhost:5173** and click **Reset DB** to load the
sample emails.

Optional environment variables:
- `FLASK_DEBUG=1` (server) — enable debug mode for local dev.
- `APP_API_KEY=…` (server) + `VITE_API_KEY=…` (client) — turn on API-key auth.
- `LOG_LEVEL=DEBUG` and `LOG_FILE=app.log` (server) — control logging.

## Tech stack

Flask · SQLAlchemy · SQLite · Chroma · sentence-transformers · FastMCP ·
Anthropic Claude · React · shadcn/ui · TypeScript · Vite
