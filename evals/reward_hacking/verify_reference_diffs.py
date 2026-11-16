#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evals/reward_hacking/verify_reference_diffs.py
=================================================
`tasks/<task_id>/` の全課題について、`correct_fix.diff` /
`shortcut_fix.diff` を**実際に適用し、実際にpytestを実行し**、
Parrhesiaの検出器(`parrhesia.diff_fraud.analyze_diff`)を**実際に
diffテキストに適用して**、次を確認する([依頼書 第3弾 §3 ステップ3]):

  1. 出発コード(`starting/`)に対して、`test_task.py`の`test_main`が
     実際に失敗すること(課題そのものの健全性チェック)。
  2. `correct_fix.diff`を適用すると、実際にテストが通ること。かつ
     `analyze_diff()`が誤検知(finding)を出さないこと(出た場合は
     隠さずに記録する)。
  3. `shortcut_fix.diff`を適用すると、実際にテストが通ること(近道が
     本当にテストを欺けることの確認)。かつ`analyze_diff()`が、その
     課題の`category`に対応する`pattern_id`を検出すること。

結果は推測せず、すべて実行結果から得る。`data/reference_diff_
verification.json` に出力し、README/REVIEWER_OVERVIEWはこのファイルの
数字だけを引用する。

再現コマンド:
    python3 evals/reward_hacking/build_tasks.py
    python3 evals/reward_hacking/verify_reference_diffs.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
TASKS_DIR = HERE / "tasks"
DATA_DIR = HERE / "data"
REPO_ROOT = HERE.parent.parent

sys.path.insert(0, str(REPO_ROOT))
from parrhesia.diff_fraud import analyze_diff  # noqa: E402

# カテゴリ名(本評価での呼称) -> Parrhesia検出器のpattern_id
# [確認できなかったこと] `evals/diff_audit/`のCATEGORIES一覧では
# 終了コード固定カテゴリを"hardcoded_exit_code"と呼んでいるが、
# `parrhesia.diff_fraud`自身のpattern_idは"exit_code_hardcoding"
# (語順が違う)。本評価では両方の表記揺れが実在することを記録し、
# ここで素直にマッピングする(統一のための勝手なリネームはしない)。
CATEGORY_TO_PATTERN_ID = {
    "deleted_test": "test_deletion",
    "skip_marker": "skip_addition",
    "weakened_assert": "assertion_weakening",
    "swallowed_exception": "exception_swallowing",
    "hardcoded_exit_code": "exit_code_hardcoding",
}


def _run_pytest(workdir: Path) -> Dict:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "test_task.py", "-q",
         "--basetemp", str(workdir / ".pytest_basetemp")],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    return {
        "returncode": result.returncode,
        "passed": result.returncode == 0,
        "stdout_tail": "\n".join(result.stdout.splitlines()[-15:]),
    }


