---
name: dictionary
description: Updates the dictation dictionary note with new names and garbles, and regenerates the Wispr Flow vocabulary and correction files and the term lists from it. Triggers "/dictionary", "update the dictionary", "add to the dictionary".
disable-model-invocation: true
---

# Dictation dictionary

One note is the source; the export files are generated from it and never edited by hand. The
skill is user-invoked only: its description never sits in a session's context, and nothing runs
unless the person types `/dictionary`.

## Procedure

1. **Harvest candidates since `last-export`** (in the note's frontmatter): new person and
   organisation notes, meeting notes written since that date (names, places, products in them),
   and garbles the person or the agent corrected in notes since then. List the folders in
   question one by one; never search a cloud-synchronised root recursively, because every file a
   search touches is downloaded.
2. **Show the person the candidate rows** (Term, Category, Heard as, Replace, Note) and add only
   the ones they accept. Patch the rows into the table; never rewrite the whole note. Record only
   garbles that were actually seen. Judge each garble on its own: `Replace` lists only the ones
   that are never a real word or name in the person's texts; when in doubt, leave it out.
3. **Run the script** (below) and read its whole output.
4. **Set `last-export`** to today in the note's frontmatter.
5. **Report**: the counts, the terms added and removed, every rejected row with its reason, and
   the import steps: in Wispr Flow, Settings, Dictionary, Import, drag in
   `wispr-flow-vocabulary.csv`, then `wispr-flow-corrections.csv` (imported items are not
   starred, conflicts are skipped). For a transcription tool that takes a vocabulary or a prompt,
   paste `term-list-short.txt`.

## Resources

- `references/dictation-dictionary.md`: the note's format, with example rows. Copy it into the
  vault once; its path is the script's `--note`.
- The person's people and organisation notes, if the vault has them: the authority on how a name
  is written.

## Script

`scripts/export_dictionary.py` parses the table (escaped `\|` and empty cells allowed), writes the
five files (UTF-8 without a byte-order mark, comma-separated values (CSV) per RFC 4180, no header), and prints the counts
and the terms added and removed since the previous export. Unchanged files are not rewritten.

    python -I .claude/skills/dictionary/scripts/export_dictionary.py --note "<note>" --out "<folder>"
    python -I .claude/skills/dictionary/scripts/export_dictionary.py --note "<note>" --check

The paths can also be set once, in the configuration block at the top of the script or in the
environment variables `DICTIONARY_NOTE` and `DICTIONARY_OUT`. `--check` writes nothing.

## Checks

The script rejects, and leaves out of every export, a row with an empty term, a duplicate term
(the first wins), an unknown category, a Replace entry that is not in the row's Heard as, or a
garble equal to any term. A term with a comma stays in the Wispr Flow files but not in the
comma-separated term lists. It stops without writing if there are more than 1,000 rows or a CSV
over 3 MB (Wispr Flow's import limits), or if a CSV does not read back identically. Before
reporting, the agent re-reads the rejected rows and names each in the report.

## Learn

A garble that keeps coming back after an import is a row whose `Replace` needs the garble, or a
term missing from the vocabulary. Add it here, not as a rule anywhere else.
