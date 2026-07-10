# memory-watchdog.ps1 — kills the top memory hog before pagefile thrashing freezes the box.
# Trigger: available RAM below WarnFreeMB -> log; below CritFreeMB AND top process commit
# above KillCommitGB -> Stop-Process -Force (unless whitelisted).
# Installed as scheduled task "MemoryWatchdog" (at logon, highest privileges).
# Log: %LOCALAPPDATA%\memory-watchdog\watchdog.log

param(
    [int]$IntervalSec   = 15,
    [int]$WarnFreeMB    = 6144,   # warn tier: just log
    [int]$CritFreeMB    = 3072,   # kill tier: act
    [int]$KillCommitGB  = 24,     # never kill anything committing less than this
    [int]$CooldownSec   = 90      # min pause between kills
)

$ErrorActionPreference = 'SilentlyContinue'

# Processes we never touch, no matter how big
$NeverKill = @(
    'System','Idle','Memory Compression','Registry','Secure System','smss','csrss',
    'wininit','winlogon','services','lsass','svchost','dwm','explorer','fontdrvhost',
    'sihost','ctfmon','audiodg','spoolsv','MsMpEng','SearchIndexer','RuntimeBroker',
    'vmmem','vmmemWSL','vmwp','powershell','pwsh','taskmgr','Taskmgr'
)

$logDir = Join-Path $env:LOCALAPPDATA 'memory-watchdog'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$log = Join-Path $logDir 'watchdog.log'

function Write-Log([string]$msg) {
    "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg | Add-Content -Path $log
}

# Keep the watchdog itself responsive under memory pressure:
# high CPU priority + pinned minimum working set so it doesn't get paged out.
try {
    $me = Get-Process -Id $PID
    $me.PriorityClass = 'High'
    $me.MinWorkingSet = [IntPtr]::new(150MB)
    $me.MaxWorkingSet = [IntPtr]::new(400MB)
} catch {}

Write-Log "watchdog started (warn<$($WarnFreeMB)MB, kill<$($CritFreeMB)MB & commit>$($KillCommitGB)GB, interval ${IntervalSec}s)"

$lastKill = [DateTime]::MinValue
$lastWarn = [DateTime]::MinValue

while ($true) {
    Start-Sleep -Seconds $IntervalSec

    $os = Get-CimInstance Win32_OperatingSystem
    if (-not $os) { continue }
    $freeMB = [int]($os.FreePhysicalMemory / 1024)

    if ($freeMB -ge $WarnFreeMB) { continue }

    # Top consumers by committed private bytes
    $top = Get-Process |
        Where-Object { $_.PagedMemorySize64 -gt 500MB } |
        Sort-Object PagedMemorySize64 -Descending |
        Select-Object -First 5

    $topStr = ($top | ForEach-Object { "{0}(pid {1})={2:N1}GB" -f $_.ProcessName, $_.Id, ($_.PagedMemorySize64/1GB) }) -join ', '

    if ($freeMB -ge $CritFreeMB) {
        # warn tier: log at most once per 5 min
        if (((Get-Date) - $lastWarn).TotalSeconds -gt 300) {
            Write-Log "WARN free=${freeMB}MB; top: $topStr"
            $lastWarn = Get-Date
        }
        continue
    }

    # critical tier
    Write-Log "CRITICAL free=${freeMB}MB; top: $topStr"

    if (((Get-Date) - $lastKill).TotalSeconds -lt $CooldownSec) { continue }

    $victim = $top |
        Where-Object { $NeverKill -notcontains $_.ProcessName -and $_.PagedMemorySize64 -gt ($KillCommitGB * 1GB) } |
        Select-Object -First 1

    if ($victim) {
        $desc = "{0} (pid {1}, commit {2:N1}GB)" -f $victim.ProcessName, $victim.Id, ($victim.PagedMemorySize64/1GB)
        Write-Log "KILLING $desc"
        Stop-Process -Id $victim.Id -Force
        $lastKill = Get-Date
        # best-effort user notification
        try { msg.exe $env:USERNAME "Memory watchdog killed $desc (free RAM was ${freeMB}MB)" } catch {}
    } else {
        Write-Log "critical, but no process exceeds ${KillCommitGB}GB commit outside whitelist - not killing"
    }
}
