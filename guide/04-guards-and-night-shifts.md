# 4. Guards, and work that runs while you are away

*How a few rules are turned from text the agent may forget into a script it cannot get round, and
what an agent may do while nobody is watching. About twenty minutes to read. Kevin's kit has one
guard, on the folder of originals; this guide extends it to the three roots, to jobs that run
overnight, and to the computer they run on.*

## Why a hook and not a sentence

**The idea, in any agent.** An agent follows its rules in two ways. Rules written as text are read
and followed most of the time; in a long session, or under pressure to finish, one can be missed.
Rules written as a program that runs around the agent are applied every time, whatever the agent
decides. So a rule that is mechanical (a folder, a command) and whose breach cannot be undone
belongs in such a program. Everything that needs judgement stays text.

**In Claude Code**, that program is a **hook**: a small script that Claude Code runs at a fixed
moment, here before every action of the agent (Anthropic calls that moment `PreToolUse`). The hook
receives the planned action and can refuse it, ask you, or let it through. Claude Code's
documentation says so plainly: written rules are context, not enforced configuration, and to block
an action whatever the agent decides, use a hook. The agent cannot forget a hook. Hooks are
registered in a settings file (`~/.claude/settings.json` for every session on the computer).

**In other agents.** Codex CLI, OpenAI's command-line interface (CLI) agent, documents hooks of
the same kind: a `PreToolUse` event, configured in `hooks.json` or `config.toml` in `~/.codex/` or
the project's `.codex/`, that refuses a call with exit code 2 or with a "deny" answer. Its documentation adds a caution
that holds for every agent: "Treat tool hooks as a useful guardrail, not a complete enforcement
boundary." This kit's guard reads Claude Code's format; before you use it with another agent, check
that agent's documentation for the event, the tool names and the answer it expects, and run the
self-test and the live test there.

## The guard in this kit

`kit/hooks/guard.py` gives every file edit, every shell command, every read and every note write one
of three verdicts.

**Deny: the originals.** A folder you list as immutable holds originals: raw data as downloaded,
transcripts as recorded. The guard refuses any action that would change, overwrite, move or delete a
file there, and tells the agent why; the agent then proposes the correction downstream, in processed
data or in the note. Adding a new file is allowed, because a new delivery is a new original. A
second strictness, `never`, refuses every write at all, for a folder that is only ever filled by you
(a staging folder in the inbox). A third, `existing-only`, lets a file there be changed in place but
refuses anything new, any move and any delete, for an archive that only a script fills: an archived
note can still be corrected, but nothing is filed there by hand.

**Deny: reads outside the roots on a cloud drive.** A cloud drive keeps most files online only, as
placeholders; listing or opening one downloads it. Your data and notes roots sit on the drive and
stay readable; the rest of it is closed to the agent's Read, Glob and Grep and to the shell's
listing and reading commands, with "ask the person for the file". A recursive search started above
the drive is refused too, since it would reach into it. The list of blocked folders is
configurable (`read_blocked_for` in the guard), and a plan can open one file or one folder for a job
(below).

**Deny: the git commands that lose work.** A force push to a protected branch (`main` by default),
`git reset --hard`, `git clean` (its dry run passes), `git branch -D`, deleting a protected branch,
and `git checkout -- .` or `git restore .` are refused, each with its reason and the safe
alternative. Deleting any other branch is asked. These are the commands whose damage cannot be
undone from the repository itself.

**Ask: outside the roots.** A write anywhere outside your three roots and the agent's working folders
(its own settings folder, the temporary folder) is not refused but asked: Claude Code shows you a
permission prompt with the guard's reason. Downloads, your desktop, another project's shared drive,
a folder of administrative documents: the agent reads them freely and writes there only with a yes.
In auto mode, where a classifier approves most actions on its own, the documentation states that a
hook's "ask" goes to you and not to the classifier.

**Pass: everything else.** Inside the roots, the guard stays silent, and Claude Code's own permission
settings decide as if the guard were not there. Reading is restricted only on the cloud drive outside
your roots.

Two situations change these verdicts, both described below: nobody at the keyboard, and a battery
running low.

## Write scope, settled in the plan

A job that runs while you are away cannot answer a prompt. In a background session an "ask" would
wait until you come back (this kit's guard turns it into a refusal with a note instead, see
"Nobody at the keyboard"); in a run started with `claude -p`, where nobody can answer, it ends as a
refusal. Either way the job cannot do the write. That is the right outcome for a write nobody
foresaw. For a write the job needs, the question belongs before the job, not during it.

So every job that may run unattended names in its plan the folders it will write to and where it
saves its results. Anything outside the roots is asked for there, in the plan, and you answer once.
After your yes, the session writes a **grant**: a small file with the folders, the plan it belongs
to, and an expiry time (`kit/hooks/write-scope.example.json`). Its `write` list opens folders to
write in; its `read` list opens exact files in a blocked folder, or a whole folder written with `/**`
at the end, so a job that needs one document from the closed part of the drive names it in the plan
instead of being refused at night. The guard reads the grant from the job's own folder (the folder in
`CLAUDE_JOB_DIR`, see below) or, for one attended session, from `.claude/write-scope.local.json` in
the project, and ignores it once `expires` has passed. A grant widens the roots; it never opens an
immutable folder. The plan is the single place where you grant, and the prompt stays the fallback
when you are at the keyboard.

