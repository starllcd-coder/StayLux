param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$issFile = Join-Path $repoRoot "desktop\staylux_installer.iss"
$distExe = Join-Path $repoRoot "dist\StayLux\StayLux.exe"

if (-not (Test-Path $issFile)) {
    throw "Inno Setup script not found: $issFile"
}

if (-not (Test-Path $distExe)) {
    throw "Desktop build not found: $distExe. Build PyInstaller first."
}

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6 first."
}

Write-Host "Using ISCC: $iscc"
Write-Host "Building installer version: $Version"

Push-Location (Join-Path $repoRoot "desktop")
try {
    & $iscc "/DMyAppVersion=$Version" "staylux_installer.iss"
}
finally {
    Pop-Location
}

Write-Host "Installer build completed. Check: dist\installer"
