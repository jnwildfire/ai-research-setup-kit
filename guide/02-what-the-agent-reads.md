# 2. What the agent reads before you type a word

*Why the quality of an answer is decided before the question, and how to choose what goes into the
agent's view. About fifteen minutes to read. Kevin's lesson was "choose what the model reads"; this
guide shows what that means inside a terminal agent, where you lay the desk yourself.*

## The desk

In a chat window, a project's files sit in a drawer: a small drawer is read whole, a large one is
searched, and only what the search finds reaches the model. In Claude Code there is no search in
front of the model. Before you type a word, the agent already has a stack on its desk:

- Claude Code's own instructions and the descriptions of its built-in tools;
- your **rules file** (`CLAUDE.md`), the one in your user folder and the one in the folder where the
  session started;
- the one-line **description of every skill** it could use;
- the **instructions and tools of every connector** that is switched on (a Model Context Protocol, or MCP, server: a
  program that gives the agent access to a service such as a reference manager or a notes app);
- the descriptions of your **agents**;
- the index of its **memory** for this folder.

Everything you then say, every file it opens and every answer it gives goes on the same desk, and
stays there for the whole session. On every turn, the model reads the entire desk again. When the
desk is full, the agent sweeps it: it keeps a summary and forgets the rest.

Three things follow. **You lay the desk**, by what you write into the rules file and what you
switch on. **The stack is paid for on every turn**, in your plan's allowance and in the model's
attention: an instruction in a crowded desk is followed less reliably than the same instruction on
a clear one. **A long session degrades**, so a new task is a new session, and the files, not the
conversation, hold what must be remembered.

## Tokens, in plain words

A **token** is the unit the model reads and is billed by: a short word, or a piece of a longer one.
On average a token is about three quarters of an English word, so a page of plain text is roughly
600 to 800 tokens. The **context window** is how many tokens fit on the desk at once; for current
Claude models it is several hundred thousand.

What costs a lot: the agent reading a large file or a data table itself, instead of running a script
that reads it and reports a summary; a long session in which every early turn is re-read on every
later one; connectors and skills switched on that the work never uses. What costs little: your own
sentences, however polite: a "please" costs a token or two.

In the author's own setup, the stack before the first word was 60,000 to 66,000 tokens (median of
73 sessions, measured in October 2026), with 15 to 30 sessions a week. The fixed stack, not the
work, was the largest share of the cost. `kit/tools/measure_context.md` shows how to measure yours.

## The design rule: six shifts

Anthropic has said that it cut most of Claude Code's own system prompt for its newer models,
because, in the words of an Anthropic engineer, "this new class of models want a smaller system
prompt" (quoted by The Decoder, 2 July 2026). A summary that circulated in November 2026 drew six
consequences for anyone who writes instructions for an agent. The original text behind that summary
could not be found, so read the six as the design rule this kit adopts, not as Anthropic's words.

1. **Judgement over hard rules.** Write the reason with the rule, in one clause. A capable model
   applies a reason to the case the rule did not foresee; it applies a bare prohibition rigidly or
   not at all. Rules that are really mechanisms ("never change this folder") become hooks.
2. **Interfaces instead of examples.** Give the shape of the result (a template, a table with named
   columns, a script with a `--check`) rather than three examples of it. Examples narrow a capable
   model to the examples.
3. **Progressive disclosure.** Only what applies everywhere sits on the desk from the start; the
   rest is a short description that loads its body when it is needed. That is what skills do.
4. **Short tool descriptions, said once.** Every description is read on every turn. Say what the
   tool or skill does, when to use it, and one "not for"; never the same rule in two places, because
   two copies drift apart.
5. **Let memory work.** Claude Code now keeps its own notes on where each project stands. Your job
   is to keep each memory file to one screen, a resume point and not a journal.
6. **Rich references.** Point to one good example of the artefact (a real meeting note, a real
   card) instead of describing its format in prose.

## What belongs where

The question for every rule is: does something trigger it? If nothing would prompt the agent to
look it up, it belongs on the desk. If it applies only once the agent is doing a particular thing,
it belongs where that thing lives.

| Kind of instruction | Where it goes | Example |
|---|---|---|
| Fires on ordinary output, and the default would be wrong | the **rules file**, one line with its reason | every number carries its basis |
| Applies once a task of a kind starts | a **skill**: its procedure, its checks | how to turn a transcript into a meeting note |
| Mechanical, and must never fail | a **hook** | originals are never changed |
| Applies to a kind of file | a **path-scoped rule** (`.claude/rules/`, loaded when a matching file is opened) | how project code reads paths and saves data |
| Where a project stands, a preference | **memory** | the next step on the data pipeline |
| Long reference material, read on a trigger | a **reference file**, named in the rules file's routing table | how each data source is documented |
| Why a rule exists, when it was set | the **changelog** | the incident that led to the rule |

## The 200-line target

Claude Code's documentation says: "target under 200 lines per CLAUDE.md file. Longer files consume
more context and reduce adherence" (read November 2026). The template in `kit/CLAUDE.md.template` is
about 130 lines with its placeholders. When yours passes 200, something moves out before anything
comes in; the `learn` skill (guide 03) does that routing every time you correct the agent.

The usual reasons a rules file grows, and where the text goes instead:

- **Incident stories.** "Caught on 14 March: ..." is the reason for a rule, but the story belongs
  in the changelog. The rule keeps one clause of reason.
- **Procedures.** Six steps for processing a meeting are a skill, which loads only when a meeting is
  processed.
- **Project facts.** Who operates which building, which meter is which: those are the project's notes.
- **Repetition.** A rule that is also in a skill or a hook is cut from the rules file.

## Memory: one screen

Claude Code keeps a memory folder per project, with an index (`MEMORY.md`, of which it loads the
first 200 lines or 25 KB) and one file per topic. It writes these itself while you work. What it
does not do is keep a topic file short, and a resume point that is appended to stops being a resume
point: in the author's setup, one memory file grew to 41 KB through Claude's own saves. Keep each one
to a screen; when one grows, its history moves into a handover note in the vault
(`kit/templates/handover-note.md`), and the memory keeps where things stand and the next step.

## Terms used

- **Context window**: everything the model reads on one turn; the desk.
- **Token**: the unit the model reads and is billed by, about three quarters of a word.
- **Rules file**: `CLAUDE.md`, read at the start of every session in its folder.
- **Skill**: a folder with a `SKILL.md`: a short description always on the desk, a body loaded when
  the skill is used.
- **Connector (MCP server)**: a program that gives the agent tools for a service.
- **Hook**: a script Claude Code runs before or after an action of the agent, which can refuse it.
- **Memory**: the agent's own notes on where each project stands, kept in your user folder.
- **Path-scoped rule**: a rules file in `.claude/rules/` that loads only when the agent opens a file
  matching its `paths:`.
