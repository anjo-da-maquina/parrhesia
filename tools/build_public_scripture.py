"""
tools/build_public_scripture.py
==================================
[新設 2026-10] 「ライセンス証明書機構(maquina_gatekeeper)の公開配布からの分離」

これまで `pyproject.toml` の `packages = ["sefer"]` により、`sefer` パッケージ
単体を配布物として切り出すこと自体は既に可能な構成になっていた
(実機検証済み: setuptools の build_py.find_all_modules() は
`sefer/__init__.py` と `sefer/audit_chain.py` の2ファイルしか返さない)。

しかし、これが「本当にそうなっているか」を毎回信用だけに頼るのは、
本プロジェクトが掲げる「ゼロトラスト」の精神に反する。本モジュールは
実際にsdist(ソース配布物)をビルドし、その内容そのものを検査して、
ライセンス証明書機構(maquina_gatekeeper.py / ataraxia_certificate.json /
adapters/provisioning_agent.py)やadversarial_training(旧名Tartarus、闘技場・creator's air)が
一切含まれていないことを機械的に確認してから「公開配布可能」と
報告する。これを「経典(scripture)のビルド」と呼ぶ
— 世界に配るのは天使(Sefer)のみであり、堕天使(Tartarus)や
鍵(ゲートキーパー)を同梱してはならない、というプロジェクトの
世界観に基づく命名。

使い方:
    python tools/build_public_scripture.py
"""
import re
import sys
import tarfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# 経典(公開配布物)に絶対に含まれてはならないファイル名・内容の断片。
# ファイル名ベースの禁止リストと、内容ベースの禁止リストの両方で検査する
# (ファイル名を変えて同じ内容を混入させる手口への対策)。
FORBIDDEN_FILENAME_FRAGMENTS = [
    "maquina_gatekeeper", "ataraxia_certificate", "provisioning_agent",
    # [改名 2026-11] armageddon(.py/_core.py) は local_only_selfplay_gate /
    # selfplay_engine_core に改名された(docs/lore/OUT_OF_SCOPE_RENAME_PROPOSAL.md §2)。
    # 旧名も残しているのは、改名前のアーカイブやバックアップに対しても
    # 本チェックが引き続き機能するための保険であり、実体は新名の方である。
    "armageddon", "local_only_selfplay_gate", "selfplay_engine_core",
    "zk_audit_trail", "remote_ledger_sync",
]
FORBIDDEN_CONTENT_FRAGMENTS = [
    # [注意] "LossOfAtaraxia" はここに含めない。sefer/__init__.py 自身が
    # 同名の例外クラスを独立に定義しており(maquina_gatekeeper.py側の
    # 同名クラスとは無関係)、これを禁止語に入れるとsefer本体が常に
    # 偽陽性でブロックされてしまう(実機検証済み)。
    "MAQUINA_PUBLIC_KEY_PEM", "enforce_maquina_seal",
    "COMMANDER_HASH", "_verify_creators_air", "hardware_fingerprint",
]


def build_sdist(outdir: Path) -> Path:
    from setuptools.build_meta import build_sdist as _build_sdist
    outdir.mkdir(parents=True, exist_ok=True)
    name = _build_sdist(str(outdir))
    return outdir / name


def verify_scripture_is_clean(sdist_path: Path) -> list[str]:
    """ビルドされたsdistを実際に開いて検査する。問題を文字列のリストで返す
    (空リストなら問題なし)。"""
    problems = []
    with tarfile.open(sdist_path, "r:gz") as tf:
        members = tf.getmembers()
        for m in members:
            name_lower = m.name.lower()
            for frag in FORBIDDEN_FILENAME_FRAGMENTS:
                if frag.lower() in name_lower:
                    problems.append(f"禁止ファイル名が同梱されています: {m.name} (キーワード: {frag})")

            if m.isfile() and m.name.endswith((".py", ".json", ".md", ".txt")):
                try:
                    content = tf.extractfile(m).read().decode("utf-8", errors="ignore")
                except Exception:
                    continue
                for frag in FORBIDDEN_CONTENT_FRAGMENTS:
                    if frag in content:
                        problems.append(f"禁止キーワードが同梱ファイルの内容に含まれています: {m.name} (キーワード: {frag})")
    return problems


def main() -> int:
    # .gitignore の既存の "dist/" 除外パターンをそのまま再利用する。
    outdir = _REPO_ROOT / "dist"
    print("=== [経典のビルド] sdistを実際に構築し、内容を検査します ===")
    try:
        sdist_path = build_sdist(outdir)
    except Exception as e:
        print(f"[致命的エラー] ビルドに失敗しました: {e}", file=sys.stderr)
        return 1

    print(f"[システム] ビルド成果物: {sdist_path}")
    problems = verify_scripture_is_clean(sdist_path)

    if problems:
        print("\n=== ❌ [検査失敗] この経典は公開配布してはいけません ===", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print("\n=== ✅ [検査合格] ライセンス証明書機構・adversarial_training(旧名Tartarus)関連の内容は含まれていません ===")
    print(f"公開配布可能な経典: {sdist_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
