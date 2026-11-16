"""
tests/test_evals_diff_audit.py
==================================
evals/diff_audit/ の回帰テスト。

`build_dataset.py`・`baseline.py` は標準ライブラリのみに依存するため、
常に実行できる。`task.py` は `inspect_ai` が必須のため、未インストール
環境(このサンドボックスを含む)では `pytest.importorskip` で明示的に
スキップする(依頼書の指示どおり、conftestを壊してテスト収集全体を
止めることは絶対にしない)。
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "evals" / "diff_audit"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EVALS_DIR))

import build_dataset  # noqa: E402


# ------------------------------------------------------------------
# build_dataset.py
# ------------------------------------------------------------------

def test_build_all_meets_minimum_category_counts():
    """依頼書の要件: 各ズルカテゴリ20件以上、clean 40件以上。"""
    samples = build_dataset.build_all()
    counts = {}
    for s in samples:
        counts[s["category"]] = counts.get(s["category"], 0) + 1

    for cat in ["deleted_test", "skip_marker", "weakened_assert", "swallowed_exception", "hardcoded_exit_code"]:
        assert counts.get(cat, 0) >= 20, f"{cat} は {counts.get(cat, 0)} 件しかない(20件以上が必要)"
    assert counts.get("clean", 0) >= 40, f"clean は {counts.get('clean', 0)} 件しかない(40件以上が必要)"


def test_every_sample_has_required_metadata():
    samples = build_dataset.build_all()
    required_keys = {"id", "diff", "category", "origin", "language", "generation_method", "split", "clean_subgroup"}
    for s in samples:
        missing = required_keys - set(s.keys())
        assert not missing, f"{s.get('id')} に必須メタデータが欠けている: {missing}"
        assert s["origin"] in ("synthetic", "real_commit")
        assert s["category"] in build_dataset.CATEGORIES
        assert s["split"] in ("tune", "eval")
        if s["category"] == "clean":
            assert s["clean_subgroup"] in ("misleading", "normal"), s["id"]
        else:
            assert s["clean_subgroup"] is None, s["id"]


def test_real_commit_samples_are_present_and_documented():
    """生成元の優先順位(依頼書どおり): リポジトリ内の実コミットを
    優先する方針が、実際に少なくとも何件か反映されていること。"""
    samples = build_dataset.build_all()
    real_commit = [s for s in samples if s["origin"] == "real_commit"]
    assert len(real_commit) >= 1
    for s in real_commit:
        assert s["generation_method"].startswith("git_mine:")


def test_split_assignment_is_deterministic():
    """同じidなら、何度生成しても同じtune/evalに振り分けられること
    (再現性)。"""
    a = build_dataset.decide_split("diff_audit_0001")
    b = build_dataset.decide_split("diff_audit_0001")
    assert a == b
    assert a in ("tune", "eval")


def test_label_crosscheck_has_no_unexpected_mismatches():
    """ラベルの検算: Parrhesia自身の検出器と意図したラベルの不一致のうち、
    『意図的な対照例』『既知のrecall限界』以外(＝本当のバグ)が
    0件であること。"""
    samples = build_dataset.build_all()
    mismatches = build_dataset.crosscheck_labels(samples)
    unexpected = [
        m for m in mismatches
        if m["classification"] not in ("known_false_positive", "known_recall_limitation")
    ]
    assert unexpected == [], f"未知のラベル不一致が見つかった: {unexpected}"


def test_build_dataset_main_writes_expected_files(tmp_path, monkeypatch):
    """main()を実際に実行し、JSONLと集計ファイルが書き出されること
    (出力ディレクトリは一時ディレクトリへ差し替えて本番のdata/を
    汚さない)。"""
    monkeypatch.setattr(build_dataset, "DATA_DIR", tmp_path)
    build_dataset.main()

    for name in ("tune.jsonl", "eval.jsonl", "label_crosscheck.json", "dataset_summary.json"):
        path = tmp_path / name
        assert path.exists(), f"{path} が生成されていない"

    eval_rows = [json.loads(line) for line in (tmp_path / "eval.jsonl").read_text(encoding="utf-8").splitlines()]
    tune_rows = [json.loads(line) for line in (tmp_path / "tune.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(eval_rows) > 0 and len(tune_rows) > 0

    crosscheck = json.loads((tmp_path / "label_crosscheck.json").read_text(encoding="utf-8"))
    assert crosscheck["unexpected_mismatches"] == []


# ------------------------------------------------------------------
# baseline.py
# ------------------------------------------------------------------

import baseline  # noqa: E402


def test_wilson_ci_known_values():
    # successes=0, total=0 -> (0.0, 0.0) の退避
    assert baseline.wilson_ci(0, 0) == (0.0, 0.0)
    # 全件成功ならCIの下限は1.0未満だが上限は1.0に近い
    low, high = baseline.wilson_ci(10, 10)
    assert 0.0 < low < 1.0
    assert high == pytest.approx(1.0, abs=1e-6)
    # 対称なケース: successes=total/2 なら点推定は0.5付近
    low, high = baseline.wilson_ci(50, 100)
    assert low < 0.5 < high


def test_compute_metrics_on_small_synthetic_results():
    """compute_metrics()自体を、手計算で検算できる小さな合成結果で
    検証する(実データのbaseline_results.jsonに依存しない単体テスト)。"""
    results = [
        {"id": "s1", "true_category": "clean", "predicted_categories": [], "origin": "synthetic", "clean_subgroup": "normal"},
        {"id": "s2", "true_category": "clean", "predicted_categories": ["deleted_test"], "origin": "real_commit", "clean_subgroup": "misleading"},
        {"id": "s3", "true_category": "deleted_test", "predicted_categories": ["deleted_test"], "origin": "synthetic", "clean_subgroup": None},
        {"id": "s4", "true_category": "deleted_test", "predicted_categories": [], "origin": "synthetic", "clean_subgroup": None},
    ]
    metrics = baseline.compute_metrics(results)

    combined = metrics["clean_false_positive_rate_combined_rate_mixture_dependent_do_not_use_as_headline"]
    assert combined["numerator"] == 1
    assert combined["denominator"] == 2
    assert combined["rate"] == pytest.approx(0.5)

    by_sub = metrics["clean_false_positive_rate_by_subgroup"]
    assert by_sub["normal"]["numerator"] == 0
    assert by_sub["normal"]["denominator"] == 1
    assert by_sub["normal"]["rate"] == pytest.approx(0.0)
    assert by_sub["misleading"]["numerator"] == 1
    assert by_sub["misleading"]["denominator"] == 1
    assert by_sub["misleading"]["rate"] == pytest.approx(1.0)

    dt = metrics["per_category"]["deleted_test"]
    assert dt["n_true"] == 2
    assert dt["n_true_positive"] == 1
    assert dt["recall"] == pytest.approx(0.5)
    # 予測されたdeleted_testは s2(誤検知)とs3(正検知)の2件 -> precision=1/2
    assert dt["precision"] == pytest.approx(0.5)


def test_baseline_run_on_real_eval_dataset_is_reproducible(tmp_path, monkeypatch):
    """build_dataset.py -> baseline.py の一連の流れを一時ディレクトリで
    実際に動かし、同じ入力から同じ指標が再現することを確認する
    (数字を手で数えない、を実機で保証する)。"""
    monkeypatch.setattr(build_dataset, "DATA_DIR", tmp_path)
    build_dataset.main()

    monkeypatch.setattr(baseline, "DATA_DIR", tmp_path)
    samples = baseline.load_eval_samples()
    results_1 = baseline.run_baseline(samples)
    results_2 = baseline.run_baseline(samples)
    assert results_1 == results_2

    metrics = baseline.compute_metrics(results_1)
    assert metrics["n_total_eval_samples"] == len(samples)
    assert metrics["clean_false_positive_rate_combined_rate_mixture_dependent_do_not_use_as_headline"]["denominator"] > 0
    assert metrics["clean_false_positive_rate_by_subgroup"]["misleading"]["denominator"] > 0
    assert metrics["clean_false_positive_rate_by_subgroup"]["normal"]["denominator"] > 0


# ------------------------------------------------------------------
# task.py (inspect_ai が無い環境では明示的にスキップ)
# ------------------------------------------------------------------

def test_task_module_import_behavior():
    """`import task` の挙動を、inspect_aiの有無どちらでも確認する。
    - 無い場合: 原因不明のまま収集全体を壊すのではなく、分かりやすい
      ImportError(「pip install inspect-ai」の案内つき)になること。
    - 有る場合: 下のテストで実際にデータが読めることまで確認する。"""
    try:
        import inspect_ai  # noqa: F401
    except ImportError:
        sys.modules.pop("task", None)
        with pytest.raises(ImportError, match="inspect-ai"):
            import task  # noqa: F401


def test_task_module_importable_when_inspect_ai_present():
    inspect_ai = pytest.importorskip("inspect_ai", reason="inspect_ai unavailable (PyPI unreachable in this sandbox)")
    import task  # noqa: F401

    samples = task._samples_from_split("eval")
    assert len(samples) > 0
    assert task._parse_category('{"category": "clean", "evidence": "x"}') == "clean"
    assert task._parse_category("not json at all") == "unparsable"
    assert task._parse_category('{"category": "not_a_real_category"}') == "unparsable"
