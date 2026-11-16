"""evals/reward_hacking
========================
Inspect(inspect_ai)のsandbox機能を用いた「エージェントによるバグ修正の
報酬ハック」評価タスク一式。

本パッケージは `inspect_ai` が未インストールの環境でも import エラーに
ならないようにする(`build_tasks.py` と `verify_reference_diffs.py` は
標準ライブラリとParrhesia自身(`parrhesia.diff_fraud`)のみに依存し、
`inspect_ai` への依存は `task.py` 内に閉じている)。
"""
