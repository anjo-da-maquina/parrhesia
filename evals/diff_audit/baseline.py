#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evals/diff_audit/baseline.py
================================
Parrhesia自身のルールベース検出器(`parrhesia/diff_fraud.py`)を、
`data/eval.jsonl`(最終評価用、tuneには使わない)に対して実際に実行し、
カテゴリ別のrecall/precisionと、cleanの誤検知率(最重要指標、Wilson信頼
区間つき)を算出する。

本スクリプトは標準ライブラリのみに依存し、`inspect_ai`を一切importしない
(ベースラインはLLMではなく既存のルールベース検出器そのものであるため)。

再現コマンド:
    python3 evals/diff_audit/baseline.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
DATA_DIR = HERE / "data"

sys.path.insert(0, str(REPO_ROOT))
from parrhesia.diff_fraud import analyze_diff  # noqa: E402

PATTERN_ID_TO_CATEGORY = {
    "test_deletion": "deleted_test",
    "skip_addition": "skip_marker",
    "assertion_weakening": "weakened_assert",
    "exception_swallowing": "swallowed_exception",
    "exit_code_hardcoding": "hardcoded_exit_code",
}
SHORTCUT_CATEGORIES = list(PATTERN_ID_TO_CATEGORY.values())
ALL_CATEGORIES = ["clean"] + SHORTCUT_CATEGORIES


def wilson_ci(successes: int, total: int, z: float = 1.959963985) -> tuple:
    """Wilson score interval(95%、z≈1.959963985)。
    totalが0の場合は (0.0, 0.0) を返す(分母ゼロの退避)。"""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z ** 2 / total
    center = p + z ** 2 / (2 * total)
    margin = z * math.sqrt((p * (1 - p) / total) + (z ** 2 / (4 * total ** 2)))
    low = (center - margin) / denom
    high = (center + margin) / denom
    return (max(0.0, low), min(1.0, high))


def load_eval_samples() -> List[Dict]:
    path = DATA_DIR / "eval.jsonl"
    if not path.exists():
        print(f"エラー: {path} がありません。先に build_dataset.py を実行してください。", file=sys.stderr)
        sys.exit(1)
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def run_baseline(samples: List[Dict]) -> List[Dict]:
    results = []
    for s in samples:
        findings = analyze_diff(s["diff"])
        predicted = sorted({PATTERN_ID_TO_CATEGORY.get(f.pattern_id, f.pattern_id) for f in findings})
        results.append({
            "id": s["id"],
            "true_category": s["category"],
            "predicted_categories": predicted,
            "origin": s.get("origin"),
        })
    return results


def compute_metrics(results: List[Dict]) -> Dict:
    n_true = defaultdict(int)
    n_pred = defaultdict(int)
    n_tp = defaultdict(int)

    for r in results:
        true_cat = r["true_category"]
        n_true[true_cat] += 1
        for cat in ALL_CATEGORIES:
            predicted_cat = cat in r["predicted_categories"] if cat != "clean" else not r["predicted_categories"]
            if predicted_cat:
                n_pred[cat] += 1
                if cat == true_cat:
                    n_tp[cat] += 1

    per_category = {}
    for cat in ALL_CATEGORIES:
        recall = n_tp[cat] / n_true[cat] if n_true[cat] else None
        precision = n_tp[cat] / n_pred[cat] if n_pred[cat] else None
        per_category[cat] = {
            "n_true": n_true[cat],
            "n_predicted": n_pred[cat],
            "n_true_positive": n_tp[cat],
            "recall": recall,
            "precision": precision,
        }

    # clean誤検知率(最重要指標): true_category == clean なのに、
    # 何らかのショートカットカテゴリを誤って予測した割合。
    clean_results = [r for r in results if r["true_category"] == "clean"]
    n_clean = len(clean_results)
    n_clean_false_flagged = sum(1 for r in clean_results if r["predicted_categories"])
    fpr = n_clean_false_flagged / n_clean if n_clean else None
    fpr_ci = wilson_ci(n_clean_false_flagged, n_clean)

    # 全体正解率(補助指標。単独では主張に使わない)
    n_total = len(results)
    n_correct = sum(
        1 for r in results
        if (r["true_category"] == "clean" and not r["predicted_categories"])
        or (r["true_category"] in r["predicted_categories"])
    )
    overall_accuracy = n_correct / n_total if n_total else None

    return {
        "n_total_eval_samples": n_total,
        "per_category": per_category,
        "clean_false_positive_rate": {
            "numerator": n_clean_false_flagged,
            "denominator": n_clean,
            "rate": fpr,
            "wilson_95ci_low": fpr_ci[0],
            "wilson_95ci_high": fpr_ci[1],
        },
        "overall_accuracy_auxiliary_only": overall_accuracy,
    }


def main():
    samples = load_eval_samples()
    results = run_baseline(samples)
    metrics = compute_metrics(results)

    out_path = DATA_DIR / "baseline_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "metrics": metrics}, f, ensure_ascii=False, indent=2)

    print(f"evalサンプル数: {metrics['n_total_eval_samples']}")
    print("\nカテゴリ別 recall/precision:")
    for cat, m in metrics["per_category"].items():
        r = "N/A" if m["recall"] is None else f"{m['recall']:.3f}"
        p = "N/A" if m["precision"] is None else f"{m['precision']:.3f}"
        print(f"  {cat:22s} recall={r:6s} ({m['n_true_positive']}/{m['n_true']})  "
              f"precision={p:6s} ({m['n_true_positive']}/{m['n_predicted']})")

    fp = metrics["clean_false_positive_rate"]
    print(f"\n[最重要] cleanの誤検知率: {fp['numerator']}/{fp['denominator']}"
          f" = {fp['rate']:.3f}  (Wilson 95%CI: [{fp['wilson_95ci_low']:.3f}, {fp['wilson_95ci_high']:.3f}])")
    print(f"\n(補助指標)全体正解率: {metrics['overall_accuracy_auxiliary_only']:.3f}")
    print(f"\n詳細結果を {out_path} に書き出しました。")


if __name__ == "__main__":
    main()
