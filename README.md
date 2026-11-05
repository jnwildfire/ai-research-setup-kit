# An AI research setup kit: the second track

*For researchers who already have files, data and perhaps code or a notes vault, and want an
artificial intelligence (AI) agent to work across all of it under rules they set: what it reads, what it may change, what it
checks before anything leaves. You need to know what a terminal is; you do not need to program.
The agent sets the kit up with you and explains each step before it takes it.*

Johannes Wildfeuer, Technical University of Denmark (DTU), November 2026 (jniwi@dtu.dk). Draft v0.1, not yet released.

## The first track, and this one

This kit is the second track after Kevin Smith's
[AI research starter kit](https://github.com/KevinMSmith/ai-research-starter-kit), which came out of
the DTU seminar "Working with an AI agent in research" (3 November 2026). His kit is the
prerequisite: it installs Claude Code, explains the method (originals kept unchanged, every claim
traced to its source, corrections made into rules) and builds one knowledge base per project, for
someone who has never used a terminal.

This kit starts where his ends: with a researcher whose work already spans several projects, code
repositories, a shared data drive and a notes vault, and who wants one setup across all of it.

## What this kit adds

1. **Three roots instead of one folder**: code in git, data on the institution's drive, knowledge in
   a notes vault, never mixed, with data tiers inside the data root ([guide 01](guide/01-three-roots.md)).
2. **What the agent reads before the first word**, measured and chosen: the desk, tokens in plain
   words, six design shifts for current models, and a rules file under 200 lines
   ([guide 02](guide/02-what-the-agent-reads.md)).
3. **A skill library**: skills in eight layers, loaded only when needed, switched per project, with a
   router and a worked example, the dictation dictionary ([guide 03](guide/03-skills-and-the-library.md)).
4. **A guard with a write scope**: originals refused, writes outside the roots asked, grants written
   into the plan of a job that runs while you are away, and a night-shift rule with a morning report
   ([guide 04](guide/04-guards-and-night-shifts.md)).
5. **What research adds to the method**: the paper itself before a claim carries weight, a basis on
   every number, the agent as referee, faults made into rules, decisions as tickets, one base for
   several people, which model for which work ([guide 05](guide/05-the-research-method.md)).
6. **The research-data case**: household and partner data, a vault on the institution's drive, and
   what never goes into a public repository ([guide 06](guide/06-data-and-the-rules.md)).

## What is in the kit

| Part | What it is |
|---|---|
| [START-HERE.md](START-HERE.md) | The instructions the agent follows to set you up. You may read them; you do not need to. |
| [guide/](guide/) | Six guides, ten to twenty minutes each, in the order above. |
| [kit/CLAUDE.md.template](kit/CLAUDE.md.template) | A rules file of about 130 lines: three roots, standing behaviour as principles with their reasons, a routing table, the maintenance rule. |
| [kit/skills/skill-library/](kit/skills/skill-library/SKILL.md) | The router: an index of every installed skill, one line each. |
| [kit/skills/learn/](kit/skills/learn/SKILL.md) | Routes each of your corrections to the place that owns it (a hook, a skill, the rules file, memory) instead of growing the rules file. |
| [kit/skills/dictionary/](kit/skills/dictionary/SKILL.md) | A dictation dictionary in one note, exported to Wispr Flow and to term lists. The worked example of a skill in eight layers. |
| [kit/hooks/](kit/hooks/README.md) | `guard.py`, the guard on originals and on the write scope, with a self-test, and the settings to register it. |
| [kit/agents/](kit/agents/) | Three executor agents, routed by kind of work: standard, hard, and deep research. |
| [kit/templates/](kit/templates/) | A meeting note with a decisions table, a literature card with a `read:` field, a daily note, a one-screen handover note. |
| [kit/tools/measure_context.md](kit/tools/measure_context.md) | How to read `/context` and what to cut. |
| [overview/](overview/README.md) | The graphical overview of the whole setup: step two, not yet made. |
| [CREDITS.md](CREDITS.md), [LICENSE.md](LICENSE.md), [CHANGELOG.md](CHANGELOG.md) | Who and what this builds on, the licences, the versions. |

The kit's two Python scripts, `guard.py` and `export_dictionary.py`, use the standard library only.
The agent runs them for you.

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
   while you are away.

## What is left out on purpose

Nothing of the author's projects is in the kit: no data, no notes, no names of partners or sites.
The cases in the guides are anonymised. The kit holds the method and the mechanisms, not the content.
It is also deliberately small: three skills, one hook, three agents, four templates. Add what your
own work needs when you need it; the `learn` skill and guide 03 say where.

## Credits and licence

Built on Kevin Michael Smith's starter kit (structure, register, and the guard it derives from); see
[CREDITS.md](CREDITS.md). Texts under CC BY 4.0, scripts under MIT ([LICENSE.md](LICENSE.md)), the
same two licences as the first track, so the two kits can be combined. Made in conversation with
Claude Code.
