# Speaker guide: format and worked example

The guide is an assembly manual for the person who built the deck: what each slide is for, how to get
onto it, what must be said. It is read in a rehearsal and glanced at on stage, so every field is a
line or a bullet, never a paragraph.

## Format

**Deck header** (once, before the first slide):

- **One idea**: the sentence; **said on** the slides where it comes back (three of them).
- **Fence**: what it is not, and on which slide that is said.
- **Question to the room**: the question, the slide, "wait five to seven seconds".
- **Last words**: the salute or the line that ends the talk (never "thank you").
- **Time**: the total minutes against the slot; the slides to drop when running late.

**Per slide:**

```
### <n>. <slide title> (<minutes> min)
- **Key message:** <one line>
- **Transition:** <one line bridging from slide n-1>
- **Must say:**
  - <at most four bullets>
- **If time:**
  - <short bullets, optional>
```

## Worked example

Illustrative: three slides of a 20-minute seminar talk built on guide 02 of this kit ("what the agent
reads"). The slide numbers are this example's.

**Deck header**

- **One idea**: the agent is only as good as what it reads before it answers, and in a terminal agent
  that is yours to choose, check and keep. **Said on** 2 (the promise), 5 (the desk), 13 (the
  contributions).
- **Fence**: not "the model is clever or not"; what decides is what lies on its desk. Said on 5.
- **Question to the room**: "What would you put on the desk first in your own project?" On 12; wait
  five to seven seconds.
- **Last words**: a salute to the room's own projects; no "thank you".
- **Time**: 20 min; if late, drop 7 and say its one line on 8.

### 4. The colleague who forgets (2 min)
- **Key message:** The agent reasons well but remembers nothing between sessions; what it knows is what it reads now.
- **Transition:** "So far, what the model can do; now, what it can remember."
- **Must say:**
  - a colleague who keeps their reasoning but loses each day's memory: sharp in the conversation, blank the next morning
  - so the notes on the desk are the memory, not the conversation
- **If time:**
  - the folder is the memory; a new task is a new session

### 5. The desk (3 min)
- **Key message:** Before you type a word, the desk is already laid by rules, and every turn the whole desk is read again.
- **Transition:** "So what does our colleague read? Look at the desk."
- **Must say:**
  - the stack before the first word: the rules file, the skill descriptions, the tool instructions, the memory index
  - everything you say and every file it opens lands on the same desk
  - every turn the model reads the entire desk again
  - when the desk is full it is swept: a summary stays, the rest is gone
- **If time:**
  - click 1 the stack, click 2 the pile, click 3 the broom
  - subagents keep the desk clean: they read elsewhere and bring back only the answer

### 6. Tokens (2 min)
- **Key message:** Tokens are the unit of the desk; the start of a session is cheap, a large file read by the agent is not.
- **Transition:** "The desk has a size, and it is counted in tokens."
- **Must say:**
  - a token is a piece of a word; the desk and the bill are both counted in them
  - tens of thousands of tokens lie on the desk before the first word
  - a 10 MB data file is millions of tokens: a script reads it, not the agent
- **If time:**
  - stock against flow: the window is what lies on the desk at once, the bill is what is read over the session
