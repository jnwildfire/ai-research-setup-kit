# Keep a Windows computer awake while a long job runs, also with the lid closed, and pause the job
# before the battery runs out. Part of the keep-awake skill (SKILL.md, one folder up).
#
# While it runs:
#   1. It asks Windows for "system required" (SetThreadExecutionState), so the computer does not
#      fall asleep when idle. The screen still turns off as usual.
#   2. It sets the lid-close action to "Do nothing", on mains and on battery, and puts the previous
#      values back when it ends. They are saved in lid.json first, so -Restore can put them back if
#      this script was killed before it could.
#   3. It reads the battery once a minute. On battery at LowBattery percent or less it writes a pause
#      flag, which the guard hook (kit/hooks/guard.py) reads to refuse every action with "paused:
#      battery at N %, connect power or say continue". Power back, or the continue file, ends it.
#
# Start it as a background command, so it lives as long as the session:
#   pwsh -NoProfile -File keep_awake.ps1
#   (Windows PowerShell 5.1: powershell -NoProfile -ExecutionPolicy Bypass -File keep_awake.ps1)
# Stop it; the lid action is restored and the pause lifted within two seconds:
#   New-Item -ItemType File -Force "$HOME/.claude/keep-awake/stop"
# Also:
#   keep_awake.ps1 -Status     power source, battery, lid action, a keeper running, a pause
#   keep_awake.ps1 -Restore    put the saved lid action back, after a crash
#
# What it cannot do: stop a sleep that the power button or a critical battery asks for, or change a
# lid action that your organisation sets by policy (it says so). A closed laptop in a bag gets hot:
# with the lid action at "Do nothing" it keeps running there.

param(
    [switch]$Status,
    [switch]$Restore,
    [switch]$KeepLid,              # leave the lid-close action as it is
    [int]$LowBattery = 20,         # percent on battery at which the job is paused
    [double]$MaxHours = 20,        # stop by itself after this long
    [int]$IntervalSeconds = 60,    # how often the battery is read
    [string]$StateDir = (Join-Path $HOME '.claude/keep-awake'),
    [string]$SimulateFile = ''     # tests only: a file holding "battery 15" or "ac 80" replaces the reading
)

$ErrorActionPreference = 'Stop'
$LidNames = @{ 0 = 'Do nothing'; 1 = 'Sleep'; 2 = 'Hibernate'; 3 = 'Shut down' }
$LidPolicy = 'HKLM:\SOFTWARE\Policies\Microsoft\Power\PowerSettings\5ca83367-6e45-459f-a27b-476b1d01c936'
$Files = @{}
foreach ($n in 'stop', 'pause', 'continue', 'lid.json', 'keeper.pid') { $Files[$n] = Join-Path $StateDir $n }

Add-Type -Namespace KeepAwake -Name Native -MemberDefinition @'
[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);
[StructLayout(LayoutKind.Sequential)] public struct PowerStatus {
    public byte ACLineStatus; public byte BatteryFlag; public byte BatteryLifePercent; public byte SystemStatusFlag;
    public int BatteryLifeTime; public int BatteryFullLifeTime; }
[DllImport("kernel32.dll")] public static extern bool GetSystemPowerStatus(out PowerStatus status);
'@
$ES_CONTINUOUS = [uint32]2147483648    # 0x80000000: the request holds until it is cleared
$ES_SYSTEM_REQUIRED = [uint32]1        # 0x00000001: no idle sleep; the display may still turn off

function Get-Power {
    # GetSystemPowerStatus says plainly whether mains power is connected; Win32_Battery's status
    # code needs interpreting and may read "low" or "critical" instead of "discharging".
    if ($SimulateFile) {
        $kind, $pct = (Get-Content $SimulateFile -TotalCount 1).Trim() -split '\s+'
        return [pscustomobject]@{ HasBattery = $true; OnBattery = ($kind -eq 'battery'); Percent = [int]$pct }
    }
    $s = New-Object KeepAwake.Native+PowerStatus
    [void][KeepAwake.Native]::GetSystemPowerStatus([ref]$s)
    $pct = $null
    if ($s.BatteryLifePercent -le 100) { $pct = [int]$s.BatteryLifePercent }
    [pscustomobject]@{ HasBattery = (($s.BatteryFlag -band 128) -eq 0); OnBattery = ($s.ACLineStatus -eq 0); Percent = $pct }
}

