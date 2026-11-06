---
name: literature-note
description: >-
  Literature notes from the reference manager: creating them through the notes plugin, the card
  with its read field and the location of every point, filling the summary, the routes to a
  paper's full text, a Markdown copy of a pivotal paper. Use on "add this paper", "make a
  literature note", "summarise this paper", "what does <citekey> say", "convert the PDF". Not
  for checking citations in a draft.
---

# Literature notes

The citation key is the thread: reference manager item, literature note `<citekey>.md`, wiki
article, manuscript (guide 07). A literature note is a **card**, not a summary: a later session must
be able to tell what was read and where each recorded point sits in the paper, because a note's
silence proves nothing when nobody knows what was read. In the author's vault a method the work
needed was in a paper all along and missing from its note, which had been written for another
question.

## Procedure

1. **Is there a note already?** Look for `<citekey>.md` in the literature lane before anything else.
2. **Create it through the plugin, never by hand.** Add the item to the reference manager first if it
   is not there, with its PDF in the same pass (an item without its PDF is not finished). Then let the
   notes plugin create the note (in the author's setup, ZotLit), named by the key Better BibTeX
   generated, and check that the file exists.
3. **First import: the collections.** Read the item's collections, write them into `collections:` in
   lowercase with hyphens, and suggest two to four tags from the abstract; add them after the person
   confirms. Never write a field the plugin owns.
4. **Fill the card** (`kit/templates/literature-card.md`): `read:` says what was read (`fulltext`, the
   sections by name, or `abstract`), and `read-on:` when. Every point the card records carries its
   location (page, equation, table, figure) and a short verbatim phrase. One line says what the paper
   does not cover that a reader might expect.
5. **The summary from a grounded tool, the connections by the agent.** Where a tool answers with
   quotations from the paper (NotebookLM, in the author's setup), take the summary sections from its
   quote-grounded answer, since the grounding is what guards against an invented detail. Write the
   connections to the vault yourself: that tool sees the paper, not the vault.
6. **Looking up one detail later goes by route**: a pivotal paper gets one local Markdown copy
   (MinerU) and is then read by searching it and reading a window of lines around each hit; an
   occasional open-access paper through a citation service's excerpts by DOI (digital object
   identifier) and term; an occasional paywalled paper through the reference manager's full text,
   inside a research subagent that returns only the passage and its page. A full text read whole
   costs about fifty thousand characters of context for one sentence.
7. **Before a literature claim carries weight** (it decides a method, corrects the person, or is about
   to be cited), open the paper unless the card records that detail with its location, and say which
   you checked: the card or the paper.
8. **Highlights:** after the person syncs their highlights, the plugin's update brings them in. Never
   its overwrite, which destroys what was written in the note.
9. **Cite in the vault as `[[citekey]]`**: every key used anywhere needs its note here.

### Full text in the vault stays sparse

A Markdown copy costs as much to read as the connector's full text and far more to make, so keep it
for the person's own papers and thesis and a very few pivotal references, as
`fulltext_<citekey>.md` beside the literature notes (the prefix keeps a link to the key pointing at
the card), with its figures in a folder beside it and `fulltext_path:` on the card.

## Resources

- `kit/templates/literature-card.md`: the card, with `read:`, locations, numbers with their basis,
  "what it does not cover" and `### Inferred`.
- `kit/tools/literature-stack.md`: the tools in the order to install them, with a test for each.
- Guide 07: how the parts work together, and the traps (overwrite is not update; templates leak).

## Scripts

None of its own. MinerU converts a PDF (`mineru -p paper.pdf -o out/ -b pipeline` on a computer
without a graphics card; a few minutes per paper); check its output before it enters the vault, since
complex layouts and scanned pages can parse poorly.

## Checks

- The note exists under its key, made by the plugin.
- `read:` is set and honest; every recorded point has a location and a verbatim phrase.
- No field the plugin owns was written; `collections:` set once.
- A claim that carried weight in the session names whether the card or the paper was checked.

## Learn

A correction to the card or the routes goes here through `learn`; a finding about the plugin's
mechanics goes into the vault's note on the plugin, with its date.
