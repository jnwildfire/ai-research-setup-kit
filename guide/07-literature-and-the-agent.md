# 7. Literature and the agent

*How a reference manager, its citation keys, the notes in your vault and the agent's reading of
full texts fit together, so that every claim about a paper can be traced to the passage it rests
on. About fifteen minutes to read. Guide 05 gives the rule, "the paper itself, before a claim
carries weight"; this guide gives the tools that make the rule cheap enough to follow every time.*

## The idea, in any setup

Five parts, each with one job:

| Part | Its job | What makes it work |
|---|---|---|
| A **reference manager** | the library of record: one item per paper, with its metadata and its PDF (the paper as a portable document format file) | every paper you cite is in it, with the PDF attached |
| A **citation key** per item | the join between everything else: `smith2023` names the item, its literature note, every link to it and the citation in the manuscript | the key is generated once and never changes |
| A **literature note** per item, in the vault | what the paper holds for your work, each item with its page and a short quotation (the card of guide 05) | named by the key and created from the library, so the two never disagree |
| A **connector** for the agent | the agent searches the library, reads metadata and full text, adds items | it reads the full text, not only the abstract |
| **Literature services** | existence checks, how other papers cite a claim, systematic search | used to check and to discover, never as the source of a claim |

Any reference manager with stable keys, and any connector that reads full text, will do. What
follows is the form in the author's setup, with Claude Code as the agent.

## The form in this setup

| Part | Tool | What it does here |
|---|---|---|
| Reference manager | **Zotero** | items, PDFs, collections; synchronised to zotero.org |
| Citation keys | **Better BibTeX for Zotero** | generates a key such as `smith2023` for each item and stores it in the item's citation key field |
| Literature notes | **ZotLit**, an Obsidian plugin | creates one note per item, named by its key, with properties filled from Zotero, and brings your PDF highlights into the note |
| Agent connector | a **Zotero connector** (a Model Context Protocol, MCP, server; MCP is the standard by which a connector gives the agent its tools) | searches the library, reads an item's metadata and Zotero's full-text index of its PDF, adds items by DOI (digital object identifier, a paper's permanent name) and attaches open-access PDFs through Unpaywall |
| Full text of pivotal papers | **MinerU** | turns a PDF into Markdown with formulas as LaTeX and tables as tables; on a computer without a graphics card it runs on the central processing unit (CPU) alone (`-b pipeline`), a few minutes per paper |
| Claims and citation context | the **scite** connector | how later papers cite a claim (supporting, contrasting, mentioning), retraction and correction notices, excerpts of full texts |
| Discovery and existence | a **Scopus** connector | systematic searches (`TITLE-ABS-KEY(...)`), existence checks, the papers that cite a paper; needs a key for Elsevier's application programming interface (API), usually through your institution |
| Reading across many papers (optional) | **NotebookLM**, through a connector | answers grounded in quotations across a set of sources, for comparing several papers at once |

`kit/tools/literature-stack.md` has the setup steps and a test for each part.

## How they work together

**Adding a paper.** The agent searches the library first, so nothing is added twice. It adds the
paper by DOI, and the connector attaches the PDF where an open-access copy exists. An item without
its PDF is not finished: the agent attaches it in the same pass, or lists the paper as one you fetch
yourself through your institution. Then the literature note is created through the plugin, named
by the key Better BibTeX generated. Use that generated key rather than one you choose: a key chosen
by hand for an item the agent added does not take until you refresh it in Zotero yourself.

**Reading for a claim.** The agent starts from the literature note. If the claim carries weight, it
reads the passage in the full text, through the connector or, for a pivotal paper, in the Markdown
copy, and quotes it with its page. It says whether it checked the note or the paper. A note whose
`read:` field says "abstract" cannot carry a method detail.

**Pivotal papers, read by line.** For the few papers the work leans on (your own, the method you
build on), one Markdown copy made with MinerU sits beside the literature notes, named
`fulltext_<key>.md` so that a link to the key still finds the note. The agent never reads the copy
whole: it searches it for a term (`grep -n "boundary condition" fulltext_smith2023.md`) and reads
the forty lines around each hit. Every other paper is read through the connector, on demand,
because a copy in the vault costs as much to read and far more to make.

**Checking a citation.** A citation in an agent's draft is checked in three places, a web search,
scite and Scopus: author, year, title, journal and DOI, and then the passage it is cited for.
scite's notices say whether the paper was retracted or corrected. A citation that none of them finds
is not used.

**Citing.** In the vault every reference is a link to its literature note, `[[smith2023]]`, which
opens with a click. The manuscript cites the same key, from Better BibTeX's export. One key
everywhere is what lets a sentence in the paper be traced back to the note and to the passage.

## Traps worth knowing

- **Overwrite is not update.** A plugin command that overwrites a literature note destroys what you
  wrote in it. ZotLit's update adds new highlights and keeps your text; its overwrite does not.
- **A recomputed property can be emptied.** A property the plugin recomputes from Zotero on every
  update can be blanked by an expression that fails while it runs, although the settings accepted
  it. Try a new property on a throwaway note, never on one whose text you cannot replace.
- **Templates leak.** A template file with its own properties block passes that block into every
  note made from it.
- **A metadata-only item looks finished.** It is not, and the agent that has just read the PDF is
  the one that should attach it.

## In other agents

The connectors are MCP servers, which any agent that speaks MCP can use: Codex CLI, OpenAI's
command-line interface (CLI) agent, lists them under
`[mcp_servers.<name>]` in its `config.toml`, or adds one with `codex mcp add`. Zotero, Better BibTeX,
ZotLit and MinerU do not depend on the agent at all. For the services that come as connectors of
one provider (here scite through Claude), check whether your agent's provider offers them.

## Terms used

- **Reference manager**: the program that keeps your library of papers, such as Zotero.
- **Citation key**: the short, stable name of an item, such as `smith2023`, used for the note, the
  links and the citation.
- **Literature note** (or card): one note per paper, named by its key, saying what the paper holds
  for your work and where.
- **Full text**: the whole paper, as opposed to its abstract or a note about it.
- **DOI**: digital object identifier, the permanent name of a published paper.
- **Open access**: a paper anyone may read and download.
- **Connector (MCP server)**: a program that gives the agent tools for a service.
- **Pivotal paper**: one of the few papers your work leans on, worth a full-text copy in the vault.
