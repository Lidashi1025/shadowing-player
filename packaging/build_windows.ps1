# Build a Windows folder package for Shadowing Player.
# Usage:
#   .\packaging\build_windows.ps1
#   .\packaging\build_windows.ps1 -SkipModel
#   .\packaging\build_windows.ps1 -SkipModel -Zip
param(
    [switch]$SkipModel,
    [switch]$Zip
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Spec = Join-Path $PSScriptRoot "ShadowingPlayer.spec"
$Libmpv = Join-Path $ProjectRoot "vendor\libmpv\libmpv-2.dll"
$Icon = Join-Path $ProjectRoot "assets\app-icon.ico"
$ModelSource = Join-Path $env:LOCALAPPDATA "ShadowingPlayer\models\faster-whisper-small"
$OutputRoot = Join-Path $ProjectRoot "dist\ShadowingPlayer"
$ModelTarget = Join-Path $OutputRoot "models\faster-whisper-small"
$DistRoot = Join-Path $ProjectRoot "dist"

foreach ($RequiredPath in @($Python, $Spec, $Libmpv, $Icon)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Missing packaging input: $RequiredPath"
    }
}

if (-not $SkipModel) {
    foreach ($ModelFile in @("model.bin", "config.json", "tokenizer.json")) {
        $RequiredModelFile = Join-Path $ModelSource $ModelFile
        if (-not (Test-Path -LiteralPath $RequiredModelFile)) {
            throw "Incomplete faster-whisper small model: $RequiredModelFile (or pass -SkipModel)"
        }
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

if (-not $SkipModel) {
    New-Item -ItemType Directory -Path $ModelTarget -Force | Out-Null
    Copy-Item -Path (Join-Path $ModelSource "*") -Destination $ModelTarget -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $ModelTarget -Force | Out-Null
    $ModelReadme = @(
        "This package was built with -SkipModel.",
        "The offline ASR model is downloaded on first transcription,",
        "or place faster-whisper small files here:",
        "  model.bin",
        "  config.json",
        "  tokenizer.json"
    ) -join "`r`n"
    Set-Content -LiteralPath (Join-Path $ModelTarget "README.txt") -Value $ModelReadme -Encoding UTF8
}

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README.txt") -Destination $OutputRoot -Force

$RequiredOutputs = @(
    $Executable,
    (Join-Path $OutputRoot "_internal\assets\app-icon.ico"),
    (Join-Path $OutputRoot "_internal\vendor\libmpv\libmpv-2.dll"),
    (Join-Path $OutputRoot "_internal\vendor\ffmpeg\ffmpeg.exe"),
    (Join-Path $OutputRoot "_internal\vendor\ffmpeg\ffprobe.exe")
)
if (-not $SkipModel) {
    $RequiredOutputs += (Join-Path $ModelTarget "model.bin")
}
foreach ($OutputFile in $RequiredOutputs) {
    if (-not (Test-Path -LiteralPath $OutputFile)) {
        throw "Incomplete packaging output: $OutputFile"
    }
}

$Size = (Get-ChildItem -LiteralPath $OutputRoot -File -Recurse | Measure-Object Length -Sum).Sum
Write-Host ("Package complete: {0}" -f $OutputRoot)
Write-Host ("Total size: {0:N1} MB" -f ($Size / 1MB))

if ($Zip) {
    $Version = & $Python -c "from shadowing_player import __version__; print(__version__)"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Version)) {
        $Version = "dev"
    }
    $Suffix = if ($SkipModel) { "slim" } else { "full" }
    $ZipName = "ShadowingPlayer-windows-x64-v$Version-$Suffix.zip"
    $ZipPath = Join-Path $DistRoot $ZipName
    if (Test-Path -LiteralPath $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }
    Compress-Archive -Path $OutputRoot -DestinationPath $ZipPath -CompressionLevel Optimal
    $ZipSize = (Get-Item -LiteralPath $ZipPath).Length
    Write-Host ("Zip ready: {0} ({1:N1} MB)" -f $ZipPath, ($ZipSize / 1MB))
}
