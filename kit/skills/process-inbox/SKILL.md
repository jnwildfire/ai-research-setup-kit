---
name: process-inbox
description: Routes the inbox's captures and the raw wiki input into the vault, and builds or updates wiki articles and data-source notes, behind the inbox gate. Use on "process inbox", "build a wiki article", "update the wiki article", "document this data source", "file this capture". Not for meeting transcripts (process-meeting) or papers (literature-note).
---

# Process the inbox, build the wiki

## The inbox gate

The inbox and the raw-input lane hold unvetted capture: clippings, dictations, forwarded material.
Plausible claims there have turned out contested or wrongly termed, so synthesising a capture
silently turns a draft into apparent fact. The gate is the folder, not a field on the note:

- **Ask the person before synthesising a capture** from these lanes into a wiki article, a project
  note or a permanent note, naming the note and what you would take from it.
- **Never cite a raw note from a lasting note.** If it was processed, follow its `processed-into`
  link and cite the article; if not, say so and ask.
- A staging folder the person keeps inside the inbox (for example `_later/`) is never touched; the
  guard refuses it.

## Procedure

1. **Read** every note at the top of the inbox (one folder listing, never a recursive search) and the
   raw inputs not marked processed.
2. **Classify** each item: meeting content to `process-meeting`; a project decision or task to the
   project's note; reusable knowledge to a wiki article; a paper to the reference manager first, then
   `literature-note` (listed for the person, never added on the agent's own); a mail to its project
   by sender and subject, or as a file in the data root with a line in a mail index; a web clipping:
   ask whether it is worth citing (no: the raw-input lane; yes: the reference manager, then a
   literature note).
3. **Present the routing plan** as a table (item, destination, action) and wait for the go-ahead.
4. **Carry it out** through `notes-editing`: a link back to the source in every destination, the
   source marked processed (and `processed-into` filled on a raw input). Never delete an inbox item.
5. **Task board check** (`task-board`, the checker): every capture that is or changes a task
   updates the board; ask where a match is uncertain.
6. Log what was processed, with links, in the daily note.

### Building or updating a wiki article

Read `references/wiki-articles.md` first. In short: one article per concept, not per source; written
for the person and for a later session that remembers nothing; every literature claim cited inline
as `[[citekey]]` and listed in `sources:`; literature linked, not summarised again (one or two
sentences on what the source means for this concept); measured, assumed and unknown kept visibly
apart, with a `### Inferred` heading for what was reconstructed; conflicts under
`## Tensions and conflicts`, gaps under `## Gaps and open questions`; when updating, every existing
line kept and the new material integrated, never a wholesale rewrite.

### Documenting a data source

Each external data source (a vendor's API, an export, a portal) gets its own wiki note, the
deliberate exception to one article per concept, because a data source is an interface to document
field by field before anything can be joined to it (`references/wiki-articles.md`, "Data-source
notes").

### What a source was asked for is not evidence of what it sent

When recording that a partner sent something in reply to a request, check that what arrived matches
what was asked for before writing the label as settled. People answer with the closest thing they
hold. If it cannot be checked independently (an address that matches, an ID that resolves in the
dataset, a second source), write "X sent this, described as Y" and keep the identification under
`## Gaps and open questions` until it is confirmed. In the author's vault, five meter numbers were
labelled as the meters that had been asked for; they were other meters, and the label spread through
four notes before he caught it.

## Resources

- `references/wiki-articles.md`: the audience, citations, the two bars for sources, conflicts and
  gaps, data-source notes.
- The vault's templates for a wiki article, an inbox capture and a raw input.

## Scripts

None. Reading the inbox is a listing of one folder.

## Checks

- Nothing from the unvetted lanes was synthesised without the person's yes, and no lasting note
  links a raw capture.
- Every destination links its source; every processed source says so.
- A wiki article's `sources:` lists every `[[citekey]]` it cites, each with a literature note.
- A partner's reply is labelled by what arrived, not by what was asked for.
- The task board check ran.

## Learn

Corrections to the routing or to the article shape go into this file or its reference through
`learn`.
