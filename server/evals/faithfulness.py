"""Faithfulness eval — LLM-as-judge check that outputs are grounded.

For each thread we generate a summary (through the normal MCP feature), then ask
a judge model whether every claim in the summary is supported by the source
emails. Score is 1-5 (5 = fully grounded, nothing invented); the judge also lists
any unsupported claims.

The generator runs on Sonnet (the app default); the judge runs on Opus — using a
stronger grader is good practice. This makes real LLM calls (a summary + a judge
call per thread), so it costs tokens. Run from server/:

    uv run python -m evals.faithfulness
"""

from __future__ import annotations

from main import app
from agents.retrieval import get_thread
from agents.summarizer import summarize_thread
from agents.llm import complete_json, MODEL_OPUS

THREADS = [
    "phoenix-timeline-001",
    "mobile-offline-002",
    "enterprise-dash-004",
    "bug-escalation-010",
    "design-review-003",
]

JUDGE_SYSTEM = (
    "You are a strict evaluator of summary faithfulness. A faithful summary makes "
    "only claims supported by the source emails. Penalize invented facts, wrong "
    "names/dates/numbers, and unsupported conclusions. Do NOT penalize omissions — "
    "a summary leaving something out is fine; inventing something is not. "
    "Treat claims that are clearly ENTAILED by the source as supported — e.g. "
    "resolving a relative date ('tomorrow' on a dated email) to the actual date, or "
    "noting a question received no reply, or a promised item did not arrive, within "
    "the thread. Only flag claims that "
    "add facts, roles, or conclusions the source genuinely does not support. "
    "Score 1-5: 5 = every claim supported; 3 = mostly supported with a minor "
    "unsupported detail; 1 = significant fabrication."
)

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["score", "unsupported_claims", "reasoning"],
    "additionalProperties": False,
}


def _source_text(thread_id: str) -> str:
    emails = get_thread(thread_id)
    return "\n\n---\n\n".join(
        f"From: {e['sender']}\nDate: {e['created_at']}\nSubject: {e['subject']}\n\n{e['body']}"
        for e in emails
    )


def _judge(summary: str, source: str) -> dict:
    prompt = (
        "SOURCE EMAILS:\n"
        f"{source}\n\n"
        "SUMMARY:\n"
        f"{summary}\n\n"
        "Score how faithful the summary is to the source emails, and list any "
        "claims in the summary that the source does not support."
    )
    return complete_json(prompt, JUDGE_SCHEMA, system=JUDGE_SYSTEM, model=MODEL_OPUS)


def evaluate() -> dict:
    """Run the faithfulness eval and print a report. Returns summary metrics."""
    print(f"Faithfulness eval, {len(THREADS)} summaries (judge: Opus)")
    print("=" * 60)
    print(f"{'thread':<28}{'score':>7}{'unsupported':>14}")
    print("-" * 60)

    total = 0
    flagged = []
    for thread_id in THREADS:
        summary = summarize_thread(thread_id)["summary"]
        with app.app_context():
            source = _source_text(thread_id)
        verdict = _judge(summary, source)

        total += verdict["score"]
        n_unsupported = len(verdict["unsupported_claims"])
        if n_unsupported:
            flagged.append((thread_id, verdict["unsupported_claims"]))
        print(f"{thread_id:<28}{verdict['score']:>7}{n_unsupported:>14}")

    n = len(THREADS)
    mean = total / n
    print("-" * 60)
    print(f"mean faithfulness: {mean:.2f} / 5")

    if flagged:
        print("\nUnsupported claims:")
        for thread_id, claims in flagged:
            print(f"  {thread_id}:")
            for claim in claims:
                print(f"    - {claim}")

    return {"mean_faithfulness": mean, "n": n, "flagged": flagged}


if __name__ == "__main__":
    evaluate()