## Nobody at the keyboard: two variables a background job carries

On the author's computer, Claude Code sets two environment variables in a background job, a
session that runs on without you. They are Claude Code's own: nothing in the author's configuration
sets them (checked on 5 November 2026). Neither was found in Claude Code's documentation read on
that day, so the kit treats them as observed behaviour, which a later version may change, and falls
back to the documented behaviour when they are absent.

- **`CLAUDE_JOB_DIR`**: a folder Claude Code gives the job for its own files. The kit keeps the
  job's grant there, as `write-scope.json`, so the grant ends with the job. Without the variable,
  the guard reads only the grant in the project (`.claude/write-scope.local.json`): write the
  job's grant there instead, with an expiry that ends with the job.
- **`CLAUDE_CODE_SESSION_ATTENDED`**: `0` in a background job, meaning nobody is there to answer a
  prompt. When it reads `0`, the guard turns an "ask" into a refusal with a note to the agent:
  write the question down for the morning report, with a recommendation, and go on with what does
  not depend on it. A prompt nobody answers would otherwise hold the job until you come back.
  Without the variable, the guard asks as usual. `UNATTENDED_ASK = "ask"` in the guard's
  configuration switches this off.

Check both in your own setup before relying on them: in a background job, have the agent print the
two variables, and run `python guard.py --show-config`, which reports what the guard reads.

## What the guard cannot do

The guard reads shell commands as text and matches patterns; it does not run them in its head the
way a shell would. A Python script that writes files is one command to the guard, which sees only
the paths written on the command line. A command built from variables it cannot resolve is let
through. So the guard is a net under the rules, not a sandbox. Claude Code's permission prompts, and
in auto mode its classifier, are the second net, and the rules file still says why each rule exists.

Test the guard before you trust it: `python guard.py --self-test` runs about 150 synthetic actions
against a temporary folder tree, and `kit/hooks/README.md` gives a live test that ends with the
agent refused in front of you. A guard that has never refused anything may simply not be running.
A test that cannot fail proves nothing either: when the guard was built, each rule was switched off
in turn, and its cases had to fail.

## Night shifts: your own list

Kevin Smith's seminar of 3 November 2026 put the rule for unattended work in a few words: what
needs no word from you and can be undone. His list of what a job never does on its own is short:
**never a simulation, an account, an install, a rule.** This kit adds **a payment**. That is his
list with one addition, not a law. What may run while you are away depends on your work, so the
list that binds your agent is yours, written into your rules file (the template has a line for it).

As a starting point: tests, builds, data pipelines run on copies, figures regenerated from
processed data, and drafts that wait for your reading can often run unattended. Anything that
cannot be undone, anything that touches originals, anything that spends money, and anything that
creates or uses an account in your name cannot. A group whose simulations run every night on a
cluster will move that item to the first list; a group with expensive licences may add more to
the second. This kit's default, to adapt:

**A job may, without asking:**

- read anything it needs;
- write inside the roots and inside its grant;
- run the scripts the plan names, on copies or on outputs that can be regenerated;
- commit after every unit of work, on its own branch, so that every step can be undone;
- open a pull request or a draft, never merge one.

**A job never, while you are away:**

- creates, changes or signs into an account, or sends a message in your name;
- installs a program or a package, or changes the computer's settings (the lid action that you
  hand to the `keep-awake` skill yourself, below, is the one exception, and it is put back);
- changes a rule: the rules file, a hook, the settings, a skill's procedure;
- spends money, or starts anything that runs on after the job (a scheduled task, a server);
- deletes what it did not create in this job.

If the job reaches one of these, it stops that branch of the work, writes the question down with
its recommendation, and carries on with whatever does not depend on the answer.

## Keeping the computer awake, and the battery

**The idea, in any setup.** A job stops without a word when the computer sleeps. Three things put
a laptop to sleep: idle time, the lid, and the battery. Each needs its own answer: a request to the
operating system to stay awake while the job runs; a lid-close action that does nothing for the
length of the job and is put back afterwards; and a pause before the battery is empty, so the job
stops at a point it can resume from instead of mid-write. The first two are a plain script and
work with any agent; the pause needs a hook that can refuse the agent's next action.

**In this kit**, the `keep-awake` skill (`kit/skills/keep-awake/`) does all three. You start it
yourself, with `/keep-awake`, before you leave; it never runs on its own. On Windows its script asks
for "system required", so idle time does not put the computer to sleep while the screen still
turns off; it saves the lid-close action, sets it to "Do nothing" on mains and on battery, and puts
the saved values back when it ends; and once a minute it reads the battery. On battery at 20 % or
less it writes a pause flag, and the guard then refuses every action it sees with "paused: battery
at N %, connect power or say continue". Connect power and the pause ends by itself; say continue
and the agent records it, and the job runs on battery until power is back. On macOS, `caffeinate`
and `pmset` do the same, in a note beside the skill.

