$ErrorActionPreference = 'Stop'
$studioVenv = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $studioVenv)) {
    $studioBundled = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $studioBundled) {
        & $studioBundled -m venv (Join-Path $PSScriptRoot '.venv')
    } else {
        py -3.12 -m venv (Join-Path $PSScriptRoot '.venv')
    }
    if ($LASTEXITCODE -ne 0) { throw '请安装 Python 3.12 后重新运行。' }
}
& $studioVenv -m pip install -r (Join-Path $PSScriptRoot 'requirements.lock.txt')
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败，请检查网络后重试。' }
Write-Host '安装完成，可以双击「启动面试工坊.cmd」。'
