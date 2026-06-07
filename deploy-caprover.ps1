<#
.SYNOPSIS
    Builds a CapRover deployment tarball for the backend or frontend app.

.DESCRIPTION
    CapRover deploys one app per tarball. Each tarball must contain a
    `captain-definition` file at its root that points at the app's Dockerfile.
    This script generates that file (if missing), then packs the app's source
    into a .tar.gz ready to upload via the CapRover dashboard or:

        caprover deploy -t .\deploy\<app>.tar

    The Postgres database is NOT part of these tarballs - provision it as a
    CapRover one-click app and wire DATABASE_URL via the backend's env vars.

.PARAMETER App
    Which app to package: "backend" or "frontend". Defaults to "backend".

.PARAMETER OutDir
    Directory to write the tarball into. Defaults to ".\deploy".

.EXAMPLE
    .\deploy-caprover.ps1 -App backend
    .\deploy-caprover.ps1 -App frontend
#>
[CmdletBinding()]
param(
    [ValidateSet("backend", "frontend")]
    [string]$App = "backend",

    [string]$OutDir = "deploy"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$appDir = Join-Path $root $App

if (-not (Test-Path $appDir)) {
    throw "App directory not found: $appDir"
}
if (-not (Test-Path (Join-Path $appDir "Dockerfile"))) {
    throw "No Dockerfile in $appDir - CapRover needs one."
}

# tar ships with Windows 10+ (bsdtar). Confirm it's available.
$tar = (Get-Command tar -ErrorAction SilentlyContinue)
if (-not $tar) {
    throw "tar not found on PATH. Windows 10+ ships bsdtar; check your environment."
}

# 1. Ensure a captain-definition exists at the app root.
$capDef = Join-Path $appDir "captain-definition"
if (-not (Test-Path $capDef)) {
    Write-Host "Creating captain-definition in $App ..." -ForegroundColor Cyan
    '{
  "schemaVersion": 2,
  "dockerfilePath": "./Dockerfile"
}' | Set-Content -Path $capDef -Encoding ascii
}

# 2. Decide what to exclude so the tarball stays small and clean.
$excludes = @(
    "--exclude=./.git",
    "--exclude=./deploy",
    "--exclude=*.tar",
    "--exclude=*.tar.gz",
    "--exclude=./.env"          # secrets — set these via CapRover env vars instead
)
if ($App -eq "frontend") {
    $excludes += "--exclude=./node_modules"
    $excludes += "--exclude=./build"
}
if ($App -eq "backend") {
    $excludes += "--exclude=./__pycache__"
    $excludes += "--exclude=*.pyc"
    $excludes += "--exclude=./data"
    $excludes += "--exclude=./.venv"
}

# 3. Build the tarball.
$outAbs = Join-Path $root $OutDir
if (-not (Test-Path $outAbs)) { New-Item -ItemType Directory -Path $outAbs | Out-Null }
$tarPath = Join-Path $outAbs "$App.tar"

Write-Host "Packing $App -> $tarPath" -ForegroundColor Cyan
# Run tar from inside the app dir so paths in the archive are relative to its root.
Push-Location $appDir
try {
    tar -czf $tarPath $excludes -C $appDir .
}
finally {
    Pop-Location
}

$sizeMB = [math]::Round((Get-Item $tarPath).Length / 1MB, 2)
Write-Host "Done: $tarPath ($sizeMB MB)" -ForegroundColor Green
Write-Host ""
Write-Host "Deploy it with either:" -ForegroundColor Yellow
Write-Host "  - CapRover dashboard -> App -> Deployment -> Upload tarball"
Write-Host "  - CLI:  caprover deploy -t `"$tarPath`""