Why the lid: in the author's setup, a laptop slept twice in one evening on battery while a script
that asked Windows to stay awake was running. The event log showed both standbys starting the moment
the lid was closed. Closing the lid is a request to sleep, and no "stay awake" request overrules it;
only the lid-close action does.

What it cannot do: stop a sleep that the power button or a nearly empty battery asks for, or change
a lid action that your organisation sets by policy (it says so). A closed laptop in a bag keeps
running and gets hot; leave it on a desk.

## The morning report

The job ends with a report you can read in two minutes, at the top of the note or the pull request
it made:

1. **What ran**: each unit of work, one line, with the commit or the file.
2. **What was refused or asked**: every guard verdict and every prompt left unanswered, with what the
   job did instead.
3. **Decided without asking**: each choice the job made on your behalf, with its reason and how to
   undo it.
4. **Questions**: the minimum you need to answer, each with a recommendation, so that a blank answer
   can mean "as recommended".
5. **Next**: what the next session should start with.

## The automation map

The guard, a weekly measurement, an archive script, a startup script in the notes app, a hook that
backs up the agent's memory, the keep-awake keeper: each runs without a session asking for it, and
each fails quietly. A scheduled task that stopped, or a hook that points at a moved script, says
nothing in any session, because no session asked for it. So the setup keeps one table of them,
`kit/context/automation-map.md`: per automation, what it does, its trigger, where it lives, what it
writes, what depends on it, how to see its last run, and what else must change when it changes. The
rules file routes to it with one line ("changing or adding a scheduled task, hook, startup script or
sync"), and its rule is short: **when you change an automation, update its row and whatever depends
on it, in the same change.** A row that leaves a trace (a log line, a task's last result, a commit)
can be checked by the weekly measurement, so a stopped automation shows within a week.

## Before a compaction

When a session's context fills up, Claude Code compacts it: the conversation is replaced by a
summary, and whatever the summary leaves out is gone. The author's setup treats that as a step to
prepare, not an event to wait for.

- **Auto-compact off.** With `"autoCompactEnabled": false` in `~/.claude/settings.json` a session
  compacts only when you type `/compact` (idle compaction is off with it, by the settings reference).
  A compaction then happens when you choose it, after the save step below, never in the middle of a
  piece of work.
- **The save step before a manual compact.** Rules and corrections go to their files through the
  `learn` skill, knowledge to the vault (the note the work belongs in, the daily note's progress
  log), the state of the work to memory. Then `/compact` with focus instructions: keep every decision
  taken, every file and note written with its path, every open question, the current task and the
  next step; drop tool output.
- **The documented lever is a section of the rules file.** Claude Code's documentation (its page on
  costs, read 6 November 2026) describes a "Compact instructions" section in `CLAUDE.md` that shapes
  every compaction, an automatic one at the window's end included; the template has it as an
  optional section. A `PreCompact` hook cannot do that: by the hooks reference read the same day, it
  receives the trigger (manual or automatic) and the instructions typed after `/compact`, and can
  only block the compaction (exit code 2, or a "block" decision); what it prints does not reach the
  summary. A `SessionStart` hook on the `compact` source can add context after a compaction.
- **A long session plans its own end.** Past about 60 % of the context window, the session runs the
  save step, writes a handover (done, next, where things stand) and suggests a fresh session. The
  `workflow-health` script prints a session's peak context without a model, and its weekly report
  lists the sessions that passed the line.

## Terms used

- **Hook**: a script that the agent's program runs before an action of the agent, and that can
  refuse it.
- **Guard**: the hook in this kit, `guard.py`.
- **Immutable folder**: a folder of originals, which the guard keeps unchanged.
- **Roots**: the three top folders for code, data and knowledge (guide 01).
- **Grant**: a file that lets one job or session write to folders outside the roots, or read named
  files in a blocked folder, after you approved the plan that names them.
- **Read block**: the folders on a cloud drive outside your roots, which the guard keeps the agent
  from listing, searching or opening.
- **Auto mode**: a Claude Code mode in which a classifier approves most actions without a prompt.
- **Background job**: a session that runs without you at the keyboard.
- **Environment variable**: a named value a program hands to the programs it starts, such as
  `CLAUDE_JOB_DIR`.
- **Lid-close action**: what the computer does when the lid closes: sleep, hibernate, shut down or
  nothing.
- **Pause flag**: the file the battery watch writes, which makes the guard refuse every action.
- **Pull request**: a proposed set of changes to a repository, which a person reviews and merges.
- **Automation map**: the table of everything that runs without a session asking for it, with what
  depends on each.
- **Compaction**: Claude Code replacing a long conversation with a summary, to free the context
  window.
