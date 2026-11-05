# 5. What research adds to the method

*Kevin's method (deposit, never edit; every claim says what it rests on; corrections become rules)
holds for any knowledge work. Research adds a few demands of its own: claims about other people's
papers, numbers that travel, work checked before it leaves, several people on one base, and a
choice of models. About twenty minutes to read.*

## The paper itself, before a claim carries weight

The fear in a research audience is the invented citation and the paper summarised from its
abstract. The agent rarely invents a paper when it works from your reference library. The more
common fault is subtler: a claim is built on a note about a paper, and the note was written for
another question, or from the abstract alone.

The rule: **when a literature claim carries weight** (it decides a method, corrects someone, or is
about to be cited), **the agent opens the full text**, finds the passage, and says which it checked,
the note or the paper. A note's silence proves nothing; a note that does not mention a mechanism
does not show that the paper leaves it out. In the author's work, the full texts of two papers that
had been summarised from their abstracts overturned the claims built on them.

Two habits make the rule cheap to follow:

- **Literature cards, not summaries** (`kit/templates/literature-card.md`). A card lists what the
  paper holds for your work, each item with its page, equation or table and a short verbatim
  phrase, and a `read:` field that says what was actually read: the full text, some sections, or
  the abstract. A card read from the abstract cannot carry a method detail, and says so.
- **Full text by route.** A paper you rely on often gets one local text extraction, which the agent
  then searches by line. An occasional paper is read through your reference manager's full text or
  a literature service, by a background agent that returns the passage with its page.

Guide 07 sets up the tools behind both habits: the reference manager and its citation keys, the
literature notes made from it, the agent's connector, and the services that check a citation.

## Every number carries its basis

Kevin's rule says every claim says what it rests on. Numbers need one more word: what kind of thing
they are. **Measured, simulated, design, estimated, literature, judgement.** An annual heating
demand of 80 kWh per square metre can be a measurement in one building, a figure from a paper, a
design value from an energy certificate, or a parameter someone typed into a model run. All four
travel as "80 kWh/m²", and only the basis word tells a reader which one they are holding. Put the
word next to every number that carries weight, in notes, tables and slides; it is what a reviewer
asks for first.

## The agent as referee

The agent is used first as a writer. Researchers come to trust it as a critic, because a referee
pass finds what the author no longer sees. Three conditions make a review worth having:

1. **A separate reviewer.** A new agent, with a fresh context, that did not write the text. The
   agent that wrote a paragraph defends it.
2. **The strongest setting you have.** The best model for the domain, at the highest effort. A weak
   review costs a second one.
3. **Claim by claim against the sources.** Every cited claim against what the cited paper says;
   every project fact against the primary record (the meeting note, the data). The review lists the
   finding, the place in the text, and the source.

You decide, and you answer the review in a table that names the place and what you did. A rule that
came out of the review goes into the rules file or the skill the same day.

## Faults made into rules

Every rule in a good rules file has a story. Three from the author's work, anonymised, each with what
went wrong, how it showed, and the rule it left behind:

- **The wrong sign.** A screening of flats for undersupply looked for indoor temperatures that fell
  as the outdoor temperature rose, the opposite of what an undersupplied flat does, found none, and a
  slide reported that no flat ran short. A criterion that can never fire and a criterion that is
  never met give the same empty result. *Rule: a classification written in the session is not a
  finding until it has fired on a case that should trigger it.*
- **The number nobody sourced.** A minimum number of buildings for a demonstration entered an early
  note without a source, was copied into later notes and a plan, and read as established until
  someone asked where it came from, and nobody could say. *Rule: every project number carries its
  source; an inherited number without one is flagged, not repeated.*
- **The wrong "last week".** A draft thanked a partner for an e-mail "last week". The e-mail was two
  months old; it had reached the agent that day. *Rule: the date something reaches the agent is not
  the date it happened; relative dates come from the source.*

The pattern is Kevin's: a correction made twice becomes a rule the same day. What this kit adds is
where the rule goes: the `learn` skill (guide 03) routes it to a hook, a skill's checks, or the rules
file, and the story to the changelog.

## Decisions as tickets

A decision recorded without its reason is reopened a month later. Two patterns keep the reason:

- **A decisions table at the top of each meeting note** (`kit/templates/meeting-note.md`): one row
  per decision, with what depends on it, its status now, and a Verdict column you fill only where
  you disagree. A blank cell means approved, so reviewing a meeting takes a minute.
- **A ticket per decision** for a design that unfolds over weeks: one issue on GitHub (or any
  tracker) per open decision, linked from a map issue, with the issues that block it. The
  discussion stays attached to the decision, and closing the ticket records what was decided, when
  and why.

The agent can draft both. You decide.

## One base, several people

A research base is rarely one person's. An assistant writes into the same vault, a student is fed
from the same concept notes, a partner uses a tool built from the data. Three conventions keep that
workable:

- **Each note has an owner**: the person who writes in it. Others comment or propose; the owner
  changes the text.
- **A reading flag, not a gate.** A field such as `reviewed: false` says the owner has not read the
  note yet. It is set to false on everything the agent writes and set to true only by the owner.
  The note is still used, linked and cited meanwhile; the flag tells the owner what is new to them,
  nothing more. If the agent substantially changes a note the owner has read, it sets the flag back.
- **One real gate: unvetted capture.** An inbox of raw captures (clippings, dictations, forwarded
  material) is not cited until it has been processed into a proper note. Cite the processed note.

## Which model for which work

Route by the kind of work first, and only then by effort. Raise the effort before you change the
model.

In November 2026 the author routes three kinds of work:

- **Deep scientific work** (synthesis across many papers, method design, interpreting results
  against the literature) goes to the research lane: Fable 5.1 at the highest effort.
- **Visual work** goes to Opus 5.5: user interfaces, figures, images and video, and any judgement on
  something rendered, such as a screenshot, a drawing or a page. This holds even when the task looks
  small, and even when it sits inside a research task, because a verdict on a figure is only as good
  as the eye that gave it.
- **Everything else** (code, data, writing, design, mechanical edits) goes to Opus 5.5 at high
  effort, and at the highest effort when the task is hard.

There is no Sonnet or Haiku lane in this setup, by design. The smaller models are faster and use
less of a plan's allowance, but here quality comes first: a slightly wrong note or analysis costs a
review cycle and is read for months, so the cheaper pass is not cheaper. For the same reason nothing
that matters runs at low effort.

The reasons for the split are the published benchmarks at each model's release and the author's
experience, and both age. Re-check when a new model ships, before changing an agent's settings.

Here the session that hands out a task makes the routing call. A decision model such as Jev can make
that call automatically; it is the more advanced option, and not part of this kit yet.

The three executor agents in `kit/agents/` carry this routing: `exec-standard` and `exec-hard` for
everything that is not deep research, visual work included, and `exec-research` for what is. Each
says what it may write, that it runs no git command unless told, and that it stops and reports when
the task is bigger than its brief.

## Terms used

- **Full text**: the whole paper, as opposed to its abstract or a note about it.
- **Literature card**: an index of what a paper holds for your work, with locations and quotations.
- **Basis**: what kind of number a number is: measured, simulated, design, estimated, literature,
  judgement.
- **Referee pass**: a review of a finished text by a separate agent, claim by claim against sources.
- **Ticket**: an issue in a tracker such as GitHub, here one per decision.
- **Reading flag**: a field that says whether a note's owner has read it.
- **Effort**: how long the model thinks before it answers; higher effort is slower and more careful.
