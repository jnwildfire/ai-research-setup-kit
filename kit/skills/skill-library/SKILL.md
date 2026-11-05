---
name: skill-library
description: Index of every installed skill with one line each. Use when a request may match a skill that is not listed with a description, when several skills could fit, or when the person asks "which skill", "is there a skill for this", "what can you do here".
---

# Skill library

Every skill installed for this person, one line each. Skills that fire often keep their full
description in the session's skill listing and fire on their own. Skills set to `name-only` in
the settings (`skillOverrides`) appear in the listing by name alone; their purpose is written
here, so that this one page, loaded on demand, stands in for many descriptions loaded every turn.

## How to use this page

1. Find the line whose "Use when" matches the request. If two match, take the more specific one
   and say in one sentence why.
2. Invoke the skill by its name. A skill marked "typed" is user-invoked only: tell the person the
   command (`/name`) instead of running it.
3. If nothing matches, say so and do the work without a skill. If the same kind of request comes
   up a third time, propose a new skill to the person (see "Adding a skill" below).

## The index

State: `on` = full description in every session; `name-only` = name in the listing, purpose here;
`typed` = runs only when the person types `/name`; `off` = switched off in this project.

| Skill | Scope | State | Use when |
|---|---|---|---|
| `skill-library` | personal | on | a request may match a skill, or the person asks which skill fits (this page) |
| `learn` | personal | on | the person corrects an output or says "next time", "from now on", "remember to": route the correction to the place that owns it |
| `dictionary` | project | typed | the person wants new names or garbles added to the dictation dictionary and the exports rebuilt |
| `keep-awake` | personal | typed | a long or unattended job is about to run on a laptop: "keep awake", "night shift" |
| `<name>` | `<personal or project>` | `<state>` | `<the situation in the person's words, in one line>` |

## Per project

A project switches off what it never uses in its own `.claude/settings.json`, so the listing in
that project carries only what can fire there:

    {
      "skillOverrides": {
        "dictionary": "off",
        "<a skill this project never uses>": "off",
        "<a skill that rarely fires>": "name-only"
      }
    }

Selection stays automatic: the person never switches a skill on by hand before a task. A skill
goes to `name-only` only after a trigger test showed that it still fires from this page
(guide 03, "Checks").

## Adding a skill

Add its line here in the same change that adds the skill, with the state it starts in. A skill
without a line here is invisible once it is set to `name-only`.
