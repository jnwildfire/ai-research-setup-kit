---
name: notes-editing
description: >-
  How to write to the notes vault without damage: through the notes connector first, one passage
  at a time, frontmatter and the modified date set last, shared folders, and the known traps of
  the connector's patch tool. Use before any vault write ("patch the note", "add to the note",
  "write a note", "update the wiki"). The workflow skills (meetings, inbox, daily note, task
  board) call it.
---

# Notes editing

The person usually has a note open while the agent works on it, and a notes app rewrites an open
note on disk (tables, frontmatter, line endings). A direct file edit therefore races with the
editor, and one side's change is lost. Hence the rule: **read off disk freely, write through the
notes connector.** Reading a note at a known path is cheap and safe; a recursive search over a
cloud-synchronised vault is not (guide 01). A session without the connector (a job inside a code
repository) edits on disk under the same rules, where a full Write is the connector's write and an
Edit is its patch, and says so in its report.

In Obsidian the connector is the Local REST API plugin with a Model Context Protocol (MCP) server in
front of it; its tools are named like `vault_write`, `vault_patch`, `vault_append`,
`vault_get_document_map`. Other notes apps have their own; the rules hold for any connector that
can replace a section.

## Procedure

1. **Read the template first** when creating a note (`kit/templates/`, or the vault's template
   folder), and follow its current structure.
2. **Pick the tool.** A new note: write it whole. An existing note: patch one target (a heading
   path, a block id, a frontmatter key) or append. Writing an existing note whole is a fallback for
   what a patch cannot do (list or boolean frontmatter, a stray heading level, a file with Windows
   line endings), never in a shared folder (step 6). Not knowing how to target a patch is no licence
   to rewrite: find the heading or the block, or append.
3. **Read before every structural patch**: the note's heading map for the exact targets, and the
   section's text verbatim, so that a bad patch can be restored in one call. Count an invariant
   before and after (list items, headings, task lines). Before a section replace you have not run on
   that note before, copy the section to a scratch file.
4. **Target narrowly, and know the traps** (`references/connector-gotchas.md`; read it before the
   first replace in a session). The ones that destroy text silently:
   - never replace the content of the document's top heading: its content runs to the end of the
     file;
   - never remove an entry by block index: read the section and replace it with the text minus the
     entry;
   - never edit part of a list by block index: a list with blank lines between items is one block;
   - headings in a payload are relative to the target: `#` becomes a direct child, for append as for
     replace;
   - to add a table row, read the section and replace it whole.
5. **Correctness, not size.** A large section replace is right when it is the only correct change:
   read verbatim, change only what must change, keep the rest byte for byte.
6. **Shared folders are co-edited** (a folder synchronised in real time with colleagues, for
   example by the Relay plugin): patch or append only, never write a whole note there, one write per
   file per session, and assume a comment may be a colleague's. The agent's writes do not travel
   through the sharing plugin's own sync, so a whole-note write can overwrite what someone typed
   meanwhile. Keep the list of shared folders in your rules file.
7. **Frontmatter.** New notes carry the template's fields. Quote any value that holds a colon, a hash
   or a leading quote: unquoted, the frontmatter stops parsing and the connector refuses every later
   patch. Lists and booleans keep their type only in a whole-note write; a patch stores them as text.
   Fields a plugin owns (a reference manager's, a date manager's) are read, never written.
8. **The modified date last.** After the body edits have settled, set `date-modified` with the stamp
   from the clock script (`daily-note/scripts/now.py`), in the form the note already uses, then read
   it back: a sync plugin can revert a frontmatter patch, and the connector's "OK" says nothing.
   Never touch `date-created` on an existing note.
9. **Content rules for every note**: sources as `[[citekey]]` links to one literature note per source;
   abbreviations in full on first use in each note; where a claim's weight depends on it, a claim
   word (`[conf:: confirmed]`, `stated`, `inferred`, `assumed`) and every number with its basis
   (measured, simulated, design, estimated, literature, judgement). Not on every sentence.
10. **The person's comments in a note are instructions** (in Obsidian, a comment such as
    `%% @agent ... %%`): act on them when the person points to the note or asks for a sweep, then
    delete the comment (the version history is the trail). Ask when one is ambiguous.
11. **Verify, then show.** Read the changed passage back off disk. Then, if the person is to read it,
    open the note for them. Never patch a note that is open in a pane: opening can rewrite it on disk
    under the patch.

## Resources

- `references/connector-gotchas.md`: every known behaviour of the Obsidian connector's patch tool,
  with the safe form, from the author's vault (November 2026).
- `kit/templates/`: the note templates (meeting, literature card, daily, handover).

## Scripts

None of its own. The time stamp comes from `../daily-note/scripts/now.py`. Binary attachments
(images, PDFs) cannot go through the connector: copy them into the vault's attachments folder with
the shell, the one sanctioned direct write, and embed them with a link.

## Checks

- The changed text reads back on disk as intended, and the invariant count matches.
- `date-modified` landed (read back); `date-created` untouched.
- Frontmatter still parses: run `kit/hooks/output_check.py` on the note.
- No whole-note write in a shared folder.

## Guard

A folder the person fills alone (a staging folder) and an archive filled by a script are refused to
every tool by the guard (`kit/hooks/guard.py`, the `never` and `existing-only` strictnesses), whatever
this skill says.

## Learn

A new connector behaviour goes into `references/connector-gotchas.md` with its date and the safe
form, and the incident into the rules changelog. A correction to a note convention goes to the skill
that owns the workflow, through `learn`.
