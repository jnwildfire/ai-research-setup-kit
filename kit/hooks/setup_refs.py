"""Setup references: who names a thing, and which references point at nothing. No model tokens.

    python -I setup_refs.py --who process-meeting series_digest.py "date-modified"
    python -I setup_refs.py                 # the broken references; exit code 1 if any
    python -I setup_refs.py --self-test

A change to the setup (a skill, a step, a script, a flag, a folder, a field) is finished when
everything that names the changed thing agrees with it (kit/rules/setup-changes.md, guide 02).

The setup is the project the command is run in: the nearest folder at or above the current one
that holds a `.claude` folder, or the one given with --root.

  --who NAME ...   every line of the setup that names NAME (plain text, case ignored): CLAUDE.md,
                   .claude/** (text files; no worktrees), and outside the project the rules file
                   one folder up, ~/.claude/CLAUDE.md, the user-level skills and agents. These are
                   the dependents to read. Hits in rules-changelog.md are history, only counted.
  (no argument)    three checks a script can make, on the project's Markdown:
     path    a `.claude/...` path in backticks, or `scripts/...`, `references/...`, `../...` inside
             a skill, that does not exist. Not checked: a line that speaks of the past ("until
             2026-11-06", "retired", "moved here from"), a line with `$HOME` or `~`, a placeholder.
     step    "`skill` step N" (or a bare "step N" in a skill's own file) beyond the last numbered
             step of that skill's Procedure
     index   a project skill that the skill-library page names nowhere, or a row without a skill
             (project or user level). Rows are read under a heading that says "index" or "own
             skills"; keep rows for built-in and plugin skills under another heading.
   On a fresh install it lists the reference files the rules file routes to and you have not
   written yet: write them, or take the rows out.
   What it cannot see is a dependent that is wrong without being broken (a description that no
   longer fits, a count, a folder list in a script): that is what --who and a reader are for.

Standard library only. It never writes.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

TEXT = {".md", ".py", ".ps1", ".sh", ".json", ".xml", ".toml", ".yaml", ".yml", ".txt"}
HISTORY = "rules-changelog.md"            # names things as they were: never a dependent, never checked
SKIP_PARTS = {"worktrees", "__pycache__", "node_modules", ".git"}
TICK_RE = re.compile(r"`([^`\n]+)`")
REPO_PATH_RE = re.compile(r"(?<![\w/~.-])\.claude/[\w./-]+")
SKILL_PATH_RE = re.compile(r"^(?:scripts|references|\.\.)/[\w./-]+$")
NAMED_STEP_RE = re.compile(r"`([a-z][a-z0-9-]+)`,?\s+(?:its\s+)?steps?\s+(\d+)")
BARE_STEP_RE = re.compile(r"\bsteps?\s+(\d+)\b")
STEP_LINE_RE = re.compile(r"^\s{0,3}(\d+)\.\s")
PLACEHOLDER = set("<>*{}$")
PAST_RE = re.compile(r"\b(until|retired|removed|deleted|replaced|formerly|moved (?:here )?from|no longer)\b", re.I)


def find_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / ".claude").is_dir() and d != Path.home():
            return d
    return None


def main_checkout(root: Path) -> Path:
    s = str(root)
    i = s.lower().replace("/", "\\").find("\\.claude\\worktrees\\")
    return Path(s[:i]) if i >= 0 else root  # gitignored files exist only in the main checkout


def setup_files(root: Path, outside: bool) -> list[tuple[str, Path]]:
    out = []
    for p in [root / "CLAUDE.md", *sorted((root / ".claude").rglob("*"))]:
        if p.is_file() and p.suffix.lower() in TEXT and not SKIP_PARTS & set(p.relative_to(root).parts):
            out.append((p.relative_to(root).as_posix(), p))
    if outside:
        home = Path.home() / ".claude"
        extra = [root.parent / "CLAUDE.md", home / "CLAUDE.md", *sorted(home.glob("skills/*/SKILL.md")),
                 *sorted(home.glob("agents/*.md")), *sorted(home.glob("context/*.md"))]
        out += [("~/.claude/" + p.relative_to(home).as_posix() if home in p.parents else str(p), p)
                for p in extra if p.is_file() and root not in p.parents]
    return out


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def who(root: Path, names: list[str], outside: bool = True) -> int:
    files = setup_files(root, outside)
    for name in names:
        rx, hits, history = re.compile(re.escape(name), re.I), 0, 0
        print(f"== {name}")
        for label, p in files:
            lines = [(n, ln.strip()) for n, ln in enumerate(read(p).splitlines(), 1) if rx.search(ln)]
            if not lines:
                continue
            if p.name == HISTORY:
                history += len(lines)
                continue
            hits += len(lines)
            print(f"  {label}")
            for n, ln in lines:
                print(f"    {n}: {ln[:170]}")
        print(f"  {hits} line(s) to read; {history} more in {HISTORY} (history, left as written)")
    return 0


def last_steps(skill_dirs: list[Path]) -> dict[str, int]:
    """Skill name -> the highest step number of its Procedure."""
    out = {}
    for d in skill_dirs:
        for f in sorted(d.glob("*/SKILL.md")):
            inside, top = False, None
            for ln in read(f).splitlines():
                if ln.startswith("## "):
                    inside = ln.strip().lower() == "## procedure"
                elif inside and (m := STEP_LINE_RE.match(ln)):
                    top = max(top or 0, int(m.group(1)))
            if top is not None:
                out.setdefault(f.parent.name, top)
    return out


def broken(root: Path, user_skills: Path | None = None) -> list[dict]:
    skills_dir = root / ".claude" / "skills"
    user_skills = Path.home() / ".claude" / "skills" if user_skills is None else user_skills
    rows, main, steps = [], main_checkout(root), last_steps([skills_dir, user_skills])
    for label, p in setup_files(root, outside=False):
        if p.suffix.lower() != ".md" or p.name == HISTORY:
            continue
        own = p.relative_to(skills_dir).parts[0] if skills_dir in p.parents else None
        fence = False
        for n, ln in enumerate(read(p).splitlines(), 1):
            if ln.lstrip().startswith("```"):
                fence = not fence
            # a sentence about the past may name what is gone; a path under $HOME is not the project's
            skip_paths = bool(PAST_RE.search(ln)) or "$HOME" in ln or "~" in ln
            for tick in ([] if skip_paths else [ln] if fence else TICK_RE.findall(ln)):
                found = [(m.group(0), root, m.end()) for m in REPO_PATH_RE.finditer(tick)]
                if own and not fence and SKILL_PATH_RE.match(tick):
                    # `../x` is relative to the file's own folder, `scripts/x` to the skill's
                    found.append((tick, p.parent if tick.startswith("..") else skills_dir / own, len(tick)))
                for raw, base, end in found:
                    if PLACEHOLDER & set(tick[end:end + 1]) or ".local." in raw or "YYYY" in raw:
                        continue
                    rel = raw.rstrip("./")
                    if not ((base / rel).exists() or (main / rel).exists()):
                        rows.append({"file": label, "line": n, "kind": "path", "what": raw})
            if fence:
                continue
            named = {(m.group(1), int(m.group(2))) for m in NAMED_STEP_RE.finditer(ln)}
            if own and p.name == "SKILL.md" and not named:
                named |= {(own, int(m.group(1))) for m in BARE_STEP_RE.finditer(ln)}
            for skill, k in sorted(named):
                if skill in steps and k > steps[skill]:
                    rows.append({"file": label, "line": n, "kind": "step",
                                 "what": f"`{skill}` step {k}, its Procedure ends at {steps[skill]}"})
    index = next((d / "skill-library" / "SKILL.md" for d in (skills_dir, user_skills)
                  if (d / "skill-library" / "SKILL.md").is_file()), None)
    if index:
        own_skills = {f.parent.name for f in skills_dir.glob("*/SKILL.md")}  # the project's own must be indexed
        have = own_skills | {f.parent.name for f in user_skills.glob("*/SKILL.md")}
        text = read(index)
        named = set(TICK_RE.findall(text))  # a skill counts as indexed when the page names it anywhere
        listed, inside = set(), False       # a row counts only in the index proper
        for ln in text.splitlines():
            if ln.startswith("#"):
                inside = "index" in ln.lower() or "own skills" in ln.lower()
            elif inside and (m := re.match(r"\|\s*`([a-z][a-z0-9-]+)`\s*\|", ln)):
                listed.add(m.group(1))
        label = index.relative_to(root).as_posix() if root in index.parents else "~/.claude/skills/skill-library/SKILL.md"
        rows += [{"file": label, "line": 0, "kind": "index", "what": f"skill `{s}` has no row"} for s in sorted(own_skills - named)]
        rows += [{"file": label, "line": 0, "kind": "index", "what": f"row `{s}` has no skill"} for s in sorted(listed - have)]
    return rows


def self_test() -> int:
    """Each check must fire on a reference built to be broken and stay silent on its sound twin."""
    files = {
        "CLAUDE.md": "Read `.claude/context/there.md`, not `.claude/context/gone.md`. Run `python -I .claude/hooks/ok.py --x`.\n",
        ".claude/context/there.md": "Placeholders stay: `.claude/skills/<name>/SKILL.md`, `.claude/context/*.md`.\n"
                                    "It lived in `.claude/context/old-home.md` until 2026-11-06.\n"
                                    "```\n$f = Join-Path $HOME '.claude/state/x.json'\n```\n",
        ".claude/rules-changelog.md": "History may name `.claude/context/deleted-long-ago.md` and `alpha` step 9.\n",
        ".claude/hooks/ok.py": "# names alpha\n",
        ".claude/skills/alpha/SKILL.md": "# Alpha\n\n## Procedure\n\n0. **Zero.**\n1. **One.** See step 2.\n2. **Two.** "
                                         "`scripts/a.py`, `scripts/missing.py`, then step 7.\n\n## Checks\n\n1. not a step\n",
        ".claude/skills/alpha/scripts/a.py": "",
        ".claude/skills/alpha/references/r.md": "Back to `../SKILL.md`.\n",
        ".claude/skills/beta/SKILL.md": "# Beta\n\nAfter `alpha` step 2 and `alpha` step 3.\n",
        ".claude/skills/skill-library/SKILL.md": "# L\n\n## The index\n\n| Skill | What |\n|---|---|\n"
                                                 "| `alpha` | a |\n| `skill-library` | this |\n| `ghost` | gone |\n\n## Built in\n\n| `x` | y |\n",
    }
    with tempfile.TemporaryDirectory() as tmp:
        for rel, text in files.items():
            p = Path(tmp) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        got = {(r["file"], r["kind"], r["what"].split(",")[0]) for r in broken(Path(tmp), Path(tmp) / "no-user-skills")}
    want = {
        ("CLAUDE.md", "path", ".claude/context/gone.md"),
        (".claude/skills/alpha/SKILL.md", "path", "scripts/missing.py"),
        (".claude/skills/alpha/SKILL.md", "step", "`alpha` step 7"),
        (".claude/skills/beta/SKILL.md", "step", "`alpha` step 3"),
        (".claude/skills/skill-library/SKILL.md", "index", "skill `beta` has no row"),
        (".claude/skills/skill-library/SKILL.md", "index", "row `ghost` has no skill"),
    }
    for row in sorted(want - got):
        print("FAIL  should fire:  ", row)
    for row in sorted(got - want):
        print("FAIL  should not fire:", row)
    print(f"{len(want & got)} of {len(want)} broken references found, {len(got - want)} false")
    return 0 if got == want else 1


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--who", nargs="+", metavar="NAME", help="list every line of the setup that names NAME")
    ap.add_argument("--root", help="the project folder that holds .claude (default: found from the current folder)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    root = Path(a.root).resolve() if a.root else find_root(Path.cwd().resolve())
    if not root or not (root / ".claude").is_dir():
        print("no .claude folder at or above the current folder; run it inside the project or pass --root", file=sys.stderr)
        return 2
    if a.who:
        return who(root, a.who)
    rows = broken(root)
    for r in rows:
        print(f"{r['file']}:{r['line']}  {r['kind']:5}  {r['what']}")
    print(f"{len(rows)} broken reference(s)")
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
