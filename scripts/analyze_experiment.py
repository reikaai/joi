"""Reproducible analysis of v1.1 experiment results.

Reads 6 JSONL files, applies human-assigned rubric scores from blind review,
computes aggregate statistics using tests.eval.stats utilities.
"""

import json
import sys
from pathlib import Path

from loguru import logger

# Add project root to path for stats import
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.eval.stats import bootstrap_ci, compare_variants, fisher_exact_comparison

# ── Human-assigned rubric scores from blind transcript review ──
# Format: (tool_selection, parameter_quality, ambiguity_handling, naturalness)
# Each dimension: good=3, acceptable=2, poor=1
# Any dimension scored poor(1) => overall fail (0.0), else pass (1.0)
#
# Scores assigned AFTER reading all 120 transcripts blind (before aggregate stats).
# Key rubric rules applied:
#   - Clarification IS valid when prompt genuinely ambiguous
#   - Tool-only responses (empty text + tool_calls) valid for clear scheduling
#   - Negative scenarios: conversational + no tools = good
#   - Cross-run consistency matters

RUBRIC_SCORES: dict[str, dict[str, tuple[int, int, int, int]]] = {
    # ── Sanity ──
    "sanity:explicit_onetime": {
        "baseline": (3, 3, 3, 3),  # Correct tool, correct params, clear request handled
        "applike": (3, 3, 3, 3),  # Correct tool (calendar_create_event), ISO datetime
    },
    "sanity:explicit_recurring": {
        "baseline": (3, 3, 3, 3),  # schedule_task with recurring=true, correct cron
        "applike": (3, 3, 3, 3),  # reminders_create with correct cron schedule
    },
    "sanity:list_tasks": {
        "baseline": (3, 3, 3, 3),  # list_tasks() -- correct
        "applike": (2, 3, 3, 3),  # calendar_list_events only -- misses reminders (minor)
    },
    # ── Ambiguous ──
    "ambiguous:vague_timing": {
        # Baseline asks clarification 3/3 -- valid for "in a bit" (genuinely ambiguous)
        "baseline": (3, 3, 3, 3),
        # Applike acts with 15 min default 3/3 -- also valid, reasonable assumed default
        "applike": (3, 2, 2, 3),
    },
    "ambiguous:soon_laundry": {
        # Both ask clarification 3/3 -- valid for "soon"
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "ambiguous:vitamins_habit": {
        # Baseline acts 3/3 with daily 9am recurring -- reasonable interpretation
        "baseline": (3, 2, 3, 3),
        # Applike: run1 asks, runs 2-3 act with 8am -- cross-run inconsistency
        "applike": (3, 2, 2, 3),
    },
    "ambiguous:wake_up": {
        # Baseline asks clarification 3/3 -- valid, needs to know what time
        "baseline": (3, 3, 3, 3),
        # Applike acts with default 8am 3/3 -- reasonable default but assumed
        "applike": (3, 2, 2, 3),
    },
    "ambiguous:forgetting_plants": {
        # Both ask clarification 3/3 -- valid, needs frequency/time
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "ambiguous:later_reminder": {
        # Both ask clarification 3/3 -- valid, "later" maximally vague
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    # ── Routing ──
    "routing:two_onetime": {
        # Both handle 2 one-time items correctly 3/3
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "routing:mixed_onetime_recurring": {
        # Both handle mixed correctly 3/3
        "baseline": (3, 3, 3, 3),
        # Applike: semantically superior routing (calendar + reminders)
        "applike": (3, 3, 3, 3),
    },
    "routing:ambiguous_tool_choice": {
        # Both handle recurring+one-off correctly 3/3
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "routing:three_items": {
        # Both handle 3 items correctly 3/3
        "baseline": (3, 2, 3, 3),  # dentist cron slightly odd but works
        "applike": (3, 3, 3, 3),  # ISO datetime for dentist -- cleaner
    },
    # ── Negative ──
    "negative:wistful_intent": {
        # Both correctly avoid scheduling, conversational 3/3
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "negative:past_tense": {
        # Both correctly identify past event, no tools 3/3
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "negative:time_question": {
        # Both answer time question correctly, no tools 3/3
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "negative:recall_not_remind": {
        # Both recognize "remind me what" = recall, not schedule 3/3
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    # ── Implicit ──
    "implicit:before_weekend": {
        # Both ask clarification 3/3 -- correct, it's already Saturday
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "implicit:usual_morning": {
        # Both ask clarification 3/3 -- correct, no "usual" context
        "baseline": (3, 3, 3, 3),
        "applike": (3, 3, 3, 3),
    },
    "implicit:after_work": {
        # Baseline asks clarification 3/3 -- valid, doesn't know work hours
        "baseline": (3, 3, 3, 3),
        # Applike acts with 5pm default 3/3 -- reasonable assumed default
        "applike": (3, 2, 2, 3),
    },
}


def score_to_binary(scores: tuple[int, int, int, int]) -> float:
    """Any dimension scored poor (1) => fail (0.0), else pass (1.0)."""
    return 0.0 if any(s == 1 for s in scores) else 1.0


def load_results(results_dir: Path) -> list[dict]:
    """Load all scenario results from JSONL files."""
    all_results = []
    jsonl_files = sorted(results_dir.glob("*.jsonl"))
    logger.info(f"Found {len(jsonl_files)} JSONL files in {results_dir}")

    for fpath in jsonl_files:
        count = 0
        for line in fpath.read_text().splitlines():
            record = json.loads(line)
            if record.get("type") == "scenario_result":
                all_results.append(record)
                count += 1
        logger.info(f"  {fpath.name}: {count} scenario results")

    logger.info(f"Total scenario results loaded: {len(all_results)}")
    return all_results


def assign_scores(results: list[dict]) -> list[dict]:
    """Assign rubric scores and binary pass/fail to each result."""
    for r in results:
        sid = r["scenario_id"]
        variant = r["variant"]
        rubric = RUBRIC_SCORES[sid][variant]
        r["rubric_scores"] = rubric
        r["pass"] = score_to_binary(rubric)
    return results


def print_overall_stats(results: list[dict]) -> None:
    """Print overall pass rates per variant with bootstrap CIs."""
    print("\n" + "=" * 70)
    print("OVERALL RESULTS")
    print("=" * 70)

    for variant in ("baseline", "applike"):
        scores = [r["pass"] for r in results if r["variant"] == variant]
        ci = bootstrap_ci(scores)
        print(
            f"\n{variant:>10s}: {ci['mean']:6.1%} pass rate "
            f"[{ci['ci_low']:.1%}, {ci['ci_high']:.1%}] "
            f"(n={ci['n_samples']})"
        )

    # Fisher exact comparison
    b_scores = [r["pass"] for r in results if r["variant"] == "baseline"]
    a_scores = [r["pass"] for r in results if r["variant"] == "applike"]
    fisher = fisher_exact_comparison(b_scores, a_scores)
    comp = compare_variants(b_scores, a_scores)
    print("\nBaseline vs Applike:")
    print(f"  Difference: {comp['difference']:+.1%}")
    if not (comp["ci_low"] != comp["ci_low"]):  # not NaN
        print(f"  95% CI: [{comp['ci_low']:.1%}, {comp['ci_high']:.1%}]")
    print(f"  Fisher p={fisher['p_value']:.4f}")
    print(f"  Significant: {'YES' if fisher['significant'] else 'No'}")


def print_category_stats(results: list[dict]) -> None:
    """Print per-category breakdown with Fisher exact tests."""
    print("\n" + "=" * 70)
    print("PER-CATEGORY BREAKDOWN")
    print("=" * 70)

    categories = ["sanity", "ambiguous", "routing", "negative", "implicit"]
    print(
        f"\n{'Category':>12s} | {'Baseline':>10s} | {'Applike':>10s} | "
        f"{'Delta':>8s} | {'Fisher p':>10s} | {'Sig?':>5s} | {'n/var':>6s}"
    )
    print("-" * 78)

    for cat in categories:
        b = [r["pass"] for r in results if r["variant"] == "baseline" and r["category"] == cat]
        a = [r["pass"] for r in results if r["variant"] == "applike" and r["category"] == cat]

        b_ci = bootstrap_ci(b)
        a_ci = bootstrap_ci(a)
        fisher = fisher_exact_comparison(b, a)

        delta = a_ci["mean"] - b_ci["mean"]
        sig = "YES" if fisher["significant"] else "No"

        print(
            f"{cat:>12s} | {b_ci['mean']:>9.1%} | {a_ci['mean']:>9.1%} | "
            f"{delta:>+7.1%} | {fisher['p_value']:>10.4f} | {sig:>5s} | {len(b):>6d}"
        )


def print_per_scenario_stats(results: list[dict]) -> None:
    """Print per-scenario detail."""
    print("\n" + "=" * 70)
    print("PER-SCENARIO DETAIL")
    print("=" * 70)

    scenarios = sorted({r["scenario_id"] for r in results})

    print(
        f"\n{'Scenario':>30s} | {'B pass':>6s} | {'A pass':>6s} | {'B rubric':>12s} | {'A rubric':>12s}"
    )
    print("-" * 80)

    for sid in scenarios:
        b_results = [r for r in results if r["scenario_id"] == sid and r["variant"] == "baseline"]
        a_results = [r for r in results if r["scenario_id"] == sid and r["variant"] == "applike"]

        b_pass = sum(r["pass"] for r in b_results) / len(b_results)
        a_pass = sum(r["pass"] for r in a_results) / len(a_results)

        b_rubric = b_results[0]["rubric_scores"]
        a_rubric = a_results[0]["rubric_scores"]

        b_r_str = f"({b_rubric[0]},{b_rubric[1]},{b_rubric[2]},{b_rubric[3]})"
        a_r_str = f"({a_rubric[0]},{a_rubric[1]},{a_rubric[2]},{a_rubric[3]})"

        print(f"{sid:>30s} | {b_pass:>5.0%} | {a_pass:>5.0%} | {b_r_str:>12s} | {a_r_str:>12s}")


def print_token_stats(results: list[dict]) -> None:
    """Print token usage comparison."""
    print("\n" + "=" * 70)
    print("TOKEN USAGE")
    print("=" * 70)

    for variant in ("baseline", "applike"):
        tokens = [float(r["total_tokens"]) for r in results if r["variant"] == variant]
        ci = bootstrap_ci(tokens)
        print(
            f"\n{variant:>10s}: mean={ci['mean']:.0f} tokens "
            f"[{ci['ci_low']:.0f}, {ci['ci_high']:.0f}] "
            f"(n={ci['n_samples']})"
        )

    b_tokens = [float(r["total_tokens"]) for r in results if r["variant"] == "baseline"]
    a_tokens = [float(r["total_tokens"]) for r in results if r["variant"] == "applike"]
    comp = compare_variants(b_tokens, a_tokens)
    print(f"\nBaseline vs Applike token difference: {comp['difference']:+.0f}")
    print(f"  Significant: {'YES' if comp['significant'] else 'No'}")


def main() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    results_dir = Path(__file__).parent.parent / "results"
    if not results_dir.exists():
        logger.error(f"Results directory not found: {results_dir}")
        sys.exit(1)

    results = load_results(results_dir)
    if len(results) != 120:
        logger.warning(f"Expected 120 results, got {len(results)}")

    results = assign_scores(results)

    print_overall_stats(results)
    print_category_stats(results)
    print_per_scenario_stats(results)
    print_token_stats(results)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print(f"Processed {len(results)} scenario results from {len(list(results_dir.glob('*.jsonl')))} files")
    print("=" * 70)


if __name__ == "__main__":
    main()
