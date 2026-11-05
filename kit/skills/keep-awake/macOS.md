# Keep awake on macOS

*A note, not a tested script: the author works on Windows. The commands below are macOS's own
(`caffeinate`, `pmset`); check them against `man caffeinate` and `man pmset` on your Mac before a
night relies on them.*

## No idle sleep

`caffeinate` keeps a Mac awake for as long as it runs:

    caffeinate -dims

`-i` prevents idle sleep, `-m` disk sleep, `-s` system sleep (on mains power only), and `-d` keeps
the display on. Leave out `-d` to let the screen go dark as the Windows keeper does
(`caffeinate -ims`). `caffeinate -ims -w <pid>` holds only while the process `<pid>` runs, and
`caffeinate -ims <command>` holds while that command runs. Stop it with Ctrl+C or by ending the
process.

## The lid

A Mac sleeps when the lid closes, whatever `caffeinate` says, unless it runs closed with mains
power, an external display and a keyboard connected (clamshell mode). A setting that is widely
shared for keeping a closed Mac running is

    sudo pmset -a disablesleep 1      # and afterwards: sudo pmset -a disablesleep 0

It needs an administrator password, it is not described in `man pmset` on every macOS version,
and nothing restores it if you forget. Check the current value with `pmset -g` (the line
`SleepDisabled`) before and after. A closed laptop in a bag gets hot; keep it on a desk.

## The battery watch, for the guard

The guard (`kit/hooks/guard.py`) pauses the job while the file `~/.claude/keep-awake/pause` exists
and is fresh. On macOS a small loop can write it from `pmset -g batt`, the same way the Windows
keeper does: on battery at 20 % or less, write the percentage; on mains power, remove the pause and
the continue file; while the continue file exists, remove the pause.

    mkdir -p ~/.claude/keep-awake
    caffeinate -ims sh -c '
      dir="$HOME/.claude/keep-awake"
      while [ ! -f "$dir/stop" ]; do
        b=$(pmset -g batt)
        pct=$(printf "%s\n" "$b" | grep -Eo "[0-9]+%" | head -n 1 | tr -d "%")
        if printf "%s\n" "$b" | grep -q "AC Power"; then
          rm -f "$dir/pause" "$dir/continue"
        elif [ -f "$dir/continue" ]; then
          rm -f "$dir/pause"
        elif [ -n "$pct" ] && [ "$pct" -le 20 ]; then
          echo "$pct" > "$dir/pause"
        fi
        sleep 60
      done
      rm -f "$dir/stop" "$dir/pause" "$dir/continue"'

Stop it with `touch ~/.claude/keep-awake/stop`. The decision logic was checked on Windows against
sample `pmset -g batt` output (on battery at 76 % and 18 %, after a continue, on mains power); it
has not run on a Mac.
