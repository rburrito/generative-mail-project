# GenMail — LLM-Powered Email Intelligence
*Presentation summary (with speaker notes)*

---

## Slide 1 — What it is

A product manager's email client (Acme Corp, `pm@acme.com`) augmented with an
**LLM intelligence layer**. Ten AI features analyze and act on email — summaries,
triage, drafting, cross-inbox reasoning — built on a **RAG + MCP** architecture
with a full **eval suite**, a **React UI**, and **production-minded security**.

**Three objectives, all met:** ① LLM analysis features ② LLM integrated with the
REST layer ③ multi-email reasoning & synthesis.

> **Speaker notes.** Here's the pitch in one breath: it's an email app for a busy
> product manager, with an AI layer bolted on that actually reads the inbox and
> tells you what matters — what needs a reply, what you promised someone, what's on
> fire. I want to stress it's not just a bag of features. There's a real design
> under it, we actually tested whether it works, we locked it down, and it runs in
> a real UI. Everything ties back to three goals: build the AI features, wire the
> AI into our existing app, and have it reason across lots of emails at once.
>
> **Quick reminders (what these are):**
> - **LLM** — "large language model," i.e. the AI (in our case Claude).
> - **RAG** — searching emails by *meaning*, then feeding those to the AI.
> - **MCP** — the set of "tools" the AI is allowed to use to look things up.

---

## Slide 2 — Architecture (major components)

```
React client ──HTTP──▶ Flask REST API ──▶ MCP client ──▶ MCP server (tools)
                            │                                   │
                            ├─ /analytics (deterministic)       ├─ RAG: Chroma + local embeddings
                            └─ Claude (Anthropic)               └─ SQLite (emails)
```

- **Data layer** — Flask + SQLAlchemy + SQLite; REST CRUD over an `Email` model.
- **RAG retrieval layer** — Chroma vector store + local `sentence-transformers`
  embeddings (offline, no embedding-API key). One vector per email.
- **MCP integration layer** — a **FastMCP server** exposes email operations as
  tools (`search_emails`, `get_thread`, `get_email`, `emails_from_sender`,
  `list_unread`, `get_stats`); a **persistent-session MCP client** runs Claude's
  tool-use loop.
- **LLM** — Anthropic **Claude** (Sonnet workhorse; Haiku/Opus tiers), with
  **structured outputs** for typed results.
- **Client** — React + shadcn UI.

**Design rule:** LLM features reach data *only through MCP tools* — never direct
DB calls. (Pure counting, like `/analytics`, stays deterministic — LLMs miscount.)

