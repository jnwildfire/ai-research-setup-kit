---
name: learn
description: Routes a correction to the place that owns it (a hook, a skill's procedure or checks, a path-scoped rule, the rules file, or memory) instead of adding it to the rules file by default. Use when the person corrects an output or says "do it better next time", "from now on", "remember to", "don't do that again".
---

# Learn: a correction goes to the place that owns it

A correction that lives only in the conversation is lost when the conversation ends. A correction
written into the rules file by reflex makes the file longer every week, until the rules that
matter drown. So each correction goes to the one place where it will fire at the right moment, and
only there.

## Procedure

1. **State it in one line**: the behaviour wanted from now on, and the incident that showed it was
   missing (what went wrong, on which output, on which date).
2. **Look for a rule that already covers it**, in the rules file, the skill that owns the
   workflow, the hooks and the changelog. If one exists, change that rule instead of adding a
   second one; if the existing rule was right and simply not followed, say so, and ask whether it
   should become a check or a hook.
3. **Choose the destination**, the first that fits, in this order:
   1. **A hook**, if the rule is mechanical and must never fail: a folder, a command, a format a
      script can check (the guard, an output check). A hook acts whatever the agent decides.
   2. **The skill that owns the workflow**: its Procedure if it is a step, its Checks if it is
      something to verify before reporting (meeting notes, daily notes, the dictionary, a talk).
   3. **A path-scoped rule** (`.claude/rules/<topic>.md` with `paths:` in its frontmatter), if it
      binds to a kind of file, such as project code.
   4. **The rules file** (`CLAUDE.md`), only if it fires on ordinary output and nothing would
      prompt the agent to look it up. Then as one line of judgement with its reason in one clause.
   5. **Memory**, if it is a preference or the state of a project rather than a rule.
4. **Write it**, as small as it can be. Show the person the change before it lands when it touches
   the rules file, a hook or the settings.
5. **Record the incident** in `.claude/rules-changelog.md`: the date, what happened, where the rule
   went. The story lives there, so the rule itself can stay one line.
6. **Report** the destination and the change in two lines. Whenever the rules file was touched,
   report its line count; past 200 lines, move something out (step 3 decides where) before adding.

## Checks

- The rule says why, in one clause. A rule without its reason cannot be applied to the case it did
  not foresee.
- The rule is not a copy of one that lives elsewhere. Two copies drift apart.
- A rule written as a prohibition ("never X") is rewritten as the judgement behind it, unless it is
  truly mechanical, in which case it belongs in a hook.
- If the correction was about a classification or a check that came out negative, test that the
  new rule can fire on a case that should trigger it before reporting it as fixed.
