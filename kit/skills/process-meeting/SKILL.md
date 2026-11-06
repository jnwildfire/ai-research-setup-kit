---
name: process-meeting
description: Turns a meeting transcript into a meeting note in three phases (load the series' context, summarise with the decisions table on top, link and propagate), and files the transcript unchanged. Use on "process meeting", "process the transcript", a transcript dropped in, or "process the reviewed meeting notes". Not for preparing a meeting (pre-meeting).
---

# Process a meeting

The point is that names, terms and open threads carry across meetings without the person explaining
them again, and that every meeting note is wired into the rest of the vault. The person does not read
the summary end to end: the prose is the agent's context for later, the table at the top is what the
person acts on. Never ask again for context the earlier notes already hold.

Meetings are kept as **series**: one folder per recurring meeting (a weekly, a supervision, a steering
group). The series is the key to the earlier context.

## Procedure

### Phase 1: load the context before summarising

1. Identify the series from the attendees and the topic. If none fits, ask which folder to use rather
   than inventing a near-duplicate.
2. Run `python -I <skills>/pre-meeting/scripts/series_digest.py <series>` for the decisions still
   standing, the items carried over and the last open issues; then read the latest one or two notes
   of the series for spellings and threads, and the agenda note of this meeting if one exists.
3. Read the project notes of every project the meeting touches.
4. Fix transcription errors against the vault's own spellings: the person notes, a names note if the
   vault keeps one, and the dictation dictionary (`kit/skills/dictionary/`).
5. If a technical concept is central, read its wiki article: for the terms, and as a link target for
   phase 3.

### Phase 2: summarise

6. Write the meeting note from `kit/templates/meeting-note.md` into the series' folder, named the way
   the series' notes are named (`YYYY-MM-DD <series>.md`): the date, the attendees by role,
   `collections:` the projects touched, a one-line `summary:` (quoted if it holds a colon),
   `reviewed: false`.
7. **Open with `## 0. Decisions taken (review this table, skip the rest)`**: one row per decision
   that something now depends on, not per topic. The `#` cell is the inline field
   `[decision:: <ID>]` with a short, stable ID per series (a letter and a number, `W12`), so another
   note can cite it and a query can find it. `Status now` is the agent's reading: Holds, Superseded,
   Overturned, Never actioned, Open. `Verdict` stays blank for the person: blank means the row
   stands; they mark only what they disagree with.
8. Then the body: discussion by topic (each subsection names its decision IDs), tasks with owner and
   date, open issues, what happened to the last meeting's open items, and what the transcript left
   uncertain. A `### Inferred` heading holds what the agent reconstructed and nobody said; nothing
   under it is cited as anyone's position. Where a claim's weight depends on it, mark it
   `[conf:: stated]` (a named person said it in this meeting), `inferred` or `assumed`, and give
   every number its basis (measured, design, estimated, stated).
9. **Ask while writing, not after.** A garbled name, an ambiguous decision, an unclear owner: ask in
   one line as it comes up. The uncertainty table at the end is for dead ends only.
10. **File the transcript unchanged** in the data root's transcript folder for the series, renamed
    `<note's file name> - transcript.<ext>` (or `- recap`, `- recording`), so that the note and its
    source share a name and sort together. The guard keeps the folder deposit-only: the transcript
    is never edited, and errors are corrected in the note. Record the path in the note's
    `transcript:` field.

### Phase 3: link and propagate

11. **In this note, without asking**: links to the previous meeting of the series, to the project
    notes, to every wiki article whose concept came up, and to the person notes.
12. **In other notes, proposed first**: a table of planned changes (note, change) for decisions,
    tasks and open issues that belong in project notes (each linking back to the meeting), reusable
    findings for a wiki article, a person note for a new attendee, and transcription fixes in the
    names note. Carry out what the person confirms.
13. **Task board check** (`task-board`, the checker): match the meeting's tasks and progress against
    the board. A task from the meeting's table reaches the board only when the person marks it in
    the `Keep` column or says so.
14. Log the meeting, with a link to the note, in the daily note (`daily-note`).
15. Report: the tasks still open across the series, contradictions with earlier notes, questions.

### The person's marks, and the reviewed sweep

- A mark or a contradicting comment on a decision means the note's own conclusion is wrong: correct
  it in place, with a callout at the section saying what changed and why.
- "Process the reviewed meeting notes": every meeting note the person has marked as reviewed and not
  yet processed is actioned like their comments (the comments, and any edit of theirs that implies a
  change elsewhere), then marked processed. Edits to other notes found on the way are still proposed
  first.

## Resources

- Template: `kit/templates/meeting-note.md` (the decisions table, tasks with a `Keep` column, the
  `### Inferred` heading, the uncertainty table).
- `notes-editing` for every write.

## Scripts

`../pre-meeting/scripts/series_digest.py <series>` for phase 1.

## Checks

- Every decision row carries `[decision:: ID]`, the IDs unique within the series.
- Every open item of the previous meeting appears in the section on the last meeting, with its state.
- The transcript is filed unchanged under the naming rule, and the note names its path.
- Every garble is either fixed against the vault's spellings or listed as uncertain.
- The task board check ran, and the daily note has its line.
- `kit/hooks/output_check.py` on the note is clean.

## Learn

A correction to the note's shape or to this procedure goes into this file through `learn`; a new
garble goes into the dictation dictionary.
