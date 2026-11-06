---
name: keep-awake
description: Keeps the computer working through a long or unattended job, also with the lid closed, and pauses the job on battery at 20 %. Triggers "/keep-awake", "keep awake", "night shift". Not for scheduling a job.
disable-model-invocation: true
---

# Keep awake

A laptop that sleeps stops every agent and job on it without a word. This skill keeps it awake
(no idle sleep), keeps it running when the lid is closed (the lid-close action set to "Do nothing"
and put back afterwards), and pauses the job before the battery runs out. On Windows the script
`scripts/keep_awake.ps1` does all three; on macOS see `macOS.md`. The pause is enforced by the
guard hook (`kit/hooks/guard.py`); without the guard, the pause flag is only a sign.

The script lives at `~/.claude/skills/keep-awake/scripts/keep_awake.ps1` when installed for the
person, or under the project's `.claude/skills/` when installed there. Run it with
`pwsh -NoProfile -File <script>`, or with Windows PowerShell 5.1 as
`powershell -NoProfile -ExecutionPolicy Bypass -File <script>`.

## Procedure

1. **Check first.** Run the script with `-Status` and report the power source and the battery
   level. On battery, say so plainly: the job pauses at 20 %, and a long job wants mains power.
   If the status reports a left-over `lid.json`, run `-Restore` first and say what it put back.
2. **Say what will change, and ask once.** The lid-close action goes to "Do nothing" on mains and
   on battery until the keeper stops, so the laptop keeps running with the lid closed: on a desk,
   not in a bag, where it would get hot. If the person declines, add `-KeepLid` and tell them to
   keep the lid open.
3. **Start the keeper as a background command** (in Claude Code, the Bash or PowerShell tool with
   `run_in_background`), so it lives as long as the session. Read its first lines: power, idle
   sleep, the lid action before and after, the battery watch.
4. **Report in four lines**: idle sleep off; the lid action from what to what (or left alone, and
   why); the battery watch at 20 %, where the guard pauses the job; how to stop (say "stop keep
   awake", or create the file `~/.claude/keep-awake/stop`).
5. **When the guard refuses with "paused: battery at N %"**, stop the work and tell the person.
   If they say continue, create the empty file `~/.claude/keep-awake/continue` with the Write tool:
   it is the one action the guard lets through, and the job then runs on battery until power is
   back. Connecting power ends the pause by itself within a minute.
6. **At the end of the work**, or when the person says stop: create the stop file, wait for the
   keeper's last lines ("lid action restored", "keep-awake off"), then run `-Status` and confirm
   that the lid action is what step 1 showed. If the keeper ended any other way (killed, the
   session closed, Claude Code stopped it because memory ran short), run `-Restore` and confirm
   with `-Status`.

## Checks

- Before the report of step 4: the lid action read back from Windows is the one the keeper says it
  set. The keeper checks this itself and says "WARNING: lid action not changed" otherwise.
- At the end: `-Status` shows the lid action of step 1 and "keeper: not running". A lid action
  left at "Do nothing" is a fault to report, not a detail.
- The battery path can be tested without unplugging: start the keeper with
  `-KeepLid -SimulateFile <file> -IntervalSeconds 2` and write `battery 15` into the file. The
  pause flag must appear, and the guard must refuse a shell command with "paused: battery at 15 %".
  Write `ac 80` and the pause must go.

## Limits

- It cannot stop a sleep that the power button or a critical battery level asks for, and it cannot
  change a lid action that an organisation policy sets (`-Status` and the keeper say so).
- The guard refuses only the tools it is registered for: file writes, shell commands, reads (Read,
  Glob, Grep) and note writes, in `kit/hooks/settings.example.json`. Other tools (a web fetch, a
  connector's read) go on during a pause unless the matcher is widened (`kit/hooks/README.md`).
- If the keeper is killed, the lid action stays at "Do nothing" until `-Restore` runs. Step 6
  covers it, and the next start finds the saved values and restores those, not "Do nothing".

## Learn

If the computer slept anyway, find out why before changing anything: on Windows the System event
log holds the standby events (Kernel-Power 506 and 507 on laptops with Modern Standby) with the
reason and whether the lid was open. Record the cause in the changelog, and change this skill only
if the cause is one it can reach.
