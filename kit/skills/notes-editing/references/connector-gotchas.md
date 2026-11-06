# Notes connector: the patch traps

Learned in the author's Obsidian vault from July to November 2026, against the Local REST API
plugin's Model Context Protocol (MCP) server. The server's behaviour changed under these rules more
than once, so treat each as the current best knowledge and check yours: **verify what landed on
disk, never the "OK".** The tool and parameter names are that server's; another connector has its
own names and, very likely, its own traps.

## Destructive

- **Never replace the content of the document's top heading.** A heading's content normally runs to
  the next heading of any level; for the document's H1 it runs to the end of the file and swallows
  every section below. Three times in one month a replace on an H1 cut a long note down to its
  first lines (a requirements note from 26 KB to 3.5 KB; a task list with all its tasks; a
  1,163-line article to 35 lines). **So:** to edit the text between the H1 and the first `##`, give
  it its own `##` heading first, or rewrite the note whole (outside a shared folder). Check the
  heading map first; if the target has children, patch a leaf, or append or prepend.
- **Never delete by block index.** A `delete` with `within: -1` on a heading removed not one block
  but the whole section: two such calls emptied a day's progress log. **So:** to remove an entry,
  read the section and replace its content with the text minus the entry.
- **`within` counts blocks, and a blank line inside a list does not start a new one.** A list with
  blank lines between its items is one block, so a replace at `within: n` consumes every item.
  **So:** never use `within` to edit part of a list; read the section verbatim and replace it whole.
  Count items (`grep -c "^- "`), not lines, before and after.
- **Never pass `within` where a wrong guess deletes a section.** The server once ignored
  `within: 0` on a heading replace and replaced the whole section body (21 tasks gone, with "OK"),
  and later honoured it. Where `within` is used anyway, compare the file before and after.
- **`targetScope: "marker"` on a heading deletes the section body.** There is no safe way to patch a
  heading line alone: to fix a level, replace the parent section with corrected levels, or rewrite
  the note.
- **Adding a table row: read the section and replace it whole.** A row array was refused ("not a
  table", because the section's last block is the blank line), and `trimTargetWhitespace` then glued
  the new row, the last row and the next heading into one line. Never pass `trimTargetWhitespace` on
  a heading target.
- **The patch corrupts files with Windows line endings (CRLF).** It miscounts byte offsets,
  truncates heading lines and can split an emoji. Rewrite such a note whole (LF) first; notes the
  connector wrote are LF and patch fine.

## Heading levels and targets

- **Heading levels in a payload are relative to the target.** A leading `#` becomes a direct child,
  for append as for replace: `##` sent into an H2 section lands as H4, `###` into an H3 as level 7,
  which renders as literal hashes. Write the desired level minus the target's level, and check the
  levels on disk.
- **A heading target needs its full path** (`["Note title", "Section"]`); a bare section name is
  "not found". A duplicate heading's key carries an invisible suffix: copy it from the heading map,
  never retype it.
- **`createTargetIfMissing` puts the heading in the wrong place** (as an H1 at the end of the file).
  To add a subsection, append literal Markdown to the parent heading's full path.

## Frontmatter

- A replace on a field works only if the field exists; it cannot create one.
- **Lists stay lists only in a whole-note write.** A patch on a list field stores a quoted string,
  which breaks queries over the field and the links inside it.
- **Booleans the same:** a patched `true` lands as the string `"true"`. A plain read prints `true`
  either way; check the type with a query.
- **A date-manager plugin** that stamps `date-modified` on the person's own edits does not see the
  connector's writes, so the agent sets the date itself, last, and reads it back.
- **Audit dates by content, not by file time.** A sync client rewrites files without changing them.

## Other

- **Binary files cannot go through the connector**: copy them with the shell, then link them.
- **A query plugin may not re-index a file written through the connector** until the app re-reads
  it: refresh its cache once at the end of a batch of writes.
- **Do not patch a note that is open in a pane**: opening can rewrite the file on disk, and the next
  patch is computed against the layout read before it. Patch, verify, then open.