function Format-Power($p) {
    if (-not $p.HasBattery) { return 'mains power, no battery' }
    $source = if ($p.OnBattery) { 'on battery' } else { 'on mains power' }
    "$source, battery at $($p.Percent) %"
}

function Get-Scheme {
    if ((powercfg /getactivescheme | Out-String) -match '[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}') { return $Matches[0] }
    throw 'powercfg did not report an active power scheme'
}

function Get-Lid([string]$Scheme) {
    # /qh also lists settings the power plan hides, which the lid action is on some computers.
    # The last two hexadecimal values are the mains and the battery setting, in any language.
    foreach ($q in '/qh', '/q') {
        try { $out = powercfg $q $Scheme SUB_BUTTONS LIDACTION 2>$null | Out-String } catch { continue }
        $hex = [regex]::Matches($out, '0x([0-9a-fA-F]{8})')
        if ($hex.Count -ge 2) {
            return [pscustomobject]@{
                Scheme = $Scheme
                AC = [Convert]::ToInt32($hex[$hex.Count - 2].Groups[1].Value, 16)
                DC = [Convert]::ToInt32($hex[$hex.Count - 1].Groups[1].Value, 16)
            }
        }
    }
    return $null
}

function Format-Lid($l) { "mains: $($LidNames[[int]$l.AC]), battery: $($LidNames[[int]$l.DC])" }

function Set-Lid([string]$Scheme, [int]$AC, [int]$DC) {
    powercfg /setacvalueindex $Scheme SUB_BUTTONS LIDACTION $AC
    if ($LASTEXITCODE) { throw "powercfg could not set the lid action on mains (exit $LASTEXITCODE)" }
    powercfg /setdcvalueindex $Scheme SUB_BUTTONS LIDACTION $DC
    if ($LASTEXITCODE) { throw "powercfg could not set the lid action on battery (exit $LASTEXITCODE)" }
    powercfg /setactive SCHEME_CURRENT    # apply the change to the plan in use
}

function Restore-Lid {
    if (-not (Test-Path $Files['lid.json'])) { return 'lid action: nothing saved, nothing to restore' }
    $saved = Get-Content $Files['lid.json'] -Raw | ConvertFrom-Json
    Set-Lid $saved.Scheme $saved.AC $saved.DC
    $now = Get-Lid $saved.Scheme
    if ($now -and $now.AC -eq $saved.AC -and $now.DC -eq $saved.DC) {
        Remove-Item $Files['lid.json']
        return "lid action restored ($(Format-Lid $now))"
    }
    "lid action NOT restored: it reads ($(Format-Lid $now)), it should read ($(Format-Lid $saved)). lid.json is kept; run -Restore again, or set it in the Control Panel's power options."
}

function Get-Keeper {
    if (-not (Test-Path $Files['keeper.pid'])) { return $null }
    $id = Get-Content $Files['keeper.pid'] -TotalCount 1
    if ($id -and (Get-Process -Id $id -ErrorAction SilentlyContinue)) { return $id }
    return $null
}

if ($Status) {
    "power: $(Format-Power (Get-Power))"
    $lid = Get-Lid (Get-Scheme)
    if ($lid) { "lid action: $(Format-Lid $lid)" } else { 'lid action: not readable with powercfg' }
    if (Test-Path $LidPolicy) { 'lid action: set by an organisation policy; this script cannot change it' }
    $id = Get-Keeper
    if ($id) { "keeper: running (process $id)" } else { 'keeper: not running' }
    if ((Test-Path $Files['lid.json']) -and -not $id) { 'lid.json is left over from a keeper that did not finish: run -Restore' }
    if (Test-Path $Files['pause']) { "pause flag: present (battery at $((Get-Content $Files['pause'] -TotalCount 1)) %)" }
    if (Test-Path $Files['continue']) { 'continue file: present' }
    exit 0
}

