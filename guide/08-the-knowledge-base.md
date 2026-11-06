# 8. The knowledge base: lanes, not a folder tree to copy

*How a notes vault that you and the agent both write into can be laid out, why each part exists,
and how the agent's outputs archive themselves. About ten minutes to read. Guide 01 placed the
vault among the three roots; this guide is about its inside. Set up your own; the author's layout
below is one example of it.*

## Where this layout started: Research Memex

The author's vault started from **Research Memex** ([research-memex.org](https://research-memex.org)),
by Xule Lin (SKEMA Business School and Imperial College London), an open guide to research with
artificial intelligence (AI) tools. Its Obsidian setup guide offers "one possible structure" for an empty research vault and
says to create only the folders your work needs:

```
00-Inbox/               temporary notes, to be processed
01-Literature-Notes/    one note per source, from Zotero
02-Permanent-Notes/     your synthesised insights
03-AI-Conversations/    conversations exported from AI tools
04-Research-Projects/   notes per project
05-Daily-Notes/         a research journal
06-Maps-of-Content/     index and overview notes
Templates/              note templates
Attachments/            images and PDFs kept locally
```

Over time the author added lanes for meeting notes, people, publications, a raw-input lane and a
wiki, and renumbered. You can start from Research Memex in the same way and add this kit's lanes
where your work needs them.

