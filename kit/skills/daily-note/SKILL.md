---
name: daily-note
description: >-
  Writes the daily note: which day an entry belongs to, creating a missing note from the
  template, progress-log entries stamped from the clock script, and what carries over. Use
  whenever something is logged ("log this", "update the daily note", "create today's note") and
  at the end of finished work. Not for changes to the task board (task-board).
---

# Daily note

The daily note is a running protocol: the agent logs to it as things happen, without being asked.
It records the event and links the artefact (the note, the commit, the file), not the conversation
about it. Read three months later, it should say what happened that day and where the results are.

## Procedure

1. **Run the clock script before every entry**, not once per session:
   `python -I <skills>/daily-note/scripts/now.py`. It prints `now`, `stamp`, the working date, the
   note's path and whether it exists. Every time stamp in the entry and in the note's
   `date-modified` comes from that output. A model has no clock: a stamp it estimates is a guess
   written down as a fact.
2. **The working day may end after midnight** (`DAY_ENDS_AT` in the script; the author's ends at
   06:00, because he works in long evening blocks and one session split across two notes reads
   badly). The script decides it per entry, so a long session logs to the new date once the
   boundary has passed.
3. **If the note is missing, create it** at the path the script names, from the daily-note template
   (`kit/templates/daily-note.md` or the vault's copy), with every date placeholder filled for the
   working date. Then log. Never skip an entry because the note is missing.
4. **Log in the progress log**, appended to that section with the notes connector (`notes-editing`),
   one bullet per event: `- (HH:MM) **Headline.** One or two sentences, with a link to the
   artefact.` Log finished work and solved problems, a meeting held (a link to its note, not its
   content), notes or analyses created, decisions taken (a decision also goes to the decisions
   section). Do not log that the person asked something or that the agent checked something. The
   test: would this matter to the person reading the note in three months?
5. **What carries over is the person's choice.** Either open tasks roll forward into the new note's
   to-do list, or nothing is carried and the to-do list shows only what the person scheduled on the
   task board. The author switched the roll off in November 2026; either way the board stays the one
   list of tasks. If the roll is on: bump only tasks that were already scheduled, never schedule a
   task for the first time, and count each roll in the task's `carried::` field instead of appending
   a sentence.
6. **Suggestions for the day draw on the task board** (its scheduled dates, deadlines and
   priorities), never on a copy of a task's text: one task, one line, on the board.

## Resources

- Template: `kit/templates/daily-note.md` (to do today, progress log, decisions and insights, carry
  forward).
- `notes-editing`: how to append without damaging the note.

## Scripts

`scripts/now.py` (`--at "YYYY-MM-DD HH:MM"` to test a moment, `--vault` for another vault,
`--self-test` for the day boundary). Set `NOTES_ROOT`, `DAILY` and `DAY_ENDS_AT` at the top once.

## Checks

- The stamp of each entry equals the script's `stamp` at the time of writing.
- The entry went to the note the script named (run it again after the boundary in a long session).
- Each entry links its artefact, records an event, and is not a one-item list in disguise.
- No task text copied into the note.

## Learn

A correction to how entries are written or dated goes into this file through `learn`. If stamps go
wrong again although the script exists, the fix is a check that runs the script, not another
sentence.
