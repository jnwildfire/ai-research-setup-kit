# Deferred-task queue

The queue of the `do-it-later` skill (`../SKILL.md` has the rules). This file is the one place the
queue lives; a finished task leaves it for a dated entry in the rules changelog.

## Overview

Scan this table; read a spec below only when that task is run.

| ID | What | Effort | Deferred | Status |
|---|---|---|---|---|
| DT-1 | Example: replace the plain-text paths left after a folder rename | small | <YYYY-MM-DD> | pending (an example; delete it with your first real entry) |

## Pending

### DT-1 Example: replace the plain-text paths left after a folder rename

**Deferred:** <YYYY-MM-DD>. **Effort:** small, under half an hour. **Depends on:** nothing.

**Background.** A folder of the vault was renamed inside the notes app, so every link followed. Text
that names a path without being a link did not: it still names the old folder, and a reader or a cold
session following it finds nothing there.

**Scope.** The notes that name `<old folder>/` in plain text, found with one search of the vault for
that string (through the notes app's own search, not a recursive search on disk). Not the links, which
already point to the right place; not the archive, whose notes stay as they were written.

**How.** For each hit: replace the path with the new one, or with a link where the text means the
note. One patch per note through the connector (`notes-editing`), its modified date set last.

**Must not touch.** Any note in a shared folder without the person's yes; the archive.

**Done when.** The search for `<old folder>/` returns no hit outside the archive, and the rules
changelog has the entry with the list of notes changed.
