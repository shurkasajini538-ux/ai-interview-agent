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
$studioNpm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $studioNpm) { throw '请安装 Node.js 24 LTS，重新打开窗口后再次运行安装依赖。' }
Push-Location (Join-Path $PSScriptRoot 'frontend')
try {
    & $studioNpm.Source ci
    if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败，请检查网络后重试。' }
    & $studioNpm.Source run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败，请保留日志。' }
} finally { Pop-Location }
Write-Host '安装和前端构建完成，可以双击「启动面试工坊.cmd」。'
