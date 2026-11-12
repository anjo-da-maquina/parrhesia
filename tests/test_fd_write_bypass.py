"""
[脆弱性修正 2026-10] 回帰テスト: fd事前オープンによる Michael's Sword 回避。

CPython の sys.addaudithook には os.write / os.pwrite / os.writev に
対応する監査イベントが存在しないため、Sandbox コンテキストへ入る前に
書き込み用のファイルディスクリプタを確保しておけば、os.open の監査を
完全に回避して allowed_dirs 外へ任意の書き込みができてしまっていた。
このテストは、その回避が今後も塞がれ続けていることを保証する。
"""
import os
import subprocess
import sys
from pathlib import Path


def run_fd_bypass_attempt(target_path: str) -> subprocess.CompletedProcess:
    # [バグ修正 2026-10: 重大な偽陰性] 以前は `except BaseException as e:` が
    # 成功パス自身の `sys.exit(0)` が送出する SystemExit まで捕捉してしまい、
    # 「バイパスが実際に成功した場合でも」常に exit code 42（遮断成功）に
    # 書き換えられていた（実機検証済み）。つまり本テストは fd事前オープンに
    # よる書き込みバイパスが再発しても絶対に検知できない、偽陰性確定の
    # 壊れたテストだった。LossOfAtaraxia（Sefer本来の遮断時例外）のみを
    # 捕捉するよう修正し、成功パスのSystemExitを素通しさせる。
    script = f"""
import os, sys
sys.path.insert(0, {repr(str(Path(__file__).resolve().parent.parent))})
from runtime_guard import Sandbox, LossOfAtaraxia

fd = os.open({repr(target_path)}, os.O_WRONLY | os.O_CREAT)
try:
    with Sandbox(allowed_dirs=[]):
        os.write(fd, b"PWNED")
    sys.exit(0)  # 書き込みが通ってしまった = バイパス成功（失敗ケース）
except LossOfAtaraxia:
    sys.exit(42)  # 期待通りブロックされた
finally:
    os.close(fd)
"""
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)


def test_fd_preopened_before_sandbox_write_is_blocked(tmp_path: Path):
    target = tmp_path / "outside_canary.txt"
    res = run_fd_bypass_attempt(str(target))
    assert res.returncode == 42, (
        f"CRITICAL: fd事前オープンによる書き込みバイパスが再発しています。"
        f"stdout={res.stdout} stderr={res.stderr}"
    )
    content = target.read_bytes() if target.exists() else b""
    assert b"PWNED" not in content, "CRITICAL: ブロック前にデータが書き込まれてしまいました。"


def test_stdout_stderr_fd_are_not_blocked():
    """fd 0/1/2 (stdin/stdout/stderr) は監視対象外であること（通常動作への影響がないことの確認）。"""
    script = """
import sys
sys.path.insert(0, ".")
from runtime_guard import Sandbox
with Sandbox(allowed_dirs=[]):
    import os
    os.write(1, b"hello\\n")
sys.exit(0)
"""
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent.parent))
    assert res.returncode == 0, f"stdout書き込みが誤ってブロックされました: {res.stderr}"
