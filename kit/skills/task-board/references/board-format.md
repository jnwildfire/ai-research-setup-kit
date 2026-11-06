# The board's format, and how to patch it

## One task, one line

    - [ ] Send the revised figures to the co-authors [prio:: A] [est:: 30m] [due:: 2026-11-20] [next:: export the PNGs] [created:: 2026-11-04] ^t-a12

- A Markdown task, `- [ ]` open and `- [x]` done, at the start of the line.
- Fields inline as `[key:: value]` (the Dataview plugin's syntax, so a query can read them):

| Field | Holds | Set by |
|---|---|---|
| `prio::` | A (a deadline, or someone waits), B (important), C (tools and polish) | the person; the agent proposes |
| `do::` | the day it is scheduled for | the person only |
| `due::` | a real deadline | the person, or a document that states it |
| `est::` | an estimate | the agent proposes |
| `next::` | the next physical step, for A and B only | the agent, at the end of a work session |
| `created::` | the day the line was made | the agent |
| `carried::` | how often the task rolled to another day | the roll, if the person uses one |

- A block id at the end of the line, `^t-<section letter><number>` (`^t-a12`, `^t-a12-1` for a
  subtask). The id makes a single-task edit possible instead of a section rewrite, and lets other
  notes link the task.
- Reasoning and history go into a context note, under a heading per task (`### a12`), never onto the
  board: the board stays one line per task.

## Patching (the Obsidian connector, November 2026)

The connector's behaviour changed under these rules more than once in five weeks, so: **look at the
line you just wrote, never trust the "OK".** The general traps are in
`../../notes-editing/references/connector-gotchas.md`.

1. **The block patch**: target the block id, replace its content, and pass the leading `- ` and the
   trailing id; then read the line and repair it if the marker doubled or the id went missing (both
   have happened, in turn).
2. **Never pass `within`** on a board section: a wrong guess deleted a whole section once.
3. **A block id only indexes when it ends its block.** Keep a blank line between top-level tasks: it
   is load-bearing. A task followed by an indented paragraph, or a parent whose subtasks run into the
   next task, cannot be reached by its id.
4. **Never block-patch a task that has subtasks.** The patch glues the first subtask onto the parent
   line; the line then carries two ids and neither resolves. Patch the parent's heading section
   instead.
5. **Verify by counting ids, not by looking at markers**: `open_tasks.py --check` before and after,
   and the heading map lists every id. A marker check alone passed while a whole section was missing.

## Section replaces

When several tasks change, or in doubt, replace the heading section: sections have none of the block
traps. Stage it: the current section to a scratch file, the new version built from it, the two
compared, the patch, then a comparison with what landed. Size is not the criterion: bumping fields on
many tasks is a legitimate section replace. Never patch the board while it is open in a pane.

## The undo

A notes app's own file recovery often snapshots only what the editor saved, so it may not cover a
note written only through the connector. The cloud drive's version history does: pick the newest
version whose size matches the intact file, not merely the newest.
