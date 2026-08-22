<#
.SYNOPSIS
    Builds the GameSpeedUnlocked mod and copies it into the game's Mods folder.

.EXAMPLE
    .\build.ps1
    .\build.ps1 -GameDir "D:\SteamLibrary\steamapps\common\Farthest Frontier"
#>
[CmdletBinding()]
param(
    [string]$GameDir = "C:\games\Farthest Frontier",
    [string]$Configuration = "Release",
    [switch]$NoDeploy
)

$ErrorActionPreference = "Stop"

$project = Join-Path $PSScriptRoot "src\GameSpeedUnlocked\GameSpeedUnlocked.csproj"
$modsDir = Join-Path $GameDir "Mods"

if (-not (Test-Path $modsDir)) {
    throw "Mods folder not found at '$modsDir'. Is MelonLoader installed for this game?"
}

$running = Get-Process -Name "Farthest Frontier" -ErrorAction SilentlyContinue
if ($running) {
    throw "The game is running - close it first, otherwise the mod DLL is locked."
}

dotnet build $project -c $Configuration -p:GameDir="$GameDir" -v minimal
if ($LASTEXITCODE -ne 0) { throw "Build failed." }

$dll = Join-Path $PSScriptRoot "src\GameSpeedUnlocked\bin\$Configuration\GameSpeedUnlocked.dll"
if (-not (Test-Path $dll)) { throw "Built DLL not found at '$dll'." }

if ($NoDeploy) {
    Write-Host "Built: $dll (not deployed)"
    return
}

Copy-Item $dll -Destination $modsDir -Force
Write-Host "Deployed to $(Join-Path $modsDir 'GameSpeedUnlocked.dll')"
