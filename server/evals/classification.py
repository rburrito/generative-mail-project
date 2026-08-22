"""Classification eval — accuracy / precision / recall for /ai/classify.

Runs the classifier over a labeled set of threads and reports, per field
(urgency, thread_state, category):
  - accuracy (% of threads the field got right)
  - precision / recall / F1 per class, plus macro-F1

It also records per-call latency and token cost while running, so this one
harness covers accuracy + latency + cost for the classifier.

GOLD labels are a judgment call (urgency/state/category are partly subjective) —
edit them to match how YOU would label each thread; the metric is only as good as
this set. Run from server/:

    uv run python -m evals.classification
"""

from __future__ import annotations

import time

from agents.classifier import classify_thread
from agents.mcp_client import reset_usage, get_usage

# thread_id -> expected {urgency, thread_state, category}. Edit to taste.
GOLD = {
    "bug-escalation-010": {"urgency": "urgent", "thread_state": "waiting_on_them", "category": "customer_issue"},
    "mobile-offline-002": {"urgency": "normal", "thread_state": "resolved", "category": "product_decision"},
    "recognition-012": {"urgency": "low", "thread_state": "fyi", "category": "recognition"},
    "enterprise-dash-004": {"urgency": "high", "thread_state": "waiting_on_them", "category": "sales"},
    "competitive-011": {"urgency": "normal", "thread_state": "fyi", "category": "internal_update"},
    "data-insights-006": {"urgency": "normal", "thread_state": "fyi", "category": "internal_update"},
    "support-feedback-005": {"urgency": "high", "thread_state": "fyi", "category": "customer_issue"},
    "phoenix-timeline-001": {"urgency": "high", "thread_state": "waiting_on_me", "category": "launch"},
    "marketing-launch-007": {"urgency": "normal", "thread_state": "resolved", "category": "launch"},
    "design-review-003": {"urgency": "normal", "thread_state": "waiting_on_them", "category": "launch"},
}

FIELDS = ["urgency", "thread_state", "category"]


def _prf(gold: list[str], pred: list[str]) -> tuple[float, dict, float]:
    """Return (accuracy, {class: (P, R, F1, support)}, macro_F1)."""
    classes = sorted(set(gold) | set(pred))
    rows = {}
    for c in classes:
        tp = sum(1 for g, p in zip(gold, pred) if g == c and p == c)
        fp = sum(1 for g, p in zip(gold, pred) if p == c and g != c)
        fn = sum(1 for g, p in zip(gold, pred) if g == c and p != c)
        support = sum(1 for g in gold if g == c)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        rows[c] = (precision, recall, f1, support)

    present = [c for c in classes if rows[c][3] > 0]  # macro over classes in gold
    macro_f1 = sum(rows[c][2] for c in present) / len(present) if present else 0.0
    accuracy = sum(1 for g, p in zip(gold, pred) if g == p) / len(gold)
    return accuracy, rows, macro_f1


def evaluate() -> dict:
    """Run the classification eval and print a report. Returns summary metrics."""
    preds = {}
    latencies = []
    tokens_in = tokens_out = 0

    for thread_id in GOLD:
        reset_usage()
        start = time.perf_counter()
        result = classify_thread(thread_id)
        latencies.append(time.perf_counter() - start)
        usage = get_usage()
        tokens_in += usage["input_tokens"]
        tokens_out += usage["output_tokens"]
        preds[thread_id] = result

    print(f"Classification eval - /ai/classify ({len(GOLD)} threads)")
    print("=" * 56)

    summary = {}
    for field in FIELDS:
        gold = [GOLD[t][field] for t in GOLD]
        pred = [preds[t][field] for t in GOLD]
        accuracy, rows, macro_f1 = _prf(gold, pred)
        summary[field] = {"accuracy": accuracy, "macro_f1": macro_f1}

        print(f"\nField: {field:<14} accuracy {accuracy:.2f}   macro-F1 {macro_f1:.2f}")
        print(f"  {'class':<18}{'P':>6}{'R':>6}{'F1':>6}{'n':>4}")
        for c in sorted(rows):
            p, r, f1, support = rows[c]
            print(f"  {c:<18}{p:>6.2f}{r:>6.2f}{f1:>6.2f}{support:>4}")

    n = len(GOLD)
    print("\n" + "-" * 56)
    print(
        f"latency: mean {sum(latencies)/n:.1f}s "
        f"(min {min(latencies):.1f}s, max {max(latencies):.1f}s)"
    )
    print(
        f"cost:    mean {(tokens_in + tokens_out)//n} tokens/call "
        f"(in {tokens_in//n}, out {tokens_out//n})"
    )

    return {
        "fields": summary,
        "mean_latency_s": sum(latencies) / n,
        "mean_tokens": (tokens_in + tokens_out) / n,
    }


if __name__ == "__main__":
    evaluate()
