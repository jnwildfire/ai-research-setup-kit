# 3. Skills, and a library of them

*How a procedure you repeat becomes something the agent does the same way every time, and how many
of them can be installed without crowding the desk. About fifteen minutes to read. Kevin's kit has
five commands (`/start`, `/close`, `/deposit`, `/integrate`, `/ask`); this guide is about the
moment you have twenty.*

## What a skill is

**The idea, in any agent.** A procedure you repeat is written down once, in its own folder: a
short description that the agent always sees, and a body it reads only when the task comes up.
The description says when; the body says how. Scripts and example files sit beside it.

**In Claude Code**, a **skill** is a folder with a file named `SKILL.md` in it. The file starts with
a short header: the skill's name and a **description** of one or two sentences. Below the header is
the **body**: the procedure, in numbered steps. The folder may also hold scripts and example files.
Claude Code finds skills in two places: your personal skills in `~/.claude/skills/<name>/`, which
every project on the computer sees, and a project's skills in `.claude/skills/<name>/` inside that
project, which only sessions started there see.

**In other agents.** Codex CLI, OpenAI's command-line interface (CLI) agent, uses the same shape: a folder with a `SKILL.md` that declares a
`name` and a `description`, found in `.agents/skills` inside a repository and in
`$HOME/.agents/skills` for the person. The body of a skill is plain text and carries over; the
folders and the header settings differ, so check them in your agent's documentation.

## How a skill loads

This is the part that decides how many skills you can afford.

- At the start of every session, **only the name and the description** of each skill go on the
  desk. Claude Code shortens a description to 1,536 characters in that list.
- The **body loads only when the skill is used**: when the model judges that a request matches the
  description, or when you type `/name`.

So the description is the trigger: it is how the model recognises the moment to use the skill, and
it is paid for in every session. The body is free until it runs. A good description says what the
skill does in one sentence, the phrases you actually use when you want it, and one "not for" that
sends a near miss elsewhere. About 400 characters is enough; everything else goes into the body.

Two settings in the header change this:

- `disable-model-invocation: true`: the skill runs only when you type `/name`. Its description
  leaves the desk entirely. Right for anything you always start yourself, and for anything that
  should never run by surprise.
- `user-invocable: false`: the reverse; only the model can call it, and it is hidden from the `/`
  menu. Right for background procedures you never type.

Codex CLI loads skills the same way, name and description first and the body on use. There you
call a skill by mentioning it with `$name` or from `/skills`, and `allow_implicit_invocation: false`
in the skill's `agents/openai.yaml` makes it run only when called, the counterpart of
`disable-model-invocation`.

## The eight layers

A skill that holds up over months has more than a description and a body. This kit lays out its own
skills in eight layers. The layer names come from a practitioner article on building a skill library
that was summarised to the author in November 2026 and has not been located since; the mapping onto
Claude Code is the author's.

| Layer | What it is | Where it lives |
|---|---|---|
| **Library** | all your skills, with one index and one router | `~/.claude/skills/` and `.claude/skills/`; the `skill-library` skill; `skillOverrides` per project |
| **Trigger** | when the skill fires | the description: one sentence, the trigger phrases, one "not for" |
| **Procedure** | what the agent does, step by step | the body of `SKILL.md`, numbered |
| **Resources** | one good example of what the skill makes | `references/` in the skill folder |
| **Scripts** | the steps a program does better than a model | `scripts/` in the skill folder |
| **Checks** | what is verified before the agent reports | a "Checks" section: what the script tests, what the agent re-reads |
| **Guard** | what must never happen, whatever the agent decides | a hook (guide 04) |
| **Learn** | how a correction changes the skill | the `learn` skill, the changelog, the trigger tests |

Not every skill needs all eight. A skill without a script has no Scripts layer. But a skill whose
output can be checked by a program should have one, because a rule a script can check goes into the
check, not into the prose.

## The worked example: the dictation dictionary

The `dictionary` skill in `kit/skills/dictionary/` keeps a personal dictionary for dictation: the
names and terms of your field that a dictation program gets wrong, with the garbles it produces.
Kevin's kit recommends Wispr Flow for dictation, and Wispr Flow imports a vocabulary and a list of
corrections from comma-separated values (CSV) files. Here is the skill, layer by layer:

- **Trigger**: none on the desk. The skill is `disable-model-invocation: true`, so it costs nothing
  until you type `/dictionary`.
- **Procedure**: harvest new names since the last export (new notes about people and organisations,
  new meeting notes), show you the candidates, add the ones you accept to the dictionary note, run
  the export, report the import steps.
- **Resources**: `references/dictation-dictionary.md`, an example of the note with its five columns
  (Term, Category, Heard as, Replace, Note). The note in your vault is the source; the export files
  are generated and never edited by hand.
- **Scripts**: `scripts/export_dictionary.py` reads the table and writes the Wispr Flow vocabulary,
  the Wispr Flow corrections, and two plain term lists.
- **Checks**: the script rejects duplicates, unknown categories, a correction that is not among the
  garbles, and a garble that is itself a term; it stops if Wispr Flow's import limits would be
  exceeded; it reads its own CSV files back to prove the quoting is right. The agent names every
  rejected row in its report.
- **Guard**: the generated files are written by the script, not by hand.
- **Learn**: a garble that keeps coming back is a missing row, added to the note, not a rule
  elsewhere.

The judgement in the skill is the `Replace` column. A correction is safe only for a garble that is
never a real word in your texts: "Zatero" for Zotero, yes; "cloud" for Claude, no, because you also
write about clouds. The script cannot judge that. The procedure tells the agent to decide row by
row, and to leave a garble out when in doubt.

## One library, selected per project

