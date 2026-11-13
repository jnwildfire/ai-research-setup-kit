# Changelog

## v0.1.3 (unreleased, 9 November 2026)

The fourth round: the author's answers of 9 November 2026 to the questions of the night shift, and a
review of v0.1.2 by Kevin Smith's Claude (points 1 to 3 accepted, point 4 taken as information).

- **The guard parses shell commands instead of matching patterns.** Bash and PowerShell are read the
  way the shell reads them (quotes, escapes, `$( )`, heredocs, `pwsh -Command` bodies, script blocks,
  variables from the environment or set earlier in the same command); only a verb's path arguments
  and the redirect targets count as paths, so a quoted `$env:TEMP`, a sed script, a grep pattern or a
  heredoc line no longer trips it. The write scope is never inspected inside a `-Command` body or a
  heredoc; the folders of originals keep a substring scan over the whole text as a backstop. A
  `cd`, `git -C` or any argument into a blocked folder is refused, and so is a blocked path written
  in code handed to an interpreter. Before the change it was replayed on the author's 30,380
  distinct shell commands of five days.
- **Grants by folder or file**: a folder opens with its subfolders, a file alone, for reading and
  for saving alike; `python guard.py --grant read|write PATH...` writes the grant file.
- **Secrets are not for the model to read** (review point 3): `.env`, `.env.*`, `~/.ssh/**`,
  `~/.claude/.credentials.json`, `*.pem`, `*.key`, `*credentials*`, `*token*.json` are refused to
  Read, Grep and the shell's readers; a script may still load them, listing a name and copying the
  file pass, source code and `.env.example` and kin pass.
- **git**: `git branch -d` (git itself refuses an unmerged branch) and `git worktree remove` pass; a
  remote branch deletion, or a local one whose name the guard cannot read, asks; `branch -D` stays
  refused. A deposit is any new file or folder, so `mkdir -p` and `cp` into a deposit folder pass; a
  copy out of an `existing-only` archive is a read. Self-test 209 of 209 on Windows; each new rule
  switched off turns its cases red.
- **A note moved into a deposit folder by the folder's name** (11 November 2026): an Obsidian
  connector reads a destination ending in `/` as "into this folder, keeping the file name", but the
  guard checked it as written, found the folder existing and refused the move as a change to the
  originals. A destination ending in `/` or `\` is now that folder plus the note's own name; a name
  already filed there is still refused. Found filing a processed inbox note on the author's computer.
  Self-test 213 of 213 on Windows.
- **A filed transcript takes a corrections block** (12 November 2026): misheard names corrected only
  in the meeting note met the next reader of the transcript again. A transcript stays deposit-only,
  with one exception: an Edit or Write that changes nothing outside a block from `NOTE CORRECTIONS`
  to `NOTE END CORRECTIONS`, at the top (after the `WEBVTT` line in a `.vtt`) or the very end, with
  no blank line and no `-->` inside, so a `.vtt` stays valid. The top was chosen because a reader
  starts there; a separate corrections file was rejected because a reader of the transcript alone
  would not see it. Shell edits stay refused. 15 new self-test cases.
- **Guide 04**: grants by folder or file; `permissions.denyInsteadOfPrompting` (Claude Code 2.1.319,
  scope unconfirmed) as the thing to test on the next night shift through a launch-time settings
  file, with the guard's unattended refusal kept as the fallback (review point 2); Claude Code's
  sandbox exists on macOS, Linux and WSL2, not on native Windows, where the guard is the substitute
  (review point 4).
- **A change to the setup carries its dependents** (13 November 2026): a skill had been extended
  and the question came up whether the files that name it follow by themselves. They do not. New:
  the path-scoped rule `kit/rules/setup-changes.md` (a change is finished when everything that
  names the changed thing agrees with it; it loads whenever the agent opens a file of the setup),
  the script `kit/hooks/setup_refs.py` (`--who <name>` lists every line that names a thing;
  without an argument it lists paths that do not exist, steps beyond a skill's last and skills
  without an index row; `--self-test` plants six dead references among sound twins), a git
  `pre-commit` hook that runs it on commits touching the setup, a check in `learn`, a row in the
  automation map, a paragraph in guide 02. On the author's setup the first run found no dead
  reference; three false alarms were designed out before that (a path under `$HOME`, a sentence
  about the past, a `../` path relative to the file's own folder).
- **Effort, in Anthropic's words** (review point 1): guide 05 and the three agents no longer say
  "the highest effort"; `medium` is Opus 5.5's default, run an effort sweep on your own evals rather
  than carrying settings over, raise for the hard case and keep what the sweep justifies.
- **Credits**: "reconnaissance first" was said by Kevin Smith in the seminar of 3 November 2026, not
  in his public kit; the talk rules follow Patrick Winston's lecture, now named.
- **The seminar slides**: the second half of the talk of 3 November 2026 at DTU, as a PDF in
  `docs/seminar/`, linked from the README; CC BY 4.0 like the kit's texts, credit "Johannes
  Wildfeuer, DTU".

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
