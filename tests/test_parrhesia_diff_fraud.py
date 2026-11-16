"""
tests/test_parrhesia_diff_fraud.py
======================================
[新設 2026-11] parrhesia/diff_fraud.py (B章「主張の検証と突きつけ」の
うち、差分による不正検出・報告との突き合わせ・参照の実在確認)の単体
テスト。

[レッドチーム/ブルーチームの適用 — ユーザー指示 2026-11-03 継続]
各検出器について、「正当な変更(リネーム・等価な置き換え・移動)を
誤って不正として検知してしまわないか」を赤チーム観点として確認する。
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parrhesia.diff_fraud import (
    analyze_diff,
    check_references_exist,
    detect_assertion_weakening,
    detect_exception_swallowing,
    detect_exit_code_hardcoding,
    detect_skip_addition,
    detect_test_deletion,
    diff_changed_files,
    find_undisclosed_changes,
    parse_unified_diff,
)


# ------------------------------------------------------------------
# test_deletion
# ------------------------------------------------------------------

def test_detect_test_deletion_flags_removed_test_with_no_replacement():
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,4 +1,1 @@\n"
        "-def test_important_check():\n"
        "-    assert 1 == 1\n"
        "-\n"
        " def test_other():\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_test_deletion(per_file)
    assert any(f.evidence == "test_important_check" for f in findings)


def test_detect_test_deletion_does_not_flag_rewritten_test_with_same_name():
    """[赤チーム] 同名のテスト関数が削除され、同じ名前で(内容を変えて)
    再度追加されている場合(=書き換え)は、削除とは別の問題であり、
    test_deletionとしては誤って検知しないこと。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def test_example():\n"
        "-    assert 1 == 1\n"
        "+def test_example():\n"
        "+    assert 1 == 2\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_test_deletion(per_file)
    assert findings == []


# ------------------------------------------------------------------
# skip_addition
# ------------------------------------------------------------------

def test_detect_skip_addition_flags_new_skip_marker():
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,3 @@\n"
        " def test_example():\n"
        "+    pytest.skip(\"flaky\")\n"
        "     assert 1 == 1\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_skip_addition(per_file)
    assert len(findings) == 1


def test_detect_skip_addition_does_not_flag_a_moved_marker():
    """[赤チーム] 既存のスキップ指定が、全く同じ文言のまま別の行に移動
    しただけの場合は、新規追加として誤って検知しないこと。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-    pytest.skip(\"flaky\")\n"
        " def test_example():\n"
        "+    pytest.skip(\"flaky\")\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_skip_addition(per_file)
    assert findings == []


# ------------------------------------------------------------------
# assertion_weakening
# ------------------------------------------------------------------

def test_detect_assertion_weakening_flags_net_decrease():
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,3 +1,1 @@\n"
        "-    assert a == 1\n"
        "-    assert b == 2\n"
        "+    assert a == 1\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_assertion_weakening(per_file)
    assert any(f.detail.startswith("assert文が") for f in findings)


def test_detect_assertion_weakening_does_not_flag_one_to_one_replacement():
    """[赤チーム] assert文が1件削除され、別のassert文が1件追加された
    (件数は変わらない)だけの、正当な書き換えを誤って検知しないこと。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-    assert a == 1\n"
        "+    assert a == 2\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_assertion_weakening(per_file)
    assert findings == []


def test_detect_assertion_weakening_flags_assert_true_literal():
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-    assert compute(x) == expected\n"
        "+    assert True\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_assertion_weakening(per_file)
    assert any("assert True" in f.detail for f in findings)


# ------------------------------------------------------------------
# exception_swallowing
# ------------------------------------------------------------------

