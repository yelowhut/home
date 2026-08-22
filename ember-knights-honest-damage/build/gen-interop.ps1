#Requires -Version 5.1
<#
.SYNOPSIS
    Offline IL2CPP interop assembly generation for Ember Knights (BepInEx 6 IL2CPP).

.DESCRIPTION
    Generates Il2CppInterop proxy assemblies in lib/interop/ without launching the game.
    Required outputs: Assembly-CSharp.dll (game), Il2Cppmscorlib.dll, UnityEngine.*.dll,
    Il2CppInterop.Runtime.dll, Il2CppInterop.Common.dll (from BepInEx be.735 core).

    Generator version: Il2CppInterop.Generator 1.4.6, which is EXACTLY what BepInEx be.735
    bundles and uses at game start. This ensures the compile-time proxy surface matches
    the runtime proxy surface. The generator's Pass16 xref scan uses the be.735-bundled
    LibCpp2IL (Cpp2IL 2022.1.0-pre-release.19), which supports IL2CPP metadata v31.

    WHY be.735 (not be.697): Ember Knights is metadata v31. be.697 bundles a Cpp2IL
    (2022.1.0.0) that CANNOT read v31, and its BepInEx.Unity.IL2CPP bootstrap crashed
    at game start (BadImageFormatException in Il2CppSystem.String..cctor during delegate
    bridging). be.735 bundles v31-capable Cpp2IL + a revised bootstrap. Il2CppInterop
    (Generator/Runtime/Common) is byte-identical between be.697 and be.735 (both 1.4.6-ci.426),
    so the plugin's interop ABI is unchanged.

.PREREQUISITES
    Download these into build/tools/ before running:
      1. Cpp2IL-2022.1.0-pre-release.21-Windows.exe  -> rename to cpp2il.exe
         https://github.com/SamboyCoding/Cpp2IL/releases/tag/2022.1.0-pre-release.21
         (used to produce the dummy assemblies; v31-capable)
      2. BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.735+5fef357.zip -> extract to build/tools/BepInEx-be735/
         https://builds.bepinex.dev/projects/bepinex_be/735/
      3. Unity base libs 2022.3.62.zip -> extract to build/tools/unity-libs/2022.3.62/
         https://unity.bepinex.dev/libraries/2022.3.62.zip

    NOTE: Il2CppInterop.CLI is NOT used. The generator is taken directly from the
    BepInEx be.735 bundle (core/Il2CppInterop.Generator.dll v1.4.6) via build/gen-interop-host/.

.NOTES
    Tool versions used:
      Cpp2IL (dummies):  2022.1.0-pre-release.21 (SamboyCoding/Cpp2IL, v31-capable)
      LibCpp2IL (Pass16): 2022.1.0-pre-release.19 (from be.735 bundle, v31-capable)
      Il2CppInterop:     1.4.6-ci.426 (from be.735 bundle -- both generator and runtime)
      BepInEx:           6.0.0-be.735
      Unity base libs:   2022.3.62 (from unity.bepinex.dev)
      Metadata version:  31 (Unity 2022.3.62f3)

    Version alignment: both the generator (step 2) and the runtime DLLs copied to lib/interop/
    (step 3) come from the same BepInEx be.735 bundle.

    To deploy: after this script, build the plugin and run build/deploy-pack.ps1 -Target dist|live.
#>

$ErrorActionPreference = "Stop"

$root    = Split-Path $PSScriptRoot -Parent
$tools   = Join-Path $PSScriptRoot "tools"
$work    = Join-Path $PSScriptRoot "work\cpp2il"
$out     = Join-Path $root "lib\interop"
$hostDir = Join-Path $PSScriptRoot "gen-interop-host"
$hostOut = Join-Path $PSScriptRoot "work\gen-interop-host-bin"

# Game root: override with env var EMBERKNIGHTS_DIR, else probe known Steam library paths.
# (Steam libraries differ per machine: Program Files on the original PC, C:\games\steam here.)
$gameRoot = $env:EMBERKNIGHTS_DIR
if (-not $gameRoot) {
    foreach ($cand in @(
        "C:\Program Files (x86)\Steam\steamapps\common\EmberKnights",
        "C:\games\steam\steamapps\common\EmberKnights")) {
        if (Test-Path (Join-Path $cand "GameAssembly.dll")) { $gameRoot = $cand; break }
    }
}
if (-not $gameRoot) { Write-Error "EmberKnights install not found. Set `$env:EMBERKNIGHTS_DIR." }
Write-Host "Game root: $gameRoot" -ForegroundColor DarkCyan

$gameDll     = Join-Path $gameRoot "GameAssembly.dll"
$metaData    = Join-Path $gameRoot "EmberKnights_64_Data\il2cpp_data\Metadata\global-metadata.dat"
$unityLibs   = Join-Path $tools "unity-libs\2022.3.62"
$cpp2il      = Join-Path $tools "cpp2il.exe"
# be.735 bundles a v31-capable Cpp2IL/LibCpp2IL (pre-release.19). be.697's plain
# Cpp2IL 2022.1.0.0 does NOT support metadata v31. The GenInteropHost project
# references this bundle's core for the generator + LibCpp2IL (see its .csproj).
$bepinexCore = Join-Path $tools "BepInEx-be735\BepInEx\core"

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

# --- Step 3: Copy BepInEx runtime DLLs ---
# These must match what BepInEx loads at game time (v1.4.6-ci.426 from BepInEx be.735).
# The generator (step 2) uses the same 1.4.6 version, ensuring full surface alignment.
Write-Host "[3/3] Copying Il2CppInterop runtime DLLs from BepInEx be.735 core..." -ForegroundColor Cyan
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
