#Requires -Version 5.1
<#
.SYNOPSIS
    Offline IL2CPP interop assembly generation for Ember Knights (BepInEx 6 IL2CPP).

.DESCRIPTION
    Generates Il2CppInterop proxy assemblies in lib/interop/ without launching the game.
    Required outputs: Assembly-CSharp.dll (game), Il2Cppmscorlib.dll, UnityEngine.*.dll,
    Il2CppInterop.Runtime.dll, Il2CppInterop.Common.dll (from BepInEx 6 pre.2 core).

.PREREQUISITES
    Download these into build/tools/ before running:
      1. Cpp2IL-2022.1.0-pre-release.21-Windows.exe  → rename to cpp2il.exe
         https://github.com/SamboyCoding/Cpp2IL/releases/tag/2022.1.0-pre-release.21
      2. Il2CppInterop.CLI.1.5.3.zip (extract to build/tools/Il2CppInterop-1.5.3/)
         https://github.com/BepInEx/Il2CppInterop/releases/tag/v1.5.3
      3. BepInEx-Unity.IL2CPP-win-x64-6.0.0-pre.2.zip (extract to build/tools/BepInEx-6/)
         https://github.com/BepInEx/BepInEx/releases/tag/v6.0.0-pre.2
      4. Unity base libs 2022.3.62.zip → extract to build/tools/unity-libs/2022.3.62/
         https://unity.bepinex.dev/libraries/2022.3.62.zip

.NOTES
    Tool versions used:
      Cpp2IL:           2022.1.0-pre-release.21 (SamboyCoding/Cpp2IL)
      Il2CppInterop CLI: 1.5.3 (BepInEx/Il2CppInterop)
      BepInEx:          6.0.0-pre.2 (Il2CppInterop.Runtime 1.4.6-ci.426)
      Unity base libs:  2022.3.62 (from unity.bepinex.dev)
      Metadata version: 31 (Unity 2022.3.62f3)

    Il2CppInterop.Runtime.dll / Il2CppInterop.Common.dll are copied FROM
    the BepInEx 6 pre.2 bundle (v1.4.6), which is the runtime BepInEx will
    load at game time. The generator (v1.5.3) produces the proxy DLLs;
    the runtime DLLs come from the deploy target, not the generator.

    IMPORTANT: The Il2CppInterop.CLI exe in the zip is a Linux ELF binary.
    Use the .dll with "dotnet" on Windows (see step 2 below).
#>

$ErrorActionPreference = "Stop"

$root    = Split-Path $PSScriptRoot -Parent
$tools   = Join-Path $PSScriptRoot "tools"
$work    = Join-Path $PSScriptRoot "work\cpp2il"
$out     = Join-Path $root "lib\interop"

$gameDll   = "C:\Program Files (x86)\Steam\steamapps\common\EmberKnights\GameAssembly.dll"
$metaData  = "C:\Program Files (x86)\Steam\steamapps\common\EmberKnights\EmberKnights_64_Data\il2cpp_data\Metadata\global-metadata.dat"
$unityLibs = Join-Path $tools "unity-libs\2022.3.62"
$cpp2il    = Join-Path $tools "cpp2il.exe"
$cliDll    = Join-Path $tools "Il2CppInterop-1.5.3\net6.0\publish\Il2CppInterop.CLI.dll"
$bepinexCore = Join-Path $tools "BepInEx-6\BepInEx\core"

# dotnet SDK (use the SDK dotnet, NOT the runtime-only one in Program Files)
$dotnet = "C:\Users\$env:USERNAME\.dotnet\dotnet.exe"
if (-not (Test-Path $dotnet)) {
    $dotnet = (Get-Command dotnet -ErrorAction Stop).Source
}

# Validate prerequisites
foreach ($required in @($gameDll, $metaData, $cpp2il, $cliDll, $unityLibs, $bepinexCore)) {
    if (-not (Test-Path $required)) {
        Write-Error "Missing prerequisite: $required`nSee .PREREQUISITES in this script header."
    }
}

New-Item -ItemType Directory -Force -Path $work, $out | Out-Null

# --- Step 1: Cpp2IL: GameAssembly.dll + global-metadata.dat -> dummy assemblies ---
Write-Host "[1/3] Cpp2IL: extracting dummy assemblies..." -ForegroundColor Cyan

# NOTE: Paths with spaces must be handled via a cmd wrapper to avoid argument splitting.
$step1Script = "$env:TEMP\cpp2il-run.cmd"
@"
@echo off
"$cpp2il" --force-binary-path "$gameDll" --force-metadata-path "$metaData" --force-unity-version 2022.3.62 --output-as dummydll --output-to "$work"
"@ | Set-Content -Path $step1Script -Encoding ASCII

$proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$step1Script`"" -Wait -NoNewWindow -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Error "Cpp2IL failed with exit code $($proc.ExitCode)"
}
Write-Host "  Done. Dummy DLLs: $(Get-ChildItem $work -Filter '*.dll' | Measure-Object | Select-Object -Expand Count)"

# --- Step 2: Il2CppInterop.Generator: dummy -> interop proxy assemblies ---
Write-Host "[2/3] Il2CppInterop.Generator: generating proxy assemblies..." -ForegroundColor Cyan

$step2Script = "$env:TEMP\il2cppinterop-run.cmd"
@"
@echo off
"$dotnet" "$cliDll" generate --input "$work" --output "$out" --unity "$unityLibs" --game-assembly "$gameDll"
"@ | Set-Content -Path $step2Script -Encoding ASCII

$proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$step2Script`"" -Wait -NoNewWindow -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Error "Il2CppInterop.Generator failed with exit code $($proc.ExitCode)"
}
Write-Host "  Done. Proxy DLLs: $(Get-ChildItem $out -Filter '*.dll' | Measure-Object | Select-Object -Expand Count)"

# --- Step 3: Copy BepInEx 6 runtime DLLs ---
# These must match what BepInEx loads at game time (v1.4.6-ci.426 from BepInEx 6 pre.2).
Write-Host "[3/3] Copying Il2CppInterop runtime DLLs from BepInEx 6 pre.2 core..." -ForegroundColor Cyan
foreach ($dll in @("Il2CppInterop.Runtime.dll", "Il2CppInterop.Common.dll")) {
    $src = Join-Path $bepinexCore $dll
    Copy-Item $src $out -Force
    Write-Host "  Copied: $dll"
}

Write-Host ""
Write-Host "Interop assemblies written to: $out" -ForegroundColor Green
Write-Host "Key files:"
@("Assembly-CSharp.dll", "Il2Cppmscorlib.dll", "UnityEngine.CoreModule.dll",
  "Il2CppInterop.Runtime.dll", "Il2CppInterop.Common.dll") | ForEach-Object {
    $path = Join-Path $out $_
    if (Test-Path $path) {
        Write-Host "  [OK] $_ ($((Get-Item $path).Length) bytes)"
    } else {
        Write-Host "  [MISSING] $_" -ForegroundColor Red
    }
}
