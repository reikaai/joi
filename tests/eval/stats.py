from collections import defaultdict
from pathlib import Path

import numpy as np
from loguru import logger
from scipy.stats import bootstrap
from scipy.stats import fisher_exact as _fisher_exact

# Haiku 4.5 pricing (USD per token)
HAIKU_INPUT_COST_PER_TOKEN = 1.0 / 1_000_000  # $1 per 1M input tokens
HAIKU_OUTPUT_COST_PER_TOKEN = 5.0 / 1_000_000  # $5 per 1M output tokens


def compute_cost(input_tokens: int, output_tokens: int) -> float:
    return input_tokens * HAIKU_INPUT_COST_PER_TOKEN + output_tokens * HAIKU_OUTPUT_COST_PER_TOKEN


def bootstrap_ci(
    data: list[float],
    confidence_level: float = 0.95,
    n_resamples: int = 9999,
) -> dict:
    arr = np.array(data, dtype=float)
    mean_val = float(np.mean(arr))
    n = len(arr)

    # Edge case: zero variance -- bootstrap fails on constant data
    if np.all(arr == arr[0]):
        return {
            "mean": mean_val,
            "ci_low": mean_val,
            "ci_high": mean_val,
            "std_error": 0.0,
            "n_samples": n,
        }

    rng = np.random.default_rng(42)
    result = bootstrap(
        (arr,),
        statistic=np.mean,
        confidence_level=confidence_level,
        n_resamples=n_resamples,
        method="BCa",
        random_state=rng,
    )
    return {
        "mean": mean_val,
        "ci_low": float(result.confidence_interval.low),
        "ci_high": float(result.confidence_interval.high),
        "std_error": float(result.standard_error),
        "n_samples": n,
    }


def compare_variants(
    a_scores: list[float],
    b_scores: list[float],
    confidence_level: float = 0.95,
    n_resamples: int = 9999,
) -> dict:
    a = np.array(a_scores, dtype=float)
    b = np.array(b_scores, dtype=float)
    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    diff = mean_a - mean_b

    # Edge case: fewer than 3 samples
    if len(a) < 3 or len(b) < 3:
        return {
            "mean_a": mean_a,
            "mean_b": mean_b,
            "difference": diff,
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "confidence_level": confidence_level,
            "significant": False,
            "standard_error": float("nan"),
            "warning": f"Too few samples (a={len(a)}, b={len(b)}). Need >= 3 each.",
        }

    def mean_difference(x, y, axis):
        return np.mean(x, axis=axis) - np.mean(y, axis=axis)

    rng = np.random.default_rng(42)
    result = bootstrap(
        (a, b),
        statistic=mean_difference,
        confidence_level=confidence_level,
        n_resamples=n_resamples,
        method="BCa",
        paired=True,
        random_state=rng,
    )

    ci_low = float(result.confidence_interval.low)
    ci_high = float(result.confidence_interval.high)
    significant = not (ci_low <= 0 <= ci_high)

    return {
        "mean_a": mean_a,
        "mean_b": mean_b,
        "difference": diff,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "confidence_level": confidence_level,
        "significant": significant,
        "standard_error": float(result.standard_error),
    }


def fisher_exact_comparison(a_scores: list[float], b_scores: list[float]) -> dict:
    """Fisher exact test on binary success/fail outcomes."""
    a_pass = sum(1 for s in a_scores if s >= 1.0)
    a_fail = len(a_scores) - a_pass
    b_pass = sum(1 for s in b_scores if s >= 1.0)
    b_fail = len(b_scores) - b_pass
    table = [[a_pass, a_fail], [b_pass, b_fail]]
    odds_ratio, p_value = _fisher_exact(table, alternative="two-sided")
    return {
        "table": table,
        "odds_ratio": float(odds_ratio),
        "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
    }


def generate_report(
    results_by_variant: dict[str, list[dict]],
    output_path: Path,
) -> dict:
    report: dict = {"variants": {}, "comparisons": []}
    variant_names = list(results_by_variant.keys())

    for name, results in results_by_variant.items():
        if not results:
            continue

        scores = [r["correct_tool_score"] for r in results]
        tokens = [float(r["total_tokens"]) for r in results]
        costs = [
            compute_cost(r["input_tokens"], r["output_tokens"])
            for r in results
        ]

        # Per-category breakdown
        by_category: dict[str, list[float]] = defaultdict(list)
        for r in results:
            by_category[r["category"]].append(r["correct_tool_score"])
        category_stats = {
            cat: bootstrap_ci(cat_scores) for cat, cat_scores in sorted(by_category.items())
        }

        report["variants"][name] = {
            "n_samples": len(results),
            "success_rate": bootstrap_ci(scores),
            "token_usage": bootstrap_ci(tokens),
            "cost_usd": bootstrap_ci(costs),
            "by_category": category_stats,
        }

        logger.info(
            f"Variant '{name}': n={len(results)}, "
            f"success={report['variants'][name]['success_rate']['mean']:.2%}, "
            f"tokens={report['variants'][name]['token_usage']['mean']:.0f}, "
            f"cost=${report['variants'][name]['cost_usd']['mean']:.6f}"
        )

    # Pairwise comparisons
    if len(variant_names) >= 2:
        for i, a_name in enumerate(variant_names):
            for b_name in variant_names[i + 1 :]:
                a_results = results_by_variant[a_name]
                b_results = results_by_variant[b_name]
                if not a_results or not b_results:
                    continue

                a_scores = [r["correct_tool_score"] for r in a_results]
                b_scores = [r["correct_tool_score"] for r in b_results]
                comparison = compare_variants(a_scores, b_scores)
                comparison["variant_a"] = a_name
                comparison["variant_b"] = b_name
                comparison["fisher_exact"] = fisher_exact_comparison(a_scores, b_scores)
                report["comparisons"].append(comparison)

                sig_label = "SIGNIFICANT" if comparison["significant"] else "not significant"
                logger.info(
                    f"Comparison {a_name} vs {b_name}: "
                    f"diff={comparison['difference']:.3f} [{comparison['ci_low']:.3f}, {comparison['ci_high']:.3f}] "
                    f"({sig_label})"
                )

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    output_path.write_text(json.dumps(report, indent=2, default=str))
    logger.info(f"Report written to {output_path}")

    return report
