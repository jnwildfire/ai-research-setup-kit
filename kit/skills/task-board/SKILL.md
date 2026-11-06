---
name: task-board
description: >-
  Keeps the task board as the person's secretary: checks every input (a transcript, a note, a
  mail, progress in an issue tracker) against the board and updates it, refines new entries,
  patches single tasks safely, verifies each write. Use on any board change ("add a task",
  "close the task", "update the board", "what is on my board") and as the check step of other
  skills.
---

# Task board

One note in the vault is the single list of the person's tasks. The agent keeps it as a secretary
would: the board reflects reality without the person having to ask, and the daily note's
suggestions draw on it. The person schedules; the agent maintains.

## The checker (a standing rule)

Every input that reaches the agent is checked against the board, and the board is updated: a
transcript, a note, a mail, progress in the issue tracker, a finished piece of work. The skills
that process meetings, the inbox and the daily note call this as a check step; in any other session,
run it when such an input arrives. The rules file carries it as one line, because nothing else
would prompt the check.

1. From the input, list what is or changes a task: something finished, advanced, blocked,
   rescheduled by someone else, newly asked of the person, or no longer needed.
2. Find the candidates: `python -I <skills>/task-board/scripts/open_tasks.py <terms>`, with the names,
   projects and issue numbers from the input.
3. For each item decide: it closes a task (tick it, with a one-line note in the task's context
   section), advances it (update its `next::`, or one line of context), is new (an inbox line on the
   board, refined as below, not scheduled), or is uncertain. **Where the match is uncertain, ask**, in
   one line naming the task id and the input.
4. Write through `notes-editing`, verify (below), and say in the report what changed on the board.

## Procedure

1. **Read narrowly.** A long board is expensive to read whole: use the script, or a search for one
   id, or the heading map, or a line range off disk.
2. **One task, one line, on the board only.** A daily note shows tasks through a query on their
   scheduled date, never as a copy: two checkboxes for one task stop agreeing.
3. **The person schedules.** The agent never sets a first scheduled date (`do::`) and never changes
   a priority on its own; it may suggest a day's set in chat. The exception: the person hands over the
   choice ("plan my day", "you pick").
4. **Refine new entries.** A raw one-liner in the board's inbox becomes one action line with an
   estimate, a created date, a proposed priority, a next step for the important ones, and a new block
   id, plus a context section for any reasoning. Ask only what cannot be inferred: the priority, and
   whether a real deadline exists.
5. **Patch one task by its block id**, or the whole heading section when several tasks change or a
   task has subtasks (`references/board-format.md`). Stage a section replace: the section's text to a
   scratch file, the new text built from it, compared, patched, compared again with what landed.
6. **Verify every write**: `open_tasks.py --check` before and after (the task count, duplicate ids,
   lines without an id, doubled list markers), and the heading map lists every id you expect.

## Working rules

- **Capture the next step at the end of a work session, never at a cold start**, from what the
  person says while the work is still loaded: the most useful thing the agent does for the board.
- **A slipped task is data, not a verdict.** Raise a task only when its carry count says something
  (not a priority, mis-scoped, blocked on something unnamed).
- **Guard against the board becoming the work**: if a session drifts into keeping the system instead
  of shipping, say so.
- **A carry writes a counter, not a story**: `carried::` goes up by one; a changed plan is one line
  in the context section, replacing the previous such line.

## Resources

- `references/board-format.md`: the line format, the fields, the block ids and the patch rules.
- The board, a context note beside it (one section per task, for reasoning and history), and an
  archive for done tasks.

## Scripts

`scripts/open_tasks.py [terms] [--done] [--check] [--board <file>]`: the open tasks one line each,
filtered by any term; `--check` for the verification counts (exit 1 on a duplicate id or a doubled
marker); `--self-test`. Set `NOTES_ROOT` and `BOARD` at the top once.

## Checks

- `--check` before and after every write: the totals as intended, no duplicate id, every line with an
  id, no doubled marker.
- No scheduled date set or changed unless the person handed over the choice.
- Every input of the session went through the checker; uncertain matches were asked.

## Learn

A new patch behaviour goes into `references/board-format.md` with its date; a correction to how the
board is kept goes into this file through `learn`.
