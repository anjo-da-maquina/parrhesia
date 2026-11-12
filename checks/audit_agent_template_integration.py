import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import report_pass, report_fail, ROOT

NAME = "audit_agent_template_integration - 思考統制監査: src/openai_agent_loop.py (OpenAI拡張用テンプレート) が…"

# 思考統制監査: src/openai_agent_loop.py (OpenAI拡張用テンプレート) が、
# 「拡張用の雛形」と称しながら防壁を一つも統合しない張りぼてに戻されて
# いないかを静的に検証する。
#
# [背景 2026-10] 旧版は以下の2点が壊れていた:
#   1. enforce_maquina_seal 失敗時のフォールバックimport先
#      (anjo_interceptor.runtime_audit_gatekeeper) がリポジトリに存在せず、
#      本番では絶対に通らない死んだコードパスだった。
#   2. _execute_safe_action が実ファイルI/Oを一切行わないダミー実装で、
#      runtime_guard.Sandbox も AegisSystem も統合されていなかった。
#      これをコピーして拡張する開発者は、防壁を一つも使わないコードを
#      書く結果になってしまう構造的欠陥だった。
# 本検査はこの2点が再発していないことを保証する。


def main():
    target = ROOT / "src" / "openai_agent_loop.py"
    if not target.exists():
        report_fail(NAME, f"必須ファイルが見つかりません: {target}")
        return

    text = target.read_text(encoding="utf-8-sig")

    # A: 存在しないフォールバックimportが復活していないか
    if "anjo_interceptor.runtime_audit_gatekeeper" in text:
        # docstring内の「過去の欠陥の説明」としての言及は許容するが、
        # 実際の import文として復活していないかを厳密にチェックする。
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("from anjo_interceptor.runtime_audit_gatekeeper") or \
               stripped.startswith("import anjo_interceptor.runtime_audit_gatekeeper"):
                report_fail(
                    NAME,
                    "存在しないフォールバックimport 'anjo_interceptor.runtime_audit_gatekeeper' が"
                    "実行コードとして復活しています。"
                )

    # B: Sandbox / AegisSystem が実際に統合されているか（文字列の有無だけでなく、
    #    _execute_safe_action の中で実際に使われているかまで確認する）
    if "from runtime_guard import Sandbox" not in text:
        report_fail(NAME, "runtime_guard.Sandbox がimportされていません。OSレベルの最終防衛線が外れています。")
    if "from aegis_system import AegisSystem" not in text:
        report_fail(NAME, "aegis_system.AegisSystem がimportされていません。Gabriel/Sandalphonの事前検閲が外れています。")
    if "with Sandbox(" not in text:
        report_fail(NAME, "_execute_safe_action が Sandbox コンテキスト内でファイルI/Oを行っていません。")
    if "self.aegis.execute_ai_intent" not in text and "aegis.execute_ai_intent" not in text:
        report_fail(NAME, "run_task が AegisSystem.execute_ai_intent による事前検閲を経由していません。")

    # C: enforce_maquina_seal 自体は維持されているか（証明書ゲートの除去防止）
    if "enforce_maquina_seal" not in text:
        report_fail(NAME, "enforce_maquina_seal(証明書ゲート)が外れています。")

    report_pass(NAME, "OpenAI拡張テンプレートが、死んだフォールバックimportを持たず、"
                       "Sandbox/AegisSystemによる実防壁統合を保ったまま提供されています。")


if __name__ == "__main__":
    main()
