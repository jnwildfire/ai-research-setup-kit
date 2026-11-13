# Automation map

Everything that runs without a session asking for it, or sits as a hook on every session. Copy this
file to `<workspace>/.claude/context/automation-map.md` and route to it from the rules file:

    | Changing or adding a scheduled task, hook, startup script or sync | `.claude/context/automation-map.md` |

**When you change an automation, update its row and whatever depends on it, in the same change.**
An automation fails quietly: a scheduled task that stopped, a hook pointing at a moved script, a
startup script whose folder was renamed. Nothing in a session tells you, because nothing in a session
asked for it. The last column is there so that changing one row does not break another.

| Automation | What it does | Trigger | Where it lives | What it writes | What depends on it | How to see its last run | What else must change when it changes |
|---|---|---|---|---|---|---|---|
| PreToolUse guard | Refuses changes to originals, reads in blocked folders and the git commands that lose work; asks before writes outside the roots | Every Write, Edit, Bash, PowerShell, Read, Glob, Grep and note-connector write | `~/.claude/settings.json` → PreToolUse; `~/.claude/hooks/guard.py` | Nothing; a refusal reaches the agent as the tool's error | The roots and the folders of originals in the rules file; the grant step of the plan for a job | Only its refusals leave a trace (tool errors in the transcripts); `guard.py --show-config` | A moved root or a renamed folder of originals changes its configuration block; run `--self-test` after any change |
| Git pre-commit hook: setup references | Refuses a commit that touches the rules file or `.claude/` and leaves a dead reference in the setup: a path that does not exist, a step beyond a skill's last, a project skill without its index row (`setup_refs.py`, about a second, no model) | Every `git commit` in the workspace repository, by whoever commits; wired once per clone with `git config core.hooksPath .githooks` | `<workspace>/.githooks/pre-commit`; `~/.claude/hooks/setup_refs.py` | Nothing; a refusal prints the list and stops the commit | The rule `.claude/rules/setup-changes.md`; the Checks of `learn` | `git config --get core.hooksPath`; `setup_refs.py --self-test` proves the check fires. A refusal leaves no log, only the failed commit | A new clone needs the `git config` line again; a moved `setup_refs.py` changes the hook, the rule and the skills that run it |
| Weekly workflow measurement | Measures the sessions, the configuration and the vault with no model (`workflow_health.py`) | `<weekly, for example Sunday 23:00>`; starts at the next wake if missed | `<Task Scheduler, cron or launchd>`; the script in the `workflow-health` skill | The report note in the vault; optionally a JSON file in the data root | The `workflow-health` skill (reads the note, fills its Judgement) | The note's first line and its `date-modified`; the scheduler's last result | A renamed report note or heading changes the skill's targets; a moved vault changes the script's configuration |
| Agent-notes archive | Moves the agent's dated notes into `Archive/YYYY-MM/` after thirty quiet days (`kit/tools/archive_notes.py`) | `<as a first action of the weekly task, with --dry-run until you decide>` | `<the scheduled task>`; the script | Moves on disk; one line per move in `Archive/archive-log.md` | The guard's `existing-only` rule on the archive folder | The last line of the archive log; a dry run lists what is due | The same thirty-day rule lives in the notes app's startup script: change both together |
| Notes-app startup script | The same archive move inside the notes app, so links follow the note | Each time the notes app starts | `<the vault's template folder>/startup/`, registered in the templating plugin's settings | Moves only | Nothing; the script above is its outside twin | The count of quiet notes still on top, in the weekly report | As the row above |
| Keep-awake | Holds the laptop awake and the lid action at "Do nothing" during a long job; writes the battery pause flag | Started by a session with `/keep-awake`; stops on the stop file or after its time limit | `~/.claude/skills/keep-awake/scripts/keep_awake.ps1` | The lid action (put back at the end); `~/.claude/keep-awake/pause` | The guard's battery pause; jobs that run while you are away | `keep_awake.ps1 -Status` | The guard's `PAUSE_FLAG` and `CONTINUE_FILE` |
| Dictionary export | Regenerates the dictation tool's vocabulary and correction files from the dictionary note | `/dictionary`, on demand | `kit/skills/dictionary/scripts/export_dictionary.py` | The export folder in the data root | The imports into the dictation tool | `last-export` in the dictionary note's frontmatter | The note's table columns and the script's parser change together |
| `<a sync of your configuration to a repository>` | `<copies the rules files, settings and skills into a repository and pushes>` | `<daily, scheduled>` | `<the script and the task>` | `<commits>` | `<a new computer, a restore>` | `<the task's last result; the repository's last commit>` | `<a new kind of file goes into the sync's list>` |

Not automations, so not in the table: the skills (they run inside a session, when asked) and the
background agents (they belong to the session that started them).

The author's weekly measurement also reads the last run of every row that leaves a trace (a scheduled
task's last result, a log's last line, a repository's last commit), so that a stopped automation shows
within a week instead of when its output is missed. The kit's `workflow_health.py` leaves that part
out, because the commands differ from one computer to the next; the column "How to see its last run"
is where to start if you add it.
