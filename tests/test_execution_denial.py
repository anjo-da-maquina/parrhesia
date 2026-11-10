import subprocess
import sys
from pathlib import Path

def run_guarded(code_snippet):
    script = f"""
import sys
from runtime_guard import Sanctum
try:
    with Sanctum(allowed_dirs=[]):
        exec({repr(code_snippet)})
except BaseException:
    sys.exit(42)
"""
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

def test_os_system_denied_with_side_effect(tmp_path: Path):
    canary = tmp_path / "canary_system.txt"
    # Windows/Linux両対応のファイル作成コマンド
    code = f"import os; os.system('echo pwned > {canary.as_posix()}')"
    
    res = run_guarded(code)
    
    assert res.returncode == 42, f"Block failed. Expected 42, got {res.returncode}. stderr: {res.stderr}"
    assert not canary.exists(), "CRITICAL: os.system was executed and canary file was created!"

def test_subprocess_popen_denied_with_side_effect(tmp_path: Path):
    canary = tmp_path / "canary_popen.txt"
    code = f"import subprocess; subprocess.Popen('echo pwned > {canary.as_posix()}', shell=True)"
    
    res = run_guarded(code)
    
    assert res.returncode == 42, f"Block failed. Expected 42, got {res.returncode}. stderr: {res.stderr}"
    assert not canary.exists(), "CRITICAL: subprocess.Popen was executed and canary file was created!"