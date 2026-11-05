# 4. Guards, and work that runs while you are away

*How a few rules are turned from text the agent may forget into a script it cannot get round, and
what an agent may do while nobody is watching. About fifteen minutes to read. Kevin's kit has one
guard, on the folder of originals; this guide extends it to the three roots and to jobs that run
overnight.*

## Why a hook and not a sentence

A rule in the rules file is read by the agent and followed most of the time. In a long session, or
under pressure to finish, it can be missed. Claude Code's documentation says so plainly: written
rules are context, not enforced configuration, and to block an action whatever the agent decides,
use a hook. A **hook** is a small script that Claude Code runs at a fixed moment, here before every
action of the agent (Anthropic calls that moment `PreToolUse`). The hook receives the planned action
and can refuse it, ask you, or let it through. The agent cannot forget a hook.

Only a few rules deserve one: those that are mechanical (a folder, a command) and whose breach cannot
be undone. Everything that needs judgement stays text.

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

## Write scope, settled in the plan

A job that runs while you are away cannot answer a prompt. In a background session an "ask" waits
until you come back; in a run started with `claude -p`, where nobody can answer, it ends as a refusal.
Either way the job stalls on the first write outside the roots. That is the right outcome for a write
nobody foresaw. For a write the job needs, the question belongs before the job, not during it.

So every job that may run unattended names in its plan the folders it will write to and where it
saves its results. Anything outside the roots is asked for there, in the plan, and you answer once.
After your yes, the session writes a **grant**: a small file with the folders, the plan it belongs
to, and an expiry time (`kit/hooks/write-scope.example.json`). The guard reads it from the job's
own folder (Claude Code gives a background job one, in the variable `CLAUDE_JOB_DIR`) or, for one
attended session, from `.claude/write-scope.local.json` in the project. A grant widens the roots;
it never opens an immutable folder. The plan is the single place where you grant, and the prompt
stays the fallback when you are at the keyboard.

## What the guard cannot do

The guard reads shell commands as text and matches patterns; it does not run them in its head the
way a shell would. A Python script that writes files is one command to the guard, which sees only
the paths written on the command line. A command built from variables it cannot resolve is let
through. So the guard is a net under the rules, not a sandbox. Claude Code's permission prompts, and
in auto mode its classifier, are the second net, and the rules file still says why each rule exists.

Test the guard before you trust it: `python guard.py --self-test` runs about fifty synthetic actions
against a temporary folder tree, and `kit/hooks/README.md` gives a live test that ends with the
agent refused in front of you. A guard that has never refused anything may simply not be running.

## Night shifts

Kevin Smith's seminar of 3 November 2026 put the rule for unattended work in a few words, and it
holds: what needs no word from you and can be undone. This kit spells it out.

**A job may, without asking:**

- read anything it needs;
- write inside the roots and inside its grant;
- run the scripts the plan names, on copies or on outputs that can be regenerated;
- commit after every unit of work, on its own branch, so that every step can be undone;
- open a pull request or a draft, never merge one.

**A job never, while you are away:**

- creates, changes or signs into an account, or sends a message in your name;
- installs a program or a package, or changes the computer's settings;
- changes a rule: the rules file, a hook, the settings, a skill's procedure;
- spends money, or starts anything that runs on after the job (a scheduled task, a server);
- deletes what it did not create in this job.

If the job reaches one of these, it stops that branch of the work, writes the question down with
its recommendation, and carries on with whatever does not depend on the answer.

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

- **Hook**: a script that Claude Code runs before an action of the agent, and that can refuse it.
- **Guard**: the hook in this kit, `guard.py`.
- **Immutable folder**: a folder of originals, which the guard keeps unchanged.
- **Roots**: the three top folders for code, data and knowledge (guide 01).
- **Grant**: a file that lets one job or session write to folders outside the roots, after you
  approved the plan that names them.
- **Auto mode**: a Claude Code mode in which a classifier approves most actions without a prompt.
- **Background job**: a session that runs without you at the keyboard.
- **Pull request**: a proposed set of changes to a repository, which a person reviews and merges.
