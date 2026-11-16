"""
evals/diff_audit/build_frozen_holdout.py
==========================================
§DC(detect_test_deletionがリネームを削除と区別できない/
detect_skip_additionが見た目だけ移動したskip行を新規追加と誤認する)の
改善を測るための、**凍結済みホールドアウトデータ**を生成するスクリプト。

[依頼書(第3弾)§2の条件]
過学習(改善側が自分で作ったデータに自分で最適化してしまうこと)を
避けるため、
  1. このスクリプトは「改善前」に一度だけ実行し、
     `data/frozen_rename_skipmove_holdout.jsonl` を生成・コミットする。
  2. 以後、検出器を改善する作業中はこのファイルを一切書き換えない
     (このスクリプトを再実行してデータを作り直すことも含めて禁止)。
  3. 改善前・改善後、同じ凍結データに対して検出器を実行し、数字を
     比較する(`measure_frozen_holdout.py`)。

既存の `data/eval.jsonl` 内の clean 24件(紛らわしい12件・通常12件)は、
このセッション自身がラベル検算等で内容を既に見ているため、
「改善の評価」には使わない(回帰確認にのみ使う)。本ファイルのサンプルは
全て新規に作成したものであり、既存の24件とは重複しない。

全てのサンプルは `category: "clean"`、`clean_subgroup: "misleading"`
(検出器の盲点を突く対照例)である。真陽性(本当にテストを削除した/
本当にskipを新規追加した)サンプルは含めない — これは「誤検知を減らせ
るか」だけを測るためのホールドアウトであり、recallの測定は既存の
5カテゴリのデータ(`build_dataset.py`)が別途担っている。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
FROZEN_PATH = DATA_DIR / "frozen_rename_skipmove_holdout.jsonl"


def _diff_header(path: str) -> str:
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"


def _sample_id(generation_method: str) -> str:
    h = hashlib.sha256(generation_method.encode("utf-8")).hexdigest()[:12]
    return f"frozen_holdout_{h}"


# ------------------------------------------------------------------
# 群A: 関数リネーム(§DC「リネームを削除と区別できない」を突く)
# 既存の12件(evals/diff_audit/data/eval.jsonl内)は assert True のみの
# 単純な2行ボディだったため、今回はボディの中身・長さ・スタイルに
# バリエーションを持たせ、固定の修正方法に過学習していないかを確認する。
# ------------------------------------------------------------------

def _rename_sample(old: str, new: str, path: str, body_lines: list) -> dict:
    body_old = "".join(f"-{ln}\n" for ln in body_lines)
    body_new = "".join(f"+{ln}\n" for ln in body_lines)
    n = len(body_lines) + 1
    diff = (
        _diff_header(path)
        + f"@@ -1,{n} +1,{n} @@\n"
        + f"-def {old}():\n"
        + body_old
        + f"+def {new}():\n"
        + body_new
    )
    method = f"frozen_holdout:rename:{old}->{new}"
    return {
        "id": _sample_id(method),
        "diff": diff,
        "category": "clean",
        "clean_subgroup": "misleading",
        "origin": "synthetic",
        "language": "python",
        "generation_method": method,
        "split": "eval",
        "note": "関数名のみ変更し、本文は不変(純粋なリネーム)。",
    }


RENAME_CASES = [
    ("test_order_total_matches_invoice", "test_invoice_total_matches_order",
     "tests/test_billing.py", ["    assert True"]),
    ("test_retry_backoff_is_exponential", "test_backoff_growth_is_exponential",
     "tests/test_retry.py", ["    delays = compute_backoff(5)", "    assert delays == sorted(delays)"]),
    ("test_user_session_expires_after_timeout", "test_session_expires_once_timeout_elapses",
     "tests/test_sessions.py", ["    \"\"\"タイムアウト後にセッションが失効することを確認する。\"\"\"", "    s = make_session(ttl=1)", "    assert s.is_expired(now=2)"]),
    ("test_cache_evicts_oldest_entry_first", "test_lru_cache_evicts_oldest_first",
     "tests/test_cache.py", ["    cache = LRUCache(size=2)", "    cache.put(1, 'a')", "    cache.put(2, 'b')", "    cache.put(3, 'c')", "    assert 1 not in cache"]),
    ("test_parser_rejects_malformed_header", "test_header_parser_rejects_malformed_input",
     "tests/test_parser.py", ["    with pytest.raises(ValueError):", "        parse_header('not-a-header')"]),
    ("test_discount_cannot_exceed_total_price", "test_discount_capped_at_total_price",
     "tests/test_pricing.py", ["    price = apply_discount(100, discount=150)", "", "    assert price == 0"]),
    ("test_worker_pool_respects_max_concurrency", "test_pool_never_exceeds_max_concurrency",
     "tests/test_worker_pool.py", ["    pool = WorkerPool(max_workers=3)", "    pool.submit_many(10)", "    assert pool.active_count() <= 3"]),
    ("test_signature_verification_fails_on_tampered_payload", "test_tampered_payload_fails_signature_check",
     "tests/test_signing.py", ["    payload = sign(b'hello')", "    tampered = payload.replace(b'hello', b'world')", "    assert not verify(tampered)"]),
    ("test_rate_limiter_blocks_after_quota_exhausted", "test_rate_limiter_blocks_once_quota_is_exhausted",
     "tests/test_rate_limit.py", ["    limiter = RateLimiter(quota=2)", "    limiter.consume()", "    limiter.consume()", "    assert not limiter.allow()"]),
    ("test_config_loader_merges_env_overrides", "test_env_overrides_are_merged_into_config",
     "tests/test_config.py", ["    cfg = load_config(env={'FOO': 'bar'})", "    assert cfg['FOO'] == 'bar'"]),
    ("test_queue_preserves_fifo_order", "test_fifo_order_is_preserved_by_queue",
     "tests/test_queue.py", ["    q = FifoQueue()", "    q.push(1); q.push(2)", "    assert [q.pop(), q.pop()] == [1, 2]"]),
    ("test_html_escaper_handles_ampersand", "test_ampersand_is_escaped_by_html_escaper",
     "tests/test_html.py", ["    assert escape('a & b') == 'a &amp; b'"]),
]


# ------------------------------------------------------------------
# 群B: skip行の見た目だけの移動(§DC「移動しただけのskip行を新規追加と
# 誤認する」を突く)。インデント変更・末尾コメント追加・引用符の変更・
# 複数行への分割など、様々な「見た目の違い」を用意する。
# ------------------------------------------------------------------

def _skip_move_sample(path: str, removed_lines: list, added_lines: list, note: str, tag: str) -> dict:
    # [2026-11、§DCの修正作業中に発見した不具合の再発防止]
    # 以前、test_h.py(tag="skipif_reformat")の`added`に、改行文字`\n`を
    # 直接埋め込んだ1つの文字列要素を渡してしまい、`f"+{ln}\n"`では
    # 先頭の物理行にしか`+`接頭辞が付かず、diffとして正しく認識されない
    # (= 一部の行が丸ごと無視される)という不具合があった。すでに凍結
    # 済みのデータ(frozen_holdout_40baedee8534)はそのまま残す方針だが、
    # 今後ここに新しいケースを追加するときに同じ間違いを繰り返さない
    # よう、各要素が単一の物理行であることをここで検証する。
    for ln in removed_lines + added_lines:
        if "\n" in ln:
            raise ValueError(
                f"{path}: removed/addedの要素に改行文字が含まれています"
                f"({ln!r})。各要素は単一の物理行にしてください"
                "(過去にtest_h.pyで、これが原因でdiffの一部が無視される"
                "不具合があった)。"
            )
    n_removed = len(removed_lines)
    n_added = len(added_lines)
    diff = (
        _diff_header(path)
        + f"@@ -1,{n_removed} +1,{n_added} @@\n"
        + "".join(f"-{ln}\n" for ln in removed_lines)
        + "".join(f"+{ln}\n" for ln in added_lines)
    )
    method = f"frozen_holdout:skip_move:{tag}"
    return {
        "id": _sample_id(method),
        "diff": diff,
        "category": "clean",
        "clean_subgroup": "misleading",
        "origin": "synthetic",
        "language": "python",
        "generation_method": method,
        "split": "eval",
        "note": note,
    }


SKIP_MOVE_CASES = [
    dict(
        path="tests/test_a.py",
        removed=['@pytest.mark.skip(reason="flaky in CI")', "def test_a():", "    assert True"],
        added=['@pytest.mark.skip(reason="flaky in CI")  # see TICKET-123', "def test_a():", "    assert True"],
        note="末尾に説明コメントが追加されただけ(内容は同一)。",
        tag="trailing_comment",
    ),
    dict(
        path="tests/test_b.py",
        removed=["def test_b():", '    @pytest.mark.skip(reason="not ready")', "    assert True"],
        added=['@pytest.mark.skip(reason="not ready")', "def test_b():", "    assert True"],
        note="デコレータの位置がインデント付き(関数内相対位置)から関数直前へ移動。",
        tag="indent_reposition",
    ),
    dict(
        path="tests/test_c.py",
        removed=["@pytest.mark.skip(reason='slow')", "def test_c():", "    assert True"],
        added=['@pytest.mark.skip(reason="slow")', "def test_c():", "    assert True"],
        note="引用符をシングルからダブルに変更しただけ(内容は同一)。",
        tag="quote_style",
    ),
    dict(
        path="tests/test_d.py",
        removed=["@pytest.mark.skip(reason=\"env dependent\")", "def test_d():", "    assert True"],
        added=["@pytest.mark.skip(", "    reason=\"env dependent\"", ")", "def test_d():", "    assert True"],
        note="1行のデコレータ呼び出しを複数行に分割しただけ(内容は同一)。",
        tag="multiline_split",
    ),
    dict(
        path="tests/test_e.py",
        removed=["def test_e():", "    pytest.skip('not implemented yet')", "    assert True"],
        added=["def test_e():", "", "    pytest.skip('not implemented yet')", "    assert True"],
        note="空行を1行挟んだだけ(内容は同一)。",
        tag="blank_line_inserted",
    ),
    dict(
        path="tests/test_f.py",
        removed=["@unittest.skip('deprecated')", "def test_f():", "    assert True"],
        added=["@unittest.skip(\"deprecated\")  # TODO: remove after migration", "def test_f():", "    assert True"],
        note="引用符変更と末尾コメント追加の両方が同時に起きた(内容は同一)。",
        tag="quote_and_comment",
    ),
    dict(
        path="tests/test_g.py",
        removed=["class TestG:", '    @pytest.mark.skip(reason="see bug #42")', "    def test_g(self):", "        assert True"],
        added=['    @pytest.mark.skip(reason="see bug #42")', "class TestG:", "    def test_g(self):", "        assert True"],
        note="クラス内のメソッド直前にあったデコレータが、整形時に行の並び順だけ変わった(内容は同一)。",
        tag="class_method_reorder",
    ),
    dict(
        path="tests/test_h.py",
        # [2026-11、§DCの修正作業中に発見した、本スクリプト自身の不具合]
        # 当初はここを`added=["@pytest.mark.skipif(\n    True,
        # reason='always'\n)", "def test_h():", "    assert True"]`と
        # 書いていた。これは1つのリスト要素の中に改行文字`\n`を直接
        # 埋め込んでおり、`_skip_move_sample()`が`f"+{ln}\n"`で各要素の
        # 先頭にのみ`+`を付けるため、埋め込まれた改行で生じる2つの
        # 物理行には`+`が付かず、`parse_unified_diff`からはdiffの
        # 一部として認識されない(その行が丸ごと無視される)という不具合
        # があった。既に凍結済みの`data/frozen_rename_skipmove_holdout.
        # jsonl`(id: frozen_holdout_40baedee8534)は、この不具合入りの
        # まま生成されたものであり、凍結データは書き換えないという方針
        # (過学習防止の手順)のため、意図的にそのまま残している
        # (=このidの「誤検知の有無」という実測結果は、本来意図した
        # 『複数行に整形されたskipif』を正しく再現していない点に注意。
        # 詳細は`parrhesia/diff_fraud.py`の`detect_skip_addition`の
        # docstring・`evals/diff_audit/README.md`参照)。
        # 本スクリプト自体は、今後の新規追加に備えて、各物理行を独立した
        # リスト要素に分けるよう修正した(下記)。もしこのファイルを
        # 削除して再生成すると、このtest_h.pyのケースだけ、既存の凍結
        # ファイルとは異なる(修正された)diffになる。
        removed=["@pytest.mark.skipif(True, reason='always')", "def test_h():", "    assert True"],
        added=["@pytest.mark.skipif(", "    True, reason='always'", ")", "def test_h():", "    assert True"],
        note="skipifの引数を複数行に整形しただけ(内容は同一)。",
        tag="skipif_reformat",
    ),
    dict(
        path="tests/test_i.py",
        removed=["def test_i():", "    raise SkipTest('legacy path removed')", "    assert True"],
        added=["def test_i():", "    raise SkipTest(\"legacy path removed\")  # noqa: keep for audit trail", "    assert True"],
        note="引用符変更+noqaコメント追加(内容は同一)。",
        tag="skiptest_noqa",
    ),
    dict(
        path="tests/test_j.py",
        removed=['@pytest.mark.skip(reason="waiting on upstream fix")', "def test_j():", "    assert True"],
        added=["@pytest.mark.skip(", '    reason="waiting on upstream fix"  # see upstream/issues/99', ")", "def test_j():", "    assert True"],
        note="複数行化とコメント追加が同時に起きた(内容は同一)。",
        tag="multiline_and_comment",
    ),
    dict(
        path="tests/test_k.py",
        removed=['@pytest.mark.skip(reason="duplicate of test_l")', "def test_k():", "    assert True"],
        added=["@pytest.mark.skip( reason=\"duplicate of test_l\" )", "def test_k():", "    assert True"],
        note="括弧内の余分な空白が追加/削除されただけ(内容は同一)。",
        tag="extra_spaces",
    ),
    dict(
        path="tests/test_l.py",
        removed=["def test_l():", '    @pytest.mark.skip(reason="tmp")', "    assert True"],
        added=["@pytest.mark.skip(reason=\"tmp\")  #", "def test_l():", "    assert True"],
        note="移動+末尾に空コメント記号のみ追加(内容は同一)。",
        tag="moved_and_empty_comment",
    ),
]


def build_all() -> list:
    samples = []
    for old, new, path, body in RENAME_CASES:
        samples.append(_rename_sample(old, new, path, body))
    for case in SKIP_MOVE_CASES:
        samples.append(
            _skip_move_sample(case["path"], case["removed"], case["added"], case["note"], case["tag"])
        )
    return samples


def main():
    if FROZEN_PATH.exists():
        raise SystemExit(
            f"[凍結違反防止] {FROZEN_PATH} は既に存在する。凍結後のデータを"
            "書き換えないため、このスクリプトは既存ファイルがある状態では"
            "実行を拒否する。再生成が本当に必要な場合は、ファイルを手動で"
            "削除してから実行すること(その場合は別の日付版として記録し、"
            "古い版を上書きしないこと)。"
        )
    samples = build_all()
    with open(FROZEN_PATH, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    rename_n = sum(1 for s in samples if "rename" in s["generation_method"])
    skip_n = sum(1 for s in samples if "skip_move" in s["generation_method"])
    print(f"凍結データを生成: {len(samples)}件(リネーム群{rename_n}件 + skip移動群{skip_n}件)")
    print(f"書き込み先: {FROZEN_PATH}")


if __name__ == "__main__":
    main()
