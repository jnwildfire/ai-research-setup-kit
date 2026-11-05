# Changelog

## v0.1.1 (unreleased)

The second round, after the author's review of v0.1 on 5 November 2026.

- **General first.** The README, START-HERE and guides 02 to 04 state each idea (the rules file,
  skills, hooks, memory, the desk) before its form in Claude Code, and name the equivalent in Codex
  CLI, OpenAI's command-line interface (CLI) agent, from its documentation of November 2026. Nothing of the Claude Code detail was removed.
- **Guide 07, literature and the agent**, with `kit/tools/literature-stack.md`: reference manager
  and citation keys, literature notes, a full-text connector, MinerU for pivotal papers read by
  line, scite and Scopus for checks and discovery, NotebookLM optional; a test for each part.
- **Guide 08, the knowledge base**: the vault in lanes, the author's layout as one example,
  Research Memex (Xule Lin) as the starting structure and credited, permanent notes as an optional
  lane, and the agent-outputs lane that archives itself after thirty days without an edit.
- **`kit/skills/keep-awake/`**: a Windows keeper (no idle sleep, the lid-close action set to "Do
  nothing" for the session and restored, a battery watch) and a macOS note. Tested without
  elevation; the battery path with a simulated reading.
- **`guard.py`**: the battery pause ("paused: battery at N %, connect power or say continue"), and
  a refusal with a note for the morning report instead of an ask when a background job reports
  that nobody is at the keyboard. Self-test of 63 checks.
- **Guide 04**: the never-list as the reader's own (Kevin Smith's, plus a payment), the two
  environment variables of background jobs as observed behaviour, keeping the computer awake.
- **Optional add-ons** named in the README and guide 03: ponytail, Agent-Reach behind its
  ask-first gate, Claude in Chrome, and the Obsidian plugins the vault side rests on.
- `LICENSE.md`: PowerShell scripts under MIT, like the Python ones.

## v0.1 (unreleased)

The first version, for the attendees of the seminar at the Technical University of Denmark (DTU) "Working with an AI agent in research"
(3 November 2026) and its follow-up workshop. A draft: the author reviews everything before release.

- README and START-HERE in the shape of Kevin Smith's starter kit, as its second track.
- Guides 01 to 06: three roots; what the agent reads; skills and the library; guards and night
  shifts; what research adds to the method; data and the rules.
- `kit/CLAUDE.md.template`: a rules file under 200 lines.
- Skills: `skill-library` (router and index), `learn` (routes corrections), `dictionary` (dictation
  dictionary with its export script, the worked example of the eight layers).
- `kit/hooks/guard.py`: originals denied, writes outside the roots asked, grants per job, a
  self-test of 51 synthetic checks.
- Three executor agents, four note templates, and a text on measuring the context.

Planned for v0.2: the graphical overview (`overview/`); the skills in their final form after the
author's own setup has been restructured along the same lines; trigger tests for the skills.