> **Speaker notes.** Okay, the way I think about this: the app has a few layers
> that hand work to each other. The screen you click talks to our server. When you
> ask for something smart, the server passes it to the AI. Two pieces matter — one
> finds the right emails by *meaning*, not just keyword matching (that's the "RAG"
> part), and the other is a set of "tools" the AI is allowed to use to look things
> up (that's "MCP"). The big idea: the AI never touches the database itself, it
> just asks for what it needs through those tools — which keeps its answers honest,
> because it's always working from real emails. One exception: the plain stats page
> skips the AI entirely, because AI is genuinely bad at counting.
>
> **Quick reminders (what these are):**
> - **Flask** — our web server; it answers requests from the app.
> - **SQLAlchemy** — lets us read/write the database with Python instead of raw SQL.
> - **SQLite** — the database itself (one file that stores the emails).
> - **Chroma** — a "vector database": it stores each email's meaning-fingerprint so
>   we can search by meaning.
> - **sentence-transformers** — the local model that turns an email into that
>   meaning-fingerprint (runs on our machine, no API key needed).
> - **FastMCP** — the library we used to build the "tool server" the AI calls.
> - **Claude / Anthropic** — the AI model doing the reasoning (Anthropic is the
>   company; Sonnet/Haiku/Opus are size/cost tiers).
> - **React / shadcn** — what the front-end screen is built with (React) using
>   ready-made UI pieces (shadcn).
> - **Structured outputs** — a mode where the AI returns clean, typed data (like a
>   filled-in form) instead of free text.

---

## Slide 3 — Key technical decisions (what we didn't use, and why)

The `[ai]` dependency group *included* RAGAS, LangChain, and LangGraph — we
deliberately did **not** build on them.

**No LangChain / LangGraph (agent framework)**
- We wanted the agent loop and MCP integration to be **transparent** — a manual
  tool-use loop on the core `anthropic` SDK + the `mcp` client library makes the
  mechanics visible (ideal for a learning project) instead of hidden behind
  framework abstractions.
- Our control flow is simple (a tool loop, plus deterministic fetch for two
  features) — LangGraph's orchestration would be overhead, not leverage.
- **MCP + the Anthropic SDK already provide** tool-calling and integration; a
  framework would add abstraction, version fragility, and dependency surface for
  no capability we lacked.

**No RAGAS (eval framework)**
- RAGAS (and deepeval) default to **OpenAI as the judge** — we only had an
  Anthropic key. Wiring Claude in means `langchain-anthropic` + LLM/embeddings
  adapters: fragile and version-sensitive.
- At our scale (24 emails), **retrieval is best scored deterministically**
  (recall@k / MRR) — exact and flake-free, where an LLM-judged metric adds noise.
- Our lightweight harness reuses the existing stack (Claude-as-judge for
  faithfulness, plain Python for retrieval) — **no OpenAI key, no extra installs**,
  and it still exercises the real concepts.

**Principle:** prefer the smallest, most transparent toolset that meets the need;
add a framework only when it earns its abstraction.

> **Speaker notes.** This is the "why should you trust our choices" slide. Here's
> the honest bit: two popular toolkits — LangChain and RAGAS — were already sitting
> in our project, and we chose *not* to use them, on purpose. LangChain (and
> LangGraph) is a framework for building AI agents; we skipped it because we wanted
> to actually see and understand how the AI picks its tools, and a framework hides
> exactly that part. Our setup is simple enough that it'd just be extra weight.
> RAGAS is a testing toolkit, but it's wired to use OpenAI's models to do the
> grading — and we're a Claude shop, so bending it to use Claude is fiddly and
> breaks easily. For our small inbox, a simple homegrown check is actually more
> reliable. The rule I'd repeat: use the simplest thing that does the job, and only
> reach for a big framework when it earns its keep. And they're still installed, so
> we can switch later if we ever need to.
>
> **Quick reminders (what these are):**
> - **LangChain** — a framework for chaining together AI calls, tools, and data.
> - **LangGraph** — LangChain's cousin for multi-step "agent" workflows.
> - **RAGAS / deepeval** — libraries that grade AI answer quality for you.
> - **Anthropic SDK** — the official code library for talking to Claude.
> - **mcp client library** — the code that lets our app connect to the tool server.
> - **"the judge"** — in AI testing, a model used to grade another model's output.

---

## Slide 4 — The features (10)

| Feature | What it does |
|---|---|
| **Ask** | Free-form Q&A over the inbox (agentic) |
| **Summarize** | Thread → concise summary |
| **Classify** | Urgency / thread-state / category (structured) |
| **State** | Where a thread stands + why |
| **Urgency** | 1–10 score from content, sender history, context |
| **Digest** | "Needs attention," grouped by sender/thread |
| **Clusters** | A sender's mail → topic clusters |
| **Commitments** | Promises the PM made + Done/Overdue/Open |
| **Draft** | Contextual reply in the PM's voice |
| **Analytics** | Deterministic inbox stats (volume/people/threads) |

> **Speaker notes.** Don't read the table — let me just group it. Some of these
> work on the email you're looking at: summarize it, tag how urgent it is, tell you
> where the thread stands, draft a reply. The others look across your whole inbox:
> what needs attention today, group one person's emails by topic, and — my favorite
> — "commitments," which scans your *sent* mail for promises you made and flags the
> ones you're now late on. The urgency one is clever too: it doesn't just read the
> email, it also checks how often that person cries wolf and whether the topic
> matters elsewhere, then gives it a score.
>
> **Quick reminders (what these are):**
> - **"agentic"** — the AI decides which tools to use on its own, step by step.
> - **"structured" output** — the answer comes back as tidy fields, not paragraphs.
> - **"deterministic"** — plain code with no AI; same input always gives same
>   output (that's why Analytics is exact).

---

## Slide 5 — Build phases

- **P0 — Foundation:** run baseline, install deps, Claude wrapper.
- **P1 — RAG:** embeddings + semantic retrieval (verified recall@5 = 1.0).
- **P2 — MCP:** FastMCP server + client tool-use loop + `/ai/ask`.
- **P3 — Core features:** summarize, classify, digest (structured output).
- **P4 — Multi-email reasoning:** commitments, urgency, thread-state, clustering,
  reply drafting.
- **P5 — Evaluation:** 6 harnesses (incl. a prompt-injection red-team), 4 metrics.
- **UI:** React wiring of every feature.
- **Optimization:** tool allowlist, persistent MCP session (**latency −50%**),
  deterministic fetch (**commitments −72%, urgency −85%** input tokens).
- **Security:** validation, auth, rate limiting, dependency hygiene, **layered
  prompt-injection defenses (red-teamed 6/6)**.

> **Speaker notes.** The thing I'd highlight here is the *order* we built in. We
> laid the two foundation pieces first — the "find emails by meaning" part and the
> "tools the AI can use" part — then built every feature on top, so they all got
> that foundation for free. And we measured quality *before* we optimized, because
> you can't speed up or trim something you haven't measured yet. Then the UI, then
> performance, then security. We checked each piece worked before moving on to the
> next.
>
> **Quick reminders (the optimization terms):**
> - **tool allowlist** — give each feature only the specific tools it needs, so we
>   send the AI less each time (cheaper).
> - **persistent MCP session** — keep the tool server running instead of restarting
>   it on every request (much faster).
> - **deterministic fetch** — for two features, grab the data ourselves in one shot
>   instead of letting the AI go back and forth (cheaper).
> - **latency** — how long a request takes; **tokens** — the unit we're billed on,
>   so fewer tokens = lower cost.

---

## Slide 6 — Evaluation (quality is measured, not assumed)

Six runnable harnesses (`evals/`) — four quality metrics plus a safety red-team:

- **Retrieval** — recall@k + MRR (deterministic).
- **Faithfulness** — LLM-as-judge grounding score (Opus judges Sonnet).
- **Classification** — accuracy / precision / recall / F1 **+ latency + cost**.
- **Hallucination rate** — % of verifiable claims that are wrong.
- **Per-feature profile** — latency + token cost across the suite.
- **Prompt-injection red-team** — seeds crafted attack emails into the inbox,
  runs the real features, and a judge rules *resisted* vs. *compromised*
  (**currently 6/6 resisted**). Cleans up the mailbox after itself.

Demonstrated the full loop: **measure → diagnose → fix → re-measure** — and the
judgment to *stop* when run-to-run variance (not a defect) dominates.

```
THE IMPROVEMENT LOOP

  ┌─────────────────────────────────────────────┐
  ▼                                             │
MEASURE ──▶ DIAGNOSE ──▶ FIX ──▶ RE-MEASURE ────┘
                                  (stop when the score only
                                   wobbles from randomness)
```

> **Speaker notes.** This is what makes it a real system instead of a cool demo —
> we actually tested it. We check four things: is it right, is it honest (is it
> making stuff up), is it fast, and is it cheap (how much each call costs). Two
> quick calls worth mentioning: for "did it find the right emails," we just check
> exactly, no AI grading needed. And when we *do* need AI to grade quality, we have
> a smarter model grade the cheaper one's work — like a senior person reviewing a
> junior's draft. There's also a fifth harness that's really a *safety* test: we
> actually mail the app malicious emails that try to hijack the AI and score
> whether it holds — it currently blocks all six attacks we throw at it. Next
> slide: this testing actually changed the product.
>
> **Quick reminders (what these metrics mean):**
> - **recall@k** — of the emails that *should* show up for a search, how many
>   actually did (in the top k results). 1.0 = found them all.
> - **MRR** — how high the right answer landed in the list (higher = nearer the top).
> - **faithfulness** — is the answer backed by the real emails?
> - **hallucination rate** — how often it states something that's actually wrong.
> - **precision / recall / F1** — standard "was the label right" scores; F1 blends
>   the two.

---

## Slide 7 — Challenges & what the evals changed

The evals didn't just score the system — they drove concrete fixes.

**Faithfulness (summaries)**
- Caught the summarizer **inventing details** — an unstated "engineering team"
  label, an overstated "on hold." → Tightened the prompt: no unstated
  roles/characterizations, no status it can't cite.
- Caught the **judge being too strict** — flagging correct-but-implicit
  inferences ("tomorrow" → a date, "no reply yet"). → Recalibrated the judge to
  accept clear entailment.
- Caught the summarizer **computing calendar dates** from weekday mentions
  (correct, but unverifiable by the judge). → Keep time references verbatim.
  **Lesson: don't make the generator compute what the reader/judge can't verify.**
- Score oscillated **4.4–4.8 across runs** → recognized variance, not a defect →
  **stopped tuning** to avoid overfitting to one run.

**Classification**
- `thread_state` scored only **0.50** — the classifier prompt defined just 2 of 4
  states, so the model avoided `resolved`/`fyi`. → Defined all four (and unified
  them with the standalone state feature). **0.50 → 0.70.**
- Some misses were **debatable gold labels** (a "competitive intel" email forced
  into `internal_update`), not model errors → fix the benchmark, not the model.

**Performance profile**
- Input tokens dominated by **tool schemas re-sent every turn** → per-feature
  **tool allowlist** (~20–30% cut).
- Latency dominated by **re-spawning the MCP subprocess + reloading the embedding
  model** per call → **persistent MCP session** (**−50%** latency).
- The two heaviest features re-sent a **growing tool-result history** across
  agentic turns → **deterministic fetch + single call**
  (**commitments −72%, urgency −85%** input tokens).

**Takeaway:** evals turned "seems fine" into measured decisions — fix the
generator for real errors, recalibrate the judge for fairness, and know when to
stop.

> **Speaker notes.** This is the slide I'd slow down on. Three quick stories.
> First: our honesty test caught the summarizer making things up — it invented a
> team name and overstated where a project stood — so we tightened its
> instructions. But it *also* caught our grader being too harsh, dinging the AI for
> reasonable guesses, so we fixed the grader too. And when the AI started turning
> "Thursday" into an exact calendar date — technically right, but nobody could
> easily double-check it — we just told it to leave dates as written. The takeaway:
> don't make the AI compute stuff people can't verify. Second: one test scored low,
> and it turned out we'd only told the AI about half its answer options — once we
> spelled out all four, the score jumped. And some "wrong" answers were really just
> our own labels being debatable, not the AI's fault. Third: we looked at where
> time and money went, and each hotspot had a clear fix — the two most expensive
> features got roughly 70–85% cheaper. Last thing: we also knew when to *stop* —
> once the score was just bouncing from normal randomness, more tweaking would've
> been chasing noise.
>
> **Quick reminders (jargon on this slide):**
> - **the generator** — the AI doing the task (e.g. writing the summary).
> - **the judge / grader** — the separate AI that scores the generator's answer.
> - **gold labels** — the "correct answers" we grade against; if they're wrong, the
>   score is misleading even when the AI is right.
> - **overfitting** — over-tweaking to chase one test run's random noise.

---

## Slide 8 — Security implemented

- **Input validation** — a `validation.py` layer: JSON-shape checks, required
  fields, length/type caps, email-shape validation, integer-id lists, 1 MB
  request cap, global query/path-length limits. Malformed input → clean **400**,
  not 500. (The ORM already prevents SQL injection.)
- **Authentication** — opt-in API key: `APP_API_KEY` → `X-API-Key` required on
  `/ai/*` and `/reset` (constant-time compare); client sends it via `VITE_API_KEY`.
- **Rate limiting** — Flask-Limiter: global 120/min cap **+ 15/min on the paid
  `/ai/*` routes** (cost control). *Verified: 15 succeed, 16th → 429.*
- **Infrastructure** — CORS restricted to the client origin; **debug off by
  default** (Werkzeug-debugger RCE risk); secrets (`.env`) gitignored.
- **Dependency hygiene** — `security_check.sh` (pip-audit + bandit + npm audit);
  patched **Flask & Werkzeug CVEs**; client 0 vulns.
- **Prompt-injection defense (layered)** — email bodies are attacker-controllable
  and flow into the LLM. Defenses in `agents/guard.py`: every piece of email
  content is **fenced as untrusted data** with a **per-process random marker it
  can't forge**; **invisible/control characters are stripped** (a common way to
  hide instructions from a human reviewer); a **system-prompt guard** on every
  feature says fenced content and tool results are *data, never instructions*;
  **structured outputs** constrain most responses; and the **MCP tools are
  read-only** — so even a successful injection yields *misleading output, not
  destructive action*. **Red-teamed** (`evals/injection.py`): 6 crafted attacks —
  instruction-override, data-exfil, label/urgency hijack, malicious-draft
  injection, invisible-character smuggling — **6/6 resisted**. Documented in
  `SECURITY.md`.

> **Speaker notes.** Quick tour of how we locked it down. First, we check every
> incoming request, so bad input gives a clean error instead of crashing — and we
> cap sizes so nobody can spam the expensive AI calls. There's an optional login
> key on the sensitive routes; it's off by default so the demo just runs, and you
> switch it on with one setting. We added rate limiting — and we tested it: the
> 16th AI call in a minute gets turned away. We scanned our building blocks and
> patched two real security holes in our web framework. The question everyone asks
> is "can a sneaky email trick the AI?" — so we took it seriously and layered up.
> Anything from an email gets wrapped in a kind of quarantine tape the email can't
> fake, we strip out invisible characters people use to hide instructions, and we
> tell the AI plainly that email text is data to read, never orders to follow. And
> the ultimate safety net: the AI's tools are *read-only*, so even if something
> slipped through, the worst case is a misleading summary — it can't send mail or
> delete anything. Best part: we didn't just claim this — we built a red-team test
> that emails the app six different attacks and checks it holds. Right now it stops
> all six. It's all written up in our security doc.
>
> **Quick reminders (what these are):**
> - **Flask-Limiter** — the add-on that enforces "only N requests per minute."
> - **CORS** — the browser rule for which websites may call our server.
> - **Werkzeug** — the low-level engine underneath Flask (where two of the holes
>   were).
> - **pip-audit / npm audit** — scanners that check our Python / JavaScript
>   building blocks for known security holes.
> - **bandit** — a scanner that reads *our own* Python code for risky patterns.
> - **CVE** — a publicly catalogued, known security vulnerability.
> - **prompt injection** — a malicious email trying to give the AI sneaky
>   instructions.
> - **data fencing** — wrapping untrusted text in unique markers so the AI knows
>   exactly where the "just data" starts and stops.
> - **red-team** — deliberately attacking your own system to prove the defenses
>   work.

---

## Slide 9 — Demo: one button click → an agent run

**Scenario:** user clicks **Summarize** on the Phoenix thread.

```
DATA FLOW — user → MCP agent → back to user

REQUEST (down)
  You ─▶ UI ─▶ Flask server ─▶ MCP client ─▶ Claude (AI)
               [auth ▸ rate-limit ▸ size]        │
                                           "I need the thread"
                                                 ▼
                                  MCP server (tools) ─▶ SQLite (emails)

RESPONSE (back up)
  SQLite ─▶ MCP server ─▶ Claude writes summary ─▶ Flask ─▶ UI ─▶ You
                                                        (+ tool_calls "receipt")
```

1. **Click** — In the email toolbar, the user opens the **✨ AI Insights** drawer
   and clicks **Summarize**.
2. **Client call** — `AiActionsDrawer` calls `ai.summarize(threadId)` →
   `GET /ai/summarize/phoenix-timeline-001` (auto-attaching `X-API-Key` if auth
   is on).
3. **Gatekeeping** — Flask runs the request through **auth → rate limit →
   input-size** checks.
4. **Feature** — `summarize_thread()` builds a task prompt + system prompt and
   calls `run_agent(tools=["get_thread"])` — exposing *only* the tool it needs.
5. **Agent loop (MCP)** — the **persistent MCP session** dispatches to Claude.
   Claude decides to call **`get_thread`** → the **MCP server** runs it against
   SQLite → returns the thread's emails → Claude writes the summary.
6. **Response** — formatted as text and rendered live in the drawer:
   ```
   Thread: phoenix-timeline-001
   Summary: "David asked about the Phoenix timeline; Alex confirmed April 15 but
   flagged the auth-integration risk; David requested a sync before the board call."
   ```
7. **Transparency** — the response's `tool_calls` trace shows `get_thread` fired —
   proof the answer is grounded via MCP + RAG, not guessed.

**One sentence:** *a button click becomes an authenticated, rate-limited REST call
that runs Claude through the MCP tool layer, which pulls the real emails and
returns a grounded, formatted result.*

> **Speaker notes.** If I can, I'll click it live; if not, I'll walk through it.
> The whole point is to make the plumbing feel real: one click travels all the way
> down — through the security checks, to the AI, out to grab the actual emails, and
> back with an answer. The moment to point at is step five: we don't tell the AI
> which tool to use — it decides, we run it, and hand the result back. And step
> seven is the trust part: every answer comes with a little receipt showing which
> tools it used, so you can prove it actually read your emails instead of making it
> up. I'd end on that one-liner — it sums up the whole talk.
>
> **Quick reminders (what these are):**
> - **REST call / endpoint** — a specific web address the app pokes to get data
>   (e.g. `/ai/summarize/...`).
> - **`get_thread`** — one of our tools; it fetches all emails in a thread.
> - **`tool_calls` trace** — the "receipt" listing which tools the AI used, so the
>   answer is auditable.
> - **API key** — the shared secret the app sends to prove it's allowed in.

---

## Slide 10 — Run it locally (setup)

Two terminals:

```
# Terminal 1 — server (API at http://localhost:5000)
cd server
uv run flask --app main run

# Terminal 2 — client (app at http://localhost:5173)
cd client
npm install        # first time only
npm run dev
```

Then open **http://localhost:5173** and click **Reset DB** to load the sample
emails.

Optional environment variables:
- `FLASK_DEBUG=1` (server) — enable debug mode for local dev.
- `APP_API_KEY=…` (server) + `VITE_API_KEY=…` (client) — turn on the API-key auth.
- `LOG_LEVEL=DEBUG` and `LOG_FILE=app.log` (server) — control logging.

> **Speaker notes.** Two terminals, that's it. One runs the Python API, the other
> runs the React app; open the browser at localhost:5173 and hit "Reset DB" to load
> the sample inbox. The first AI action takes a few seconds while it warms up. If I
> want to show the login turned on, I set those two keys — otherwise they're off and
> it just runs.
>
> **Quick reminders (what these are):**
> - **`uv run`** — runs the Python command inside the project's managed environment.
> - **`npm run dev`** — starts the React app's live dev server.
> - **Reset DB** — a button that reloads the sample emails (and re-indexes them).
