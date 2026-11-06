---
name: workflow-health
description: >-
  The judgement on top of the weekly workflow measurement: runs workflow_health.py, reads its
  report note, and adds what a script cannot see (what the sessions were for, where structure
  would have saved reads, what to type differently). Use only when the person asks:
  "/workflow-health", "workflow health", "how is the workflow running". Not a session retro, and
  not for saving a rule (learn).
---

# Workflow health: the judgement on top of the numbers

The measuring costs no model tokens: `scripts/workflow_health.py` reads Claude Code's session
transcripts, the configuration the agent loads and the structure of the vault, and rewrites one report
note: the week against the week before, the recommendations whose thresholds were crossed (each with
the number that crossed it), and an empty Judgement section. A scheduled task runs it weekly. This
skill adds the part a threshold cannot give, once, when the person asks, because judgement costs
tokens and the numbers do not.

## Procedure

1. **Run the script** (seconds to a minute): `python -I <skills>/workflow-health/scripts/workflow_health.py`.
   Its output is the headline and the recommendations; work from that and the note, never from the
   transcripts in bulk.
2. **Read the note in sections**: "This week", "Recommendations" and "Sessions, last 7 days". Read
   the configuration or vault sections only where a recommendation points there.
3. **Look closer at three sessions at most**, where a judgement needs it: the script's cost line
   (`--session-cost <id>`) and the first prompt of the transcript (a bounded read of its first lines).
   Never a whole transcript.
4. **Write the Judgement**: replace the content of the note's "Judgement" heading through the connector
   (`notes-editing`). One screen at most:
   - what the week's sessions were trying to do, and which ran long or drifted for a reason the
     numbers do not show (one task that sprawled, several tasks in one session, a handover);
   - where structure would have saved reads or context: a note to split or to give a top section, a
     missing link, a script or a subagent instead of a long read;
   - what the person could type differently: a first prompt that names the file and the section,
     `/clear` between unrelated tasks, the save step before a long session ends;
   - which recommendation to leave alone this week, and why.
   Each point names the script's number it rests on.
5. **Say what it cost**: run `--session-cost` last and quote its line.
6. **Show it**: open the note for the person, and give the headline in chat in three lines: the week
   against the one before, the one thing to act on, the cost.

The next scheduled run rewrites the whole note and clears the Judgement, as intended: a judgement
belongs to its week. Anything worth keeping goes through `learn` or onto the task board.

## Resources

- The script's docstring: the transcript fields it relies on, and the definitions.
- The automation map (`kit/context/automation-map.md`): the scheduled task that runs the script has
  its row there, with what depends on it.

## Scripts

`scripts/workflow_health.py [--no-write] [--session-cost [id]] [--workspace] [--code] [--notes] [--note]`.
Its configuration block sets the paths (the workspace, the code root, the vault, the report note, the
lanes that are not knowledge notes), the context window of your model, and the thresholds. The
thresholds are starting points, not measurements of your work; `fixed_start` stays off until you set
it from your own `/context`. Standard library only. The vault is walked one folder at a time, and an
online-only file of a cloud drive is never opened.

Register it as a weekly task (Windows Task Scheduler, or `cron` and `launchd` elsewhere) with the
Python that has nothing extra installed, and allow it to start when a run was missed. Add the task's
row to the automation map in the same change.

## Checks

- Every number quoted is the script's, from this run; a figure worked out in the session says so, and
  how it was derived.
- The Judgement adds what the recommendations do not say; it does not repeat them.
- Reads stay under ten in the run (the cost line shows them), and no transcript was read whole.
- A judgement that rests on a new pattern spotted in the sessions is checked on a session where it
  should show before it is written down.

## Learn

- A threshold that fires three runs in a row with nothing changing is raised (it describes the normal
  state, not a problem) or dropped (nobody acts on it). Propose which, with the three values; change
  `T` in the script only on the person's yes, and record why through `learn`.
- A point the Judgement keeps adding by hand becomes a rule in the script, so the next run gives it
  for free.
- A wrong or misleading number is an incident: fix the script, and record it through `learn`.
