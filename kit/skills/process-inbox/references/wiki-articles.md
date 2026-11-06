# Wiki articles and data-source notes

## The audience: the person and the agent

The wiki is the shared reference for both. The agent reads the matching article before it reasons
about a concept the article covers (a standing rule in the rules file), and writes it so that a later
session with no memory of this one can pick the concept up cold: mechanisms stated, not gestured at;
measured, assumed and unknown kept visibly apart; reusable findings written back into the article
instead of being left in the meeting note or daily note where they surfaced.

## Shape

- One article per concept, not per source. File name lowercase with hyphens.
- Every factual claim from literature cites its source inline as `[[citekey]]`; `sources:` in the
  frontmatter lists every citation key used, as a real list (set in a whole-note write; a patch
  stores a list as text).
- Related articles in `related:` and as inline links.
- A `### Inferred` heading holds what was reconstructed rather than found in a source; claim words
  and basis words where the weight depends on them.
- When updating, keep every line and link, and integrate the new material.
- A long, self-contained discussion inside an article becomes its own article and a link.

## Link literature, do not summarise it again

An article cites a source and says in one or two sentences what that source means for this concept.
It does not reproduce the paper's method, sample or findings: that is the literature note's job, and
two copies drift apart, one of them silently going stale.

**Do not claim an independent derivation without checking.** A formula that matches a paper was very
likely taken from it. Attribute a method to its source; a convergence needs evidence, not the absence
of a memory of copying.

## Two bars for sources

Conflating them produces false caution and false confidence alike:

- **Facts about equipment and operation** may rest on a manufacturer's documentation or on what a
  project partner states (a device description, an operator's supply temperatures, a metering
  agreement). These are sources to use and cite, not to hedge as "not peer-reviewed".
- **Claims about method** need a scientific source. A datasheet can establish how a device counts;
  it cannot establish how a quantity should be computed, or that a method is valid.

When a manufacturer's document is specific to one vendor, say so, so that it is not read as
describing every device on the market.

## Conflicts and gaps

- When new material contradicts the article or a linked one, say so in the chat at once and record it
  under `## Tensions and conflicts`, with both citation keys and the nature of the disagreement.
  Never resolve a conflict silently.
- Where a concept is weakly supported, uncertain in method, or has a gap that matters, write it under
  `## Gaps and open questions`: what is missing, and why it matters. No generic caveats.

## Data-source notes

One note per external data source, because a data source is an interface to document field by field
before anything can be joined to it. The note covers:

- **Fields**: name, meaning, and which access route exposes it. A source often exposes the same data
  through several routes (an API, an export, a web page) that rename the fields: document them all,
  and mark the join key.
- **Code lists**: the enumerated values and what each code means.
- **Format**: types, units, precision traps (long numeric identifiers that must stay text), the time
  stamp convention and time zone, whether a value is instantaneous, an interval or a cumulative
  register, how a missing value is written.
- **The mapping into your own data model**, field by field, and what has no home in it yet. This part
  is what makes the notes worth writing.
- **What is unknown**, under `## Gaps and open questions`, never a plausible guess.
- **Where the raw files lie** in the data root.

These notes are reference, not synthesis: `sources:` is often empty, because the material comes from
the vendor's tables. File the specification document when one exists, so the note can be checked
again and its version tracked.
