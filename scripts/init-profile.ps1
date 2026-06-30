# init-profile.ps1 — seed gitignored profile workspace from tracked examples/
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/init-profile.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/init-profile.ps1 -Force

param([switch]$Force)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Examples = Join-Path $Root "examples\profile"

if (-not (Test-Path (Join-Path $Examples "skills"))) {
    Write-Error "Missing $Examples\skills — run from repo root after clone."
}

function Copy-TreeIfNeeded {
    param(
        [string]$Src,
        [string]$Dest,
        [string]$MarkerRelative,
        [string]$Label
    )
    $marker = Join-Path $Dest $MarkerRelative
    if (-not $Force -and (Test-Path $marker)) {
        Write-Host "  $Label already present — skipping (use -Force to overwrite)"
        return
    }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    Copy-Item -Path (Join-Path $Src "*") -Destination $Dest -Recurse -Force
    Write-Host "  seeded $Label from examples/profile/"
}

Write-Host "Initializing local profile workspace..."
Copy-TreeIfNeeded -Src (Join-Path $Examples "skills") -Dest (Join-Path $Root "skills") `
    -MarkerRelative "job-application-assistant\SKILL.md" -Label "skills/"

$agents = Join-Path $Root "AGENTS.md"
if ($Force -or -not (Test-Path $agents)) {
    Copy-Item (Join-Path $Examples "AGENTS.example.md") $agents -Force
    Write-Host "  seeded AGENTS.md"
} else {
    Write-Host "  AGENTS.md already present — skipping (use -Force to overwrite)"
}

$claude = Join-Path $Root "CLAUDE.md"
if (-not (Test-Path $claude)) {
    try {
        New-Item -ItemType SymbolicLink -Path $claude -Target "AGENTS.md" | Out-Null
    } catch {
        cmd /c mklink "$claude" "AGENTS.md" | Out-Null
    }
    Write-Host "  linked CLAUDE.md -> AGENTS.md"
}

$cvDest = Join-Path $Root "cv\main_example.tex"
if ($Force -or -not (Test-Path $cvDest)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "cv") | Out-Null
    Copy-Item (Join-Path $Examples "cv\main_example.tex") $cvDest -Force
    Write-Host "  seeded cv/main_example.tex"
} else {
    Write-Host "  cv/main_example.tex already present — skipping (use -Force to overwrite)"
}

$cvHtml = Join-Path $Root "cv\main_example.html"
if ($Force -or -not (Test-Path $cvHtml)) {
    Copy-Item (Join-Path $Examples "cv\main_example.html") $cvHtml -Force
    Write-Host "  seeded cv/main_example.html"
}

$configDest = Join-Path $Root "config\document_output.json"
if ($Force -or -not (Test-Path $configDest)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "config") | Out-Null
    Copy-Item (Join-Path $Examples "config\document_output.example.json") $configDest -Force
    Write-Host "  seeded config/document_output.json"
}

Write-Host "Done. Run /setup to populate your candidate profile."
