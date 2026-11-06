---
name: progress-report
description: Drafts a progress report for a period (a half-year report, a monthly digest) from the daily notes, the decisions of the meeting notes and the ticked tasks of the board, every line linked to the note it comes from. Triggers "/progress-report", "draft the half-year report", "what did I do since". Not for a session retro or a meeting brief.
disable-model-invocation: true
---

# Progress report

A report for a period, condensed from what the vault already records, so that writing it is reading
and deciding, not remembering. It is built from three sources only, read in this order, and every line
it states links the note it came from.

## Procedure

1. **Fix the period and the form.** Ask for the start and end dates, the reader (supervisors, a
   graduate school, a funder, the person), and whether a form exists. If the person pastes the form's
   fields, the draft follows them in their order; otherwise use the plain structure of step 5. If an
   earlier report is in the vault, take its end date as the default start and mirror its structure.
   Done when the period, the reader and the structure are settled.
2. **Read the daily notes of the period**, one month folder at a time (a listing each, never a
   recursive search), and from every note dated inside the period only two sections, by a targeted
   read: the progress log and the decisions. Keep one line per event: the date, what happened, the
   artefact it links. Done when the number of notes read equals the number the listings show for the
   period; name the count in the report. A day without a note is a gap in the record, never evidence
   that nothing happened.
3. **Read the meeting decisions of the period**: from every meeting note dated inside the period only
   the section `0. Decisions taken`. Keep each decision with its ID, the meeting's date and the note.
   Done when every meeting note of the period is read, or named as having no decisions table.
4. **Read the ticked tasks**: every done task on the board and in its archive whose completion date
   falls inside the period. A ticked task without a date is listed separately as "done, date unknown",
   never placed in the period by guess.
5. **Draft.** The plain structure, unless step 1 set another:
   - **Period and summary**: the dates, then three to five lines on what the period was about.
   - **What was done**, grouped by project or work package.
   - **What was decided**, with the meeting and its decision ID.
   - **What changed in the plan**, each change with the decision or the note behind it.
   - **What is next**: the coming period, from the open decisions and the plan. The person confirms
     this section; it is not inferred from the past.
   - **Questions for the reader.**
   Every bullet ends in its link: the daily note, the meeting note or the task. Condense: one line per
   item, the outcome rather than the activity.
6. **Land the note** through the connector in the project's or the person's administrative folder as
   `YYYY-MM-DD-progress-report-<period>.md` (the date of writing), log it in the daily note, and open
   it for the person.

## Resources

- `kit/templates/meeting-note.md` and `kit/templates/daily-note.md`: the sections this skill reads.
- The `task-board` skill's `open_tasks.py --done` lists ticked tasks with their fields.

## Scripts

None of its own.

## Checks

Confirm each before reporting, and name every miss:

- **Every claim links a daily note, a meeting note or a task.** A line with no link is cut, or marked
  for the person; it is not kept for being plausible.
- **Nothing comes from the agent's memory files.** Memory is a resume point, not a record: a fact found
  only there gets its note, or is left out and named.
- **Dates are the event's own date** (the daily note's, the meeting's, the task's completion date),
  never the day the report was written.
- **Coverage is stated**: daily notes read against notes present, meeting notes read, ticked tasks
  counted, the days of the period without a note.
- `kit/hooks/output_check.py` on the report is clean.

## Learn

What the person changes in the first draft (the structure, the grouping, what to leave out) goes into
this procedure through `learn`, so the next period's draft starts closer.
