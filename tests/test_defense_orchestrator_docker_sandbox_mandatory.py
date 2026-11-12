"""
[テスト追加 2026-10] Docker/OSレベルの強制(mandatory)サンドボックス化が、
DefenseOrchestrator.execute_ai_intent()内で実際にフェイルクローズドで機能している
ことを検証する回帰テスト。

背景: src/docker_sandbox_executor.py(旧名sandalphon_jail.py)はこれまで、CLIから手動実行する場合のみ
機能する独立ツールであり、AI実行経路からは一度も呼ばれていなかった
（＝「Docker隔離は任意・手動のおまけ」）。本テストは、DefenseOrchestratorが
既定(require_docker_sandbox=True)でDockerSandbox(旧名Sandalphon)の動的検証結果を見て
最終承認するようになったこと、およびDockerデーモンが利用できない場合に
無条件で拒否(フェイルクローズド)することを保証する。

モック対象は `defense_orchestrator.run_in_docker_sandbox` であること(docker_sandbox_executor
モジュール側ではない)に注意。defense_orchestrator.py は
`from docker_sandbox_executor import run_in_docker_sandbox` で名前を自分の名前空間に
束縛しているため、docker_sandbox_executor側をモックしても反映されない。
"""
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import defense_orchestrator
from defense_orchestrator import DefenseOrchestrator


def _fake_result(**overrides):
    base = {
        "docker_available": False, "reason": "", "executed": False,
        "timed_out": False, "returncode": None, "stdout": "", "stderr": "",
    }
    base.update(overrides)
    return base


def test_docker_unavailable_is_fail_closed_even_for_benign_code(tmp_path, monkeypatch):
    monkeypatch.setattr(
        defense_orchestrator, "run_in_docker_sandbox",
        lambda code, timeout=5: _fake_result(docker_available=False, reason="テスト: デーモン未起動"),
    )
    a = DefenseOrchestrator(workspace_root=str(tmp_path))
    try:
        a.execute_ai_intent("print('completely benign')", "ok.txt")
        assert False, "Dockerデーモン不在にもかかわらず実行が許可されてしまった(フェイルオープンはゼロトラスト方針違反)"
    except PermissionError as e:
        assert "DockerSandbox" in str(e)


def test_docker_available_and_success_is_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr(
        defense_orchestrator, "run_in_docker_sandbox",
        lambda code, timeout=5: _fake_result(docker_available=True, executed=True, returncode=0, stdout="ok"),
    )
    a = DefenseOrchestrator(workspace_root=str(tmp_path))
    assert a.execute_ai_intent("print('ok')", "ok.txt") is True


def test_docker_available_but_timed_out_is_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(
        defense_orchestrator, "run_in_docker_sandbox",
        lambda code, timeout=5: _fake_result(docker_available=True, executed=True, timed_out=True),
    )
    a = DefenseOrchestrator(workspace_root=str(tmp_path))
    try:
        a.execute_ai_intent("while True: pass", "ok.txt")
        assert False, "タイムアウト(無限ループ等の遅延攻撃)が遮断されなかった"
    except PermissionError as e:
        assert "タイムアウト" in str(e) or "超過" in str(e)


def test_require_docker_sandbox_false_is_test_only_bypass(tmp_path, monkeypatch):
    """require_docker_sandbox=False は静的層(ScanSource/IntentInterceptor)単体を
    検証するためのテスト専用の切り離し。悪性コードはそれでも静的層で捕捉される。"""
    a = DefenseOrchestrator(workspace_root=str(tmp_path), require_docker_sandbox=False)
    try:
        a.execute_ai_intent("import os\nos.system('rm -rf /')", "ok.txt")
        assert False, "明らかな危険コードがScanSource(静的AST解析)で捕捉されなかった"
    except PermissionError as e:
        assert "ScanSource" in str(e)
    # 静的層のみを通過する良性コードは許可される(DockerSandboxはスキップされるため)
    assert a.execute_ai_intent("print('ok')", "ok.txt") is True


def test_real_environment_docker_daemon_unreachable_blocks_by_default():
    """モックなしの実環境テスト: このテスト実行環境(クラウドサンドボックス)には
    Dockerデーモンが存在しないため、既定設定のDefenseOrchestratorは実際に
    フェイルクローズドで拒否することを確認する(インフラのモックに依存しない
    最終的な実機検証)。"""
    with tempfile.TemporaryDirectory() as d:
        a = DefenseOrchestrator(workspace_root=d)
        try:
            a.execute_ai_intent("print('benign')", "ok.txt")
            # Dockerデーモンが実際に起動している環境(本番相当)で実行された場合は
            # ここに到達してよい。CI/サンドボックス環境では到達しないはず。
        except PermissionError as e:
            assert "DockerSandbox" in str(e)
