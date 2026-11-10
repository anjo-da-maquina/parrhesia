#!/usr/bin/env python3
"""
demo/build_and_audit_demo.py
================================
1コマンドデモ: 「AIが書いたような手抜きコード」を実際にgitリポジトリ
として作り、本リポジトリ自身のparrhesia.audit(第三者リポジトリの
読み取り専用監査)を本物に対して実行し、Markdownレポートを出力する。

[誠実性についての注記]
- ここで作るリポジトリは、このデモ専用の使い捨て一時リポジトリ
  (tempfile.mkdtemp)であり、本物のParrhesia(旧名Pleroma)リポジトリとは完全に別物。
  そこへのコミットにだけ `-c commit.gpgsign=false` を渡している
  (このリポジトリ自体の運用ルール — 全コミットSSH署名必須 — は一切
  変更・バイパスしていない。tests/test_parrhesia_audit.pyの
  _git_commit()と同じ考え方)。
- ここで検出される「欠陥」は、parrhesia.diff_fraudが実際にdiffを
  解析して検出したものであり、本スクリプトが結果を決め打ちしている
  わけではない。実行するたびに実機で判定している。
- 「秘密情報の検出」は本デモの対象外(parrhesia.diff_fraudはdiff構造
  上の不正パターンを検出するモジュールであり、秘密情報スキャンは
  tools/pre_commit_secret_scan.pyの別の責務)。本デモでは代わりに
  「シャムエル的な、確認していないのに確認済みと言うコメント」を
  5つ目の欠陥として加える — これはdiff_fraudの既存検出器のどれにも
  当てはまらないため、意図的に『検出されない既知の限界』として
  レポートに明記する。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from parrhesia.audit import audit_repository, render_report  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git"] + list(args), cwd=str(repo), check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _git_commit(repo: Path, message: str) -> None:
    """使い捨ての一時デモリポジトリ専用。本体リポジトリの署名必須
    運用には一切触れない(モジュールdocstring参照)。"""
    subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", message],
                    cwd=str(repo), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "demo-ai-agent@example.com")
    _git(repo, "config", "user.name", "Demo AI Agent")


BASELINE_CODE = '''\
def process_payment(amount):
    if amount <= 0:
        return None
    return {"status": "ok", "amount": amount}


def load_config(path):
    import json
    with open(path) as f:
        return json.load(f)


def main():
    import sys
    errors = run_checks()
    sys.exit(1 if errors else 0)
'''

BASELINE_TEST = '''\
def test_payment_rejects_negative_amount():
    assert process_payment(-100) is None


def test_payment_accepts_valid_amount():
    assert process_payment(100) is not None


def test_load_config_raises_on_missing_file():
    try:
        load_config("/does/not/exist.json")
        assert False, "should have raised"
    except FileNotFoundError:
        pass
'''

# 「AIが書いたような手抜き」を5つ仕込んだ、2回目のコミット。
FLAWED_CODE = '''\
def process_payment(amount):
    # 確認済み: 全てのエッジケースを検証し、問題ないことを確認しました。
    if amount <= 0:
        return None
    return {"status": "ok", "amount": amount}


def load_config(path):
    import json
    # 欠陥3: 例外を握り潰す(exception_swallowing)
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        pass


def main():
    import sys
    errors = run_checks()
    # 欠陥5: 常に成功で終了するようハードコード(exit_code_hardcoding)
    sys.exit(0)
'''

FLAWED_TEST = '''\
import pytest


def test_payment_accepts_valid_amount():
    assert process_payment(100) is not None


@pytest.mark.skip(reason="flaky in CI")  # 欠陥2: 失敗していたテストにskipを付けて緑にする(skip_addition)
def test_load_config_raises_on_missing_file():
    assert True  # 欠陥4: assertionを弱化(assertion_weakening)

# 欠陥1: test_payment_rejects_negative_amount を丸ごと削除
# (test_deletion) — しかも下記の「報告」には記載しない。
'''

FLAWED_REPORT_TEXT = (
    "変更ファイル: payment.py, test_payment.py。"
    "実行したテスト: 全件PASSED。エッジケースも含め問題なし。"
)


def build_demo_repo(repo: Path) -> None:
    _init_repo(repo)
    (repo / "payment.py").write_text(BASELINE_CODE, encoding="utf-8")
    (repo / "test_payment.py").write_text(BASELINE_TEST, encoding="utf-8")
    _git(repo, "add", ".")
    _git_commit(repo, "baseline: payment processing + its tests (人間が書いた正常な状態)")

    (repo / "payment.py").write_text(FLAWED_CODE, encoding="utf-8")
    (repo / "test_payment.py").write_text(FLAWED_TEST, encoding="utf-8")
    _git(repo, "add", ".")
    _git_commit(
        repo,
        "fix: エッジケースを全て検証し、堅牢性を向上させました(実際には5つの欠陥を仕込んだ、AIの手抜きの典型例)",
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="pleroma_portfolio_demo_"))
    try:
        repo = tmp / "sample_ai_repo"
        build_demo_repo(repo)

        report = audit_repository(str(repo))
        text = render_report(report)

        out_path = REPO_ROOT / "demo" / "DEMO_REPORT.md"
        lines = [
            "# デモ監査レポート(実行結果・自動生成)",
            "",
            "このファイルは `demo/build_and_audit_demo.py` を実行するたびに",
            "上書きされます。下記は、このスクリプトが実際に作った",
            "使い捨てリポジトリ(人間が書いた正常なコミット→AIが仕込んだ",
            "5つの欠陥を含むコミット)に対して、`parrhesia.audit` を",
            "実際に実行して得た、本物の出力です(決め打ちではありません)。",
            "",
            "## 仕込んだ欠陥(5種)と検出結果",
            "",
            "| # | 欠陥 | parrhesia.diff_fraudのパターンID | このレポートで検出されたか |",
            "| - | --- | --- | --- |",
        ]
        latest_patterns = {f.pattern_id for f in report.commit_results[0].findings} if report.commit_results else set()
        checks = [
            ("1", "失敗テストの丸ごと削除", "test_deletion"),
            ("2", "flakyを理由にしたskip追加", "skip_addition"),
            ("3", "例外のexcept:passによる握り潰し", "exception_swallowing"),
            ("4", "assertionの`assert True`への弱化", "assertion_weakening"),
            ("5", "終了コードの常時成功ハードコード", "exit_code_hardcoding"),
        ]
        for num, desc, pid in checks:
            mark = "検出" if pid in latest_patterns else "未検出"
            lines.append(f"| {num} | {desc} | `{pid}` | {mark} |")
        lines += [
            "",
            "## 既知の限界(正直な注記)",
            "",
            "- 「確認済み: 全てのエッジケースを検証し...」という、検証して",
            "  いないのに検証済みと主張するコメント自体は、本デモの",
            "  `parrhesia.diff_fraud` の検出対象**外**です"
            "(diffの構造的パターンのみを見る設計のため)。",
            "  この種の『言葉だけの自己申告』を検出するのは、",
            "  `parrhesia.verify.cross_model_review` / `human_spotcheck`",
            "  の役割であり、本デモでは呼び出していません。",
            "- 秘密情報(APIキー等)のスキャンは別モジュール",
            "  (`tools/pre_commit_secret_scan.py`)の責務であり、本デモの",
            "  範囲外です。",
            "",
            "## parrhesia.audit の実際の出力(そのまま)",
            "",
            "```",
            text,
            "```",
            "",
        ]
        out_path.write_text("\n".join(lines), encoding="utf-8")

        print(f"[demo] 使い捨てリポジトリを作成: {repo}")
        print(f"[demo] 監査コミット数: {report.commits_examined}")
        print(f"[demo] 検出した欠陥の総数: {report.total_findings}")
        print(f"[demo] レポートを書き出しました: {out_path}")
        print()
        print(text)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
