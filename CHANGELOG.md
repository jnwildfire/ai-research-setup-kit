# Changelog

## v0.1.2 (unreleased, 6 November 2026)

The third round: the author's own setup was restructured on the night of 5 to 6 November 2026 along
the lines of v0.1.1, and what it added is mirrored here in generic form.

- **The map.** `docs/index.html`, the whole setup on one page, published with GitHub Pages and linked
  from the top of the README. `overview/` now only points there.
- **Eleven skills for a notes vault**, each in the eight-layer layout: `notes-editing` (through the
  connector first, one passage at a time, and `references/connector-gotchas.md`), `daily-note` (with
  `scripts/now.py`: every time stamp comes from the script, never from an estimate), `task-board`
  (the checker: every input is checked against the board; `scripts/open_tasks.py` with `--check`),
  `process-meeting`, `pre-meeting` (with `scripts/series_digest.py`), `process-inbox` (the inbox gate
  as a folder rule, wiki articles and data-source notes), `literature-note` (the card with `read:`
  and the routes to full text), `do-it-later` (a queue of specs that run cold), `talk` (with a
  speaker guide written like an assembly manual), `progress-report`, and `workflow-health` (with
  `scripts/workflow_health.py`: the sessions and the vault measured without a model, paths and
  thresholds in a configuration block). `skill-library` indexes them and holds the code words;
  `learn` routes to reference files too and checks that a file it writes into is still in shape;
  `keep-awake` names the guard's wider matcher.
- **`guard.py`**: a configurable read block for the cloud drive outside the roots (Read, Glob, Grep
  and the shell's reading commands, and a recursive search started above the drive), read grants
  (an exact path, or a folder with `/**`), a third strictness `existing-only` for an archive a script
  fills, and git guardrails (force push to a protected branch, `reset --hard`, `clean`, `branch -D`,
  `checkout -- .` and `restore .` refused; other branch deletions asked). The matcher in
  `settings.example.json` adds Read, Glob and Grep. A redirect inside `$( ... )` is read without the
  closing bracket, so `2>/dev/null)` is no longer taken for a file outside the roots. Self-test of
  156 checks; each rule was switched off in turn to see its cases fail.
- **`kit/hooks/output_check.py`**: dashes inside sentences, abbreviations before their long form,
  bare issue numbers, frontmatter that does not parse; 26 checks, with and without PyYAML.
  **`kit/tools/archive_notes.py`**: the thirty-day archive of the agent's notes as a script, with a
  dry run, a log line per move and a self-test. `kit/tools/README.md` lists the tools.
- **`kit/CLAUDE.md.template`** in the shape of the author's rules file after it went from 344 lines
  to 196: principles with their reasons, one line each for what a job may do unattended, the AI
  declaration on what leaves, the brief, the task-board checker and the model routing by kind of
  work, two layout rules for the data root, a routing table to the reference files (the automation
  map among them), and an optional "Compact instructions" section. About 180 lines.
- **`kit/context/automation-map.md`**, and in guide 04 sections on the guard's new verdicts, the
  automation map, and preparing for a compaction (auto-compact off, the save step before `/compact`,
  the "Compact instructions" section as the documented lever, a `PreCompact` hook can only block).
  Guide 04 also says that the two environment variables of background jobs are Claude Code's own.
- **Guide 03**: the trigger test as the Checks layer of a library, with the author's eight prompts
  and their expected skills. **Guide 08**: the reconnaissance pass and the dictation lane, after
  Kevin Smith's order (reconnaissance first, then the author's dictation), and the archive script.
- START-HERE installs the new skills, the guard's new settings, the read-block test and the
  automation map; guide 02 names the template's new length.

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
