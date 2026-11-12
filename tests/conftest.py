import sys
import os

# 1. 先に一つ上の階層（Anjo-Core直下）へのパスを通す
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. パスが開通した後に、参照ファイル anjo-da-maquina の中枢モジュールを読み込む。
#    runtime_audit_gatekeeper.py は `rsa` パッケージに依存しており、それが
#    インストールできない環境(PyPIに到達できないサンドボックス等)では
#    このimport自体が失敗する。ここで失敗すると conftest.py の読み込みが
#    壊れ、全テストファイルの収集(collection)自体が止まってしまうため、
#    収集全体を壊さないようにフォールバックする。rsaが無い環境で実際に
#    必要になるのは、runtime_audit_gatekeeperに直接依存する個々のテスト
#    ファイル側であり、それらは自分自身で
#    `pytest.importorskip("rsa")` を使って明示的にスキップする設計にして
#    いる(tests/test_runtime_seal_enforcement.py 等を参照)。
try:
    from runtime_audit_gatekeeper import LossOfAtaraxia
except ImportError:
    LossOfAtaraxia = None

def pytest_exception_interact(node, call, report):
    if LossOfAtaraxia is None:
        return
    if call.excinfo and call.excinfo.errisinstance(LossOfAtaraxia):
        report.longrepr = (
            f"\n=== [Anjo da máquina: 保護介入] ===\n"
            f"テスト '{node.name}' の実行中に聖域の防壁が作動しました。\n"
            f"詳細: {str(call.excinfo.value)}\n"
            f"=====================================\n"
        )
