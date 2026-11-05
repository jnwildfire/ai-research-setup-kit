# 6. Data and the rules: the research-data case

*Read Kevin Smith's guide first:
[guide 06, "Data, privacy and the rules"](https://github.com/KevinMSmith/ai-research-starter-kit/blob/main/guide/06-data-and-the-rules.md)
in his starter kit. It explains what the agent can reach, what leaves the computer, which terms
apply to which Claude plan, the training setting, and what the European and Danish rules and the
guidelines of the Technical University of Denmark (DTU) say. Everything there applies here. This guide adds the case it does not cover: research
data about people and from partners. About five minutes to read.*

## The case

Kevin's guide is about transcripts of colleagues and other people's documents. A research section
also holds data like this:

- **Measurements in people's homes**: consumption, indoor temperature, occupancy, collected with the
  residents' consent for a stated purpose.
- **Partner data under an agreement**: readings from a utility or a vendor, delivered under a data
  agreement that says who may process them, for what, and often where they must be stored.
- **A notes vault on the institution's drive**, because the agreement or the institution requires
  it, which the agent reads like any other folder.

## What follows

1. **The agreement decides before the agent does.** Read what the consent text and the data
   agreement say about processing by third parties and about storage. If an agreement names the
   institution's storage, the data stays there, and Kevin's advice to keep projects off
   synchronised drives yields to it for the data; the code still lives on the local disk (guide 01).
   If it is unclear whether an artificial intelligence (AI) service may process the data, ask the data protection or legal
   office before the agent reads it, not after.
2. **What the agent opens is sent to the provider.** A file read by the agent becomes part of the
   prompt. So the agent works on data through scripts that read the data and report aggregates, and
   it does not open household-level files to look at them. This is also cheaper (guide 02).
3. **Pseudonymise at the first tier you control.** Keep the key that links a pseudonym to an address
   or a person outside the roots the agent works in, and let processed data carry the pseudonym only.
4. **A vault on the institution's drive is still read by the agent.** Notes about partners and
   residents are written by role, not by name, where the name is not needed; an opinion about a named
   person is personal data. Decide once, in the rules file, who is never named.
5. **The dictation dictionary goes to the dictation service.** Names you put into it are uploaded
   when you import it. Put in a person's name only where that is fine with them.

## What never goes into a public repository

A kit like this one, or a repository of your own analysis code that you make public, holds method,
not content. Before anything is pushed to a public repository, check that it contains none of:

- data of any tier, including small samples and test fixtures cut from real data;
- names of partners, residents, buildings, addresses, meter numbers or anything that identifies them;
- meeting notes, transcripts, e-mails, or the dictionary of names;
- credentials: tokens, passwords, keys, a filled `.env` file;
- the agent's memory and your local settings files.

Git cannot forget (guide 01): a file once pushed stays in the history even after it is deleted, and
a public repository may have been copied by then. Make the check before the first push, and keep
`.env`, `*.local.json` and data folders in `.gitignore` from the first commit.

## Terms used

- **Data agreement**: the contract under which a partner delivers data, saying who may process it,
  for what and where.
- **Pseudonymise**: replace what identifies a person or a home with a code, keeping the key apart.
- **Prompt**: what the agent sends to the model: your words and every file it has opened.
- **Public repository**: a repository anyone can read and copy.
