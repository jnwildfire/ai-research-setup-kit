#!/usr/bin/env python3
"""Digest one meeting series for a pre-meeting brief: decisions, carry-overs, marked claims.

Reads the meeting notes of one series folder off disk (reading the vault is fine; writes go through
the notes connector) and prints Markdown with four parts:

1. Decisions of the last N record notes whose `Status now` is not Superseded, Overturned or Never
   actioned, with their Verdict mark, from the table under the heading "0. Decisions taken" of the
   meeting-note template. The ID is the row's first cell, with or without the `[decision:: ID]`
   inline field.
2. Items carried more than twice: every backticked ID (`S12`, `W3`) that appears in the carry-over
   sections ("From the last meeting", "Carried over", "Open issues") of three or more record notes
   other than the note that decided it. This is a candidate list: read the rows before a brief
   names them.
3. Claims marked `[conf:: stated]` or `[conf:: assumed]` in the series, with their note.
4. The open issues of the latest record note, verbatim.

Agenda notes (file name contains "agenda") are skipped for decisions and carry-overs, and the newest
is named, since the brief is written into it.

Usage:
    python -I series_digest.py weekly
    python -I series_digest.py supervision --last 4
    python -I series_digest.py "<meetings folder>/weekly" --min-carried 2

Standard library only; Python 3.8 or later. Part of the ai-research-setup-kit; Copyright (c) 2026
Johannes Wildfeuer, MIT licence (see LICENSE.md).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ------------------------------------------------------------------------------- configuration
NOTES_ROOT = "<notes vault, for example C:/Users/you/OneDrive - Your University/Vault>"
MEETINGS = "<meetings folder inside the vault, one subfolder per series>"
CARRY_HEADINGS = ("from the last meeting", "carried", "open issue", "still open")
# --------------------------------------------------------------------------- end of configuration

CLOSED = ("superseded", "overturned", "never actioned")
ID_IN_TICKS = re.compile(r"`([A-Z]{1,3}\d{1,3})`")
DECISION_FIELD = re.compile(r"\[decision::\s*([^\]]+)\]")
CONF_FIELD = re.compile(r"\[conf::\s*(stated|assumed)\s*\]", re.I)
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def series_dir(arg: str, vault: Path) -> Path:
    p = Path(arg)
    if p.is_absolute():
        return p
    if (vault / p).is_dir():
        return vault / p
    return vault / MEETINGS / p


def sections(lines: list[str]):
    """Yield (heading_text_lower, [lines]) for every heading section (to the next heading)."""
    title, buf = "", []
    for line in lines:
        h = HEADING.match(line)
        if h:
            yield title, buf
            title, buf = h.group(2).strip().lower(), []
        else:
            buf.append(line)
    yield title, buf


def cells(row: str) -> list[str]:
    """Split a table row on its pipes, keeping `\\|` and a pipe inside [[...|alias]] in the cell."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    out, buf, depth, i = [], [], 0, 0
    while i < len(row):
        two = row[i:i + 2]
        if two == "[[":
            depth += 1
            buf.append(two)
            i += 2
            continue
        if two == "]]" and depth:
            depth -= 1
            buf.append(two)
            i += 2
            continue
        ch = row[i]
        if ch == "|" and depth == 0 and (i == 0 or row[i - 1] != "\\"):
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf).strip())
    return out


