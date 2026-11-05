# The guard

`guard.py` is a hook: a small script that Claude Code runs before every file edit and every shell
command of the agent, and that can refuse the action. Guide 04 explains why it exists and what it
does; this page says how to install and test it.

| File | What it is |
|---|---|
| `guard.py` | the hook. Its configuration is the block at the top: your three roots, the folders that hold originals, and what happens outside the roots. |
| `settings.example.json` | the lines that register the hook with Claude Code, to merge into your settings file. |
| `write-scope.example.json` | the shape of a grant: the extra folders an approved plan lets one job or one session write to. |

## Install

1. Copy `guard.py` to `~/.claude/hooks/guard.py` (on Windows `C:\Users\<you>\.claude\hooks\guard.py`).
   Installed there, it guards every session on the computer, whichever folder the session starts
   in, which is what originals on a shared drive need.
2. Fill in the configuration block: `CODE_ROOT`, `DATA_ROOT`, `NOTES_ROOT`, and the `IMMUTABLE`
   list. Use forward slashes.
3. Run `python -I ~/.claude/hooks/guard.py --show-config` and read what it prints: every root and
   every immutable folder, as the guard sees them.
4. Run `python -I ~/.claude/hooks/guard.py --self-test`. It builds a temporary folder tree, sends
   about sixty synthetic tool calls through the same code the hook uses, and must end with every
   check passed ("63 of 63 checks passed" on Windows, one fewer elsewhere). It does not touch your
   folders, and your session's own settings do not change its result.
5. Merge `settings.example.json` into `~/.claude/settings.json` with the absolute path to the
   script. Merge, do not overwrite: the file may hold other settings. If your Python answers only
   to `python3` or `py`, use that name in `"command"`.
6. Start a new Claude Code session; hooks are read when a session starts.

## The live test

In the new session, with a test folder that matches an immutable pattern (for example
`<data root>/projects/_guard-test/data/raw/`):

1. Ask the agent to create `guard-test.txt` there. This is a deposit and goes through.
2. Ask it to change one line of that file. The guard must refuse, naming the folder and the reason.
   The refusal is the right result.
3. Ask it to write a file into your Downloads folder. Claude Code must show a permission prompt.
   Answer no. (A refusal that says "Nobody is at the keyboard" instead means the session reports
   itself as unattended; see below.)
4. Delete the `_guard-test` folder yourself, in File Explorer or Finder: the agent cannot, by design.

If step 2 changes the file instead, the hook is not running: check the path in the settings, the
Python name, and that the session was started after the change.

## Two situations that change the verdicts

**Nobody at the keyboard.** In a background job, Claude Code sets the environment variable
`CLAUDE_CODE_SESSION_ATTENDED` to `0`. This was observed on the author's computer in November
2026 and is not in the documentation read then, so treat it as observed behaviour that may change.
When it reads `0`, an "ask" becomes a refusal that tells the agent to write the question into its
morning report and go on with other work, instead of a prompt that waits all night. When the
variable is absent, the guard asks as before. `UNATTENDED_ASK = "ask"` in the configuration block
switches this off. `--show-config` prints what the guard reads in the current session.

**Battery pause.** The `keep-awake` skill (`kit/skills/keep-awake/`) writes
`~/.claude/keep-awake/pause` when the computer runs on battery at 20 % or less. While that flag
exists, every call the guard sees is refused with "paused: battery at N %, connect power or say
continue". The one call let through is a file write to `~/.claude/keep-awake/continue`, which the
agent makes when you say continue. A flag older than ten minutes is ignored, so a keeper that was
killed cannot leave the agent paused for good.

## Limits

The guard matches shell commands by pattern; it does not run them in its head the way a shell
would. A script that writes files itself is one command to it. It is a net under the rules, not a
sandbox, and Claude Code's permission prompts stay the second net.

The guard sees only the tools named in the `matcher` of `settings.example.json`: file writes,
shell commands and note writes. To let the battery pause stop reading too, widen the matcher to
`"*"` (every tool). Each tool call then starts the script once more, about a tenth of a second on
the author's laptop.
