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
and 06 instead of repeating them.

## Other sources

- **Anthropic's Claude Code documentation** (code.claude.com/docs, read November 2026): the hooks
  protocol, the skills settings (`skillOverrides`, `disable-model-invocation`), the 200-line target
  for `CLAUDE.md`, and the memory limits quoted in the guides.
- **The six design shifts** of guide 02: from a summary of an Anthropic note on smaller system prompts
  for newer models, which circulated in November 2026 and whose original could not be located; the
  one quotation in the guide is from The Decoder, 2 July 2026.
- **The eight layers** of guide 03: the layer names follow a practitioner article on building a skill
  library, summarised to the author in November 2026 and not located since; the mapping onto Claude
  Code is the author's.
- **Matt Pocock's skills collection** (github.com/mattpocock/skills): its `ask-matt` router, which the
  author adapted for his own setup, is the model for `skill-library`. No text is copied.

## Author

Johannes Wildfeuer, PhD student, DTU (Technical University of Denmark), jniwi@dtu.dk. The kit was
made in conversation with Claude Code, Anthropic's AI agent; the author reads and decides every text
and script before a release.
