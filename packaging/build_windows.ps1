$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Spec = Join-Path $PSScriptRoot "ShadowingPlayer.spec"
$Libmpv = Join-Path $ProjectRoot "vendor\libmpv\libmpv-2.dll"
$Icon = Join-Path $ProjectRoot "assets\app-icon.ico"
$ModelSource = Join-Path $env:LOCALAPPDATA "ShadowingPlayer\models\faster-whisper-small"
$OutputRoot = Join-Path $ProjectRoot "dist\ShadowingPlayer"
$ModelTarget = Join-Path $OutputRoot "models\faster-whisper-small"

foreach ($RequiredPath in @($Python, $Spec, $Libmpv, $Icon)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Missing packaging input: $RequiredPath"
    }
}

foreach ($ModelFile in @("model.bin", "config.json", "tokenizer.json")) {
    $RequiredModelFile = Join-Path $ModelSource $ModelFile
    if (-not (Test-Path -LiteralPath $RequiredModelFile)) {
        throw "Incomplete faster-whisper small model: $RequiredModelFile"
    }
}

$Ffmpeg = (Get-Command ffmpeg.exe -ErrorAction Stop).Source
$Ffprobe = (Get-Command ffprobe.exe -ErrorAction Stop).Source
if ((Split-Path $Ffmpeg -Parent) -ne (Split-Path $Ffprobe -Parent)) {
    throw "ffmpeg.exe and ffprobe.exe must be in the same directory"
}
$env:SHADOWING_FFMPEG_DIR = Split-Path $Ffmpeg -Parent

Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller --noconfirm --clean $Spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code: $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$Executable = Join-Path $OutputRoot "ShadowingPlayer.exe"
if (-not (Test-Path -LiteralPath $Executable)) {
    throw "Packaged executable not found: $Executable"
}

if (Test-Path -LiteralPath $ModelTarget) {
    $ResolvedTarget = [IO.Path]::GetFullPath($ModelTarget)
    $ResolvedOutput = [IO.Path]::GetFullPath($OutputRoot)
    if (-not $ResolvedTarget.StartsWith($ResolvedOutput, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean a model path outside the output directory: $ResolvedTarget"
    }
    Remove-Item -LiteralPath $ModelTarget -Recurse -Force
}
New-Item -ItemType Directory -Path $ModelTarget -Force | Out-Null
Copy-Item -Path (Join-Path $ModelSource "*") -Destination $ModelTarget -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README.txt") -Destination $OutputRoot -Force

foreach ($OutputFile in @(
    $Executable,
    (Join-Path $OutputRoot "_internal\assets\app-icon.ico"),
    (Join-Path $OutputRoot "_internal\vendor\libmpv\libmpv-2.dll"),
    (Join-Path $OutputRoot "_internal\vendor\ffmpeg\ffmpeg.exe"),
    (Join-Path $OutputRoot "_internal\vendor\ffmpeg\ffprobe.exe"),
    (Join-Path $ModelTarget "model.bin")
)) {
    if (-not (Test-Path -LiteralPath $OutputFile)) {
        throw "Incomplete packaging output: $OutputFile"
    }
}

$Size = (Get-ChildItem -LiteralPath $OutputRoot -File -Recurse | Measure-Object Length -Sum).Sum
Write-Host ("Package complete: {0}" -f $OutputRoot)
Write-Host ("Total size: {0:N1} MB" -f ($Size / 1MB))