def decisions(lines: list[str]):
    for title, body in sections(lines):
        if not title.startswith("0. decisions"):
            continue
        for row in body:
            if not row.lstrip().startswith("|") or set(row.strip()) <= set("|-: "):
                continue
            c = cells(row)
            if len(c) < 2 or c[0] in ("#", "ID"):
                continue
            field = DECISION_FIELD.search(c[0])
            did = field.group(1).strip() if field else re.sub(r"[`*]", "", c[0]).strip()
            text = c[1]
            bold = re.search(r"\*\*(.+?)\*\*", text)
            text = bold.group(1) if bold else text
            text = text if len(text) <= 160 else text[:157] + "..."
            status = c[3] if len(c) > 3 else ""
            verdict = c[4] if len(c) > 4 else ""
            yield did, text, status, verdict


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("series", help="series folder under MEETINGS, or a vault-relative or absolute path")
    ap.add_argument("--last", type=int, default=3, help="record notes whose decisions are listed (default 3)")
    ap.add_argument("--min-carried", type=int, default=3, help="notes an ID must be carried in (default 3, i.e. more than twice)")
    ap.add_argument("--vault", help="the notes vault (default: NOTES_ROOT)")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    vault = Path(os.path.expanduser(args.vault or NOTES_ROOT))
    if "<" in str(vault) and not Path(args.series).is_absolute():
        print("Set NOTES_ROOT and MEETINGS at the top of the script, or pass --vault.", file=sys.stderr)
        return 2
    folder = series_dir(args.series, vault)
    if not folder.is_dir():
        hint = " (MEETINGS is still a placeholder: set it, or give the series as a vault-relative path)" if "<" in MEETINGS else ""
        print(f"No series folder at {folder}{hint}", file=sys.stderr)
        return 2
    files = sorted(f for f in folder.glob("*.md"))
    records = [f for f in files if "agenda" not in f.stem.lower()]
    agendas = [f for f in files if "agenda" in f.stem.lower()]
    texts = {f: f.read_text(encoding="utf-8", errors="replace").splitlines() for f in files}

    decided_in: dict[str, str] = {}
    for f in records:
        for did, *_ in decisions(texts[f]):
            decided_in.setdefault(did, f.stem)

    carried: dict[str, set[str]] = defaultdict(set)
    for f in records:
        for title, body in sections(texts[f]):
            if any(k in title for k in CARRY_HEADINGS):
                for did in ID_IN_TICKS.findall("\n".join(body)):
                    if decided_in.get(did) != f.stem:
                        carried[did].add(f.stem)

    print(f"# Series digest: {folder.name}")
    print()
    print(f"{len(records)} record notes, {len(agendas)} agenda notes. Latest record: "
          f"`{records[-1].stem if records else 'none'}`; latest agenda: `{agendas[-1].stem if agendas else 'none'}`.")
    print()
    print(f"## Decisions of the last {args.last} records that still stand or are open")
    print()
    print("| ID | Decision | Status now | Verdict | Note |")
    print("|---|---|---|---|---|")
    n = 0
    for f in records[-args.last:]:
        for did, text, status, verdict in decisions(texts[f]):
            if status.lower().startswith(CLOSED):
                continue
            safe = re.sub(r"(?<!\\)\|", r"\\|", text)
            print(f"| {did} | {safe} | {status} | {verdict} | {f.stem} |")
            n += 1
    if not n:
        print("| | none found (no `0. Decisions taken` table in these notes) | | | |")
    print()
    print(f"## Carried in {args.min_carried} or more notes after the one that raised it")
    print()
    rows = sorted(((len(v), k, v) for k, v in carried.items() if len(v) >= args.min_carried), reverse=True)
    if rows:
        for count, did, notes in rows:
            origin = decided_in.get(did, "an agenda or an earlier series")
            print(f"- `{did}` carried in {count} notes ({', '.join(sorted(notes))}); raised in {origin}")
    else:
        print("- none")
    print()
    print("## Claims marked stated or assumed")
    print()
    hits = 0
    for f in files:
        for line in texts[f]:
            m = CONF_FIELD.search(line)
            if m:
                snippet = line.strip()
                snippet = snippet if len(snippet) <= 200 else snippet[:197] + "..."
                print(f"- {m.group(1).lower()}: {snippet} ({f.stem})")
                hits += 1
    if not hits:
        print("- none marked in this series yet")
    print()
    print("## Open issues of the latest record")
    print()
    if records:
        found = False
        for title, body in sections(texts[records[-1]]):
            if "open issue" in title:
                found = True
                print("\n".join(l for l in body if l.strip()))
        if not found:
            print("- the latest record has no Open issues section")
    return 0


if __name__ == "__main__":
    sys.exit(main())
