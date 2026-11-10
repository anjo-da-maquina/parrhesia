import sys
import os

# 1. 先に一つ上の階層（Anjo-Core直下）へのパスを通す
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. パスが開通した後に、参照ファイル anjo-da-maquina の中枢モジュールを読み込む
from runtime_audit_gatekeeper import LossOfAtaraxia

def pytest_exception_interact(node, call, report):
    if call.excinfo and call.excinfo.errisinstance(LossOfAtaraxia):
        report.longrepr = (
            f"\n=== [Anjo da máquina: 保護介入] ===\n"
            f"テスト '{node.name}' の実行中に聖域の防壁が作動しました。\n"
            f"詳細: {str(call.excinfo.value)}\n"
            f"=====================================\n"
        )