if ($Restore) {
    if (Get-Keeper) { 'a keeper is running; stop it with the stop file instead, it restores the lid action itself'; exit 1 }
    Restore-Lid
    exit 0
}

$id = Get-Keeper
if ($id) { "keep-awake is already running (process $id); nothing changed"; exit 0 }
New-Item -ItemType Directory -Force $StateDir | Out-Null
Set-Content $Files['keeper.pid'] $PID
Remove-Item $Files['stop'], $Files['pause'], $Files['continue'] -ErrorAction SilentlyContinue

$power = Get-Power
"power: $(Format-Power $power)"
if ($power.HasBattery -and $power.OnBattery) {
    "WARNING: on battery. The job pauses at $LowBattery %; connect power for a long job."
}

if ([KeepAwake.Native]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED) -eq 0) {
    Remove-Item $Files['keeper.pid'] -ErrorAction SilentlyContinue
    'keep-awake FAILED: Windows refused the request to stay awake'
    exit 1
}
'idle sleep: off while this runs (the screen still turns off as usual)'

if (-not $KeepLid) {
    try {
        if (Test-Path $LidPolicy) { 'WARNING: an organisation policy sets the lid action; it may override this change. Keep the lid open.' }
        $scheme = Get-Scheme
        if (Test-Path $Files['lid.json']) {
            'lid.json from an earlier keeper found: its values are kept as the ones to restore'
        } else {
            $orig = Get-Lid $scheme
            if (-not $orig) { throw 'the lid action is not readable with powercfg' }
            $orig | ConvertTo-Json | Set-Content $Files['lid.json']
        }
        $saved = Get-Content $Files['lid.json'] -Raw | ConvertFrom-Json
        Set-Lid $scheme 0 0
        $now = Get-Lid $scheme
        if (-not $now -or $now.AC -ne 0 -or $now.DC -ne 0) { throw "the lid action reads ($(Format-Lid $now)) after the change" }
        "lid action: was ($(Format-Lid $saved)), now Do nothing on both until the keeper stops"
    } catch {
        "WARNING: lid action not changed ($($_.Exception.Message)). Keep the lid open."
        if (Test-Path $Files['lid.json']) {
            try { Restore-Lid } catch { "WARNING: the saved lid action could not be put back: $($_.Exception.Message). Run -Restore." }
        }
        $KeepLid = $true
    }
}

$until = (Get-Date).AddHours($MaxHours)
"battery watch: pauses the job on battery at $LowBattery % or less"
"keep-awake on at {0:s}, until the stop file or {1:s}. Stop: New-Item -ItemType File -Force '{2}'" -f (Get-Date), $until, $Files['stop']

try {
    while (-not (Test-Path $Files['stop']) -and (Get-Date) -lt $until) {
        $p = Get-Power
        if (-not $p.HasBattery -or -not $p.OnBattery) {
            if (Test-Path $Files['pause']) { "{0:t} power back: pause lifted" -f (Get-Date) }
            Remove-Item $Files['pause'], $Files['continue'] -ErrorAction SilentlyContinue
        } elseif (Test-Path $Files['continue']) {
            if (Test-Path $Files['pause']) {
                Remove-Item $Files['pause']
                "{0:t} continue at {1} %: the job runs on battery until power is back" -f (Get-Date), $p.Percent
            }
        } elseif ($null -ne $p.Percent -and $p.Percent -le $LowBattery) {
            if (-not (Test-Path $Files['pause'])) { "{0:t} battery at {1} %: job paused" -f (Get-Date), $p.Percent }
            Set-Content $Files['pause'] $p.Percent    # rewritten every round; the guard ignores a flag older than ten minutes
        }
        for ($i = 0; $i -lt $IntervalSeconds -and -not (Test-Path $Files['stop']); $i++) { Start-Sleep -Seconds 1 }
    }
} finally {
    [void][KeepAwake.Native]::SetThreadExecutionState($ES_CONTINUOUS)
    if (-not $KeepLid) { Restore-Lid }
    Remove-Item $Files['stop'], $Files['pause'], $Files['continue'], $Files['keeper.pid'] -ErrorAction SilentlyContinue
    "keep-awake off at {0:s}" -f (Get-Date)
}
