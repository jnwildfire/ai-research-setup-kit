# Start here

**For you, the person.** This set-up assumes Claude Code already runs on your computer and is signed
in to a paid plan. If it does not, follow Kevin Smith's starter kit first
([guide 01, "Getting started"](https://github.com/KevinMSmith/ai-research-starter-kit/blob/main/guide/01-getting-started.md)),
and read both guides 06 (his, and [this kit's](guide/06-data-and-the-rules.md)) before the agent
reads anything of other people's. You also need Python 3.8 or later.

Then open this kit's folder in Claude Code (in VS Code: File, Open Folder; in a terminal: `cd` into
the folder and type `claude`) and type or dictate:

*Read START-HERE.md and set me up.*

The agent follows the steps below and asks you a few questions as it goes. It explains each step
before it takes it. When it wants to run a command or change a file outside this folder, Claude Code
shows what it wants to do and asks you to allow it; allow it when it matches what the agent said it
would do. Plan on about an hour, split over two sessions: step 6 needs a fresh one. If you stop,
note the step you reached and continue later with "continue the set-up in START-HERE.md from step N".

The steps are written for Claude Code. The ideas behind them (a rules file read at the start,
skills loaded when needed, a hook that runs whatever the agent decides, three roots) work in other
agents too, and the README's table "The ideas, and their form in your agent" names the equivalents
in Codex CLI, OpenAI's command-line interface (CLI) agent. With another agent, tell it which one it is at the start; it then follows its own
documentation wherever this file names a Claude Code path or setting.

---

**For the agent.** You are setting up a researcher who already has files, data and perhaps code or
a notes vault, and who knows what a terminal is but may not program. The kit adds a layer on top of
what they have; it does not move or reorganise anything of theirs. Follow these steps in order.

## Ground rules for the whole set-up

- **Explain before you act.** Before each step, say in two or three plain sentences what you are
  about to do and why, and which guide explains it. After each step, say what changed and how to
  undo it.
- **Ask before you install anything**, and before you change a settings file. Back up a settings
  file before you change it (`settings.json` to `settings.json.bak`).
- **Write only where this file says**: the workspace folder of step 3, the person's user folder
  (`~/.claude/`), and in step 7 the vault's template folder if the person agrees. Never move,
  rename or delete a file of the person's.
- **Never search a cloud-synchronised folder recursively.** List one folder at a time; a recursive
  search downloads every file it touches (guide 01).
- **One question at a time**, each with a suggested answer the person can accept.
- **If a step fails**, stop, say in plain words what went wrong and what you propose, and wait.
- Work out first whether the computer runs Windows or macOS, and use that system's commands. Write
  paths in configuration files with forward slashes.
- **If you are not Claude Code**, say so before step 3. Map each step to your own equivalents with
  the README's table, and where your documentation has no equivalent, stop at that step and say
  so rather than guessing.

## Step 1. Check the computer

Run `git --version`, `python --version` (on Windows also `py --version`, on macOS `python3
--version`) and `claude --version`. Report what is there, and remember which name of Python works:
the guard is started with it. If Python is missing or older than 3.8, explain what it is for here
(the guard and the dictionary export are small Python scripts) and ask before installing it.

## Step 2. The three roots

Explain guide 01 in four sentences: code in git, data on a shared drive, knowledge in a notes vault,
never mixed, and why. Then ask, one at a time:

1. Where does your **code** live? (Suggest a folder on the local disk, for example `C:\dev`; if they
   have no code yet, that folder will hold just the workspace of step 3.)
2. Where does your **data** live? (Often the institution's OneDrive or a network drive.)
3. Where are your **notes**? (An Obsidian vault, a folder of Markdown files, or none yet.)
4. Which folders hold **originals** that must never change: raw data as downloaded, transcripts as
   recorded? Suggest `<data root>/projects/*/data/raw` and `<data root>/meeting-transcripts`, and
   explain that `*` stands for every project.
5. Who must **never be named** in what the agent writes (for example residents, students, anyone who
   has not agreed)?

List each root's top level once (not recursively) to confirm it exists, and read the answers back as
a short table.

## Step 3. The workspace folder and the rules file

Explain: an agent reads a rules file at the start of every session in its folder (in Claude Code
`CLAUDE.md`; in Codex CLI `AGENTS.md`). The **workspace folder** is where the person starts the agent
for research work. It is a git repository
that holds the rules file, the project's skills and agents, and nothing else: no data, no notes.

1. Propose `<code root>/research` as the workspace folder, or an existing repository the person
   names. Create it if needed and run `git init`.
2. Copy `kit/CLAUDE.md.template` to `<workspace>/CLAUDE.md`. Fill in the blanks (marked `<like
   this>`) with the person, from the answers of step 2 and a few more questions: their name and field,
   their work e-mail address, two or three writing rules they care about, the language of their
   notes, and what may and may never run while they are away (guide 04, "Night shifts: your own
   list"; offer Kevin Smith's list plus a payment as the start). Leave a blank they cannot answer
   yet, and list it at the end of the step.
3. Show the filled section "Standing behaviour" and ask what to change or remove. The file must stay
   under 200 lines: report its line count.
4. Create `<workspace>/.claude/rules-changelog.md` with one line: today's date, "rules file set up
   from the ai-research-setup-kit template".
5. Add a `.gitignore` with `.env`, `*.local.json` and `__pycache__/`, and commit: "Set up the
   workspace from the ai-research-setup-kit".

## Step 4. The skills and the agents

Explain guide 03 in three sentences: a skill is a procedure the agent loads only when it is needed;
its one-line description is what is always on the desk.

1. Copy `kit/skills/skill-library` and `kit/skills/learn` to `~/.claude/skills/` (personal: every
   project sees them).
2. Copy `kit/skills/dictionary` to `<workspace>/.claude/skills/` (this workspace only; it runs only
   when typed).
3. Ask whether the person wants the three executor agents (guide 05, "Which model for which work").
   If yes, copy `kit/agents/*.md` to `~/.claude/agents/`, and ask which model they trust most for
   scientific reasoning; set `exec-research`'s `model:` to it.
4. Open `~/.claude/skills/skill-library/SKILL.md` and complete its index: one line per skill now
   installed (list `~/.claude/skills/` and `<workspace>/.claude/skills/`, one level each).

## Step 5. The guard

Explain guide 04 in four sentences: a hook is a script Claude Code runs before each action of the
agent (other agents have their own, with their own format); this one refuses any change to an
original, asks before any write outside the three roots, and stays silent otherwise; it cannot be
forgotten the way a sentence in the rules file can.

1. Copy `kit/hooks/guard.py` to `~/.claude/hooks/guard.py`.
2. Fill in its configuration block from step 2: `CODE_ROOT`, `DATA_ROOT`, `NOTES_ROOT`, and the
   `IMMUTABLE` list with one line of reason each. If the person writes notes through an Obsidian
   connector, leave `NOTE_TOOL_PREFIX` as it is; otherwise set it to `""`. Leave `UNATTENDED_ASK`,
   `PAUSE_FLAG` and `CONTINUE_FILE` as they are, and explain them in one sentence each (guide 04:
   a background job is refused instead of asked; a battery pause from the keep-awake skill).
3. Run `python -I ~/.claude/hooks/guard.py --show-config` and read the output with the person.
4. Run `python -I ~/.claude/hooks/guard.py --self-test`. Every check must pass; explain that it ran
   synthetic actions against a temporary folder and touched nothing of theirs.
5. Back up `~/.claude/settings.json` if it exists, then merge the `hooks` block of
   `kit/hooks/settings.example.json` into it, with the absolute path to the guard and the Python
   name from step 1. Merge, never overwrite: keep every setting that is already there. Claude Code
   asks the person to approve this change; say why it is needed.
6. Explain that hooks are read when a session starts, so the test needs a new session.

## Step 6. The first test (in a new session)

Ask the person to close this session, start a new one in the workspace folder, and type "continue
the set-up in START-HERE.md from step 6" (the file is in the kit's folder; give them its full path).

1. Use the Write tool to create `<data root>/projects/_guard-test/data/raw/guard-test.txt` with one
   line of text. This is a deposit, and it must go through.
2. Use the Edit tool to change that line. The guard must refuse, naming the folder and the reason.
   Tell the person: **this refusal is the right result**; the agent cannot change an original.
3. Use the Write tool to create a file in the person's Downloads folder. Claude Code must show a
   permission prompt with the guard's reason. Ask the person to answer no. If the guard refuses
   instead, saying that nobody is at the keyboard, the session reports itself as unattended: run
   `--show-config` with the person and see guide 04, "Nobody at the keyboard".
4. Ask the person to delete the `_guard-test` folder themselves, in File Explorer or Finder; the
   agent cannot, by design.

If step 2 changes the file instead of being refused, stop: the guard is not running. Check the path
and the Python name in `~/.claude/settings.json`, run `/hooks` to see whether Claude Code lists it,
and tell the person that the originals are unprotected until it is fixed.

## Step 7. Templates, the dictionary and keep-awake (optional)

Ask whether the person wants any of these now; all can wait.

- **Templates**: if they have a vault, copy `kit/templates/*.md` into its template folder (ask which),
  and show the decisions table of the meeting note: blank Verdict means approved.
- **Dictionary**: copy `kit/skills/dictionary/references/dictation-dictionary.md` into the vault,
  set `NOTE` and `OUT` at the top of the export script (in the workspace copy), and run it with
  `--check`. The output folder belongs in the data root.
- **Keep-awake**, for a laptop that runs jobs while the person is away: copy `kit/skills/keep-awake`
  to `~/.claude/skills/` and add its line to the skill library's index. On Windows, run its script
  with `-Status` and read the output with the person: the power source, the battery and the
  lid-close action. Explain that `/keep-awake` sets the lid action to "Do nothing" only while a job
  runs and puts it back afterwards, and that the guard pauses the job on battery at 20 %. On macOS,
  show them `macOS.md` instead; it is a note, not a tested script.

## Step 8. Hand over

1. Ask the person to type `/context` in a fresh session, and write the total and the largest
   categories into a note with today's date: that is the baseline (`kit/tools/measure_context.md`).
2. Give a short list: what was installed where (the rules file, the skills, the agents, the guard,
   the settings change), and how to undo each (delete the copied folder; restore `settings.json.bak`).
3. Name the blanks left open in the rules file.
4. Point to the next reading: guide 02 for what goes where, guide 05 for the research habits, and
   guide 04 before the first job that runs while they are away.
