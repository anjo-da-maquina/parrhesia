"""
[テスト追加 2026-10] src/ollama_agent_loop.py への "list" アクション統合の
回帰テスト。

背景: "list" アクションは元々 src/final_agent_loop.py (AutonomousAssistant)
という、ollama_agent_loop.pyとは別に並行して存在していた「もう一つの実運用
ループ」実装にのみ存在していた。同じDefenseOrchestrator/Sandboxをラップするループが
2系統並行して存在することは、修正が片方にしか入らず他方が取り残されるリスク
を生むため、唯一の実運用ループ(ollama_agent_loop.py)に一本化し、
final_agent_loop.pyは削除した(DEFECTS.md §M参照)。本テストは、統合後も
"list"がSandboxのワークスペース境界内で正しく動作することを固定する。

test_agent_loop_sandbox_integration.pyと同じ手法(サブプロセス起動 +
runtime_audit_gatekeeper/ollamaのスタブ化)でrsa/ollamaパッケージへの依存を避ける。
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_execute_safe_action(action_req_json: str, workspace_root: str):
    script = f"""
import sys, json
sys.path.insert(0, {str(REPO_ROOT)!r})
sys.path.insert(0, {str(REPO_ROOT / "src")!r})

import types
fake_gatekeeper = types.ModuleType("runtime_audit_gatekeeper")
def _noop_seal(*a, **kw):
    def decorator(func):
        return func
    return decorator
fake_gatekeeper.enforce_maquina_seal = _noop_seal
class _FakeLossOfAtaraxia(Exception):
    pass
fake_gatekeeper.LossOfAtaraxia = _FakeLossOfAtaraxia
sys.modules["runtime_audit_gatekeeper"] = fake_gatekeeper

fake_ollama = types.ModuleType("ollama")
fake_ollama.chat = lambda **kw: {{"message": {{"content": ""}}}}
sys.modules["ollama"] = fake_ollama

from ollama_agent_loop import OllamaAgentExecutor
from runtime_guard import LossOfAtaraxia as SeferLossOfAtaraxia

executor = OllamaAgentExecutor(workspace_root={workspace_root!r})
action_req = json.loads({action_req_json!r})
try:
    result = executor._execute_safe_action(action_req)
    print("UNBLOCKED:" + str(result))
except SeferLossOfAtaraxia as e:
    print("BLOCKED_BY_RUNTIME_GUARD:" + str(e))
"""
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)


def test_list_inside_workspace_succeeds(tmp_path: Path):
    import json

    (tmp_path / "a.txt").write_text("1", encoding="utf-8")
    (tmp_path / "b.txt").write_text("2", encoding="utf-8")

    action_req = json.dumps({"action": "list", "target": "."})
    res = _run_execute_safe_action(action_req, str(tmp_path))
    assert "UNBLOCKED:" in res.stdout, f"stdout={res.stdout} stderr={res.stderr}"
    assert "a.txt" in res.stdout and "b.txt" in res.stdout


def test_list_of_nonexistent_target_returns_error_not_exception():
    import json

    import tempfile

    with tempfile.TemporaryDirectory() as workspace:
        action_req = json.dumps({"action": "list", "target": "does_not_exist"})
        res = _run_execute_safe_action(action_req, workspace)
        assert "UNBLOCKED:[Error]" in res.stdout, f"stdout={res.stdout} stderr={res.stderr}"


def test_list_outside_workspace_via_traversal_is_blocked_by_sandbox(tmp_path: Path):
    """
    listアクションもread/writeと同じくSandboxのワークスペース境界内で
    実行されるため、トラバーサルでの脱走は遮断される。
    """
    import json

    outside_target = str(tmp_path / ".." )
    action_req = json.dumps({"action": "list", "target": outside_target})
    res = _run_execute_safe_action(action_req, str(tmp_path))
    assert "BLOCKED_BY_RUNTIME_GUARD:" in res.stdout, f"stdout={res.stdout} stderr={res.stderr}"
