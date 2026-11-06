---
name: do-it-later
description: The person's queue of deferred work. "Do it later" about a piece of work enqueues a spec that runs cold in a fresh session; naming a queued task ("do DT-3", "run the cleanup one") runs it. Only the person feeds the queue. Use on "do it later", "queue this for later", "do DT-<n>", "what is in the queue". Not for the task board (task-board).
---

# Do it later

The queue lives in `references/queue.md`: an overview table, then one section per pending task. It is
the person's list of agent work to run when they have time, kept in one place, because a mirror of
it anywhere else (on the task board, in a note) drifts: in the author's setup a mirror listed done
tasks as open for months.

## Procedure

**Enqueue** (the person says "do it later", or words to that effect, about a piece of work):

1. Write a self-contained spec under `## Pending` in `references/queue.md`, at the top:
   `### DT-<n> <title>` (the next free number), then **Deferred:** the date, **Effort:**,
   **Depends on:**; the background, the scope with paths and links, how, what it must not touch, and
   **Done when:**. It must run cold: a session without this conversation reads only the spec.
2. Add its row to the overview table, so the table and the sections stay in step.
3. Do not run it now. Commit the change.

**Run** (the person names a task):

4. Read its section, check **Depends on**, and carry it out as specified; hand it to an executor
   agent by kind of work if it is large.
5. When it is done, remove its row and section from the queue, and add a dated entry to the rules
   changelog with what was delivered and where (the record of done tasks lives there, never loaded by
   default). Log the result in the daily note.

**Only the person feeds the queue.** An entry is made when they say "do it later" and at no other
time: a session that enqueues on its own schedules their time for them. Work that comes up and that
they have not deferred is done now, inline if small, by a background agent if large.

## Resources

- `references/queue.md`: the overview and the pending specs, with one example spec that runs cold.

## Scripts

None.

## Checks

- The overview table and the sections agree: every pending section has a row, and no row lacks a
  section.
- A new spec names its paths, its done-when, and what it must not touch.
- A finished task left the queue for a changelog entry and a line in the daily note.

## Learn

A correction to how specs are written goes into this file through `learn`.
