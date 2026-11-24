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
    _join_continued_statements,
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


def test_detect_test_deletion_does_not_flag_rename_with_identical_multiline_body():
    """[2026-11、§DCの改善] 関数名だけが変わり、複数行の本文は完全一致
    している(=純粋なリネーム)場合、test_deletionとして誤って検知
    しないこと。evals/diff_audit/data/frozen_rename_skipmove_holdout.
    jsonlで実測した「リネーム群12/12 -> 0/12」の改善を、ユニットテスト
    として固定する。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,3 +1,3 @@\n"
        "-def test_old_name():\n"
        "-    value = compute()\n"
        "-    assert value == 1\n"
        "+def test_new_name():\n"
        "+    value = compute()\n"
        "+    assert value == 1\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_test_deletion(per_file)
    assert findings == []


def test_detect_test_deletion_still_flags_rename_with_changed_body():
    """[赤チーム] 名前が変わり、かつ本文も変わっている(=単純なリネーム
    ではなく、実質的な書き換え・弱体化の可能性がある)場合は、本文完全
    一致という保守的な条件を満たさないため、引き続き削除として検知
    すること(renameの誤検知抑制が、偽陰性側に振れていないことの確認)。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def test_old_name():\n"
        "-    assert value == 1\n"
        "+def test_new_name():\n"
        "+    pass\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_test_deletion(per_file)
    assert any(f.evidence == "test_old_name" for f in findings)


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


def test_detect_skip_addition_does_not_flag_trailing_comment_addition():
    """[2026-11、§DCの改善] 既存のskip指定の末尾に説明コメントが
    追加されただけ(内容自体は同一)の場合、新規追加として誤って検知
    しないこと。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,1 +1,1 @@\n"
        '-@pytest.mark.skip(reason="flaky in CI")\n'
        '+@pytest.mark.skip(reason="flaky in CI")  # see TICKET-123\n'
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_skip_addition(per_file)
    assert findings == []


def test_detect_skip_addition_does_not_flag_quote_style_change():
    """[2026-11、§DCの改善] シングルクォートからダブルクォートへの変更
    だけ(内容自体は同一)の場合、新規追加として誤って検知しないこと。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-@pytest.mark.skip(reason='slow')\n"
        '+@pytest.mark.skip(reason="slow")\n'
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_skip_addition(per_file)
    assert findings == []


def test_detect_skip_addition_still_flags_genuinely_new_marker_despite_normalization():
    """[赤チーム] 正規化(コメント除去・引用符統一・空白畳み込み)を行って
    も、削除側に対応するskip指定が全く存在しない場合は、引き続き新規
    追加として検知すること(正規化が、偽陰性側に振れていないことの確認)。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,3 @@\n"
        " def test_example():\n"
        '+    @pytest.mark.skip(reason="newly flaky")\n'
        "     assert True\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_skip_addition(per_file)
    assert len(findings) == 1


def test_join_continued_statements_merges_balanced_parens_across_lines():
    lines = [
        "@pytest.mark.skip(",
        '    reason="x"',
        ")",
        "def test_example():",
    ]
    joined = _join_continued_statements(lines)
    assert joined == ['@pytest.mark.skip(     reason="x" )', "def test_example():"]


def test_join_continued_statements_leaves_already_balanced_lines_untouched():
    lines = ['@pytest.mark.skip(reason="x")', "def test_example():"]
    assert _join_continued_statements(lines) == lines


def test_join_continued_statements_conservatively_handles_never_closed_parens():
    """構文的に異常(丸括弧が最後まで閉じない)な入力でも、例外を出さず、
    結合を諦めてそのまま返す(保守的=見逃す側に倒す)こと。"""
    lines = ["foo(", "bar"]
    result = _join_continued_statements(lines)
    assert result == ["foo( bar"]


def test_detect_skip_addition_does_not_flag_multiline_decorator_split_now_fixed():
    """[2026-11、§DCの残存限界を修正] 1行のデコレータ呼び出しが、内容は
    同一のまま複数行に分割された場合、以前は行単位の正規化だけでは
    『移動』と認識できず新規追加として誤検知していたが、
    `_join_continued_statements()`による複数行の結合で修正した
    (evals/diff_audit/data/frozen_rename_skipmove_holdout.jsonlの
    `multiline_split`タグで実測、改善後は誤検知されない)。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,4 @@\n"
        '-@pytest.mark.skip(reason="env dependent")\n'
        " def test_example():\n"
        "+@pytest.mark.skip(\n"
        '+    reason="env dependent"\n'
        "+)\n"
        " def test_example():\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_skip_addition(per_file)
    assert findings == []


