"""
[テスト追加 2026-10] 「ライセンス証明書機構の公開配布からの分離」の回帰テスト。

実際に sdist をビルドし、その内容を検査することで、将来 pyproject.toml や
MANIFEST.in が変更されても、runtime_audit_gatekeeper.py / ataraxia_certificate.json /
adapters/provisioning_agent.py / adversarial_training(旧名local_arena、hardware gate) /
運用者向けの内部テスト(tests/)が、公開配布物(公開配布物)に紛れ込んでいないことを
保証する。

[実装上の注意] setuptools.build_meta.build_sdist() は内部でdistutilsの
ディレクトリ作成キャッシュ(_path_created)を参照するため、同一プロセス内で
複数回連続して呼び出すと "Cannot update time stamp of directory" という
無関係なエラーで失敗することが実機で確認された(setuptools/distutils側の
既知の制約であり、本プロジェクトのコードの不具合ではない)。そのため、
各テストはサブプロセスとして独立したPythonプロセスでビルドを実行する。
"""
import subprocess
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS = REPO_ROOT / "tools"


def _build_sdist_in_subprocess(outdir: Path) -> Path:
    script = f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(TOOLS)!r})
import build_public_release as bps
p = bps.build_sdist(Path({str(outdir)!r}))
print("SDIST_PATH:" + str(p))
"""
    res = subprocess.run(
        [sys.executable, "-c", script], cwd=str(REPO_ROOT),
        capture_output=True, text=True,
    )
    assert res.returncode == 0, f"sdistビルドに失敗しました。stdout={res.stdout} stderr={res.stderr}"
    for line in res.stdout.splitlines():
        if line.startswith("SDIST_PATH:"):
            return outdir / Path(line[len("SDIST_PATH:"):]).name
    raise AssertionError(f"sdistのパスを取得できませんでした。stdout={res.stdout}")


def test_sdist_is_clean_and_contains_only_the_runtime_guard_package(tmp_path: Path):
    """1回のビルドで、以下の3点をまとめて検証する
    (前述の注意により、ビルド自体は1テストにつき1回のみ行う):
      1. ライセンス機構/adversarial_training(旧名Local Arena)関連の内容が混入していないこと
      2. 運用者向けの内部テスト(tests/)が同梱されていないこと
         ([実機で発見した回帰] setuptoolsのsdistは慣習的にtests/全体を
         自動的に含めてしまい、MANIFEST.inでの明示的な除外が無いと、
         runtime_audit_gatekeeper/local_only_selfplay_gateを直接参照する内部テストまで
         公開配布物に紛れ込んでしまっていた)
      3. 過剰な除外で空っぽの配布物になっていない(runtime_guard本体は残っている)こと
    """
    sdist_path = _build_sdist_in_subprocess(tmp_path)

    sys.path.insert(0, str(TOOLS))
    import build_public_release as bps
    problems = bps.verify_release_is_clean(sdist_path)
    assert problems == [], f"公開配布物にライセンス機構/adversarial_training関連の内容が混入しています: {problems}"

    with tarfile.open(sdist_path, "r:gz") as tf:
        names = tf.getnames()

    assert not any("/tests/" in n for n in names), (
        f"tests/ディレクトリが公開配布物に含まれてしまっています: {[n for n in names if '/tests/' in n]}"
    )
    assert any(n.endswith("runtime_guard/__init__.py") for n in names)
    assert any(n.endswith("runtime_guard/audit_chain.py") for n in names)