Based on [Research Memex](https://research-memex.org) by Xule Lin, Licensed under the MIT License.

## Lanes

A **lane** is a kind of note with its own job, its own author and its own rules. A folder is only
how a lane is kept apart; its name and its number are yours to choose. The lanes the author's vault
holds:

| Lane | Holds | Written by | Its rule |
|---|---|---|---|
| Inbox | unprocessed capture: clippings, dictations, forwarded material | you | not cited until processed into a proper note (guide 05) |
| Literature notes | one note per paper, named by its citation key | the reference-manager plugin and you | guide 07 |
| Permanent notes (optional) | ideas argued in your own words | you; the agent may draft | see below |
| Meeting notes | one note per meeting, with a decisions table on top | you and the agent | `kit/templates/meeting-note.md` |
| Daily notes | what happened today, what carries over to tomorrow | you and the agent | `kit/templates/daily-note.md` |
| Agent outputs | dated notes the agent writes: plans, analyses, decisions with their reasons, answers worth reading again | the agent | the archive below |
| Projects | a folder per project | both | |
| Publications | a folder per paper in the pipeline: scope, venue, status | both | |
| Maps of content | index notes that link a topic's notes | both | |
| People | one note per person: role, organisation, how the name is written | you | a profile, not a diary; only what the work needs (guide 06) |
| Raw input | material gathered for a wiki article | both | not cited, like the inbox |
| Wiki | topic articles the agent keeps from sources, citing by key | mainly the agent | the agent's working reference: read before reasoning about a concept, corrected when a session learns something new |
| Templates, attachments | the note templates; images and files embedded in notes | you, the notes app | |

## One worked example

The author's vault, in November 2026:

```
00-Inbox/                  capture; _later/ for items parked on purpose
01-Literature-Notes/       one note per paper; fulltext/ for the few Markdown full texts
02-Permanent-Notes/        ideas in the author's own words
03-Meeting-Notes/          one note per meeting
04-Daily-Notes/YYYY-MM/    one note per day, a folder per month
07-AI-Conversations/       agent outputs; Archive/YYYY-MM/ for the older ones
08-Research-Projects/      a folder per project
09-Publications/           a folder per paper in the pipeline
20-Maps-of-Content/        index notes
21-People/                 one note per person
98_raw_Wiki_Input/         material gathered for the wiki
99_Wiki/                   topic articles
Templates/
Attachments/
```

The numbers only sort the lanes in the file list; the gaps are left over from renumbering and mean
nothing. Do not copy them. Choose names you will recognise on a phone, keep the lanes you will
actually write into, and add a lane when its third note would otherwise land somewhere it does not
belong.

## Agent outputs, and an archive that runs itself

The agent writes much that is worth keeping for a while and little that is worth keeping on top: a
plan for a session, an analysis, a decision with its reasoning, an answer you would rather read in
the notes app than in the terminal. All of it goes into one lane, kept usable by four conventions:

- **Dated notes on top.** Each note is named `YYYY-MM-DD-<topic>.md`, so the folder sorts by date
  and its top holds what is current.
- **One folder, two kinds, told apart by a property.** A `type` property says what the note is:
  `ai-conversation` for a conversation kept for what it decided, `ai-output` for an answer
  rendered for reading. A property does this better than a second folder: the archive treats both
  kinds alike, and a search or a query still picks out one kind.
- **An archive that runs itself.** A note nobody has edited for thirty days moves into
  `Archive/YYYY-MM/`, the month taken from its file name. A small script does it each time the
  notes app starts (in the author's vault, a startup script of the Templater plugin). It reads the
  note's own modified-date property, which a plugin updates on every edit, not the file's
  timestamp, because a sync client changes the timestamp without changing the note. The move runs
  inside the notes app, so links follow the note. A notes app left open for weeks never restarts,
  so the same rule also runs outside it, weekly, as a scheduled script (`kit/tools/archive_notes.py`,
  with a dry run first and one log line per move).
- **The agent writes on top, never into the archive**, and never moves notes between the two by
  hand. Notes are linked by file name, which finds them wherever they are. The guard can hold the
  archive to this (`existing-only`: an archived note may be corrected in place, nothing is filed
  there by hand).

## Permanent notes, if you want them

Research Memex has a lane for synthesised insights, which the author kept as permanent notes:
ideas argued in your own words, each linked to the literature notes it rests on. The lane is
optional. It earns its place if you write to think, because writing an idea in your own words is
where you notice what you do not yet understand; an agent's draft can start a note, but the final
text is yours. If you do not work that way, leave the lane out: the wiki and the agent outputs hold
the rest.

## Reconnaissance, then dictation

A vault built over months holds a lot, and the knowledge that matters most is often not in it: why a
choice was made, which number is the right one, what a meeting actually settled. Those live in the
author's head. Two steps bring them in, in this order.

**One reconnaissance pass, read-only.** An agent on the research model reads the whole vault once
and writes one note, changing nothing else: what the corpus emphasises (the notes most linked, the
topics most written about), what it claims without a source, what it references but does not hold
(a document cited and never filed, a link to a note that does not exist), which statements contradict
each other (and which of those the record already settles), and a **dictation queue**: eight to
fifteen questions only the author can answer, each naming the note that will receive the answer. In
the author's vault the first attempt ran out of context; what kept the second within budget was a
small script that listed the vault one folder at a time, readers per folder that returned short
digests, and a check of every quotation, character for character, against its note before it was
kept.

**A dictation lane.** A folder in the inbox (`<inbox>/dictations/`) with a template: the question's
ID, the note it feeds, and the answer as spoken. The author answers by voice, a question at a time,
with a dictation program, and does not edit what it writes; the agent reads through the errors. The
agent then works each answer into the receiving note and links the dictation from it. The later word
wins: when an answer contradicts an earlier note, the change is recorded with its date and the old
text kept as replaced, never averaged. Decide once whether the inbox's gate applies to these notes:
a dictation is the author's own word, not someone else's capture, so the author may let the agent
integrate it without a second yes.

The order is Kevin Smith's: reconnaissance first, then the author dictates what is missing. His
guide 02 sets out the dictating and the rule that the later word wins. The lane itself sits in the
inbox that the Research Memex structure starts from.

## Four habits that keep a shared vault working

- Each note has an owner, and a reading flag tells the owner what is new (guide 05).
- The agent writes notes through the notes app's connector when the note may be open, and changes
  one passage at a time instead of rewriting a note (guide 03, "Optional add-ons").
- Nobody searches a synchronised vault recursively (guide 01).
- Every reference is a link to its literature note, `[[smith2023]]` (guide 07).

## Terms used

- **Vault**: a folder of linked Markdown notes, opened in a notes program such as Obsidian.
- **Lane**: a kind of note with its own job, author and rules, usually kept in its own folder.
- **Property**: a named field at the top of a note, such as `type` or `reviewed` (in Obsidian
  also called frontmatter).
- **Permanent note**: an idea argued in your own words, linked to the sources it rests on.
- **Wiki**: topic articles that the agent keeps from sources and reads before it reasons about a
  concept.
- **Map of content**: an index note that links the notes of a topic.
- **Startup script**: a small script the notes app runs each time it starts.
- **Reconnaissance pass**: one read-only reading of the whole vault that reports what it emphasises,
  what it claims without a source, what it lacks, and what only the author can answer.
- **Dictation queue**: the questions only the author can answer, each with the note that receives
  the answer.
