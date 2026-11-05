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

`kit/hooks/guard.py` gives every file edit, every shell command and every note write one of three
verdicts.

**Deny: the originals.** A folder you list as immutable holds originals: raw data as downloaded,
transcripts as recorded. The guard refuses any action that would change, overwrite, move or delete a
file there, and tells the agent why; the agent then proposes the correction downstream, in processed
data or in the note. Adding a new file is allowed, because a new delivery is a new original. A
second strictness, `never`, refuses every write at all, for a folder that is only ever filled by you.

**Ask: outside the roots.** A write anywhere outside your three roots and the agent's working folders
(its own settings folder, the temporary folder) is not refused but asked: Claude Code shows you a
permission prompt with the guard's reason. Downloads, your desktop, another project's shared drive,
a folder of administrative documents: the agent reads them freely and writes there only with a yes.
In auto mode, where a classifier approves most actions on its own, the documentation states that a
hook's "ask" goes to you and not to the classifier.

**Pass: everything else.** Inside the roots, the guard stays silent, and Claude Code's own permission
settings decide as if the guard were not there. Reading is never restricted.

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
to, and an expiry time (`kit/hooks/write-scope.example.json`). The guard reads it from the job's
own folder (the folder in `CLAUDE_JOB_DIR`, see below) or, for one attended session, from
`.claude/write-scope.local.json` in the project. A grant widens the roots; it never opens an
immutable folder. The plan is the single place where you grant, and the prompt stays the fallback
when you are at the keyboard.

## Nobody at the keyboard: two variables a background job carries

On the author's computer, Claude Code sets two environment variables in a background job, a
session that runs on without you. Neither was found in Claude Code's documentation read on
5 November 2026, so the kit treats them as observed behaviour, which a later version may change,
and falls back to the documented behaviour when they are absent.

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

Test the guard before you trust it: `python guard.py --self-test` runs about sixty synthetic actions
against a temporary folder tree, and `kit/hooks/README.md` gives a live test that ends with the
agent refused in front of you. A guard that has never refused anything may simply not be running.

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

## Terms used

- **Hook**: a script that the agent's program runs before an action of the agent, and that can
  refuse it.
- **Guard**: the hook in this kit, `guard.py`.
- **Immutable folder**: a folder of originals, which the guard keeps unchanged.
- **Roots**: the three top folders for code, data and knowledge (guide 01).
- **Grant**: a file that lets one job or session write to folders outside the roots, after you
  approved the plan that names them.
- **Auto mode**: a Claude Code mode in which a classifier approves most actions without a prompt.
- **Background job**: a session that runs without you at the keyboard.
- **Environment variable**: a named value a program hands to the programs it starts, such as
  `CLAUDE_JOB_DIR`.
- **Lid-close action**: what the computer does when the lid closes: sleep, hibernate, shut down or
  nothing.
- **Pause flag**: the file the battery watch writes, which makes the guard refuse every action.
- **Pull request**: a proposed set of changes to a repository, which a person reviews and merges.
