#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evals/diff_audit/measure_frozen_holdout.py
=============================================
§DCで記録した既知の限界(detect_test_deletionがリネームを削除と区別
できない/detect_skip_additionが見た目だけ移動したskip行を新規追加と
誤認する)の改善を測るため、`data/frozen_rename_skipmove_holdout.jsonl`
(改善前に凍結済み、24件)に対してParrhesiaの検出器を実行し、誤検知率を
Wilson信頼区間つきで算出する。

このスクリプトは「改善前」「改善後」の両方で同じコマンドを実行し、
出力をそのまま記録する(手計算・推測は行わない)。

再現コマンド:
    python3 evals/diff_audit/measure_frozen_holdout.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
DATA_DIR = HERE / "data"

sys.path.insert(0, str(REPO_ROOT))
from parrhesia.diff_fraud import analyze_diff  # noqa: E402
from baseline import wilson_ci  # noqa: E402

FROZEN_PATH = DATA_DIR / "frozen_rename_skipmove_holdout.jsonl"


def load_frozen_samples() -> List[Dict]:
    if not FROZEN_PATH.exists():
        print(
            f"エラー: {FROZEN_PATH} がありません。"
            "先に build_frozen_holdout.py を一度だけ実行してください"
            "(既に実行済みの場合はファイルが誤って削除された可能性があります)。",
            file=sys.stderr,
        )
        sys.exit(1)
    rows = []
    with open(FROZEN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def run(samples: List[Dict]) -> Dict:
    results = []
    for s in samples:
        findings = analyze_diff(s["diff"])
        predicted_categories = sorted({f.pattern_id for f in findings})
        flagged = len(predicted_categories) > 0
        tag = s["generation_method"].split(":")[1] if ":" in s["generation_method"] else "unknown"
        results.append({
            "id": s["id"],
            "tag": tag,
            "flagged": flagged,
            "predicted_categories": predicted_categories,
        })
    return results


def summarize(results: List[Dict]) -> Dict:
    n = len(results)
    n_flagged = sum(1 for r in results if r["flagged"])
    rate = n_flagged / n if n else None
    ci = wilson_ci(n_flagged, n)

    by_group = {}
    for group_key, prefix in (("rename", "rename"), ("skip_move", "skip_move")):
        rows = [r for r in results if r["tag"] == prefix or r["tag"].startswith(prefix)]
        g_n = len(rows)
        g_flagged = sum(1 for r in rows if r["flagged"])
        g_rate = g_flagged / g_n if g_n else None
        g_ci = wilson_ci(g_flagged, g_n)
        by_group[group_key] = {
            "numerator": g_flagged,
            "denominator": g_n,
            "rate": g_rate,
            "wilson_95ci_low": g_ci[0],
            "wilson_95ci_high": g_ci[1],
        }

    return {
        "n_total": n,
        "n_flagged": n_flagged,
        "false_positive_rate": rate,
        "wilson_95ci_low": ci[0],
        "wilson_95ci_high": ci[1],
        "by_group": by_group,
        "flagged_ids": [r["id"] for r in results if r["flagged"]],
    }


def main():
    samples = load_frozen_samples()
    results = run(samples)
    summary = summarize(results)

    out_path = DATA_DIR / "frozen_holdout_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "summary": summary}, f, ensure_ascii=False, indent=2)

    print(f"凍結ホールドアウト({summary['n_total']}件)に対する検出器の誤検知率:")
    print(
        f"  全体: {summary['n_flagged']}/{summary['n_total']} = "
        f"{summary['false_positive_rate']:.3f}  "
        f"(Wilson 95%CI: [{summary['wilson_95ci_low']:.3f}, {summary['wilson_95ci_high']:.3f}])"
    )
    for group, g in summary["by_group"].items():
        rate_str = f"{g['rate']:.3f}" if g["rate"] is not None else "N/A"
        print(
            f"  {group}: {g['numerator']}/{g['denominator']} = {rate_str}  "
            f"(Wilson 95%CI: [{g['wilson_95ci_low']:.3f}, {g['wilson_95ci_high']:.3f}])"
        )
    print(f"詳細: {out_path}")


if __name__ == "__main__":
    main()