Install every skill once, as a library, and let each project switch off what it never uses. Claude
Code reads a setting, `skillOverrides`, in a project's `.claude/settings.json`, with four states per
skill:

| State | In the agent's list | In your `/` menu |
|---|---|---|
| `on` (the default) | name and description | yes |
| `name-only` | name only | yes |
| `user-invocable-only` | hidden | yes |
| `off` | hidden | hidden |

So a project that never writes talks switches the talk skill `off`; a project of TypeScript code
switches off the skills for writing papers. Nothing is switched on by hand before a task: what is on
fires on its own. (Codex CLI switches a skill off with a `[[skills.config]]` entry and
`enabled = false` in `~/.codex/config.toml`.)

For skills that should stay available but rarely fire, `name-only` keeps only the name on the desk,
and the `skill-library` skill holds their one-line purpose. The model reads the library's page when
a request may match a skill it cannot recognise by name, and calls the skill from there. That costs
one page load when needed instead of a description in every session. It also fires less reliably,
because a description is what the model matches. So the rule is: descriptions for the skills that
fire often, `name-only` plus the library for the rest, `off` for the never-used, and a trigger test
decides which skill may go to `name-only`.

## Checks: the trigger test

A skill that never fires is a cost without a use, and a library has a Checks layer of its own: the
trigger test. Run it after adding skills, after shortening descriptions, and once a quarter:

1. Write one prompt per skill in your own words, the way you would actually ask, for example
   "process the transcript I just dropped into the inbox".
2. Start a fresh session for each, type the prompt, and see whether the skill you expected is used.
3. A skill that does not fire on its natural phrase gets that phrase into its description, or a line
   in the library. A skill you never wanted in three months becomes typed-only or is switched off.

The author's test of November 2026 is the worked example: eight prompts, one expected skill each,
each run as its own session without a person in it (Claude Code's print mode, `claude -p`), started
in the workspace, with only the tools to load a skill and to read allowed, and a limit of five turns,
so that a misfire could not change anything.

| Prompt, in the person's words | Skill expected |
|---|---|
| "Process this meeting:" followed by two lines of a transcript | `process-meeting` |
| "Log to today's daily note that the trigger tests ran tonight." | `daily-note` |
| "Patch the section 'Results' of the note `<path>`: add one line ..." | `notes-editing` |
| "Make the literature note for the citation key smith2023." | `literature-note` |
| "Process the inbox." | `process-inbox` (not a broader maintenance sweep) |
| "Do it later: rename the two notes called ..." | `do-it-later` |
| "Prepare the weekly." | `pre-meeting` |
| "From now on, put the meeting date at the start of every meeting note's title." | `learn` |

Every session loaded the expected skill as its first call, loaded no second skill, and wrote nothing.
That result is what allowed the routing lines for these workflows to leave the rules file: a skill
that fires on its natural phrase needs no line telling the agent where to look. Keep the eight
prompts with the library, and run them again after the next change to a description.

## Writing your own

Start from a procedure you have done with the agent three times and corrected at least once. Ask the
agent to write it as a skill in this layout: a description of about 400 characters, a numbered
procedure, one example file, a script for anything mechanical, a Checks section. Add its line to the
library in the same change. Kevin's rule holds here too: a structure is made when its third instance
would be written, not before.

## Optional add-ons

The author's setup also uses a few things from outside the kit. None is needed; each adds something
specific, and two of them act as you, which is why they are gated.

- **ponytail**, a Claude Code plugin (`/plugin marketplace add DietrichGebert/ponytail`, then
  `/plugin install ponytail@ponytail`): a "lazy senior dev" set of skills for code, the smallest
  change that solves the task and reviews that ask whether every line is needed. It adds skills,
  not permissions; switch it off in projects that hold no code.
- **Agent-Reach**, an open-source command-line tool that reads what an ordinary fetch cannot:
  pages behind a login or a bot block, video subtitles. Gated: the agent asks first, every time, naming the page, what the
  ordinary route returned and the command it would run, and the permission covers that one use.
  The reason is the pattern for any such tool: it acts on your logged-in sessions and stored
  cookies, and sends the addresses it reads through third-party services.
- **Claude in Chrome**, Anthropic's browser extension (`claude --chrome`, or `/chrome` in a
  session): the agent works in your own Chrome, with your sign-ins, for pages behind a login, forms
  and screenshots. It asks before acting on a site, and the extension's site permissions decide.
  Treat it like Agent-Reach, because it acts as you.
- **Obsidian plugins** the vault side rests on:
  - **Local REST API**: the connector the agent writes notes through, an application programming
    interface (API) served by Obsidian while it runs and opened with a key you keep in an
    environment variable. Writing through the app rather
    than to the file avoids a race with a note you have open.
  - **Dataview**: queries over the notes' properties, for example every note with
    `reviewed: false`.
  - **Templater**: templates with small scripts, including startup scripts such as the one that
    archives agent outputs (guide 08).
  - **Relay**: folders shared in real time with colleagues. The agent edits there one passage at a
    time, never a whole note, because its writes do not travel through Relay's own sync and a full
    rewrite can overwrite what a co-author typed meanwhile.

## Terms used

- **Skill**: a folder with a `SKILL.md`: a description always on the desk, a body loaded when used.
- **Description**: the skill's one or two sentences in the header; the trigger.
- **Body**: the procedure below the header, loaded only when the skill runs.
- **Typed**: a skill with `disable-model-invocation: true`, which runs only when you type `/name`.
- **Library**: all installed skills, indexed by the `skill-library` skill.
- **`skillOverrides`**: the project setting that switches each skill on, off, or to name only.
- **Trigger test**: a prompt in a fresh session that checks whether a skill fires when it should.
- **Plugin**: a package of skills, agents or hooks that Claude Code installs from a marketplace,
  a repository that lists plugins.
