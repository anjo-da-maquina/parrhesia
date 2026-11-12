# tools/renew_certificate.ps1
#
# 証明書(ataraxia_certificate.json)の「提案→確認→承認」を自動で行う
# Windows版スクリプト。tools/renew_certificate.sh のPowerShell版。
#
# 想定: あなた自身のWindowsパソコンで実行する(インターネット接続が必要)。
# このスクリプト単体を手動で実行してもよいし、
# tools/setup_weekly_renewal_task.ps1 で毎週自動実行させることもできる。

$ErrorActionPreference = "Stop"

# このスクリプト自身の場所から、リポジトリのフォルダを自動で特定する
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$ClientId = "anjo-local-tester"

Write-Host "== 1/4: 必要な道具(rsaライブラリ)の確認 =="
python -c "import rsa" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "rsaライブラリが見つかりません。インストールします..."
    pip install rsa
}

Write-Host ""
Write-Host "== 2/4: 新しい証明書の『提案』を作成 =="
python adapters\provisioning_agent.py

Write-Host ""
Write-Host "== 3/4: 提案内容の確認 =="
python tools\promote_provisioning_seal.py --list

Write-Host ""
Write-Host "== 4/4: 承認して、新しい証明書を発行 =="
python tools\promote_provisioning_seal.py --approve $ClientId

Write-Host ""
Write-Host "完了しました。ataraxia_certificate.json が新しく発行されています。"
Write-Host "注意: 新しい証明書も発行から7日間しか有効ではありません(既定値)。"
