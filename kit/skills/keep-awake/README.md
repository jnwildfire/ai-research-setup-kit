# keep-awake

A skill for jobs that run while you are away: the computer stays awake, keeps running with the lid
closed, and the job pauses before the battery runs out. You start it yourself (`/keep-awake`); it
never runs by surprise. Guide 04 explains where it fits.

| File | What it is |
|---|---|
| `SKILL.md` | the procedure the agent follows: check the power, start the keeper, report, restore at the end |
| `scripts/keep_awake.ps1` | the keeper for Windows (PowerShell 7 or Windows PowerShell 5.1) |
| `macOS.md` | the same three parts on a Mac, as a note: `caffeinate`, `pmset`, a battery loop |

## What the keeper does on Windows

1. **No idle sleep.** It asks Windows for "system required" (`SetThreadExecutionState`), the way a
   media player does. The screen still turns off as usual, and Windows returns to its normal rules
   as soon as the keeper ends.
2. **The lid.** It reads the lid-close action, saves it in `~/.claude/keep-awake/lid.json`, sets it
   to "Do nothing" on mains and on battery (`powercfg /setacvalueindex` and `/setdcvalueindex` on
   `SUB_BUTTONS LIDACTION`), and puts the saved values back when it ends. If it is killed before
   it can, `keep_awake.ps1 -Restore` puts them back, and `-Status` says when that is needed.
3. **The battery.** Once a minute it reads the power source and the charge
   (`GetSystemPowerStatus`, which states plainly whether mains power is connected; `Win32_Battery`
   gives a status code that has to be interpreted and can read "low" instead of "discharging").
   On battery at 20 % or less it writes `~/.claude/keep-awake/pause`, and the guard refuses every
   action it sees with "paused: battery at N %, connect power or say continue". Connecting power,
   or the file `continue`, lifts the pause.

Why the lid matters: a keeper that only asks for "system required" was running on the author's
laptop when it slept twice in one evening on battery. The event log showed both standbys starting
the moment the lid was closed (Kernel-Power event 506, lid state closed). Closing the lid is a
request to sleep, which no "stay awake" request overrides; only the lid-close action does.

## Tested on

A Windows 11 laptop with Modern Standby, in November 2026, from a session that was **not
elevated**: `powercfg` changed and restored the lid action without administrator rights. The lid
action is a hidden setting on that laptop, so the keeper reads it with `powercfg /qh`. The test, run
twice: before 0/1 (mains "Do nothing", battery "Sleep"); 0/0 while the keeper ran; 0/1 after the
stop file; and 0/1 again after the keeper was killed and `-Restore` ran. A second start while one
keeper runs changes nothing. The battery path was tested with `-SimulateFile` (the laptop stayed on
mains): pause flag at 15 %, the guard refusing a shell command as a separate process with the
message above, the continue file let through and lifting the pause, the pause back at 12 %, and
gone when power returned. Windows PowerShell 5.1 ran the battery loop and the status check too.

On a computer your organisation manages, a policy may set the lid action. The keeper then says so
and leaves it alone; keep the lid open.

## Install

Copy this folder to `~/.claude/skills/keep-awake/`. The pause needs the guard (`kit/hooks/`); its
default `PAUSE_FLAG` and `CONTINUE_FILE` already point at `~/.claude/keep-awake/`.
