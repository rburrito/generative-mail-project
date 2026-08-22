"""Hallucination rate — fraction of verifiable claims that are actually wrong.

Distinct from the faithfulness score: faithfulness rates overall grounding,
while this counts, across generated summaries, how many *verifiable* claims
(claims that can be checked against the source) are *incorrect* (contradict the
source or state something false). Reasonable paraphrase and omissions don't
count — only factual errors.

    hallucination_rate = incorrect_claims / total_verifiable_claims

Run from server/:

    uv run python -m evals.hallucination
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
    "You check a SUMMARY for hallucinations against the SOURCE emails. A "
    "'verifiable claim' is a factual statement in the summary that can be checked "
    "against the source. Count how many verifiable claims the summary makes "
    "(total_verifiable_claims), and list only those that are INCORRECT — they "
    "contradict the source or state something false (incorrect_claims). Do NOT "
    "count omissions, reasonable paraphrase, or claims that are simply not in the "
    "source but aren't contradicted — only outright factual errors count as "
    "incorrect."
)

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "total_verifiable_claims": {"type": "integer"},
        "incorrect_claims": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["total_verifiable_claims", "incorrect_claims", "reasoning"],
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
        "Count the verifiable claims in the summary and list any that are "
        "factually incorrect given the source."
    )
    return complete_json(prompt, JUDGE_SCHEMA, system=JUDGE_SYSTEM, model=MODEL_OPUS)


def evaluate() -> dict:
    """Run the hallucination eval and print a report. Returns summary metrics."""
    print(f"Hallucination eval, {len(THREADS)} summaries (judge: Opus)")
    print("=" * 60)
    print(f"{'thread':<28}{'claims':>8}{'incorrect':>12}")
    print("-" * 60)

    total_claims = total_incorrect = 0
    flagged = []
    for thread_id in THREADS:
        summary = summarize_thread(thread_id)["summary"]
        with app.app_context():
            source = _source_text(thread_id)
        verdict = _judge(summary, source)

        claims = verdict["total_verifiable_claims"]
        incorrect = verdict["incorrect_claims"]
        total_claims += claims
        total_incorrect += len(incorrect)
        if incorrect:
            flagged.append((thread_id, incorrect))
        print(f"{thread_id:<28}{claims:>8}{len(incorrect):>12}")

    rate = total_incorrect / total_claims if total_claims else 0.0
    print("-" * 60)
    print(
        f"hallucination rate: {rate:.1%} "
        f"({total_incorrect} incorrect / {total_claims} verifiable claims)"
    )

    if flagged:
        print("\nIncorrect claims:")
        for thread_id, claims in flagged:
            print(f"  {thread_id}:")
            for claim in claims:
                print(f"    - {claim}")

    return {"hallucination_rate": rate, "total_claims": total_claims, "flagged": flagged}


if __name__ == "__main__":
    evaluate()
