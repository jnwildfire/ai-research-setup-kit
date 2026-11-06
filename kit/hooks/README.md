# The guard, and the output check

`guard.py` is a hook: a small script that Claude Code runs before every file edit, every shell
command and every read of the agent, and that can refuse the action. Guide 04 explains why it
exists and what it does; this page says how to install and test it. `output_check.py` is the second
script here: not a hook, but a check the agent runs on a finished note before it reports.

| File | What it is |
|---|---|
| `guard.py` | the hook. Its configuration is the block at the top: your three roots, the cloud drive they sit in, the folders that hold originals, and the branches that are never rewritten. |
| `settings.example.json` | the lines that register the hook with Claude Code, to merge into your settings file. |
| `write-scope.example.json` | the shape of a grant: the extra folders an approved plan lets one job or one session write to, and the files it may read in a blocked folder. |
| `output_check.py` | the writing check: dashes inside sentences, abbreviations used before their long form, bare issue numbers, frontmatter that does not parse. |

## What the guard decides

| What the call does | Verdict |
|---|---|
| Adds a new file to a folder of originals (`deposit-only`: raw data, transcripts) | pass: a deposit |
| Changes, overwrites, moves or deletes a file there | refused, with the reason |
| Writes, moves, copies or deletes anything in a `never` folder (a staging folder only you fill) | refused |
| Creates, moves, copies or deletes in an `existing-only` folder (an archive a script fills); changing a file in place passes | refused |
| Writes inside the roots, `~/.claude`, the temporary folder, a job's own folder, a granted folder | pass, silently: Claude Code's own permissions decide |
| Writes anywhere else | ask |
| Reads on the cloud drive outside the data and notes roots: Read, Glob, Grep, `ls`, `cat`, `find`, `Get-ChildItem`, `Get-Content` and kin, a copy's source, a recursive search started above the drive | refused: "ask the person for the file" |
| A path granted in a grant file, before its `expires` | pass: `write` opens a folder, `read` an exact path or a folder ending in `/**` |
| `git push --force` or `+ref` to a protected branch, `git reset --hard`, `git clean` (the dry run `-n` passes), `git branch -D`, deleting a protected branch, `git checkout -- .`, `git restore .` | refused, with the reason per command |
| Deleting any other branch (`git branch -d`, `git push --delete`, `git push origin :x`) | ask |
| Any call while the battery pause stands (writing the continue file excepted) | refused: "paused: battery at N %, connect power or say continue" |
| An ask while `CLAUDE_CODE_SESSION_ATTENDED=0` | refused, with "write this down as a question for the morning report" |

## Install

1. Copy `guard.py` to `~/.claude/hooks/guard.py` (on Windows `C:\Users\<you>\.claude\hooks\guard.py`).
   Installed there, it guards every session on the computer, whichever folder the session starts
   in, which is what originals on a shared drive need.
2. Fill in the configuration block: `CODE_ROOT`, `DATA_ROOT`, `NOTES_ROOT`, `CLOUD_ROOT` (the cloud
   drive the data and notes roots sit in; leave the placeholder if there is none, and no read is
   blocked), the folders in `immutable_for`, and `PROTECTED_BRANCHES`. Use forward slashes.
3. Run `python -I ~/.claude/hooks/guard.py --show-config` and read what it prints: every root, every
   folder of originals, the blocked folders with the ones inside them that stay readable, the grant
   files and the protected branches, as the guard sees them.
4. Run `python -I ~/.claude/hooks/guard.py --self-test`. It builds a temporary folder tree, sends
   about 150 synthetic tool calls through the same code the hook uses, and must end with every check
   passed ("156 of 156 checks passed" on Windows, one fewer elsewhere). It does not touch your
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
4. If you set `CLOUD_ROOT`: ask it to list a folder on the cloud drive outside your roots. The guard
   must refuse with "ask the person for the file".
5. Delete the `_guard-test` folder yourself, in File Explorer or Finder: the agent cannot, by design.

If step 2 changes the file instead, the hook is not running: check the path in the settings, the
Python name, and that the session was started after the change.

## Grants

A job that runs while you are away cannot answer a prompt, so its plan names the folders it writes
outside the roots and the files it must read in a blocked folder. After your yes, the session
writes them into a grant file (`write-scope.example.json`), which the guard reads on every call and
ignores once `expires` has passed:

    $CLAUDE_JOB_DIR/write-scope.json                  a background job (the variable is described below)
    <project>/.claude/write-scope.local.json          one attended session (keep *.local.json out of git)

A grant never opens a folder of originals.

## Two situations that change the verdicts

**Nobody at the keyboard.** In a background job, Claude Code sets the environment variable
`CLAUDE_CODE_SESSION_ATTENDED` to `0`. This was observed on the author's computer in November
2026, is set by Claude Code itself (nothing in the author's configuration sets it, checked on
5 November), and is not in the documentation read then, so treat it as observed behaviour that may
change. When it reads `0`, an "ask" becomes a refusal that tells the agent to write the question
into its morning report and go on with other work, instead of a prompt that waits all night. When
the variable is absent, the guard asks as before. `UNATTENDED_ASK = "ask"` in the configuration
block switches this off. `--show-config` prints what the guard reads in the current session. If an
ordinary session at your keyboard also reports `0`, set `UNATTENDED_ASK = "ask"` and rely on the
plan's grant for jobs.

**Battery pause.** The `keep-awake` skill (`kit/skills/keep-awake/`) writes
`~/.claude/keep-awake/pause` when the computer runs on battery at 20 % or less. While that flag
exists, every call the guard sees is refused with "paused: battery at N %, connect power or say
continue". The one call let through is a file write to `~/.claude/keep-awake/continue`, which the
agent makes when you say continue. A flag older than ten minutes is ignored, so a keeper that was
killed cannot leave the agent paused for good.

## Limits

The guard matches shell commands by pattern; it does not run them in its head the way a shell
would. A script that writes or reads files itself is one command to it, and a heredoc line that
reads like a command on a blocked path is refused too. A force push whose branch the guard cannot
read is refused: name the branch. It is a net under the rules, not a sandbox, and Claude Code's
permission prompts stay the second net. Inside the roots it stays silent rather than answering
"allow", because "allow" would also skip the auto-mode classifier for edits of your settings and
of the guard itself.

The guard sees only the tools named in the `matcher` of `settings.example.json`: file writes,
shell commands, reads and note writes. Each call starts the script once, about a tenth of a second
on the author's laptop, now on every read too. To let the battery pause stop every tool, widen the
matcher to `"*"`.

A scheduled task or a script started outside Claude Code is not guarded: only the agent's own tool
calls pass through the hook.

## The output check

`output_check.py` checks a finished Markdown file for the writing rules a script can verify: an
em-dash or en-dash doing punctuation inside a sentence (bullet markers, headings, table headers, a
dash-only cell and number ranges pass), an abbreviation used before its long form in the same file
(`--undefined` also lists the ones never spelled out, as hints), a bare `#207` outside a link, and
frontmatter that does not parse. Code, links and wikilinks are skipped.

    python -I output_check.py <note.md> [<note.md> ...] [--undefined]
    python -I output_check.py --self-test

It never writes. Exit code 0 when clean, 1 with findings. Put it in the Checks of the skills that
end in a note or a document (a session's closing step, a review before something is sent), so the
rule is checked rather than remembered. It reads frontmatter with PyYAML when that is installed and
falls back to a structural check otherwise; the add-on list `COMMON` at the top holds the
abbreviations it never asks about.
