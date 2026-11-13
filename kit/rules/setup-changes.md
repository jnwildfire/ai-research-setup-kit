---
paths:
  - ".claude/**"
  - "CLAUDE.md"
---

# Changing the setup

A path-scoped rule: copy it to `<workspace>/.claude/rules/setup-changes.md`. It loads whenever the
agent opens a file of the setup and costs nothing otherwise.

**A change to the setup is finished when everything that names the changed thing agrees with
it.** The setup is one system written down in many files: a skill names another skill's step, a
script's flag, a folder, a frontmatter field, an agent, a model; a script repeats a folder list;
an index repeats a description. Nothing updates those by itself, and a dependent that still
describes the old state is followed as confidently as a correct one. So the change and its
dependents land in one commit.

It applies whenever a thing others may name changes: a skill is added, renamed, retired or
does something new; a step is added or renumbered; a script, flag, output file or key changes;
a vault folder, note type, template or frontmatter field changes; an agent or its model
changes; a rule moves to another file.

1. **Find the dependents.** `python -I ~/.claude/hooks/setup_refs.py --who <name> [<name> ...]`,
   run in the project, lists every line of the setup that names the thing: `CLAUDE.md`,
   `.claude/**`, and outside the project `~/.claude/CLAUDE.md` and the user-level skills. Ask
   for each name the thing goes by (the skill, its slash command, the script file, the key).
2. **Read each hit and bring it in line**, in the same commit: the row in `skill-library`, the
   step numbers others cite, the checks that run the script, the folder lists a script carries,
   the row in the automation map. The rules changelog is history and stays as written. A
   dependent outside the project (a user-level skill, a template in the vault) is changed there
   or named in the report as still open.
3. **Check what a script can check.** `python -I ~/.claude/hooks/setup_refs.py` exits clean: no
   path that does not exist, no step beyond a skill's last, every skill with its row in
   `skill-library`. It cannot see a dependent that is wrong without being broken; step 2 is for
   that. With the git hook installed (`kit/hooks/pre-commit`), the same check refuses a commit
   that touches the setup and leaves a dead reference. A refused commit is answered by fixing
   the reference, not by skipping the hook.
4. **Say it in the changelog entry**: which dependents were updated, and which were left and
   why.

A change made in the vault itself (a new or renamed folder) opens no file of the setup, so
nothing loads this rule. When you notice one, or the person mentions it, run `--who <folder>`:
the rules and skills that name the folder are its dependents.
