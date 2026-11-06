---
name: learn
description: Routes a correction or a new standing preference to the place that owns it (a hook, a skill's procedure or checks, a reference file, a path-scoped rule, the rules file, or memory) instead of adding it to the rules file by reflex. Use when the person corrects an output or says "do it better next time", "from now on", "remember to", "don't do that again", "always", "never".
---

# Learn: a correction goes to the place that owns it

A correction that lives only in the conversation is lost when the conversation ends. A correction
written into the rules file by reflex makes the file longer every week, until the rules that matter
drown. So each correction goes to the one place where it will fire at the right moment, and only there.

## Procedure

1. **State it in one line**: the behaviour wanted from now on, and the incident that showed it was
   missing (what went wrong, on which output, on which date).
2. **Look for a rule that already covers it**: in the rules file, the skill that owns the workflow (its
   `SKILL.md` and its `references/`), the reference files the rules file routes to, the path-scoped
   rules, the hooks and settings, and the changelog. If one exists, change it instead of adding a
   second. If it was right and simply not followed, say so, and propose a check or a hook: a sentence
   that did not hold once will not hold the second time either.
3. **Choose the destination**, the first that fits, in this order:
   1. **A hook**, if the rule is mechanical and must never fail: a folder, a command, a format a script
      can check (the guard, the output check). A hook acts whatever the agent decides. Hooks and
      settings change only with the person's yes.
   2. **The skill that owns the workflow**: its Procedure if it is a step, its Checks if it is
      something to verify before reporting (meeting notes, daily notes, the task board, a talk). A
      reference fact goes into its `references/`.
   3. **A reference file** that keeps its own trigger in the rules file's routing table (delegation,
      connectors, the automation map).
   4. **A path-scoped rule** (`.claude/rules/<topic>.md` with `paths:` in its frontmatter), if it binds
      to a kind of file, such as project code.
   5. **The rules file** (`CLAUDE.md`), only if it fires on ordinary output and nothing would prompt
      the agent to look it up. Then as one line of judgement with its reason in one clause.
   6. **Memory**, if it is a preference or the state of a project rather than a rule. A rule saved to
      memory instead of a file rots; memory holds at most a pointer.
4. **Write it**, as small as it can be. Show the person the change before it lands when it touches the
   rules file, a hook or the settings.
5. **Record the incident** in the rules changelog, newest first: the date, what happened, why, and
   where the rule went. The story lives there, so the rule itself can stay one line.
6. **Report** the destination and the change in two lines. Whenever the rules file was touched,
   report its line count; past 200 lines, something moves out (step 3 decides where) before anything
   comes in.

## Resources

- The rules changelog: its format and its precedent.
- `skill-library`: which skill owns which workflow.

## Scripts

None. The line count is `wc -l CLAUDE.md` (or `(Get-Content CLAUDE.md).Count` in PowerShell).

## Checks

- The rule says why, in one clause. A rule without its reason cannot be applied to the case it did
  not foresee.
- The rule is not a copy of one that lives elsewhere. Two copies drift apart.
- A rule written as a prohibition ("never X") is rewritten as the judgement behind it, unless it is
  truly mechanical, in which case it belongs in a hook.
- If the correction was about a classification or a check that came out negative, test that the new
  rule can fire on a case that should trigger it before reporting it as fixed.
- The file the rule went into is still in shape: past about 400 lines, or grown piece by piece until
  it is hard to scan, say so and offer a restructure; do not restructure without the person's go.

## Learn

A correction to this routing (a rule that landed in the wrong place and did not fire) goes into the
order of step 3, with its incident in the changelog.
