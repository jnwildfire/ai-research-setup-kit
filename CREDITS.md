# Credits

## Kevin Michael Smith, AI research starter kit

https://github.com/KevinMSmith/ai-research-starter-kit (read in its version of November 2026)

This kit is built as the second track to Kevin Smith's starter kit for working with an artificial
intelligence (AI) agent in research, and it owes him three things.

- **The structure and the register.** A README for people, a `START-HERE.md` that the agent follows
  with them, numbered guides that end with the terms they use, a folder of things to install, and
  plain words throughout. The shape is his, so that his readers find their way here. No text of his
  is copied; where an idea of his is used, the guide says so.
- **The guard.** `kit/hooks/guard.py` derives from his `knowledge-base/tools/hooks/guard_raw.py`
  (MIT): the idea of a hook that refuses any change to the originals, the way shell commands are
  split into statements, and the lists of destructive and copying commands. It reached this kit by
  way of the author's own guard for immutable folders. The write scope, the grants, the three
  verdicts, the notes-connector check and the self-test are added here.
- **The method this kit extends**: deposit, never edit; every claim says what it rests on; every
  number carries its basis; corrections become rules the same day; the product is judged, not the
  plan; the night-shift rule; executors that say what they may write.

His licence notice for `guard_raw.py`, as required by the MIT licence:

    Copyright (c) 2026 Kevin Michael Smith

    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
    associated documentation files (the "Software"), to deal in the Software without restriction,
    including without limitation the rights to use, copy, modify, merge, publish, distribute,
    sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies or
    substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
    NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
    OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
    CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

His texts are under CC BY 4.0. This kit quotes none of them at length; it links to his guides 01
and 06 instead of repeating them. The never-list of guide 04 ("never a simulation, an account, an
install, a rule") is his; the kit adds a payment and leaves the list to the reader.

## Xule Lin, Research Memex

https://research-memex.org (read 5 November 2026)

The author's vault started from the Obsidian structure that Research Memex suggests (an inbox,
literature notes, permanent notes, AI conversations, research projects, daily notes, maps of
content, templates, attachments), and guide 08 shows that structure as the place a reader may
start from. The folder list in guide 08 paraphrases Research Memex's Obsidian setup guide; no
other text is copied. Research Memex says: "Use this work, including for AI training. Attribution
is the only ask." Copyright (c) 2025 Xule Lin, MIT License. Its requested attribution:

    Based on [Research Memex](https://research-memex.org) by Xule Lin
    Licensed under the MIT License

## Other sources

- **Anthropic's Claude Code documentation** (code.claude.com/docs, read November 2026): the hooks
  protocol, the skills settings (`skillOverrides`, `disable-model-invocation`), the 200-line target
  for `CLAUDE.md`, the memory limits quoted in the guides, and the Chrome integration named in
  guide 03. Two environment variables in guide 04 and the guard, `CLAUDE_JOB_DIR` and
  `CLAUDE_CODE_SESSION_ATTENDED`, are not from it: they were observed in background jobs on the
  author's computer and are described as observed.
- **OpenAI's Codex documentation** (read 5 November 2026 at learn.chatgpt.com, where
  developers.openai.com/codex now leads): the pages on `AGENTS.md`, skills, hooks, memories and
  Model Context Protocol (MCP) servers, for the equivalents in Codex CLI, OpenAI's command-line
  interface (CLI) agent, named in the README and guides 02, 03, 04 and 07.
- **Microsoft's Windows power interfaces**: `SetThreadExecutionState`, `GetSystemPowerStatus` and
  `powercfg`, used by the keep-awake script, whose approach comes from the author's own keep-awake
  script.
- **Tools named but not included**: Zotero, Better BibTeX, ZotLit, MinerU, scite, Scopus and
  NotebookLM (guide 07); the ponytail plugin (marketplace `DietrichGebert/ponytail`, MIT licence),
  Agent-Reach, Claude in Chrome, and the Obsidian plugins Local REST API, Dataview, Templater and
  Relay (guide 03). Each is its makers' work under its own licence; the kit describes only how they
  fit together.
- **The six design shifts** of guide 02: Anthropic's own, from its post on Claude's official Instagram
  account on the smaller system prompt for more capable models (November 2026); the engineer's
  quotation in the guide is from The Decoder, 2 July 2026.
- **The eight layers** of guide 03: the layer names follow a practitioner article on building a skill
  library, summarised to the author in November 2026 and not located since; the mapping onto Claude
  Code is the author's.
- **Matt Pocock's skills collection** (github.com/mattpocock/skills): its `ask-matt` router, which the
  author adapted for his own setup, is the model for `skill-library`. No text is copied.

## Author

Johannes Wildfeuer, PhD student, DTU (Technical University of Denmark), jniwi@dtu.dk. The kit was
made in conversation with Claude Code, Anthropic's AI agent; the author reads and decides every text
and script before a release.
