import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

def run_in_sandbox(code_snippet, allowed_dirs=None, allowed_hosts=None):
    dirs_repr = repr(allowed_dirs or [])
    hosts_repr = repr(allowed_hosts or [])
    script = f"""
import sys
from runtime_guard import Sandbox
try:
    with Sandbox(allowed_dirs={dirs_repr}, allowed_hosts={hosts_repr}):
        exec({repr(code_snippet)})
except BaseException as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    return res

def test_michael_whitelist_open_write_blocked():
    code = "open('unauthorized.txt', 'w').close()"
    res = run_in_sandbox(code, allowed_dirs=[])
    assert "Tripwire" in res.stderr or "Unauthorized write access" in res.stderr

def test_michael_whitelist_open_write_allowed():
    with tempfile.TemporaryDirectory() as tmpdir:
        safe_dir = tmpdir.replace("\\", "\\\\")
        code = f"open('{safe_dir}/authorized.txt', 'w').close()"
        res = run_in_sandbox(code, allowed_dirs=[tmpdir])
        assert res.returncode == 0

def test_michael_whitelist_socket_blocked():
    code = "import socket; s = socket.socket(); s.connect(('203.0.113.1', 80))"
    res = run_in_sandbox(code, allowed_hosts=["api.openai.com"])
    assert "Unauthorized network connection" in res.stderr or "Tripwire" in res.stderr

def test_michael_hard_deny_settrace():
    code = "import sys; sys.settrace(lambda *args: None)"
    res = run_in_sandbox(code)
    assert "Hard-denied event" in res.stderr or "Tripwire" in res.stderr
