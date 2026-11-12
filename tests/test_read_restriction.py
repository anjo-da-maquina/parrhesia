"""
[脆弱性修正 2026-10] 回帰テスト: 読み取り制限の欠落。

以前は Michael's Sword が書き込み系イベントのみを検査し、ファイル読み取り
(open の mode="r") を一切制限していなかった。allowed_dirs 外の機密ファイル
(鍵・認証情報・ソースコード等) が無条件に読み取れてしまう状態だった。

restrict_reads=True はデフォルト非有効（既存動作との後方互換のため）。
"zero trust" を名乗る以上、機密を扱う呼び出し元は明示的に有効化すべきであり、
このテストはその機能が正しく動作することを保証する。
"""
import subprocess
import sys
from pathlib import Path


def run_with_restrict_reads(target_path: str, restrict_reads: bool) -> subprocess.CompletedProcess:
    # [バグ修正 2026-10] 以前は `except BaseException:` が `sys.exit(0)` 自体が
    # 送出する SystemExit まで捕捉してしまい、成功時でも常に終了コード42に
    # 書き換えられていた（実機検証済み: restrict_reads=False でも常に失敗する
    # 壊れたテストだった）。SystemExitはExceptionのサブクラスではないため、
    # `except Exception:` に変更して意図通り素通しさせる。
    script = f"""
import sys
sys.path.insert(0, {repr(str(Path(__file__).resolve().parent.parent))})
from runtime_guard import Sandbox, LossOfAtaraxia
try:
    with Sandbox(allowed_dirs=[], restrict_reads={restrict_reads}):
        data = open({repr(target_path)}, "r").read()
    print(data, end="")
    sys.exit(0)
except LossOfAtaraxia:
    sys.exit(42)
"""
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)


def test_read_outside_allowed_dirs_blocked_when_restrict_reads_enabled(tmp_path: Path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET")

    res = run_with_restrict_reads(str(secret), restrict_reads=True)
    assert res.returncode == 42, f"CRITICAL: restrict_reads=True なのに読み取りが通過しました。stdout={res.stdout}"
    assert "TOP SECRET" not in res.stdout


def test_read_outside_allowed_dirs_allowed_when_restrict_reads_disabled():
    """後方互換性の確認: デフォルト(restrict_reads=False)では既存動作を維持する。"""
    import tempfile
    import os as _os
    fd, path = tempfile.mkstemp()
    _os.write(fd, b"not secret")
    _os.close(fd)
    try:
        res = run_with_restrict_reads(path, restrict_reads=False)
        assert res.returncode == 0
        assert "not secret" in res.stdout
    finally:
        _os.unlink(path)
