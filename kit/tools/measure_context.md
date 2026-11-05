# Measuring what the agent reads before the first word

*How to see what is on the agent's desk when a session starts, and what to cut. About ten minutes,
once now and once after every change to the setup.*

## Measure

1. Start a **new** session in the folder where you usually work. Do not type a task.
2. Type `/context`. Claude Code shows how full the context window is and what fills it, by
   category. The names vary between versions; typically they are the system prompt and the
   built-in tools, the tools of connected servers (Model Context Protocol, or MCP, tools), custom agents, memory files (your
   rules files and the memory index), skills, and the messages so far.
3. Write the numbers down, with the date, in a table you keep (a note in the vault is fine):

| Date | Total before the first word | Memory files | Skills | MCP tools | Agents | What changed |
|---|---|---|---|---|---|---|
| | | | | | | baseline |

Measure at the first turn of a fresh session, every time. Later in a session the messages dominate
and the comparison means nothing.

## What to cut, biggest lever first

1. **Connectors you do not use in this project.** Each connected server adds its tools and often a
   page of instructions to every session. Switch it off for the project in `/mcp`, or deny it in
   the project's `.claude/settings.json`. A connector a background agent needs cannot be denied
   for the session, because a deny applies to the agents it starts as well.
2. **Skill descriptions.** Every model-invoked skill puts its description in every session. Keep
   each to about 400 characters: what it does in one sentence, the phrases that trigger it, one
   "not for" pointer. Everything else goes into the skill's body, which loads only when the skill
   runs. A skill you invoke only by typing gets `disable-model-invocation: true`; a skill a project
   never uses gets `"off"` in that project's `skillOverrides` (guide 03).
3. **The rules file.** Past 200 lines, move what has a trigger into the skill or reference file
   that owns it, the stories behind rules into the changelog, and project facts into the project's
   notes (guide 02).
4. **The memory index.** One line per entry. A memory file longer than one screen has become a
   journal; its history belongs in a handover note in the vault.
5. **Agent descriptions.** A description with example dialogues costs its full length in every
   session, for an agent that may run twice a month. Role, model and one paragraph are enough.

## What to leave alone

What the agent opens while working (files, notes, tool results) is the work, not overhead. The
lever there is habit, not configuration: section reads instead of whole files, a script for bulk
data instead of the agent reading it, a new session for a new task, and noisy work delegated to a
background agent so that only its result comes back.

## Telling whether a cut worked

Measure again in a fresh session and add a row. Then check that nothing stopped working: the
skills you shortened should still fire on the phrases you use (guide 03, "Checks"). A cut that
saves tokens and loses a skill's trigger is not a saving.
