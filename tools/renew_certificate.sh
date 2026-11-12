#!/usr/bin/env bash
# tools/renew_certificate.sh
#
# 証明書(ataraxia_certificate.json)が期限切れのときに、これ1本で
# 「提案 → 内容確認 → 承認 → 発行」まで自動で行うスクリプト。
#
# 【重要】これは「あなた自身のパソコン」で実行してください(インター
# ネットに繋がっている必要があります)。クラウドの作業環境では
# rsaライブラリが取得できず、必ず失敗します。
#
# 使い方:
#   cd <このリポジトリのフォルダ>
#   bash tools/renew_certificate.sh
#
set -euo pipefail

CLIENT_ID="${1:-local-tester}"

echo "== 1/4: 必要な道具(rsaライブラリ)の確認 =="
if ! python3 -c "import rsa" >/dev/null 2>&1; then
  echo "rsaライブラリが見つかりません。インストールします..."
  pip install --break-system-packages rsa
fi
python3 -c "import rsa" && echo "OK"

echo
echo "== 2/4: 新しい証明書の『提案』を作成 =="
python3 adapters/provisioning_agent.py

echo
echo "== 3/4: 提案内容の確認(このパソコンの指紋・有効期限をここで目視確認してください) =="
python3 tools/promote_provisioning_seal.py --list

echo
echo "== 4/4: 鍵のローテーションでないことを確認してから承認 =="
# [欠陥修正 2026-11 §CZ] 以前はここで無条件に --approve を呼んでおり、
# 「人間による帯外確認」を前提とする承認フロー(§BY)を無人の自動化が
# 素通りしてしまっていた(DEFECTS.md §CX)。--check-rotation で
# 「今回の提案は、現在信頼されている鍵と同一か(=単なる有効期限の延長)」
# だけを機械的に判定し、同一の場合のみ自動承認する。鍵そのものが変わる
# (本物のローテーション)場合は、ここで停止し、人間に手動承認を委ねる。
if python3 tools/promote_provisioning_seal.py --check-rotation "${CLIENT_ID}"; then
  python3 tools/promote_provisioning_seal.py --approve "${CLIENT_ID}"
  echo
  echo "完了しました。ataraxia_certificate.json が新しく発行されています。"
  echo "注意: 新しい証明書も、発行から7日間しか有効ではありません(provisioning_agent.pyの既定値)。"
  echo "7日おきに、このスクリプトをもう一度実行する必要があります。"
else
  rotation_exit=$?
  echo
  if [ "${rotation_exit}" -eq 2 ]; then
    echo "[停止] 信頼の起点(公開鍵)が変わる提案です。安全のため自動承認を停止しました。"
    echo "上記の指紋を別経路(電話等)で確認したうえで、手動で次を実行してください:"
    echo "  python3 tools/promote_provisioning_seal.py --approve ${CLIENT_ID}"
  else
    echo "[エラー] 承認待ちの提案を確認できませんでした(終了コード ${rotation_exit})。"
  fi
  exit "${rotation_exit}"
fi
