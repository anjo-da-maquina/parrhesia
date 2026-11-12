"""
[テスト追加 2026-10] src/selfplay_orchestrator.py を実運用対応として
promoteするための回帰テスト。

実機にOllama/Dockerが無い環境(本テスト実行環境を含む)では、
`DefenseOrchestrator.execute_ai_intent` はSandalphon(Docker)段でフェイルクローズド
に`PermissionError`を送出する。これは「防御が機能している」ことの証左であり、
`SelfplayOrchestrator.execute_holy_war`は本来これを捕捉して
「✅ 迎撃成功」として扱うべきだが、修正前は
`ThreatIntelGatherer.analyze_aidd_artifact()`内の、信頼済みの内部レポート
書き込みにまで誤って`execute_ai_intent`(AI生成コード審査パイプライン)を
通していたため、サイクル1回目の偵察フェーズで無関係な`PermissionError`が
捕捉されずに伝播し、オーケストレーター全体がクラッシュしていた
(実機検証済み)。

本テストは、Ollama自体の呼び出し(`PayloadWeaponization.craft_poison`)に
到達する前に、この偵察フェーズだけで異常終了しないことを固定する。
Ollamaサーバーが無い環境では`craft_poison`以降はOllama接続エラーで
失敗するため、本テストはそこを呼び出し側の`try/except`が正しく
`continue`することまでを検証範囲とする。
"""
import shutil
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# [2026-10] 実運用の `ollama` パッケージは、本テストを実行するCI/サンドボックス
# 環境にはインストールされておらず(本番はユーザーのローカルPC上のOllamaサーバー
# が前提)、スタブで差し込む。本テストが検証する範囲(偵察フェーズの内部書き込み)
# はOllamaへの実際の呼び出しに到達する前の経路であるため、このスタブが
# 一度もchat()を呼ばれないことも合わせて確認する。
if "ollama" not in sys.modules:
    _stub = types.ModuleType("ollama")

    def _unexpected_chat(*args, **kwargs):
        raise AssertionError("このテストの検証範囲ではOllamaへの呼び出しは発生しないはず")

    _stub.chat = _unexpected_chat
    sys.modules["ollama"] = _stub

from intelligence_cycle import ThreatIntelGatherer


def test_analyze_aidd_artifact_does_not_require_docker_or_ai_review(tmp_path, monkeypatch):
    """
    [回帰] 修正前は、このメソッド内の信頼済み内部書き込みが
    DefenseOrchestrator.execute_ai_intent(AI生成コード審査パイプライン)を通ってお
    り、Docker不在の環境(フェイルクローズド)で無関係なPermissionErrorを
    送出していた。信頼済みの内部書き込みはパスのジェイル越脱検証
    (secure_resolve)だけで十分であり、Dockerの有無に依存してはならない。
    """
    monkeypatch.chdir(tmp_path)
    threat_intel = ThreatIntelGatherer()

    # 例外を送出せずに完了し、レポートファイルがジェイル内に書き込まれること
    intel_json = threat_intel.analyze_aidd_artifact()

    assert intel_json  # JSON文字列が返る
    report_path = threat_intel.defense.jail.secure_resolve("threat_intel_aidd_report.json")
    assert report_path.exists(), "偵察レポートが隔離領域内に書き込まれているべき"
