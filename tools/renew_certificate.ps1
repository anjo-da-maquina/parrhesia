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
$LogFile = Join-Path $RepoRoot "tools\renew_certificate.log"

# 画面に出す内容を、呼び出し方(手動実行/タスクスケジューラ経由)に
# 関わらず必ずこのファイルにも記録する。記録の仕組みをこのスクリプト
# 自身に持たせることで、タスクスケジューラ側の呼び出し方に依存しない
# ようにしている。
try {
    Start-Transcript -Path $LogFile -Append | Out-Null
} catch {
    Write-Host "警告: ログの記録開始に失敗しました($LogFile)。処理は続行します。"
}

try {
    Write-Host "===== 開始: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====="

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
    Write-Host "== 4/4: 鍵のローテーションでないことを確認してから承認 =="
    # [欠陥修正 2026-11 §CZ] 以前はここで無条件に --approve を呼んでおり、
    # 「人間による帯外確認」を前提とする承認フロー(§BY)を無人の自動化が
    # 素通りしてしまっていた(GRIMOIRE.md §CX)。--check-rotation で
    # 「今回の提案は、現在信頼されている鍵と同一か(=単なる有効期限の延長)」
    # だけを機械的に判定し、同一の場合のみ自動承認する。鍵そのものが変わる
    # (本物のローテーション)場合は、ここで停止し、人間に手動承認を委ねる。
    python tools\promote_provisioning_seal.py --check-rotation $ClientId
    $RotationCheckExit = $LASTEXITCODE

    if ($RotationCheckExit -eq 0) {
        python tools\promote_provisioning_seal.py --approve $ClientId
        Write-Host ""
        Write-Host "完了しました。ataraxia_certificate.json が新しく発行されています。"
        Write-Host "注意: 新しい証明書も発行から7日間しか有効ではありません(既定値)。"
    } elseif ($RotationCheckExit -eq 2) {
        Write-Host ""
        Write-Host "[停止] 信頼の起点(公開鍵)が変わる提案です。安全のため自動承認を停止しました。"
        Write-Host "上記の指紋を別経路(電話等)で確認したうえで、手動で次を実行してください:"
        Write-Host "  python tools\promote_provisioning_seal.py --approve $ClientId"
        exit 2
    } else {
        Write-Host ""
        Write-Host "[エラー] 承認待ちの提案を確認できませんでした(終了コード $RotationCheckExit)。"
        exit $RotationCheckExit
    }
}
finally {
    try { Stop-Transcript | Out-Null } catch {}
}
