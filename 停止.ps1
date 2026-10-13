$studioPidPath = Join-Path $PSScriptRoot 'data/server.pid'
if (Test-Path -LiteralPath $studioPidPath) {
    $studioProcessId = [int](Get-Content -LiteralPath $studioPidPath)
    $studioProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $studioProcessId" -ErrorAction SilentlyContinue
    $studioApp = Join-Path $PSScriptRoot 'app.py'
    if ($studioProcess -and $studioProcess.CommandLine.Contains($studioApp)) {
        Stop-Process -Id $studioProcessId
        Remove-Item -LiteralPath $studioPidPath
        Write-Host '面试工坊已停止。练习记录仍保留在 data 文件夹。'
    } else { Write-Host '没有找到本应用的运行进程。' }
} else { Write-Host '没有找到本应用的运行记录。' }
