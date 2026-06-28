#Requires -Version 5.1
<#
.SYNOPSIS
    Offline IL2CPP interop assembly generation for Ember Knights (BepInEx 6 IL2CPP).

.DESCRIPTION
    Generates Il2CppInterop proxy assemblies in lib/interop/ without launching the game.
    Required outputs: Assembly-CSharp.dll (game), Il2Cppmscorlib.dll, UnityEngine.*.dll,
    Il2CppInterop.Runtime.dll, Il2CppInterop.Common.dll (from BepInEx 6 pre.2 core).

    Generator version: Il2CppInterop.Generator 1.4.6, which is EXACTLY what BepInEx 6 pre.2
    bundles and uses at game start to generate its own interop. This ensures compile-time
    proxy surface matches the runtime proxy surface.

.PREREQUISITES
    Download these into build/tools/ before running:
      1. Cpp2IL-2022.1.0-pre-release.21-Windows.exe  -> rename to cpp2il.exe
         https://github.com/SamboyCoding/Cpp2IL/releases/tag/2022.1.0-pre-release.21
      2. BepInEx-Unity.IL2CPP-win-x64-6.0.0-pre.2.zip (extract to build/tools/BepInEx-6/)
         https://github.com/BepInEx/BepInEx/releases/tag/v6.0.0-pre.2
      3. Unity base libs 2022.3.62.zip -> extract to build/tools/unity-libs/2022.3.62/
         https://unity.bepinex.dev/libraries/2022.3.62.zip

    NOTE: Il2CppInterop.CLI 1.5.3 is no longer needed. The generator is taken directly
    from the BepInEx 6 pre.2 bundle (core/Il2CppInterop.Generator.dll v1.4.6).

.NOTES
    Tool versions used:
      Cpp2IL:            2022.1.0-pre-release.21 (SamboyCoding/Cpp2IL)
      Il2CppInterop:     1.4.6-ci.426 (from BepInEx 6 pre.2 bundle -- both generator and runtime)
      BepInEx:           6.0.0-pre.2
      Unity base libs:   2022.3.62 (from unity.bepinex.dev)
      Metadata version:  31 (Unity 2022.3.62f3)

    Version alignment: both the generator (step 2) and the runtime DLLs copied to lib/interop/
    (step 3) come from the same BepInEx 6 pre.2 bundle. This ensures the proxy DLL surface
    exactly matches what BepInEx generates at game start.

    IMPORTANT: The Il2CppInterop.CLI exe in the zip is a Linux ELF binary.
    This script does NOT use that CLI; it uses build/gen-interop-host/ instead.
#>

$ErrorActionPreference = "Stop"

$root    = Split-Path $PSScriptRoot -Parent
$tools   = Join-Path $PSScriptRoot "tools"
$work    = Join-Path $PSScriptRoot "work\cpp2il"
$out     = Join-Path $root "lib\interop"
$hostDir = Join-Path $PSScriptRoot "gen-interop-host"
$hostOut = Join-Path $PSScriptRoot "work\gen-interop-host-bin"

$gameDll     = "C:\Program Files (x86)\Steam\steamapps\common\EmberKnights\GameAssembly.dll"
$metaData    = "C:\Program Files (x86)\Steam\steamapps\common\EmberKnights\EmberKnights_64_Data\il2cpp_data\Metadata\global-metadata.dat"
$unityLibs   = Join-Path $tools "unity-libs\2022.3.62"
$cpp2il      = Join-Path $tools "cpp2il.exe"
$bepinexCore = Join-Path $tools "BepInEx-6\BepInEx\core"

# dotnet SDK (use the SDK dotnet, NOT the runtime-only one in Program Files)
$dotnet = "C:\Users\$env:USERNAME\.dotnet\dotnet.exe"
if (-not (Test-Path $dotnet)) {
    $dotnet = (Get-Command dotnet -ErrorAction Stop).Source
}

# Validate prerequisites
foreach ($required in @($gameDll, $metaData, $cpp2il, $unityLibs, $bepinexCore, $hostDir)) {
    if (-not (Test-Path $required)) {
        Write-Error "Missing prerequisite: $required`nSee .PREREQUISITES in this script header."
    }
}

New-Item -ItemType Directory -Force -Path $work, $out, $hostOut | Out-Null

# --- Step 0: Build the GenInteropHost (1.4.6 generator wrapper) ---
Write-Host "[0/3] Building GenInteropHost (Il2CppInterop.Generator 1.4.6 wrapper)..." -ForegroundColor Cyan
$hostCsproj = Join-Path $hostDir "GenInteropHost.csproj"
$buildResult = & $dotnet build $hostCsproj -c Release --nologo -o $hostOut 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host $buildResult
    Write-Error "GenInteropHost build failed (exit $LASTEXITCODE)"
}
$hostDll = Join-Path $hostOut "GenInteropHost.dll"
if (-not (Test-Path $hostDll)) {
    Write-Error "GenInteropHost.dll not found at $hostDll after build"
}
Write-Host "  Built: $hostDll"

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

# --- Step 2: GenInteropHost (Il2CppInterop.Generator 1.4.6): dummy -> interop proxy assemblies ---
Write-Host "[2/3] Il2CppInterop.Generator 1.4.6: generating proxy assemblies..." -ForegroundColor Cyan

# Use cmd wrapper to preserve quoted paths with spaces (gameAssembly path contains Program Files)
$step2Script = "$env:TEMP\gen-interop-host-run.cmd"
@"
@echo off
"$dotnet" "$hostDll" "$work" "$out" "$unityLibs" "$gameDll"
"@ | Set-Content -Path $step2Script -Encoding ASCII

$proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$step2Script`"" -Wait -NoNewWindow -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Error "GenInteropHost (Il2CppInterop.Generator) failed with exit code $($proc.ExitCode)"
}
Write-Host "  Done. Proxy DLLs: $(Get-ChildItem $out -Filter '*.dll' | Measure-Object | Select-Object -Expand Count)"

# --- Step 3: Copy BepInEx 6 runtime DLLs ---
# These must match what BepInEx loads at game time (v1.4.6-ci.426 from BepInEx 6 pre.2).
# The generator (step 2) uses the same 1.4.6 version, ensuring full surface alignment.
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