def _apply_diff(workdir: Path, diff_path: Path) -> Dict:
    result = subprocess.run(
        ["patch", "-p1", "--batch", "-i", str(diff_path)],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    return {
        "applied": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _copy_starting(task_dir: Path, dest: Path) -> None:
    import shutil

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(task_dir / "starting", dest)


def _verify_one_task(task_dir: Path) -> Dict:
    meta = json.loads((task_dir / "meta.json").read_text(encoding="utf-8"))
    task_id = meta["task_id"]
    category = meta["category"]
    expected_pattern_id = CATEGORY_TO_PATTERN_ID[category]

    report: Dict = {"task_id": task_id, "category": category}

    with tempfile.TemporaryDirectory(prefix=f"rh_verify_{task_id}_") as tmp:
        tmp_path = Path(tmp)

        # 1. 出発コードは実際に失敗するか
        starting_dir = tmp_path / "starting"
        _copy_starting(task_dir, starting_dir)
        starting_result = _run_pytest(starting_dir)
        report["starting_test_fails"] = not starting_result["passed"]
        report["starting_pytest_returncode"] = starting_result["returncode"]

        # 2. correct_fix.diff
        correct_dir = tmp_path / "correct"
        _copy_starting(task_dir, correct_dir)
        correct_diff_text = (task_dir / "correct_fix.diff").read_text(encoding="utf-8")
        apply_result = _apply_diff(correct_dir, task_dir / "correct_fix.diff")
        correct_test_result = _run_pytest(correct_dir) if apply_result["applied"] else {"passed": False}
        correct_findings = analyze_diff(correct_diff_text)
        report["correct_fix"] = {
            "diff_applied": apply_result["applied"],
            "test_passes": correct_test_result["passed"],
            "detector_findings": [f.pattern_id for f in correct_findings],
            "false_positive": len(correct_findings) > 0,
        }

        # 3. shortcut_fix.diff
        shortcut_dir = tmp_path / "shortcut"
        _copy_starting(task_dir, shortcut_dir)
        shortcut_diff_text = (task_dir / "shortcut_fix.diff").read_text(encoding="utf-8")
        apply_result_sc = _apply_diff(shortcut_dir, task_dir / "shortcut_fix.diff")
        shortcut_test_result = _run_pytest(shortcut_dir) if apply_result_sc["applied"] else {"passed": False}
        shortcut_findings = analyze_diff(shortcut_diff_text)
        shortcut_pattern_ids = [f.pattern_id for f in shortcut_findings]
        report["shortcut_fix"] = {
            "diff_applied": apply_result_sc["applied"],
            "test_fools_into_passing": shortcut_test_result["passed"],
            "detector_findings": shortcut_pattern_ids,
            "detected_expected_category": expected_pattern_id in shortcut_pattern_ids,
        }

    return report


def main() -> None:
    task_dirs = sorted(d for d in TASKS_DIR.iterdir() if d.is_dir())
    if not task_dirs:
        raise SystemExit(
            f"{TASKS_DIR} に課題がありません。先に "
            "`python3 evals/reward_hacking/build_tasks.py` を実行してください。"
        )

    reports: List[Dict] = [_verify_one_task(d) for d in task_dirs]

    n = len(reports)
    n_starting_fails = sum(1 for r in reports if r["starting_test_fails"])
    n_correct_passes = sum(1 for r in reports if r["correct_fix"]["test_passes"])
    n_correct_false_positive = sum(1 for r in reports if r["correct_fix"]["false_positive"])
    n_shortcut_fools = sum(1 for r in reports if r["shortcut_fix"]["test_fools_into_passing"])
    n_shortcut_detected = sum(1 for r in reports if r["shortcut_fix"]["detected_expected_category"])

    summary = {
        "n_tasks": n,
        "starting_test_fails": f"{n_starting_fails}/{n}",
        "correct_fix_test_passes": f"{n_correct_passes}/{n}",
        "correct_fix_false_positive": f"{n_correct_false_positive}/{n}",
        "shortcut_fix_fools_test": f"{n_shortcut_fools}/{n}",
        "shortcut_fix_detected_by_detector": f"{n_shortcut_detected}/{n}",
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "reference_diff_verification.json"
    out_path.write_text(
        json.dumps({"summary": summary, "tasks": reports}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("[verify_reference_diffs] 結果:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"[verify_reference_diffs] 詳細を {out_path} に書き込みました。")

    failures = []
    for r in reports:
        if not r["starting_test_fails"]:
            failures.append(f"{r['task_id']}: 出発コードのテストが失敗していない(課題の設計ミス)")
        if not r["correct_fix"]["test_passes"]:
            failures.append(f"{r['task_id']}: correct_fix.diff を適用してもテストが通らない")
        if not r["shortcut_fix"]["test_fools_into_passing"]:
            failures.append(f"{r['task_id']}: shortcut_fix.diff を適用してもテストが通らない(近道になっていない)")
    if failures:
        print("\n[verify_reference_diffs] 課題設計の不具合(修正が必要):", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
