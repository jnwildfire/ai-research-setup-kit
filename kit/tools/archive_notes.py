#!/usr/bin/env python3
"""Archive the agent's dated notes once they have been quiet for thirty days.

The rule (guide 08, "Agent outputs, and an archive that runs itself"): a note at the top of the
agent-outputs folder whose file name starts with a date (YYYY-MM-DD-) moves to Archive/YYYY-MM/, the
month taken from the file name, when its last edit is more than DAYS days ago. "Last edit" is the
frontmatter `date-modified`, else `date-created`, else the date in the file name; never the file's
timestamp, which a sync client changes without changing the note. A note dated today never moves,
nothing is moved over an existing file of the same name, and an online-only file of a cloud drive
is never opened just to read its date (its file-name date counts instead).

This script moves files on disk, outside the notes app. Links that name a note by its file name
still find it; a link written as a path does not follow. The primary route is therefore a startup
script inside the notes app, which moves the note so that links follow (guide 08); this script is
its outside twin, for a scheduled task or a dry run. Every real move appends one line to
Archive/archive-log.md, so the archive can be audited and a move undone by hand.

Usage:
    python -I archive_notes.py --dry-run          list what would move, change nothing
    python -I archive_notes.py                    move, and log each move
    python -I archive_notes.py --self-test        the rule on a temporary folder
Options --vault, --folder and --days override the configuration block below.

Standard library only; Python 3.8 or later. Part of the ai-research-setup-kit; Copyright (c) 2026
Johannes Wildfeuer, MIT licence (see LICENSE.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

# ------------------------------------------------------------------------------- configuration
NOTES_ROOT = "<notes vault, for example C:/Users/you/OneDrive - Your University/Vault>"
FOLDER = "<the agent-outputs folder inside the vault, for example Agent outputs>"
ARCHIVE = "Archive"   # the subfolder that holds Archive/YYYY-MM/
DAYS = 30             # quiet this many days before a note moves
# --------------------------------------------------------------------------- end of configuration

NAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-.*\.md$")
FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)
# FILE_ATTRIBUTE_OFFLINE | RECALL_ON_OPEN | RECALL_ON_DATA_ACCESS: an online-only cloud-drive file on Windows
ONLINE_ONLY = 0x1000 | 0x40000 | 0x400000


def _fm_date(fm: str, key: str):
    m = re.search(r"^" + re.escape(key) + r":\s*[\"']?(\d{4}-\d{2}-\d{2})", fm, re.M)
    return m.group(1) if m else None


def last_touched(path: Path):
    """(date, source): date-modified, else date-created, else the date in the file name."""
    fm = ""
    try:
        attrs = getattr(path.stat(), "st_file_attributes", 0)
        if not attrs & ONLINE_ONLY:  # never download an online-only file just to read a date
            with open(path, encoding="utf-8", errors="replace") as fh:
                m = FM_RE.match(fh.read(4096))
            fm = m.group(1) if m else ""
    except OSError:
        pass
    for key in ("date-modified", "date-created"):
        d = _fm_date(fm, key)
        if d:
            return d, key
    return path.name[:10], "file name"


def eligible(folder: Path, days: int = DAYS, today: dt.date | None = None):
    """Notes at the top of the folder that the rule would archive, oldest first."""
    today = today or dt.date.today()
    cutoff = (today - dt.timedelta(days=days)).isoformat()
    out = []
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return out
    for e in entries:
        if not e.is_file() or not NAME_RE.match(e.name):
            continue
        touched, source = last_touched(Path(e.path))
        if touched >= cutoff or e.name[:10] == today.isoformat():
            continue
        target = folder / ARCHIVE / e.name[:7] / e.name
        out.append({"name": e.name, "touched": touched, "source": source,
                    "target": target, "target_exists": target.exists()})
    return sorted(out, key=lambda r: (r["touched"], r["name"]))


def archive(folder: Path, days: int = DAYS, dry_run: bool = False, today: dt.date | None = None, echo=print):
    """Move (or list) what is due; return (moved or would move, skipped)."""
    rows = eligible(folder, days, today)
    log = folder / ARCHIVE / "archive-log.md"
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    done = skipped = 0
    for r in rows:
        if r["target_exists"]:
            echo(f"skip  {r['name']}: {r['target']} already exists")
            skipped += 1
            continue
        if dry_run:
            echo(f"would move  {r['name']}  (last edit {r['touched']}, from {r['source']})  ->  {ARCHIVE}/{r['name'][:7]}/")
            done += 1
            continue
        r["target"].parent.mkdir(parents=True, exist_ok=True)
        (folder / r["name"]).rename(r["target"])  # same volume: a rename, no copy
        done += 1
        new_log = not log.exists()
        with open(log, "a", encoding="utf-8") as fh:
            if new_log:
                fh.write("# Archive log\n\nOne line per note moved by `archive_notes.py`. A move inside the "
                         "notes app (the startup script) does not log here.\n\n")
            fh.write(f"- {stamp} moved [[{r['name'][:-3]}]] to {ARCHIVE}/{r['name'][:7]}/ "
                     f"(last edit {r['touched']}, from {r['source']})\n")
    return done, skipped


def self_test() -> int:
    base = Path(tempfile.mkdtemp(prefix="archive-selftest-"))
    try:
        today = dt.date(2026, 11, 6)
        notes = {
            "2026-09-01-old-by-date-modified.md": "---\ndate-created: 2026-09-01\ndate-modified: 2026-09-20T10:00:00\n---\nx",
            "2026-09-02-recently-edited.md": "---\ndate-created: 2026-09-02\ndate-modified: 2026-10-30\n---\nx",
            "2026-08-15-no-frontmatter.md": "x",
            "2026-10-20-fresh-by-name.md": "x",
            "2026-11-06-dated-today.md": "---\ndate-modified: 2026-01-01\n---\nx",
            "2026-09-10-target-exists.md": "---\ndate-modified: 2026-09-10\n---\nx",
            "notes-without-a-date.md": "x",
        }
        for name, text in notes.items():
            (base / name).write_text(text, encoding="utf-8")
        (base / ARCHIVE / "2026-09").mkdir(parents=True)
        (base / ARCHIVE / "2026-09" / "2026-09-10-target-exists.md").write_text("older copy", encoding="utf-8")
        quiet = lambda *a, **k: None  # noqa: E731
        checks = []
        due = [r["name"] for r in eligible(base, 30, today)]
        checks.append(("the rule picks exactly the quiet notes, oldest first",
                       due == ["2026-08-15-no-frontmatter.md", "2026-09-10-target-exists.md",
                               "2026-09-01-old-by-date-modified.md"]))
        n, s = archive(base, 30, dry_run=True, today=today, echo=quiet)
        checks.append(("a dry run moves nothing", (n, s) == (2, 1) and (base / "2026-08-15-no-frontmatter.md").exists()))
        n, s = archive(base, 30, today=today, echo=quiet)
        checks.append(("a real run moves two and skips the one whose target exists", (n, s) == (2, 1)))
        checks.append(("a note goes to the month of its file name",
                       (base / ARCHIVE / "2026-08" / "2026-08-15-no-frontmatter.md").exists()
                       and (base / ARCHIVE / "2026-09" / "2026-09-01-old-by-date-modified.md").exists()))
        checks.append(("an existing archived file is not overwritten",
                       (base / ARCHIVE / "2026-09" / "2026-09-10-target-exists.md").read_text(encoding="utf-8") == "older copy"))
        checks.append(("recent, today's and undated notes stay on top",
                       all((base / x).exists() for x in ("2026-09-02-recently-edited.md", "2026-10-20-fresh-by-name.md",
                                                         "2026-11-06-dated-today.md", "notes-without-a-date.md"))))
        log = (base / ARCHIVE / "archive-log.md").read_text(encoding="utf-8")
        checks.append(("each move has one log line", log.count("\n- ") == 2))
        failed = 0
        for label, ok in checks:
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {label}")
        print(f"\n{len(checks) - failed} of {len(checks)} checks passed.")
        return 1 if failed else 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="list what would move; change nothing")
    ap.add_argument("--vault", help="the notes vault (default: NOTES_ROOT)")
    ap.add_argument("--folder", help="the agent-outputs folder inside the vault (default: FOLDER)")
    ap.add_argument("--days", type=int, default=DAYS, help=f"days without an edit (default {DAYS})")
    ap.add_argument("--self-test", action="store_true", help="run the rule on a temporary folder")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    vault, sub = args.vault or NOTES_ROOT, args.folder or FOLDER
    if "<" in vault or "<" in sub:
        print("Set NOTES_ROOT and FOLDER at the top of the script, or pass --vault and --folder.", file=sys.stderr)
        return 2
    folder = Path(os.path.expanduser(vault)) / sub
    if not folder.is_dir():
        print(f"No folder at {folder}", file=sys.stderr)
        return 2
    n, skipped = archive(folder, args.days, args.dry_run)
    cutoff = (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
    print(f"{'would move' if args.dry_run else 'moved'} {n} note(s); skipped {skipped}; rule: last edit before {cutoff}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
