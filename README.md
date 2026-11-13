# An AI research setup kit: the second track

*For researchers who already have files, data and perhaps code or a notes vault, and want an
artificial intelligence (AI) agent to work across all of it under rules they set: what it reads, what it may change, what it
checks before anything leaves. You need to know what a terminal is; you do not need to program.
The agent sets the kit up with you and explains each step before it takes it.*

Johannes Wildfeuer, Technical University of Denmark (DTU), November 2026 (jniwi@dtu.dk). Draft v0.1.2, not yet released.

**See the map first**: [the whole setup on one page](https://jnwildfire.github.io/ai-research-setup-kit/),
what is connected to what and what each part does, with text beside every part. The page is
[docs/index.html](docs/index.html) in this repository, published with GitHub Pages.

## The first track, and this one

This kit is the second track after Kevin Smith's
[AI research starter kit](https://github.com/KevinMSmith/ai-research-starter-kit), which came out of
the DTU seminar "Working with an AI agent in research" (3 November 2026). His kit is the
prerequisite: it installs Claude Code, explains the method (originals kept unchanged, every claim
traced to its source, corrections made into rules) and builds one knowledge base per project, for
someone who has never used a terminal.

This kit starts where his ends: with a researcher whose work already spans several projects, code
repositories, a shared data drive and a notes vault, and who wants one setup across all of it.

## The seminar talk

This kit grew out of the talk of 3 November 2026 at DTU, "Working with an AI agent in research", of
which the author gave the second half after Kevin Smith's: [the slides of that second half, as a PDF](docs/seminar/2026-11-03_Working-with-an-AI-agent-in-research_part-2_Wildfeuer.pdf).
The slides are under CC BY 4.0 like the kit's texts; credit them as "Johannes Wildfeuer, DTU".

## What this kit adds

1. **Three roots instead of one folder**: code in git, data on the institution's drive, knowledge in
   a notes vault, never mixed, with data tiers inside the data root ([guide 01](guide/01-three-roots.md)).
2. **What the agent reads before the first word**, measured and chosen: the desk, tokens in plain
   words, six design shifts for current models, and a rules file under 200 lines
   ([guide 02](guide/02-what-the-agent-reads.md)).
3. **A skill library**: skills in eight layers, loaded only when needed, switched per project, with a
   router, a worked example (the dictation dictionary), the skills for a notes vault (meetings, the
   daily note, the task board, the inbox, literature, talks, reports), and the trigger test that
   checks each one fires ([guide 03](guide/03-skills-and-the-library.md)).
4. **A guard with a write scope**: originals refused, reads kept out of the online-only part of a
   cloud drive, the git commands that lose work refused, writes outside the roots asked, grants
   written into the plan of a job that runs while you are away, a night-shift list of your own with a
   morning report, a computer that stays awake and pauses its job before the battery runs out, a map
   of every automation, and a compaction you prepare for ([guide 04](guide/04-guards-and-night-shifts.md)).
5. **What research adds to the method**: the paper itself before a claim carries weight, a basis on
   every number, the agent as referee, faults made into rules, decisions as tickets, one base for
   several people, which model for which work ([guide 05](guide/05-the-research-method.md)).
6. **The research-data case**: household and partner data, a vault on the institution's drive, and
   what never goes into a public repository ([guide 06](guide/06-data-and-the-rules.md)).
7. **Literature and the agent**: a reference manager with stable citation keys, one literature note
   per paper, a connector that reads full text, and the services that check a citation
   ([guide 07](guide/07-literature-and-the-agent.md)).
8. **The knowledge base**: the vault laid out in lanes, the author's as one example, Research Memex
   as a place to start, an archive for the agent's outputs that runs itself, and a reconnaissance
   pass followed by a dictation lane for what only you know ([guide 08](guide/08-the-knowledge-base.md)).

## The ideas, and their form in your agent

The kit is written for Claude Code, because the first track installs it. The ideas are not tied to
it. Each guide states the idea first, then its form in Claude Code, then the equivalent in one other
agent, Codex CLI (OpenAI's command-line interface, CLI, agent), as its documentation described it
in November 2026. For
any other agent, check its documentation; this table is a map, not a promise.

| Idea | In Claude Code | In Codex CLI |
|---|---|---|
| A **rules file** the agent reads at the start of every session | `CLAUDE.md` in your user folder and in the project | `AGENTS.md` in `~/.codex` and from the project root down to the current folder (32 KiB by default) |
| **Skills**: procedures loaded only when a task needs them | folders with a `SKILL.md` in `~/.claude/skills/` and `.claude/skills/` | folders with a `SKILL.md` in `$HOME/.agents/skills` and `.agents/skills` |
| **Hooks**: scripts that run before an action, whatever the agent decides | `PreToolUse` hooks in `settings.json`; exit code 2 refuses | `PreToolUse` hooks in `hooks.json` or `config.toml`; exit code 2 or a "deny" answer refuses |
| **Memory**: the agent's own notes on where things stand | automatic, per project, with a `MEMORY.md` index | "memories" under `~/.codex`, off by default |
| **Connectors** to services (Model Context Protocol, MCP, servers) | `claude mcp add` | `[mcp_servers.<name>]` in `config.toml`, or `codex mcp add` |
| **Three roots** and **the desk** | not tied to the agent | not tied to the agent |

## What is in the kit

| Part | What it is |
|---|---|
| [START-HERE.md](START-HERE.md) | The instructions the agent follows to set you up. You may read them; you do not need to. |
| [guide/](guide/) | Eight guides, ten to twenty minutes each, in the order above. |
| [docs/index.html](docs/index.html) | The map: the whole setup on one page, [published here](https://jnwildfire.github.io/ai-research-setup-kit/). |
| [kit/CLAUDE.md.template](kit/CLAUDE.md.template) | A rules file of about 180 lines: three roots, standing behaviour as principles with their reasons, a routing table to the reference files, the maintenance rule. |
| [kit/skills/skill-library/](kit/skills/skill-library/SKILL.md) | The router: an index of every installed skill, one line each, and the code words. |
| [kit/skills/learn/](kit/skills/learn/SKILL.md) | Routes each of your corrections to the place that owns it (a hook, a skill, a reference file, the rules file, memory) instead of growing the rules file. |
| [kit/skills/notes-editing/](kit/skills/notes-editing/SKILL.md) | How to write to the vault without damage: through the connector, one passage at a time, and the connector's known traps. |
| [kit/skills/daily-note/](kit/skills/daily-note/SKILL.md) | The daily note as a running log, every time stamp taken from a clock script. |
| [kit/skills/task-board/](kit/skills/task-board/SKILL.md) | The task board kept as a secretary: every input checked against it, single tasks patched safely, each write verified by a script. |
| [kit/skills/process-meeting/](kit/skills/process-meeting/SKILL.md), [pre-meeting/](kit/skills/pre-meeting/SKILL.md) | A transcript turned into a meeting note with the decisions on top; the one-screen brief before the next meeting of the series. |
| [kit/skills/process-inbox/](kit/skills/process-inbox/SKILL.md) | The inbox routed behind its gate; wiki articles and data-source notes. |
| [kit/skills/literature-note/](kit/skills/literature-note/SKILL.md) | The literature card with what was read and where each point sits, and the routes to a paper's full text. |
| [kit/skills/do-it-later/](kit/skills/do-it-later/SKILL.md) | A queue of deferred work, each entry a spec that runs cold in a fresh session. |
| [kit/skills/talk/](kit/skills/talk/SKILL.md), [progress-report/](kit/skills/progress-report/SKILL.md) | A talk from the brief to a deck read slide by slide, with a speaker guide like an assembly manual; a report for a period drawn from the vault. |
| [kit/skills/workflow-health/](kit/skills/workflow-health/SKILL.md) | A weekly measurement of the sessions and the vault without a model, and the judgement on top when you ask. |
| [kit/skills/dictionary/](kit/skills/dictionary/SKILL.md) | A dictation dictionary in one note, exported to Wispr Flow and to term lists. The worked example of a skill in eight layers. |
| [kit/skills/keep-awake/](kit/skills/keep-awake/README.md) | Keeps the computer awake through a long job, also with the lid closed, and pauses the job on battery at 20 %. Windows script, macOS note. |
| [kit/hooks/](kit/hooks/README.md) | `guard.py`, the guard on originals, the write scope, the read block, git and the battery pause, with a self-test, and the settings to register it; `output_check.py`, the writing check; `setup_refs.py`, which lists who names a thing in the setup and which references point at nothing, and a git hook that runs it on every commit. |
| [kit/rules/setup-changes.md](kit/rules/setup-changes.md) | A path-scoped rule, loaded whenever the agent opens a file of the setup: a change is finished when everything that names the changed thing agrees with it. |
| [kit/context/automation-map.md](kit/context/automation-map.md) | The table of everything that runs without a session asking for it, and what depends on each. |
| [kit/agents/](kit/agents/) | Three executor agents, routed by kind of work: standard, hard, and deep research. |
| [kit/templates/](kit/templates/) | A meeting note with a decisions table, a literature card with a `read:` field, a daily note, a one-screen handover note. |
| [kit/tools/](kit/tools/README.md) | The archive script for the agent's notes, how to read `/context`, and the literature tools of guide 07. |
| [CREDITS.md](CREDITS.md), [LICENSE.md](LICENSE.md), [CHANGELOG.md](CHANGELOG.md) | Who and what this builds on, the licences, the versions. |

The kit's Python scripts use the standard library only (the output check also reads frontmatter
with PyYAML when it is installed), and each has its paths in a configuration block at the top; the
keep-awake script uses PowerShell, which every Windows computer has. The agent runs them for you.

## How to start

1. **Have the first track in place.** Claude Code installed and signed in, as in Kevin's guide 01,
   and Python 3.8 or later. If you have worked through his first week, even better.
2. **Read the two guides 06**: [Kevin's](https://github.com/KevinMSmith/ai-research-starter-kit/blob/main/guide/06-data-and-the-rules.md)
   and [this kit's](guide/06-data-and-the-rules.md). They decide what the agent may read.
3. **Download this kit** (the green **Code** button, then **Download ZIP**, then unpack it) or clone
   it with git, into a folder outside your cloud drive.
4. **Open the kit's folder in Claude Code** and type: *Read START-HERE.md and set me up.* The agent
   asks where your code, data and notes are, lays your rules file from the template, installs the
   skills and the guard, and ends with a test in which the guard refuses to change an original. About
   an hour, in two sessions.
5. **Read guide 02 and guide 05** in the first week. Read guide 04 before the first job that runs
   while you are away, and guides 07 and 08 when you set up your literature and your vault.

## Optional add-ons

Not part of the kit, and none is needed. Guide 03 says more about each.

- **ponytail**, a Claude Code plugin from the marketplace `DietrichGebert/ponytail`: "lazy senior
  dev" code style and review, the smallest change that solves the task. Adds skills, not
  permissions.
- **Agent-Reach**, a command-line tool for pages behind a login or a bot block. Gated: ask first,
  every time, because it acts on your logged-in sessions and sends addresses through third parties.
- **Claude in Chrome**, Anthropic's browser extension: the agent works in your own browser, with
  your sign-ins. Gated by its per-site permissions, and treated like Agent-Reach.
- **Obsidian plugins** the vault side rests on: Local REST API (the connector the agent writes notes
  through), Dataview (queries over note properties), Templater (templates and startup scripts) and
  Relay (folders shared in real time, which the agent edits one passage at a time).

## What is left out on purpose

Nothing of the author's projects is in the kit: no data, no notes, no names of partners or sites.
The cases in the guides are anonymised. The kit holds the method and the mechanisms, not the content.
It stays deliberately small for what it covers: one hook, three agents, four templates, and skills
only for workflows the author ran and corrected for months before they were written down. Install
the ones your work has, and add what it needs when it needs it; the `learn` skill and guide 03 say
where.

## Credits and licence

Built on Kevin Michael Smith's starter kit (structure, register, and the guard it derives from), and
on Xule Lin's Research Memex for the vault's first structure; see [CREDITS.md](CREDITS.md). Texts
under CC BY 4.0, scripts under MIT ([LICENSE.md](LICENSE.md)), the same two licences as the first
track, so the two kits can be combined. Made in conversation with Claude Code.
