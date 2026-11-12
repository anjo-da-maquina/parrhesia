# tools/setup_weekly_renewal_task.ps1
#
# これを1回だけ実行すると、Windowsの「タスクスケジューラ」に
# 「毎週、証明書を自動更新する」予定が登録される。
# 登録後は、このスクリプトを二度と実行する必要はない。
# 実際の更新作業は tools/renew_certificate.ps1 が担当し、
# このスクリプトはそれを「毎週自動で呼び出す予定」を仕込むだけ。
#
# 使い方(あなた自身のWindowsパソコンで、リポジトリのフォルダに
# いる状態のPowerShellで):
#   powershell -ExecutionPolicy Bypass -File tools\setup_weekly_renewal_task.ps1

$ErrorActionPreference = "Stop"

# このスクリプト自身の場所から、更新スクリプトの場所とログの場所を
# 自動で特定する(どのフォルダにリポジトリを置いても動くように)
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RenewScript = Join-Path $RepoRoot "tools\renew_certificate.ps1"
$LogFile = Join-Path $RepoRoot "tools\renew_certificate.log"

if (-not (Test-Path $RenewScript)) {
    throw "renew_certificate.ps1 が見つかりません: $RenewScript"
}

$TaskName = "Parrhesia-CertRenewal-Weekly"

# ログの記録は renew_certificate.ps1 自身が行うので、ここでは
# 単純にそのスクリプトを呼び出すだけでよい(外側からの出力リダイレクト
# は -File モードでは機能しないため、使わない)。
$RenewArg = '-NoProfile -ExecutionPolicy Bypass -File "' + $RenewScript + '"'
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $RenewArg

# 毎週月曜の午前9時に実行(パソコンがその時刻にスリープ中でも、
# 次に起動したタイミングで実行される設定にしている)
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "証明書(ataraxia_certificate.json)を毎週自動で更新する(Parrhesiaリポジトリ)" `
    -Force | Out-Null

Write-Host "登録完了: タスク '$TaskName' が毎週月曜9時に自動実行されます。"
Write-Host "実行結果は次のファイルに記録されます:"
Write-Host "  $LogFile"
Write-Host ""
Write-Host "今すぐ1回だけ試しに実行して確認したい場合は、次を実行してください:"
Write-Host ('  Start-ScheduledTask -TaskName "' + $TaskName + '"')
Write-Host ""
Write-Host "登録されているか確認したい場合は、次を実行してください:"
Write-Host ('  Get-ScheduledTask -TaskName "' + $TaskName + '"')
