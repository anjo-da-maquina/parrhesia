"""
tests/test_evals_diff_audit_frozen_holdout.py
===================================================
`evals/diff_audit/build_frozen_holdout.py` と `measure_frozen_holdout.py`
の回帰テスト。

これまでこの2つのスクリプトには専用のpytestが無く、§DCの改善前後の
測定は手動実行とREADMEへの転記だけで行われていた。本ファイルは、
(1) `build_frozen_holdout.py`自体が壊れていないこと(過去に発見した
「要素内に改行文字を埋め込むと一部の行が無視される」不具合の再発防止
ガードが効くこと)、(2) 既にコミットされている凍結ファイル
(`data/frozen_rename_skipmove_holdout.jsonl`、書き換え禁止)に対する
現在の検出器の実測値を、pytestとして固定する。
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "evals" / "diff_audit"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EVALS_DIR))

import build_frozen_holdout  # noqa: E402
import measure_frozen_holdout  # noqa: E402


def test_build_all_produces_24_samples_split_evenly():
    """現在のSKIP_MOVE_CASES/RENAME_CASESから、例外無く24件(12+12)が
    生成できること(過去にtest_h.pyで発見した、改行文字埋め込みによる
    不具合の再発防止ガードが効くことも、ここで暗黙に確認している)。"""
    samples = build_frozen_holdout.build_all()
    assert len(samples) == 24
    rename = [s for s in samples if s["generation_method"].startswith("frozen_holdout:rename:")]
    skip_move = [s for s in samples if s["generation_method"].startswith("frozen_holdout:skip_move:")]
    assert len(rename) == 12
    assert len(skip_move) == 12


def test_skip_move_sample_rejects_embedded_newline_in_a_single_line_element():
    """[2026-11、実際に発見した不具合の回帰防止] removed/addedの要素に
    改行文字`\\n`を直接埋め込むと、`f"+{ln}\\n"`では先頭の物理行にしか
    `+`接頭辞が付かず、diffとして正しく認識されない行が発生する
    (過去にtest_h.py/skipif_reformatで実際に起きた)。これを未然に防ぐ
    ガードが、実際に例外を出すことを確認する。"""
    with pytest.raises(ValueError, match="改行文字"):
        build_frozen_holdout._skip_move_sample(
            path="tests/test_dummy.py",
            removed_lines=["@pytest.mark.skip(reason='x')"],
            added_lines=["@pytest.mark.skip(\n    reason='x'\n)"],
            note="dummy",
            tag="dummy",
        )


def test_measure_against_committed_frozen_holdout_matches_known_numbers():
    """既にコミットされている凍結ファイル(書き換え禁止)に対し、現在の
    検出器で実際に再測定し、§DCのREADME/DEFECTS.mdに記載した実測値
    (全体2/24、rename 0/12、skip_move 2/12)と一致することを固定する。
    この数字が変わった場合、検出器に意図しない変更が入ったか、
    README/DEFECTS.mdの記載自体が古くなっている可能性があるので、
    どちらかを直すまでこのテストは失敗し続ける(=数字の食い違いを
    無言で許さない)。"""
    samples = measure_frozen_holdout.load_frozen_samples()
    assert len(samples) == 24
    results = measure_frozen_holdout.run(samples)
    summary = measure_frozen_holdout.summarize(results)

    assert summary["n_flagged"] == 2
    assert summary["n_total"] == 24
    assert summary["by_group"]["rename"]["numerator"] == 0
    assert summary["by_group"]["rename"]["denominator"] == 12
    assert summary["by_group"]["skip_move"]["numerator"] == 2
    assert summary["by_group"]["skip_move"]["denominator"] == 12