def test_detect_exception_swallowing_flags_new_bare_except_pass():
    diff_text = (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,1 +1,3 @@\n"
        "-    do_work()\n"
        "+    try:\n"
        "+        do_work()\n"
        "+    except Exception:\n"
        "+        pass\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exception_swallowing(per_file)
    assert len(findings) == 1


def test_detect_exception_swallowing_flags_specific_exception_types():
    """[2026-11、evals/diff_audit/の開発中に発見した欠陥の修正、§DB]
    修正前は`except Exception:`/裸の`except:`しか認識できず、
    `except ValueError:`等の個別の例外型による握り潰しを一律で見逃して
    いた。個別の例外型でも検知できることを固定する。"""
    diff_text = (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,1 +1,3 @@\n"
        "-    do_work()\n"
        "+    try:\n"
        "+        do_work()\n"
        "+    except ValueError:\n"
        "+        pass\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exception_swallowing(per_file)
    assert len(findings) == 1


def test_detect_exception_swallowing_still_ignores_proper_handling_with_as_clause():
    """[赤チーム] `except ValueError as exc:`の直後が`pass`ではなく
    再送出・ログ記録である場合は、個別の例外型を広く認識するように
    なった後も、引き続き誤検知しないこと。"""
    diff_text = (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,1 +1,4 @@\n"
        "-    return do_work()\n"
        "+    try:\n"
        "+        return do_work()\n"
        "+    except ValueError as exc:\n"
        "+        logger.exception('failed: %s', exc)\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exception_swallowing(per_file)
    assert findings == []


def test_detect_exception_swallowing_does_not_flag_moved_pair():
    """[赤チーム] 既存の`except: pass`のペアが、全く同じ文言のまま
    別の場所へ移動しただけの場合は、新規追加として誤って検知しない
    こと。"""
    diff_text = (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-    except Exception:\n"
        "-        pass\n"
        "+    except Exception:\n"
        "+        pass\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exception_swallowing(per_file)
    assert findings == []


# ------------------------------------------------------------------
# exit_code_hardcoding
# ------------------------------------------------------------------

def test_detect_exit_code_hardcoding_flags_downgrade_from_dynamic():
    diff_text = (
        "diff --git a/src/runner.py b/src/runner.py\n"
        "--- a/src/runner.py\n"
        "+++ b/src/runner.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-    sys.exit(result_code)\n"
        "+    sys.exit(0)\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exit_code_hardcoding(per_file)
    assert len(findings) == 1


def test_detect_exit_code_hardcoding_does_not_flag_brand_new_exit_zero():
    """[赤チーム] 以前その場所に非ゼロ・動的な終了コードが一切無かった
    (=新規に追加されたコード)場合、新たに`sys.exit(0)`が出てきても、
    『ダウングレード』ではないため誤って検知しないこと。"""
    diff_text = (
        "diff --git a/src/runner.py b/src/runner.py\n"
        "--- a/src/runner.py\n"
        "+++ b/src/runner.py\n"
        "@@ -1,0 +1,1 @@\n"
        "+    sys.exit(0)\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exit_code_hardcoding(per_file)
    assert findings == []


def test_detect_exit_code_hardcoding_known_limitation_nested_call_arg():
    """[既知のrecall限界、2026-11、evals/diff_audit/の開発中に発見、
    §DB参照] `sys.exit(len(violations))`のようにネストした関数呼び出し
    を引数に取る行は、`_EXIT_NONZERO_OR_DYNAMIC_RE`の対象外であり、
    それが`sys.exit(0)`へ書き換えられても検知できない。これは未修正の
    既知の限界であり、『見逃してよい』という意味ではなく『現状は見逃す』
    という事実を、将来knowingly再発見することがないよう固定する回帰
    テストである。この限界が修正された場合は、本テストをxfailではなく
    検知成功を期待するテストへ書き換えること。"""
    diff_text = (
        "diff --git a/tools/lint_check.py b/tools/lint_check.py\n"
        "--- a/tools/lint_check.py\n"
        "+++ b/tools/lint_check.py\n"
        "@@ -1,2 +1,2 @@\n"
        " violations = lint(files)\n"
        "-    sys.exit(len(violations))\n"
        "+    sys.exit(0)\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exit_code_hardcoding(per_file)
    assert findings == [], (
        "この限界が修正されたなら、本テストをfindingsありを期待する形へ"
        "書き換え、DEFECTS.md §DBの記述も更新すること"
    )


# ------------------------------------------------------------------
# analyze_diff(統合)
# ------------------------------------------------------------------

def test_analyze_diff_aggregates_all_detectors():
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,0 @@\n"
        "-def test_important_check():\n"
        "-    assert 1 == 1\n"
    )
    findings = analyze_diff(diff_text)
    assert any(f.pattern_id == "test_deletion" for f in findings)


# ------------------------------------------------------------------
# diff_changed_files / find_undisclosed_changes
# ------------------------------------------------------------------

def test_find_undisclosed_changes_flags_file_not_mentioned_in_report():
    diff_text = (
        "diff --git a/src/a.py b/src/a.py\n"
        "--- a/src/a.py\n"
        "+++ b/src/a.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-x = 1\n"
        "+x = 2\n"
        "diff --git a/src/b.py b/src/b.py\n"
        "--- a/src/b.py\n"
        "+++ b/src/b.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-y = 1\n"
        "+y = 2\n"
    )
    report_text = "src/a.py を修正しました。"
    undisclosed = find_undisclosed_changes(diff_text, report_text)
    assert undisclosed == ["src/b.py"]


def test_diff_changed_files_extracts_both_files():
    diff_text = (
        "diff --git a/src/a.py b/src/a.py\n"
        "--- a/src/a.py\n"
        "+++ b/src/a.py\n"
        "diff --git a/src/b.py b/src/b.py\n"
        "--- a/src/b.py\n"
        "+++ b/src/b.py\n"
    )
    assert diff_changed_files(diff_text) == {"src/a.py", "src/b.py"}


# ------------------------------------------------------------------
# check_references_exist
# ------------------------------------------------------------------

def test_check_references_exist_flags_nonexistent_path():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "real_file.py").write_text("x = 1\n")
        report = "`real_file.py` と `fictional_file.py` を確認した。"
        missing = check_references_exist(report, d)
        assert "fictional_file.py" in missing
        assert "real_file.py" not in missing
