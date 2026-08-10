#Requires -Version 5.1
<#
.SYNOPSIS
    Serve the Unity base libraries to BepInEx locally, bypassing the corporate firewall.

.DESCRIPTION
    BepInEx be.735 self-generates IL2CPP interop at runtime (handoff §3). To do so it
    downloads the managed Unity base libraries from `UnityBaseLibrariesSource`
    (default https://unity.bepinex.dev/libraries/{VERSION}.zip). On the Primo network the
    DIRECT connection to unity.bepinex.dev is throttled to a trickle and never completes,
    so the game hangs at "Extracting downloaded unity base libraries" with 0% CPU and an
    empty BepInEx/interop/.

    This script serves the libs from 127.0.0.1 (which the game reaches with no proxy/firewall).
    Point BepInEx at it ONCE, launch the game so interop generates, then it's cached on disk
    and subsequent launches need neither this server nor any network.

.USAGE
    1. Ensure build/tools/unity-libs.zip exists (created by gen-interop.ps1).
    2. Run this script (it stays in the foreground serving on 127.0.0.1:8799).
    3. In another shell set, in the game's BepInEx/config/BepInEx.cfg:
         UnityBaseLibrariesSource = http://127.0.0.1:8799/{VERSION}.zip
       (deploy-pack.ps1 sets this automatically for a 'live' target).
    4. Launch the game via Steam; wait ~1-2 min while interop generates (~100 DLLs in
       BepInEx/interop/, high CPU/RAM). Once done, stop this script (Ctrl-C).

.PARAMETER Port
    Listen port (default 8799). Must match the port in UnityBaseLibrariesSource.
#>
param([int]$Port = 8799)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$zip  = Join-Path $root "build\tools\unity-libs.zip"
if (-not (Test-Path $zip)) {
    Write-Error "build/tools/unity-libs.zip not found — run gen-interop.ps1 first."
}

# Serve dir with the zip renamed to the {VERSION}.zip BepInEx requests (Unity 2022.3.62).
$serve = Join-Path $env:TEMP "ek-unity-libs"
New-Item -ItemType Directory -Force -Path $serve | Out-Null
Copy-Item $zip (Join-Path $serve "2022.3.62.zip") -Force

# Prefer python's http.server if available (simple, robust); else a PowerShell HttpListener.
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($py) {
    Write-Host "Serving $serve on http://127.0.0.1:$Port (python http.server). Ctrl-C to stop." -ForegroundColor Green
    & $py -m http.server $Port --bind 127.0.0.1 --directory $serve
} else {
    Write-Host "Serving $serve on http://127.0.0.1:$Port (HttpListener). Ctrl-C to stop." -ForegroundColor Green
    $listener = New-Object System.Net.HttpListener
    $listener.Prefixes.Add("http://127.0.0.1:$Port/")
    $listener.Start()
    try {
        while ($listener.IsListening) {
            $ctx  = $listener.GetContext()
            $name = [System.IO.Path]::GetFileName($ctx.Request.Url.LocalPath)
            $file = Join-Path $serve $name
            if (Test-Path $file) {
                $bytes = [System.IO.File]::ReadAllBytes($file)
                $ctx.Response.ContentType = "application/zip"
                $ctx.Response.ContentLength64 = $bytes.Length
                $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
                Write-Host "  served $name ($($bytes.Length) bytes)"
            } else {
                $ctx.Response.StatusCode = 404
            }
            $ctx.Response.OutputStream.Close()
        }
    } finally { $listener.Stop() }
}
