# install-adapters.ps1 — Windows adapter installer (junctions when symlinks unavailable)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/install-adapters.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Skills = @("job-application-assistant", "job-scraper", "upskill")
$Commands = @(
    @{ Name = "setup";  Desc = "Build your candidate profile from documents, CV, or interview." },
    @{ Name = "apply";  Desc = "Evaluate fit, draft tailored CV + cover letter, run reviewer, compile PDFs." },
    @{ Name = "scrape"; Desc = "Search SEEK (and optionally LinkedIn) for jobs matching your profile." },
    @{ Name = "expand"; Desc = "Enrich your profile from documents and public online presence." },
    @{ Name = "reset";  Desc = "Reset candidate profile data (destructive; asks for confirmation)." }
)

function Link-SkillDir {
    param([string]$PlatformDir, [string]$Skill)
    $LinkPath = Join-Path $PlatformDir $Skill
    $Target = Join-Path $Root "skills\$Skill"
    New-Item -ItemType Directory -Force -Path $PlatformDir | Out-Null
    if (Test-Path $LinkPath) { Remove-Item -Force -Recurse $LinkPath }
    try {
        New-Item -ItemType SymbolicLink -Path $LinkPath -Target $Target | Out-Null
        Write-Host "  symlink $LinkPath -> $Target"
    } catch {
        cmd /c mklink /J "$LinkPath" "$Target" | Out-Null
        Write-Host "  junction $LinkPath -> $Target"
    }
}

Write-Host "Linking canonical skills..."
foreach ($skill in $Skills) {
    Link-SkillDir ".claude\skills" $skill
    Link-SkillDir ".cursor\skills" $skill
    Link-SkillDir ".agents\skills" $skill
}

Write-Host "Writing Claude command wrappers..."
New-Item -ItemType Directory -Force -Path ".claude\commands" | Out-Null
foreach ($cmd in $Commands) {
    @"
---
description: $($cmd.Desc)
---

Follow the workflow in ``workflows/$($cmd.Name).md``.

## Platform: Claude Code
- Shell: Bash tool
- File edits: Edit tool
- User prompts: AskUserQuestion

User arguments: `$ARGUMENTS
"@ | Set-Content -Encoding UTF8 ".claude\commands\$($cmd.Name).md"
    if ($cmd.Name -eq "apply") {
        Add-Content ".claude\commands\apply.md" "- Reviewer subagent: Agent tool, subagent_type general-purpose"
    }
}

Write-Host "Writing Cursor command skills..."
foreach ($cmd in $Commands) {
    $dir = ".cursor\skills\$($cmd.Name)"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $extra = if ($cmd.Name -eq "apply") { "- Reviewer subagent: Task tool, subagent_type generalPurpose`n" } else { "" }
    @"
---
name: $($cmd.Name)
description: $($cmd.Desc)
disable-model-invocation: true
---

Follow the workflow in ``workflows/$($cmd.Name).md``.

## Platform: Cursor
- Shell: Shell tool
- File edits: StrReplace / Write
- User prompts: AskQuestion
$extra
User arguments: `$ARGUMENTS
"@ | Set-Content -Encoding UTF8 "$dir\SKILL.md"
}

Write-Host "Writing Antigravity workflow wrappers..."
New-Item -ItemType Directory -Force -Path ".agents\workflows" | Out-Null
foreach ($cmd in $Commands) {
    $extra = if ($cmd.Name -eq "apply") { "- Reviewer: DefineSubagent with drafts inline in the prompt`n" } else { "" }
    @"
---
description: $($cmd.Desc)
---

When the user runs /$($cmd.Name), follow ``workflows/$($cmd.Name).md``.

## Platform: Antigravity
- Shell: run_shell_command
- Reviewer: DefineSubagent / parallel subagent (pass drafts inline)
- Verify skills visible via /skills in CLI
$extra
User input: `$ARGUMENTS
"@ | Set-Content -Encoding UTF8 ".agents\workflows\$($cmd.Name).md"
}

Write-Host "Done. See PLATFORMS.md for per-tool usage."
