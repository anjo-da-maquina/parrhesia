"""
src/aegis_system.py
=====================
[新設 2026-10] src/*.py のうち8ファイル
(mythos_weaponization.py, angelic_evolution.py, gemini_oracle_feed.py,
intelligence_cycle.py, secure_oracle_feed.py, adversarial_evolution.py,
claude_agent_loop.py, final_agent_loop.py, oracle_feed.py)が
`from test_integrated_defense import AegisSystem` としてimportしていたが、
test_integrated_defense モジュール自体がリポジトリのどこにも存在せず、
これらのファイルは全て起動不能(ModuleNotFoundError)だった。

本モジュールが `AegisSystem` の正式な実装を提供する。4層の防御を統合する:

  1. Gabriel (runtime_guard.inquisition)   — 静的AST解析による危険コードの事前検知
  2. IntentInterceptor             — ハニーポット・ディレクトリトラバーサル検知
  3. WorkspaceJail                 — パスの物理的隔離(secure_resolve)
  4. DockerSandbox (Docker隔離結界、旧名Sandalphon) — OSレベルの動的実行検証（強制・既定でON）

[重要: 2026-10 改修] 1〜3は静的解析・文字列パターンに基づく「事前検閲」であり、
難読化・動的コード生成（`getattr(__builtins__, ''.join(chr(...)...))`等）を
本質的にすり抜け得る。これを補うため、本モジュールは既定で、検閲を通過した
コードを実際にDockerの隔離結界（ネットワーク完全遮断・読み取り専用・タイムアウト
監視）内で動的実行し、その結果を見てから最終承認する。これは「ゼロトラスト」の
核心であり、Dockerデーモンが利用できない環境では、無条件に実行を拒否する
（フェイルオープンではなく、フェイルクローズド）。
手元環境でDockerデーモンが起動していない場合、AIエージェントループは
一切の実行を許可されなくなる。これは不便さより安全性を優先する意図的な設計であり、
`require_docker_sandbox=False` を明示的に渡した場合のみ無効化できる
（テスト・デバッグ専用。本番運用では使用しないこと）。
さらに実際にコードを実行する/ファイルを書き込む呼び出し側は、必ず
`runtime_guard.Sandbox` (OSレベルの audit hook) の中で実行すること。
AegisSystemはSandboxの代替ではなく、Sandboxの前段に立つ追加の防御層である。
"""
import sys
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from runtime_guard import inquisition
from workspace_manager import WorkspaceJail
from anjo_interceptor.intent_checker import IntentInterceptor, SpecificationGamingDetected
from docker_sandbox_executor import run_in_docker_sandbox


class AegisSystem:
    def __init__(self, workspace_root="jail_workspace", require_docker_sandbox: bool = True,
                 sandbox_timeout: int = 5):
        self.jail = WorkspaceJail(base_dir=workspace_root)
        self.interceptor = IntentInterceptor(workspace_root=str(self.jail.base_dir))
        # [テスト専用の切り離し] require_docker_sandbox=False は、Docker不在の
        # CI環境等で1〜3の静的検閲ロジック単体を検証するためだけに存在する。
        # 本番の呼び出し側（src/*_agent_loop.py 等）は既定値(True)のまま使うこと。
        self.require_docker_sandbox = require_docker_sandbox
        self.sandbox_timeout = sandbox_timeout

    def execute_ai_intent(self, code: str, target: str):
        """
        AIが生成した `code`（これから実行/書き込みされようとしているコード片）と
        `target`（操作対象パス）を実行前に検閲する。危険と判断した場合は
        PermissionError を送出する。戻り値 True は「ここまでの全層の検閲・動的
        検証を通過した」ことを意味する。実際のファイルI/Oは依然として
        呼び出し側が `runtime_guard.Sandbox` の中で行う必要がある。
        """
        # 1. Gabriel: 静的AST解析
        findings = inquisition(code)
        critical = [f for f in findings if f.severity == "critical"]
        if critical:
            raise PermissionError(
                f"[Aegis: Gabriel] 危険なコードパターンを検知しました: {[f.message for f in critical]}"
            )

        # 2. IntentInterceptor: ハニーポット検知（readとして評価）
        try:
            self.interceptor.evaluate_action(json.dumps({"action": "read", "target": target}))
        except SpecificationGamingDetected as e:
            raise PermissionError(f"[Aegis: IntentInterceptor/Honeypot] {e}")

        # 3. IntentInterceptor: トラバーサル・保護領域検知（writeとして評価）
        try:
            self.interceptor.evaluate_action(json.dumps({"action": "write", "target": target, "content": code}))
        except SpecificationGamingDetected as e:
            raise PermissionError(f"[Aegis: IntentInterceptor/Traversal] {e}")

        # 4. DockerSandbox(旧名Sandalphon): Docker隔離結界内での動的実行検証（既定で強制）
        if self.require_docker_sandbox:
            result = run_in_docker_sandbox(code, timeout=self.sandbox_timeout)
            if not result["docker_available"]:
                raise PermissionError(
                    f"[Aegis: DockerSandbox] {result['reason']} "
                    "ゼロトラスト方針により、動的検証ができないコードの実行を拒否します。"
                )
            if result["timed_out"]:
                raise PermissionError(
                    f"[Aegis: DockerSandbox] 隔離結界内での実行が{self.sandbox_timeout}秒を"
                    "超過しました。無限ループ等の遅延攻撃と断定し拒否します。"
                )

        return True
