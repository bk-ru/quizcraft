#requires -Version 5.1
[CmdletBinding()]
param(
    [int]$Port = 5500
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $repoRoot "frontend"

if (-not (Test-Path $frontendDir)) {
    throw "Frontend directory not found at $frontendDir"
}

Write-Host "Serving frontend on http://127.0.0.1:$Port" -ForegroundColor Cyan
python -m http.server $Port --directory $frontendDir
