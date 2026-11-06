---
name: pre-meeting
description: >-
  Writes the one-screen brief before a recurring meeting: the decisions still holding, the open
  items, the assumptions by basis, and the questions carried more than twice, from the series'
  meeting notes and the task board. Use on "prepare the supervision", "before the weekly", "prep
  the meeting", "brief me for the call". Not for processing the meeting afterwards
  (process-meeting).
---

# Pre-meeting brief

The person walks into a recurring meeting knowing what was decided, what is still open, what the
work rests on that nobody has confirmed, and which question keeps coming back unanswered. One
screen; the background stays in the series' notes, linked.

## Procedure

1. **Identify the series** (one folder per series in the meetings lane) and the date. Ask if unclear.
2. **Digest the series**: `python -I <skills>/pre-meeting/scripts/series_digest.py <series> --last 3`.
   Read the latest meeting note and, if one exists, the agenda note for this date.
3. **Look across the other series** for decisions on the same projects taken since the last meeting
   (the projects a note names in its `collections:` or links), if the vault keeps a register of
   decisions.
4. **Check the board** for the series' projects and people:
   `python -I <skills>/task-board/scripts/open_tasks.py <project or person terms>`.
5. **Write the brief** as the section `## 0. Brief (one screen)` at the top of the agenda note for
   this meeting (create it from the meeting-note template if none exists, and say in its first line
   that it is preparation and the record follows in the meeting note). Four parts, each as short
   lines with the ID and a link:
   - **Decisions still holding** that this meeting builds on or might overturn.
   - **Open items**: open decisions, the open issues of the last meeting, board tasks waiting on the
     attendees.
   - **Assumptions by basis**: claims marked `[conf:: assumed]` or `[conf:: stated]`, and numbers
     whose basis is estimated, extrapolated or judgement, grouped by basis; for each, what would
     confirm it.
   - **Questions carried more than twice**, from the digest's carry list, each with a proposal: ask
     now, delegate, or drop.
   Then, only if asked or plainly needed, the list of questions for the attendees and the
   background, below the brief.
6. Verify the write, open the note for the person, and log the preparation in the daily note.

## Resources

- `kit/templates/meeting-note.md`: the decisions table whose IDs the digest reads.
- A register of decisions, if the vault keeps one (a note with a query over the `[decision:: ]`
  fields of every meeting note).

## Scripts

`scripts/series_digest.py <series> [--last N] [--min-carried N] [--vault <folder>]`: the decisions of
the last N meeting notes that still stand or are open (with or without the `[decision:: ]` field),
the IDs carried in N or more later notes (default 3, that is more than twice), the claims marked
stated or assumed, and the last meeting's open issues. Set `NOTES_ROOT` and `MEETINGS` at the top
once.

## Checks

- The brief fits one screen (about 25 lines); everything else is linked, not copied.
- Every decision and item carries its ID and a link to its note.
- The carry list was read row by row, not pasted: the script finds candidates, not conclusions.
- `kit/hooks/output_check.py` on the agenda note is clean.

## Learn

What the person adds to or strikes from a brief goes into this procedure through `learn`.
