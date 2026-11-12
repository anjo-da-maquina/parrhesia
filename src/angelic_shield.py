"""
src/angelic_shield.py
=======================
[再構築 2026-10] セルフレビューで以下3点の欠陥が発覚したため作り直した。

  1. 独自実装の `metatrons_seal`(sys.addaudithook)が、OSレベルの実行保護を
     提供しているかのような体裁("人と機械の境界は守護されています")で
     表示されていたが、実態は `runtime_guard.Sandbox` よりはるかに弱い簡易実装
     だった(保護対象の判定が `"anjo-da-maquina_2" in target_file` という
     部分文字列一致のみで、Sandboxのような allowed_dirs によるパス正規化・
     物理的隔離を一切行わない)。本ファイル自体はコードを実行せず
     (RazielCherubimは外部API呼び出し、ZadkielDominionはJSONファイル
     読み書きのみ)、audit hookを仕掛ける意味自体がそもそも薄かった。
     本当にOSレベルの保護が必要な箇所(AIが生成したコードの実行)は、
     `src/aegis_system.py` の `AegisSystem` と `runtime_guard.Sandbox` が担う。
     本ファイルはそれらの代替ではないため、誤解を招く表示を撤去した。

  2. `ZadkielDominion.assimilate_knowledge()` が、Gemini(LLM)の生出力を
     人間の承認なしに直接 `shield_rules.json`(実際に有効な禁止ルール)へ
     反映していた。これは `adversarial_training/local_only_selfplay_gate.py` で既に修正した
     「LLM出力を直接運用ルールに反映しない」という原則(§C, DEFECTS.md)
     に違反する、同種の脆弱性だった。プロンプトインジェクションや幻覚に
     よって、無関係な正規モジュール/関数が誤って禁止リストに追加される
     リスクがある。本修正では Armageddon の `raziel_ledger_pending.json`
     と同じパターンを採用し、提案はまず `runtime_guard/shield_rules_pending.json`
     に積むのみとし、`tools/promote_shield_seal.py` による人間の明示的
     承認を経て初めて `shield_rules.json` に反映されるようにした。

  3. `__main__` で `GEMINI_API_KEY` を `os.environ.get()` で読み取った後、
     環境変数から消去していなかった(secure_oracle_feed.pyで既に修正した
     パターンと同じ欠陥)。読み取り直後に `os.environ.pop()` で消去する
     ように修正した。
"""
import os
import sys
import json
import urllib.request
import urllib.error
import re
import time
from pathlib import Path
from datetime import datetime

_REPO_ROOT = Path(__file__).resolve().parent.parent
PENDING_RULES_PATH = _REPO_ROOT / "runtime_guard" / "shield_rules_pending.json"


class RazielCherubim:
    """外界(Gemini)から脆弱性の構造と防衛策に関する知識を取得する。"""

    def __init__(self, api_key):
        self.api_key = api_key.strip()

    def fetch_threat_signature(self, target_threat=None):
        threat_name = target_threat if target_threat else '未知の脅威'
        print(f"\n[智天使ラジエル] 外界より『{threat_name}』の構造と防衛策を抽出中...")

        models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-pro"]
        threat_focus = f"the '{target_threat}'" if target_threat else "a specific"
        prompt = (
            "You are an expert Blue Team cybersecurity AI. "
            f"Generate ONLY a pure JSON object describing {threat_focus} Python vulnerability. "
            "Keys must be exactly: 'vulnerability_name' (string), 'description' (string), 'dangerous_modules' (list of strings), 'dangerous_functions' (list of strings). "
            "Return pure JSON string only."
        )
        data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req) as response:
                    res_body = response.read().decode('utf-8')
                    res_json = json.loads(res_body)
                    gemini_text = res_json['candidates'][0]['content']['parts'][0]['text']
                    match = re.search(r'\{.*\}', gemini_text, re.DOTALL)
                    return json.loads(match.group(0) if match else gemini_text)
            except urllib.error.HTTPError as e:
                if e.code in (503, 404):
                    continue
                else:
                    print(f"[エラー] 致命的な接続失敗: HTTP Error {e.code}")
                    sys.exit(1)
            except Exception:
                sys.exit(1)
        print("[エラー] 全外界サーバーが応答不可。システムを一時休眠します。")
        sys.exit(1)


class ZadkielDominion:
    """
    [2026-10] ラジエルが取得したLLM生成の脅威情報を、人間承認待ちの
    提案キュー(`runtime_guard/shield_rules_pending.json`)に積むのみ。
    実際に有効な `shield_rules.json` への反映は、`tools/promote_shield_seal.py`
    による人間の明示的承認が必要(Armageddonの raziel_ledger_pending.json
    と同一のパターン)。
    """

    def __init__(self, rules_file: Path = None, pending_file: Path = None):
        self.rules_file = rules_file or Path("shield_rules.json")
        self.pending_file = pending_file or PENDING_RULES_PATH
        if not self.rules_file.exists():
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump({"blocked_modules": [], "blocked_functions": []}, f)

    def propose_knowledge(self, intel: dict):
        """LLMが生成した脅威情報を、承認待ちキューに積む（即時反映はしない）。"""
        print("[主天使ザドキエル] ラジエルの知識を解析し、防壁ルール更新案をキューに積みます...")
        print("(※ 人間の承認を得るまで、実際の防壁ルールには反映されません)")

        pending = []
        if self.pending_file.exists():
            try:
                with open(self.pending_file, "r", encoding="utf-8") as f:
                    pending = json.load(f)
            except Exception:
                pending = []

        proposal = {
            "proposed_at": datetime.now().isoformat(),
            "vulnerability_name": intel.get("vulnerability_name", "(不明)"),
            "description": intel.get("description", ""),
            "dangerous_modules": intel.get("dangerous_modules", []),
            "dangerous_functions": intel.get("dangerous_functions", []),
            "status": "PENDING_HUMAN_REVIEW",
        }
        pending.append(proposal)

        self.pending_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pending_file, "w", encoding="utf-8") as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

        print(f"=> [提案キュー登録] 脅威「{proposal['vulnerability_name']}」への対応案を"
              f" {self.pending_file.name} に登録しました。"
              " `python tools/promote_shield_seal.py --list` で確認してください。")
        return proposal


if __name__ == "__main__":
    # [2026-10] APIキーは読み取り直後に環境変数から消去する(secure_oracle_feed.py
    # と同一のパターン)。難読化等を用いた後続処理からのキー窃取を防ぐ。
    api_key = os.environ.pop("GEMINI_API_KEY", None)
    if not api_key:
        sys.exit(1)

    target_threat = sys.argv[1] if len(sys.argv) > 1 else None
    cycles = 1 if target_threat else 3

    print("=== [Merkabah] 熾天使ハシュマリエル: 外部脅威インテリジェンス取り込みサイクル ===")
    raziel = RazielCherubim(api_key)
    del api_key  # メモリ上の変数からも明示的に破棄
    zadkiel = ZadkielDominion()

    for i in range(1, cycles + 1):
        print(f"\n--- 脅威インテリジェンス取り込みサイクル 第 {i:03d} 階層 ---")
        intel = raziel.fetch_threat_signature(target_threat)
        zadkiel.propose_knowledge(intel)
        time.sleep(2)
