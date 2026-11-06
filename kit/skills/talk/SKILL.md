---
name: talk
description: Builds a talk from the vault and the data root, from the brief to a rendered deck that was read slide by slide, and a speaker guide written like an assembly manual. Triggers "/talk", "build the talk", "prepare the presentation". Not for critiquing a finished document, or a one-slide fix in a deck already handed over.
disable-model-invocation: true
---

# Talk

One talk, one plan note, one deck. The plan note holds every decision and source; the deck holds the
slides and the speaker guide.

**Where things live.**

- **Plan note**: beside the project in the vault (`<project>/talks/<slug>.md`), or in the agent-outputs
  lane for a talk that belongs to no project. Extended by appended, dated sections, never rewritten.
- **Deck and renders**: the data root, `presentations/<slug>/`, with `output/` for renders and the
  check images.
- **Build scripts** are code and live in git, not on the synchronised drive (a sync client and git
  fight over the same files). Where the person has no code home for talk scripts yet, ask once and
  record the answer in the plan note.

## Procedure

1. **The brief.** A table in the plan note: the audience (who, what they already know), the slot
   (minutes for the talk and for questions), the format (seminar, conference, job talk, milestone,
   supervision), the date and host, the file the host needs, **the one idea** (one sentence), **the
   promise** (what the audience can do at the end that it cannot now), and **the fence** (the
   neighbouring idea it will be confused with). Propose from the sources, mark each row "to
   confirm", and ask. Done when the person has confirmed or rewritten every row; nothing is built
   before.
2. **The inventory.** One line per thread the vault holds on the topic (the wiki first, then project,
   meeting and literature notes), each with its note; one line per figure in the data root that could
   carry a slide, with its path (list the folders the brief names, never a recursive search). A thread
   left out is named with the reason. Every number that may reach a slide carries its source and its
   basis. Done when every claim the talk could make points at a note, a file or a paper.
3. **The concept list.** One row per slide: number, title, the idea on it, the picture, minutes. Pace:
   two minutes for a plain slide, four to five for a question or a story, until a timed rehearsal
   gives the person's own number. Arc: the cover, the promise, a few numbered movements with
   dividers, the question to the room, the contributions; backup slides after them. Sum the minutes
   against the slot and name the slides to drop for a shorter one. Done when the person has said go.
4. **The build**, with the tool the talk needs: the host's template (python-pptx) for a talk the host
   runs, Marp for a quick seminar, Quarto for live code, equations or citations. Apply the slide rules
   below while building, not afterwards. Write the speaker guide (step 6) into each slide's notes as
   the slide is built. Once the person has opened or edited the file it is theirs: from then on,
   patch it by shape under a new file name, and never run the generator over it again.
5. **Render and read every slide**: all slides to images at presentation size, read at full size by
   an agent on a model that judges images well, against the Checks below and the concept list. Fix,
   render again, read again. Done when the last render after the last change has a clean report and
   its files match the deck being handed over (compare hashes: a sync client can serve an older
   render, and a check of a stale render checks nothing).
6. **The speaker guide, an assembly manual.** It reads like the instructions that come with flat-pack
   furniture, for the person who built the deck: per slide four fields and nothing else, **Key
   message** (one line), **Transition** (the bridge from the slide before, one line), **Must say** (at
   most four bullets), **If time** (short bullets). No prose, no paragraph, no sentence that only
   repeats the slide. Once on top for the deck: the one idea and the slides where it is said (three
   times), the fence, the question to the room and its wait (five to seven seconds), the last words (a
   salute, never "thank you"). It goes into the slide notes and, as one section, into the plan note.
   Format and a worked example: `references/speaker-guide-example.md`.
7. **The review, answered in a table.** The person reviews the rendered deck; every comment gets a row
   in the plan note: number, slide, the comment, what changed, the file version. A comment that holds
   for any talk becomes a rule in this skill the same day, through `learn`.
8. **Close.** Append "How the deck ended" to the plan note (the versions, which one is presented,
   the paths), and log the deck in the daily note. Delete stale versions only on the person's word.

## Resources

- `references/speaker-guide-example.md`: the speaker guide's format, filled for three slides.
- The talk rules in the Checks follow the MIT lecture "How to Speak" (MIT OpenCourseWare), which is
  worth an hour before the first talk built this way.

## Scripts

None of its own. The build and render scripts are the talk's code, in git.

## Checks

Before reporting, the agent that read the render (step 5) and you confirm each line; name every miss.

- **The talk**: it opens with the promise, not a joke, thanks or an apology; one idea, said three times
  from different angles, fenced; numbered movements with audible transitions; one real question to
  the room; the last slide is the contributions, enumerated, with no "thank you", "questions" or
  address slide after the backups; the one idea carries at least three of symbol, slogan, surprise,
  salient idea and story; a job or milestone talk shows the vision and a completed step in its first
  five minutes.
- **Each slide**: one idea and few words (a title of at most ten words, a bullet of at most fourteen);
  a picture where one can carry it; arrows and highlights baked in, so no pointer is needed; no logo
  clutter; "the agent" or "the model", never a product name standing for them; every number set
  against something the room knows; one animation click per idea.
- **The render read**: every slide read at full size after the last change; nothing cut off,
  overlapping or illegible at projection size; the hashes of the read render match the delivered file.
- **The speaker guide**: a block for every slide with the four fields; a transition on every slide
  after the cover; no field longer than its limit; the deck's header complete.
- **Sources**: every number and claim on a slide traced in the plan note to a note, a file or a paper;
  a literature claim that carries weight checked against the paper itself; abbreviations spelled out
  on first use in the deck; no project framing (a footer, a title) inherited from a source note.
- **The declaration**: the deck says that an agent helped make it, in the form the venue asks for,
  and the plan note names the sessions behind it.

## Learn

A comment of the person's that holds for every talk goes into the Checks above, with the date, through
`learn`; one that holds for this talk only stays in the plan note.
