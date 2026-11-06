#!/usr/bin/env python3
"""List the open tasks of the task board compactly, optionally filtered by search terms.

The task-board checker matches every input (a transcript, a note, a mail, progress in an issue
tracker) against the board. Reading a long board whole is expensive, so this prints one short line
per open task: block id, section, priority, scheduled date, deadline, carry count, and the task text
with its inline fields stripped. With terms, only tasks whose line contains any of them
(case-insensitive) are printed, so a candidate match costs a few lines of context.

The board's format (references/board-format.md): one Markdown task per line, `- [ ] text`, fields
inline as `[key:: value]`, and a block id at the end of the line, `^t-a12`. Sections are `##`
headings. Reading the board off disk is fine; every write still goes through the notes connector.

Usage:
    python -I open_tasks.py                      every open task
    python -I open_tasks.py report "^t-a4"       tasks that mention "report" or carry the id t-a4
    python -I open_tasks.py --done thesis        ticked tasks too
    python -I open_tasks.py --check              counts, duplicate ids, lines without an id
    python -I open_tasks.py --self-test

Run `--check` before and after every write to the board and compare: a check of the list markers
alone has passed while a whole section was missing.

Standard library only; Python 3.8 or later. Part of the ai-research-setup-kit; Copyright (c) 2026
Johannes Wildfeuer, MIT licence (see LICENSE.md).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter

# ------------------------------------------------------------------------------- configuration
NOTES_ROOT = "<notes vault, for example C:/Users/you/OneDrive - Your University/Vault>"
BOARD = "<the task board inside the vault, for example Maps/Tasks.md>"
SHOWN_FIELDS = ("prio", "do", "due", "carried")
# --------------------------------------------------------------------------- end of configuration

TASK = re.compile(r"^(?P<indent>\s*)- \[(?P<mark>.)\] (?P<body>.*)$")
FIELD = re.compile(r"\[(?P<key>[a-zA-Z_]+)::\s*(?P<value>[^\]]*)\]")
BLOCK_ID = re.compile(r"\^(t-[a-z0-9-]+)\s*$")
HEADING = re.compile(r"^(#{2,3})\s+(.*)$")


def parse(lines):
    section = "?"
    for no, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h and len(h.group(1)) == 2:
            section = re.sub(r"[^\w .-]", "", h.group(2)).strip()[:12] or "?"
            continue
        m = TASK.match(line)
        if not m:
            continue
        body = m.group("body")
        bid = BLOCK_ID.search(body)
        text = re.sub(r"\s+", " ", BLOCK_ID.sub("", FIELD.sub("", body))).strip()
        yield {"line": no, "sub": bool(m.group("indent")), "done": m.group("mark").lower() == "x",
               "id": bid.group(1) if bid else "(no id)", "section": section,
               "fields": {f.group("key"): f.group("value").strip() for f in FIELD.finditer(body)},
               "text": text, "raw": line}


def check(lines, out=print) -> int:
    tasks = list(parse(lines))
    ids = Counter(t["id"] for t in tasks if t["id"] != "(no id)")
    dupes = sorted(i for i, n in ids.items() if n > 1)
    missing = [t["line"] for t in tasks if t["id"] == "(no id)"]
    doubled = [no for no, line in enumerate(lines, 1) if re.match(r"^\s*- - \[", line)]
    out(f"task lines (top-level): {sum(1 for t in tasks if not t['sub'])}")
    out(f"task lines (with subtasks): {len(tasks)}")
    out(f"open: {sum(1 for t in tasks if not t['done'])}")
    out(f"duplicate ids: {', '.join(dupes) if dupes else 'none'}")
    out(f"lines without an id: {', '.join(map(str, missing)) if missing else 'none'}")
    out(f"doubled list markers: {', '.join(map(str, doubled)) if doubled else 'none'}")
    return 1 if dupes or doubled else 0


def listing(lines, terms, done=False, width=150, out=print) -> int:
    terms = [t.lower().lstrip("^") for t in terms]
    shown = 0
    for t in parse(lines):
        if (t["done"] and not done) or (terms and not any(x in t["raw"].lower() for x in terms)):
            continue
        meta = " ".join(f"{k}={t['fields'][k]}" for k in SHOWN_FIELDS if t["fields"].get(k))
        text = t["text"] if len(t["text"]) <= width else t["text"][:width - 1] + "..."
        out(f"{'  ' if t['sub'] else ''}[{'x' if t['done'] else ' '}] {t['id']:<10} {t['section']:<12} {meta:<36} {text}")
        shown += 1
    return shown


def self_test() -> int:
    board = """# Tasks

## A. Deadline, or someone waits

- [ ] Submit the report [prio:: A] [due:: 2026-11-15] ^t-a1

- [ ] Fix the import [prio:: A] [do:: 2026-11-06] [carried:: 2] ^t-a2
    - [ ] write the test ^t-a2-1

## B. Important

- [x] Read the paper [prio:: B] ^t-b1

- [ ] A line without an id [prio:: B]

- - [ ] A doubled marker ^t-b2

- [ ] Duplicate ^t-a1
""".splitlines()
    got = []
    rc = check(board, out=got.append)
    checks = [
        ("--check counts five top-level task lines and six with the subtask (a doubled marker is no task)",
         got[0].endswith(": 5") and got[1].endswith(": 6")),
        ("--check finds the duplicate id", "t-a1" in got[3]),
        ("--check finds the line without an id", got[4].split(": ")[1] == "14"),
        ("--check finds the doubled marker and exits 1", got[5].split(": ")[1] == "16" and rc == 1),
    ]
    rows = []
    n = listing(board, ["import"], out=rows.append)
    checks.append(("a term finds one open task with its fields", n == 1 and "do=2026-11-06" in rows[0] and "carried=2" in rows[0]))
    n = listing(board, ["paper"], out=rows.append)
    checks.append(("a ticked task is hidden without --done", n == 0))
    n = listing(board, ["paper"], done=True, out=rows.append)
    checks.append(("and shown with it", n == 1))
    n = listing(board, ["^t-a2"], out=rows.append)
    checks.append(("an id with ^ finds the task and its subtask", n == 2))
    failed = 0
    for label, ok in checks:
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
    print(f"\n{len(checks) - failed} of {len(checks)} checks passed.")
    return 1 if failed else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("terms", nargs="*", help="match any of these, case-insensitive (a name, a project, ^t-a4)")
    ap.add_argument("--done", action="store_true", help="include ticked tasks")
    ap.add_argument("--check", action="store_true", help="print the counts and duplicate ids only")
    ap.add_argument("--width", type=int, default=150, help="truncate the text column (default 150)")
    ap.add_argument("--board", help="the board file (default: NOTES_ROOT/BOARD)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # boards carry emoji
    except (AttributeError, ValueError):
        pass
    if args.self_test:
        return self_test()
    path = args.board or os.path.join(os.path.expanduser(NOTES_ROOT), BOARD)
    if "<" in path or not os.path.isfile(path):
        print(f"No board at {path}: set NOTES_ROOT and BOARD at the top, or pass --board.", file=sys.stderr)
        return 2
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if args.check:
        return check(lines)
    n = listing(lines, args.terms, args.done, args.width)
    print(f"-- {n} task(s) shown; board: {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
