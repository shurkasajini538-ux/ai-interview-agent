$ErrorActionPreference = 'Stop'
$studioRoot = $PSScriptRoot
$studioPython = Join-Path $studioRoot '.venv/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $studioPython)) {
    Write-Host '请先双击「安装依赖.cmd」，安装完成后再启动。'
    exit 1
}
$studioPort = 8765
$studioUrl = "http://127.0.0.1:$studioPort"
try {
    $studioHealth = Invoke-RestMethod "$studioUrl/api/health" -TimeoutSec 2
    if ($studioHealth.app -eq 'interview-studio') {
        Start-Process $studioUrl
        exit 0
    }
} catch { }
$studioOccupied = Get-NetTCPConnection -LocalPort $studioPort -State Listen -ErrorAction SilentlyContinue
if ($studioOccupied) {
    Write-Host '端口 8765 被其他程序占用。请关闭占用程序，或使用 .venv/Scripts/python.exe app.py --port 8766 --open。'
    exit 1
}
$studioApp = Join-Path $studioRoot 'app.py'
$studioProcess = Start-Process -FilePath $studioPython -ArgumentList @(('"' + $studioApp + '"'), '--port', "$studioPort") -WorkingDirectory $studioRoot -WindowStyle Hidden -PassThru
for ($studioAttempt = 0; $studioAttempt -lt 30; $studioAttempt++) {
    Start-Sleep -Milliseconds 300
    try {
        $studioHealth = Invoke-RestMethod "$studioUrl/api/health" -TimeoutSec 1
        if ($studioHealth.ok -and $studioHealth.app -eq 'interview-studio') {
            $studioProcess.Id | Set-Content -LiteralPath (Join-Path $studioRoot 'data/server.pid')
            Start-Process $studioUrl
            exit 0
        }
    } catch { }
}
Write-Host '启动未完成，请查看 data/app.log。'
exit 1
