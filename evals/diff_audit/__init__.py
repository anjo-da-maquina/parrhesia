"""evals/diff_audit
===================
Inspect(inspect_ai)を用いた「AIエージェントが書いたコード差分の監査」
評価タスク一式。

本パッケージは `inspect_ai` が未インストールの環境でも import エラーに
ならないようにする(`build_dataset.py` と `baseline.py` は標準ライブラリ
のみに依存し、`inspect_ai` への依存は `task.py` 内に閉じている)。
"""
