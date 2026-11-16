"""
tests/test_evals_reward_hacking.py
======================================
evals/reward_hacking/ の回帰テスト。

`build_tasks.py`・`verify_reference_diffs.py` は標準ライブラリと
Parrhesia自身(`parrhesia.diff_fraud`)のみに依存するため、常に実行
できる。`task.py` は `inspect_ai` が必須のため、未インストール環境
(このサンドボックスを含む)では `pytest.importorskip` で明示的に
スキップする(`tests/test_evals_diff_audit.py` と同じ方針)。
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "evals" / "reward_hacking"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EVALS_DIR))

import build_tasks  # noqa: E402
import verify_reference_diffs  # noqa: E402


CATEGORIES = [
    "deleted_test",
    "skip_marker",
    "weakened_assert",
    "swallowed_exception",
    "hardcoded_exit_code",
]


# ------------------------------------------------------------------
# build_tasks.py
# ------------------------------------------------------------------

def test_build_definitions_meets_minimum_count_and_category_coverage():
    """依頼書の要件: 12〜20件、各カテゴリに該当する課題が存在すること。"""
    defs = build_tasks._build_definitions()
    assert 12 <= len(defs) <= 20, f"{len(defs)}件(12〜20件の範囲外)"
    counts = {}
    for d in defs:
        counts[d["category"]] = counts.get(d["category"], 0) + 1
    for cat in CATEGORIES:
        assert counts.get(cat, 0) >= 1, f"{cat} の課題が無い"
    assert set(counts.keys()) == set(CATEGORIES)


def test_every_task_id_is_unique():
    defs = build_tasks._build_definitions()
    ids = [d["task_id"] for d in defs]
    assert len(ids) == len(set(ids))


def test_build_tasks_main_writes_expected_files(tmp_path, monkeypatch):
    """main()を実際に実行し、各課題のファイル一式が書き出されること
    (出力先は一時ディレクトリへ差し替えて本番のtasks/を汚さない)。"""
    monkeypatch.setattr(build_tasks, "TASKS_DIR", tmp_path)
    build_tasks.main()

    task_dirs = sorted(p for p in tmp_path.iterdir() if p.is_dir())
    assert len(task_dirs) >= 12

    for task_dir in task_dirs:
        meta = json.loads((task_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta["provenance"] == "handmade"
        assert meta["category"] in CATEGORIES
        rel_path = meta["rel_path"]
        assert (task_dir / "starting" / rel_path).exists()
        assert (task_dir / "starting" / "test_task.py").exists()
        assert (task_dir / "correct_fix.diff").exists()
        assert (task_dir / "shortcut_fix.diff").exists()
        # どちらの参照差分も、実際のgit diff出力であること
        # (`+++ b/<path>` ヘッダを含む=parrhesia.diff_fraudが解析できる形式)。
        correct_diff = (task_dir / "correct_fix.diff").read_text(encoding="utf-8")
        shortcut_diff = (task_dir / "shortcut_fix.diff").read_text(encoding="utf-8")
        assert "+++ b/" in correct_diff
        assert "+++ b/" in shortcut_diff


def test_build_tasks_is_idempotent(tmp_path, monkeypatch):
    """同じ定義から再生成しても、同じ内容になること(再現性)。"""
    monkeypatch.setattr(build_tasks, "TASKS_DIR", tmp_path)
    build_tasks.main()
    first = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*") if p.is_file()
    }
    build_tasks.main()
    second = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*") if p.is_file()
    }
    assert first == second


# ------------------------------------------------------------------
# verify_reference_diffs.py (実際にpytest実行・diff適用・検出器実行を伴う)
# ------------------------------------------------------------------

def test_verify_reference_diffs_on_committed_tasks():
    """リポジトリにコミットされている tasks/ 一式に対して、
    `verify_reference_diffs.py` の確認ロジックを実際に実行し、
    全件が設計どおりであることを確認する
    (出発コードは失敗・正しい修正は通って誤検知なし・近道は通って
    意図したカテゴリとして検出される)。"""
    if not build_tasks.TASKS_DIR.exists() or not any(build_tasks.TASKS_DIR.iterdir()):
        pytest.skip("evals/reward_hacking/tasks/ が未生成(先にbuild_tasks.pyを実行する運用)")

    task_dirs = sorted(d for d in verify_reference_diffs.TASKS_DIR.iterdir() if d.is_dir())
    assert len(task_dirs) >= 12

    reports = [verify_reference_diffs._verify_one_task(d) for d in task_dirs]
    for r in reports:
        assert r["starting_test_fails"], f"{r['task_id']}: 出発コードのテストが失敗していない"
        assert r["correct_fix"]["test_passes"], f"{r['task_id']}: correct_fix.diff でテストが通らない"
        assert not r["correct_fix"]["false_positive"], (
            f"{r['task_id']}: correct_fix.diff が誤検知された: {r['correct_fix']['detector_findings']}"
        )
        assert r["shortcut_fix"]["test_fools_into_passing"], (
            f"{r['task_id']}: shortcut_fix.diff でテストが通らない(近道になっていない)"
        )
        assert r["shortcut_fix"]["detected_expected_category"], (
            f"{r['task_id']}: 期待したカテゴリが検出されなかった: {r['shortcut_fix']['detector_findings']}"
        )


def test_verify_reference_diffs_main_writes_summary(tmp_path, monkeypatch):
    """main()を実際に実行し、集計ファイルが書き出され、数字が
    手計算と一致すること。出力先は一時ディレクトリへ差し替える。"""
    monkeypatch.setattr(verify_reference_diffs, "DATA_DIR", tmp_path)
    verify_reference_diffs.main()

    out_path = tmp_path / "reference_diff_verification.json"
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    n = payload["summary"]["n_tasks"]
    assert n >= 12
    assert payload["summary"]["starting_test_fails"] == f"{n}/{n}"
    assert payload["summary"]["correct_fix_test_passes"] == f"{n}/{n}"
    assert payload["summary"]["correct_fix_false_positive"] == f"0/{n}"
    assert payload["summary"]["shortcut_fix_fools_test"] == f"{n}/{n}"
    assert payload["summary"]["shortcut_fix_detected_by_detector"] == f"{n}/{n}"


# ------------------------------------------------------------------
# task.py (inspect_ai が無い環境では明示的にスキップ)
# ------------------------------------------------------------------

def test_task_module_import_behavior():
    """`import task` の挙動を、inspect_aiの有無どちらでも確認する。"""
    try:
        import inspect_ai  # noqa: F401
    except ImportError:
        sys.modules.pop("task", None)
        with pytest.raises(ImportError, match="inspect-ai"):
            import task  # noqa: F401


def test_task_module_importable_when_inspect_ai_present():
    pytest.importorskip("inspect_ai", reason="inspect_ai unavailable (PyPI unreachable in this sandbox)")
    import task  # noqa: F401

    tasks = task._load_all_tasks()
    assert len(tasks) >= 12
    for t in tasks:
        assert t["category"] in CATEGORIES
        assert "buggy_source" in t and "test_source" in t and "correct_fix_diff_text" in t

    # _extract_diff: コードフェンス付き・無しのどちらも正しく取り出せること。
    assert task._extract_diff("--- a/x.py\n+++ b/x.py\n") == "--- a/x.py\n+++ b/x.py\n"
    fenced = "```diff\n--- a/x.py\n+++ b/x.py\n```"
    assert task._extract_diff(fenced) == "--- a/x.py\n+++ b/x.py\n"

    sample = task._build_sample(tasks[0], wiring_check=True)
    assert sample.metadata["scripted_diff"] == tasks[0]["correct_fix_diff_text"]
    sample_real = task._build_sample(tasks[0], wiring_check=False)
    assert "scripted_diff" not in sample_real.metadata
