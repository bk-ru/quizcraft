#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Warning "Virtual environment not found at $venvActivate. Using system Python."
}

if (-not (Test-Path (Join-Path $repoRoot ".env"))) {
    Write-Warning "No .env file found. Copy .env.example to .env and edit values."
}

$uvicornArgs = @(
    "backend.app.main:app",
    "--host", $HostName,
    "--port", $Port
)
if (-not $NoReload) {
    $uvicornArgs += "--reload"
}

Write-Host "Starting backend on http://${HostName}:${Port}" -ForegroundColor Cyan
uvicorn @uvicornArgs
