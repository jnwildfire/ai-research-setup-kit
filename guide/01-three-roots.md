# 1. Three roots: code, data and knowledge, kept apart

*For a researcher who already has code, data and notes, and wants the agent to work across all
three without mixing them up. About ten minutes to read. Kevin Smith's kit puts one project into
one folder; this guide is for the case where that folder already exists three times over.*

## Why three, and not one

Kevin's knowledge base is one folder per project, under version control, with the originals, the
agent's pages and the products side by side. That is the right shape for a teaching corpus or a
single study. A research group's work rarely fits it. The measurement data is large and may have
to stay on the institution's storage because a data agreement says so. The code lives in several
repositories, some shared with colleagues. The notes span every project and are read on a phone
between meetings. Forcing all of it into one folder breaks at least one of these.

So the setup keeps three **roots**, three top folders, each holding one kind of thing:

| Root | Holds | Kept in | Why there |
|---|---|---|---|
| **Code** | scripts, analysis code, the agent's rules file, skills and settings | a folder of git repositories on the computer's own disk, for example `C:\dev\` | git records every change and can restore any earlier version; a repository can be shared with a colleague without sharing the data |
| **Data** | raw data, processed data, figures, slides, finished documents | the institution's shared drive, for example OneDrive for your university | it is backed up, it is where data agreements usually require the data to sit, and large files do not belong in git |
| **Knowledge** | notes: meetings, papers, concepts, decisions, plans, daily log | a notes vault, for example an Obsidian vault on the same shared drive | plain Markdown files that you and the agent both read and write, linked to one another, searchable, readable on a phone |

The agent works across all three in one session: it reads a meeting note in the vault, runs a
script from a repository on data from the shared drive, and writes the figure back to the data
root and a line about it into the daily note.

## Why they are never mixed

Each mix has a cost that shows only later.

- **Data or notes in a git repository.** Git cannot forget. A file once committed and pushed stays
  in the repository's history even after it is deleted, so a meeting note with a partner's name, or
  a data file with a household's consumption, cannot be withdrawn from a repository that has been
  shared. Code and configuration that are safe to keep forever go into git; nothing else.
- **A git repository on a synchronised drive.** The sync client and git both rewrite the same
  files, and the result is conflicting copies and, now and then, a broken repository. Kevin's
  guide 06 makes the same point for the knowledge base.
- **Code on the data drive.** Scripts scattered between data folders have no history, are copied
  instead of shared, and end up in three versions that disagree.
- **Results inside the notes.** A vault full of exported tables and figures becomes slow to sync
  and hard to search. The note links to the figure on the data root and says what it shows.

## What goes where

| You have | It goes to |
|---|---|
| a script that cleans a dataset | code root, in the project's repository |
| the dataset as downloaded or received | data root, `projects/<project>/data/raw/` |
| the cleaned dataset | data root, `projects/<project>/data/processed/`, made by the script |
| a figure for a paper | data root, `projects/<project>/outputs/` |
| the paper's draft | where you write papers: a repository for LaTeX, the data root for Word |
| a meeting transcript | data root, kept unchanged, for example `meeting-transcripts/<series>/` |
| the meeting note made from it | the vault |
| a literature card for a paper | the vault, one card per paper |
| the agent's rules file, skills, hooks | the code root (the workspace repository) and your user folder |
| a password, a token, a key for a service's programming interface (API) | none of them: a password manager, or a gitignored `.env` file |

## Data tiers

Inside the data root, each project keeps its data in tiers, and data only flows one way. `raw/`
holds what you downloaded or received, exactly as it came; it is never changed, and a corrected
delivery is a new file beside the old one. `processed/` holds what code made from `raw/`, in a
format that keeps types and is fast to read (parquet, for example), and can be deleted and made
again at any time. `outputs/` holds figures, tables and models, each made by a script that is in
the code root. `docs/` holds what is neither: a received specification, a data agreement, a
document for a partner. The tiers are what make a number traceable: a figure points to the script
that made it, the script to the processed file, the processed file to the raw delivery.

The guard (guide 04) enforces the first tier: it refuses any action of the agent that would change
a file in `raw/`, while still letting a new file in.

## One rule that is easy to miss: never search the drive

A cloud drive such as OneDrive often keeps files online only, as placeholders, and downloads a file
the moment anything opens it. A search through the whole drive (a recursive `find`, `grep -r`, or a
file search from the root) opens every file, so it downloads the whole drive and can fill the disk.
The agent should go to the path it knows, or list one folder. Put this into your rules file; the
template has it.

## What the agent can reach

The agent works with your permissions, so it can open anything on the three roots and anything else
you can open. Kevin's guide 06 explains what that means for other people's material; guide 06 of
this kit adds the case of data under an agreement. The short version: decide what each root may
hold before the agent reads it, because what it reads is sent to the provider to be processed.

## Terms used

- **Root**: one of the three top folders, for code, data and knowledge.
- **Repository**: a folder whose every change git records.
- **Vault**: a folder of linked Markdown notes, opened in a notes program such as Obsidian.
- **Synchronised drive**: a folder that a program (OneDrive, Dropbox) copies to the cloud.
- **Placeholder**: a file a cloud drive shows but keeps online until something opens it.
- **Tier**: a stage of a project's data: raw, processed, outputs.
- **Parquet**: a file format for tables that keeps column types and reads fast.
- **Gitignored**: listed in a repository's `.gitignore`, so git never records the file.
