$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$studioRoot = Split-Path $PSScriptRoot
$studioOut = Join-Path $studioRoot 'tmp/video'
New-Item -ItemType Directory -Path $studioOut -Force | Out-Null
$studioChapters = Get-Content -LiteralPath (Join-Path $studioRoot 'docs/演示脚本.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$studioVoice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$studioVoice.SelectVoice('Microsoft Huihui Desktop')
$studioVoice.Rate = 0
try {
  for ($chapter=0; $chapter -lt $studioChapters.Count; $chapter++) {
    $studioVoice.SetOutputToWaveFile((Join-Path $studioOut ("chapter-$chapter.wav")))
    $studioVoice.Speak($studioChapters[$chapter].text)
    $studioVoice.SetOutputToNull()
  }
} finally { $studioVoice.Dispose() }
Write-Host '普通话合成旁白已生成。'