def test_detect_skip_addition_still_flags_genuinely_new_multiline_marker():
    """複数行への分割だけでなく、本当に新規追加された複数行のskip指定
    (削除側に対応する指定が無い)は、結合後も引き続き検出されること。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,1 +1,4 @@\n"
        "+@pytest.mark.skip(\n"
        '+    reason="newly added, not a move"\n'
        "+)\n"
        " def test_example():\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_skip_addition(per_file)
    assert len(findings) == 1
    assert findings[0].pattern_id == "skip_addition"


def test_detect_skip_addition_known_limitation_comment_on_continuation_line():
    """[既知の未修正の限界、§DC] 複数行に分割されたデコレータの、継続行
    (閉じ括弧より前の行)に末尾コメントが付いている場合、結合後の文字列
    に対して`#.*$`でコメントを除去すると、コメントより後ろにある本来は
    構文上必要な閉じ括弧まで一緒に消えてしまい、比較対象の文字列が
    (除去されなかった側と比べて)閉じ括弧の有無で不一致になり、依然として
    新規追加として誤検知される
    (evals/diff_audit/data/frozen_rename_skipmove_holdout.jsonlの
    `multiline_and_comment`タグで実測、改善後も残存)。本テストは、この
    限界が意図せず『いつの間にか直っていた/いつの間にか悪化していた』
    ことに気づくための回帰テストであり、直った場合はこのassertを
    反転させること。"""
    diff_text = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,4 @@\n"
        '-@pytest.mark.skip(reason="waiting on upstream fix")\n'
        " def test_example():\n"
        "+@pytest.mark.skip(\n"
        '+    reason="waiting on upstream fix"  # see upstream/issues/99\n'
        "+)\n"
        " def test_example():\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_skip_addition(per_file)
    assert len(findings) == 1  # 既知の未修正の限界(直ったらこのテストを更新する)


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


def test_detect_exit_code_hardcoding_detects_nested_call_arg_now_fixed():
    """[§DBの既知のrecall限界、2026-11、evals/diff_audit/の開発中に発見、
    同月中に修正] 以前は`sys.exit(len(violations))`のようにネストした
    関数呼び出しを引数に取る行を「動的な終了コードだった」と認識できず、
    `sys.exit(0)`へ書き換えられても見逃していた(旧テスト名:
    `test_detect_exit_code_hardcoding_known_limitation_nested_call_arg`。
    当時はfindings == []を期待していた)。`_sys_exit_call_arg()`による
    引数抽出への修正後は、正しく検知できることを確認する回帰テスト。"""
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
    assert len(findings) == 1


def test_detect_exit_code_hardcoding_does_not_flag_removed_literal_zero():
    """[赤チーム、修正の副次効果] 旧`_EXIT_NONZERO_OR_DYNAMIC_RE`は
    `\\w+`が数字にもマッチするため、削除側の`sys.exit(0)`自体を誤って
    「非ゼロ・動的だった」と判定しうる潜在的な欠陥を持っていた
    (`\\w+`は文字列`"0"`にもマッチするため)。修正後は、削除側が
    文字列として厳密に`sys.exit(0)`である場合、それ自体を非ゼロ・
    動的とは判定しないことを確認する。"""
    diff_text = (
        "diff --git a/src/runner.py b/src/runner.py\n"
        "--- a/src/runner.py\n"
        "+++ b/src/runner.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-    sys.exit(0)\n"
        "+    sys.exit(0)\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exit_code_hardcoding(per_file)
    assert findings == []


def test_detect_exit_code_hardcoding_detects_negative_literal():
    """[修正の副次効果] 旧実装は`sys.exit(-1)`のような負数リテラルも
    (`[1-9]`は先頭が数字であることを要求し、`\\w+`は`-`を含まないため)
    認識できなかった。新しい引数抽出方式では、文字列として`"0"`と
    一致しない限り非ゼロ・動的と判定するため、負数も正しく拾える。"""
    diff_text = (
        "diff --git a/src/runner.py b/src/runner.py\n"
        "--- a/src/runner.py\n"
        "+++ b/src/runner.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-    sys.exit(-1)\n"
        "+    sys.exit(0)\n"
    )
    per_file = parse_unified_diff(diff_text)
    findings = detect_exit_code_hardcoding(per_file)
    assert len(findings) == 1


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
