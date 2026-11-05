# The literature stack: setup, and a test for each part

*The tools of guide 07 in the order to install them, each with a test that shows it works before
the next one depends on it. About an hour, much of it waiting for a first synchronisation. Keys and
tokens never go into this file, a note or a repository: keep them in environment variables, and
let configuration files refer to the variable by name.*

## 1. Zotero, the library

Install the Zotero desktop program, create an account at zotero.org and switch on synchronisation,
including files if your storage allows it.

**Test:** an item added on the desktop appears in your library on zotero.org.

## 2. Better BibTeX, the keys

Install the Better BibTeX add-on for Zotero and let it generate citation keys. Decide the key
pattern once, before the library grows (the author's keys are author and year, such as
`smith2023`), because keys are meant never to change.

**Test:** an item shows its citation key, and a new item gets one on its own.

## 3. A Zotero connector for the agent

Choose a Zotero connector, a Model Context Protocol (MCP) server, that can read full text. Several
are published; read what each does with your library before you give it a key. Two ways to reach
Zotero:

- **Zotero's web application programming interface (API)**: needs an API key from your account
  settings on zotero.org. Give it read access, and write access only if the agent should add
  items. Some servers attach open-access PDF (portable document format) files through Unpaywall
  when they add an item by its DOI (digital object identifier), which asks for an e-mail address.
- **Zotero's local API**: no key, faster, no rate limit, but only while the desktop program runs.

Register the server with Claude Code (`claude mcp add`; the options are in Claude Code's MCP
documentation) so that its configuration names the environment variable that holds the key, not
the key itself. A key written into a configuration file ends up in backups and, sooner or later,
in a repository.

**Test:** in a new session, ask the agent to find a paper you know is in the library and to quote
its first sentence from the full text, with the page.

## 4. ZotLit, the literature notes

Install ZotLit from Obsidian's community plugins. Set the folder for literature notes, the template
folder, and the note name to the citation key. Its properties are set field by field in its
settings, each with a rule for what happens on an update (recompute, add, or keep what is there);
use "keep" for every property you edit by hand.

**Test:** create the note for a known item, with ZotLit's quick switcher. The file name is the key,
the properties are filled, and your highlights from the PDF are in the note. Then run ZotLit's
update on it and check that a sentence you added by hand is still there. Never use its overwrite
command.

An agent can create notes through ZotLit too, so that every note carries the plugin's managed
properties: ZotLit registers an `obsidian://zotlit/open` link that opens an item's note and creates
it if it is missing. It takes the item's number in Zotero's database and a source identifier of
your installation; a wrong identifier fails without a message, and Obsidian's developer console
shows the one ZotLit expects. Test the link on one item before an agent relies on it.

## 5. MinerU, for pivotal papers only

Install MinerU as its documentation describes (a Python package; put it in its own virtual
environment). On a computer without a graphics card, use the backend that runs on the processor
alone (the central processing unit, CPU):

    mineru -p paper.pdf -o out/ -b pipeline

The first run downloads its models. Place the Markdown beside the literature notes as
`fulltext_<key>.md`, with its images in a subfolder, and add the file's path to the literature
note's properties.

**Test:** a formula comes out as LaTeX and a table as a table. Compare one table with the PDF, cell
by cell, before trusting any number read from the copy.

## 6. scite, for claims and citation context

scite needs an account. In the author's setup it is a connector added to Claude on claude.ai, which
Claude Code sessions then see.

**Test:** ask how a paper you know well is cited, and check that the answer quotes the citing
sentences and names the papers they come from.

## 7. Scopus, for discovery and existence checks

A Scopus connector needs an API key from Elsevier's developer portal. Most institutional
subscriptions allow one; some work only from the institution's network.

**Test:** search a known paper by its DOI (`DOI(<the doi>)`) and by a title search
(`TITLE("<exact title>")`); both return the same record.

## 8. NotebookLM, optional

For comparing several papers at once. A community connector signs in with your Google account
through the browser; the sign-in expires now and then and is renewed the same way.

**Test:** make a notebook with two papers and ask where they disagree; the answer quotes both.

## The whole chain

Add a paper by DOI through the agent, check its PDF is attached, create its literature note, cite
it as `[[key]]` in today's note, and ask the agent to check one sentence against the paper. The
answer quotes the passage with its page and says that it checked the paper, not the note.

## In the rules file

Two lines in the template carry this stack into every session: "Check the paper itself before a
literature claim carries weight" (already in `kit/CLAUDE.md.template`), and your citation rule
under "Writing", for example "Vault citations are `[[citekey]]` links to one literature note per
source".
