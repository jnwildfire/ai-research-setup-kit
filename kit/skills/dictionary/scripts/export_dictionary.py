# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""Export a dictation dictionary from one Markdown note to Wispr Flow and transcription-tool files.

Source of truth: one note (in your notes vault or anywhere) holding a single Markdown table with the
columns Term | Category | Heard as | Replace | Note, and a `short-list:` list in its frontmatter
naming the terms for a short prompt. "Heard as" and "Replace" are separated by `;`. Replace lists
the garbles that are safe to replace blindly, a subset of Heard as; empty means none.

Output folder (written, never edited by hand):
    wispr-flow-vocabulary.csv     one term per row, no header (Wispr Flow: Dictionary, Import)
    wispr-flow-corrections.csv    heard,term rows for the garbles listed in Replace, no header
    term-list.txt                 all terms, one comma-separated line
    term-list-short.txt           the short-list terms, one comma-separated line
    README.md                     what the files are and how to import them

Where the note and the output folder are, in this order of precedence:
    --note PATH and --out DIR on the command line
    the environment variables DICTIONARY_NOTE and DICTIONARY_OUT
    NOTE and OUT in the configuration block below

Standard library only.
Run:   python -I export_dictionary.py [--note PATH] [--out DIR] [--check]
  or   uv run export_dictionary.py ...
--check validates and reports without writing anything.
Exit code 0 when the export is written or unchanged, 1 on a fatal check failure.

Copyright (c) 2026 Johannes Wildfeuer, MIT licence (see LICENSE.md). Made in conversation with
Claude Code.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from pathlib import Path

# ------------------------------------------------------------------------------- configuration
NOTE = "<path to your dictionary note, for example C:/Users/you/Vault/Dictation Dictionary.md>"
OUT = "<folder for the exports, for example C:/Users/you/research/dictation>"
CATEGORIES = {"person", "organisation", "place", "product", "project",
              "abbreviation", "method", "software", "other-language"}
SHORT_LIST_KEY = "short-list"
# --------------------------------------------------------------------------- end of configuration

HEADER = ["term", "category", "heard as", "replace", "note"]
WISPR_MAX_ROWS = 1000
WISPR_MAX_BYTES = 3 * 1024 * 1024
FILES = {
    "vocab": "wispr-flow-vocabulary.csv",
    "corr": "wispr-flow-corrections.csv",
    "list": "term-list.txt",
    "short": "term-list-short.txt",
    "readme": "README.md",
}


def resolve(cli, env, default):
    for value in (cli, os.environ.get(env), default):
        if value and "<" not in value:
            return Path(os.path.expandvars(os.path.expanduser(value)))
    return None


def split_row(line: str) -> list:
    """Split one Markdown table row on unescaped pipes; unescape \\| inside cells."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def parse_frontmatter_list(text: str, key: str) -> list:
    """Return the YAML block list under `key:` in the frontmatter (no YAML library needed)."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return []
    items, inside = [], False
    for line in m.group(1).splitlines():
        if re.match(rf"^{re.escape(key)}:\s*$", line):
            inside = True
            continue
        if inside:
            item = re.match(r"^\s+-\s+(.*)$", line)
            if item:
                items.append(item.group(1).strip().strip("'\""))
            elif line.strip():
                break
    return items


def parse_table(text: str) -> list:
    """Find the table whose header is Term | Category | Heard as | Replace | Note."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and [c.lower() for c in split_row(line)] == HEADER:
            rows = []
            for j in range(i + 2, len(lines)):  # skip the separator row
                if not lines[j].lstrip().startswith("|"):
                    break
                cells = split_row(lines[j])
                cells += [""] * (5 - len(cells))
                rows.append({"line": j + 1, "term": cells[0], "category": cells[1].lower(),
                             "heard": [h.strip() for h in cells[2].split(";") if h.strip()],
                             "replace": [s.strip() for s in cells[3].split(";") if s.strip()],
                             "note": cells[4], "extra": cells[5:]})
            return rows
    raise SystemExit("FATAL: no table with the header Term | Category | Heard as | Replace | Note")


def validate(rows: list) -> tuple:
    """Return (accepted rows, rejection messages). A rejected row is left out of every export."""
    rejected, seen, accepted = [], {}, []
    for r in rows:
        tag = f"line {r['line']} '{r['term']}'"
        if not r["term"]:
            rejected.append(f"{tag}: empty term")
            continue
        if any(x for x in r["extra"]):
            rejected.append(f"{tag}: more than five cells (an unescaped pipe?)")
            continue
        key = r["term"].casefold()
        if key in seen:
            rejected.append(f"{tag}: duplicate of line {seen[key]}")
            continue
        if r["category"] not in CATEGORIES:
            rejected.append(f"{tag}: unknown category '{r['category']}'")
            continue
        stray = [s for s in r["replace"] if s not in r["heard"]]
        if stray:
            rejected.append(f"{tag}: Replace entries not in Heard as: {', '.join(stray)}")
            continue
        seen[key] = r["line"]
        accepted.append(r)
    terms = {r["term"].casefold() for r in accepted}
    clean = []
    for r in accepted:
        clash = [h for h in r["heard"] if h.casefold() in terms]
        if clash:
            rejected.append(f"line {r['line']} '{r['term']}': a garble equals a term: {', '.join(clash)}")
            continue
        clean.append(r)
    return clean, rejected


def csv_text(records: list) -> str:
    """RFC 4180: CRLF line ends, fields with a comma, quote or line break double-quoted."""
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n").writerows(records)
    return buf.getvalue()


def check_roundtrip(text: str, records: list, name: str) -> None:
    if list(csv.reader(io.StringIO(text, newline=""))) != records:
        raise SystemExit(f"FATAL: {name} does not read back to the same records (a quoting fault)")


def readme_text(note: Path, n_short: int) -> str:
    return (
        "# Dictation dictionary exports\n\n"
        f"Generated by `export_dictionary.py` from the note `{note.name}`, which is the source. "
        "Edit the note, not these files.\n\n"
        "- `wispr-flow-vocabulary.csv`: every term, one per row. In Wispr Flow: Settings, Dictionary, "
        "Import, and drag the file in. Imported items are not starred, and conflicts are skipped.\n"
        "- `wispr-flow-corrections.csv`: `heard,term` pairs, only the garbles that are safe to replace "
        "blindly. Import it the same way.\n"
        f"- `term-list.txt` and `term-list-short.txt`: all terms, and the {n_short} most frequent, as one "
        "comma-separated line, for a transcription tool that accepts a vocabulary or a prompt, and for "
        "the agent to correct a transcript against afterwards.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--note", help="the dictionary note (overrides DICTIONARY_NOTE and NOTE)")
    ap.add_argument("--out", help="the output folder (overrides DICTIONARY_OUT and OUT)")
    ap.add_argument("--check", action="store_true", help="validate and report, write nothing")
    args = ap.parse_args()

    note = resolve(args.note, "DICTIONARY_NOTE", NOTE)
    out = resolve(args.out, "DICTIONARY_OUT", OUT)
    if note is None or (out is None and not args.check):
        print("FATAL: the note or the output folder is not set: use --note and --out, the variables "
              "DICTIONARY_NOTE and DICTIONARY_OUT, or the configuration block at the top of the script")
        return 1
    if not note.is_file():
        print(f"FATAL: note not found: {note}")
        return 1
    text = note.read_text(encoding="utf-8")

    rows, rejected = validate(parse_table(text))
    rows.sort(key=lambda r: (r["category"], r["term"].casefold()))
    terms = [r["term"] for r in rows]
    if len(terms) > WISPR_MAX_ROWS:
        print(f"FATAL: {len(terms)} vocabulary rows; Wispr Flow imports at most {WISPR_MAX_ROWS}")
        return 1

    vocab_records = [[t] for t in terms]
    corr_records = [[s, r["term"]] for r in rows for s in r["replace"]]
    term_by_key = {t.casefold(): t for t in terms}
    wanted = parse_frontmatter_list(text, SHORT_LIST_KEY)
    short = [term_by_key[s.casefold()] for s in wanted if s.casefold() in term_by_key]
    for s in wanted:
        if s.casefold() not in term_by_key:
            rejected.append(f"{SHORT_LIST_KEY} '{s}': not a term in the table, left out of the short list")

    # The term lists are bare comma-separated lines, so a term with a comma cannot go there.
    list_terms = [t for t in terms if "," not in t]
    for t in terms:
        if "," in t:
            rejected.append(f"'{t}': contains a comma; kept in the Wispr Flow files, left out of the term lists")
    short = [t for t in short if "," not in t]

    vocab_csv, corr_csv = csv_text(vocab_records), csv_text(corr_records)
    check_roundtrip(vocab_csv, vocab_records, FILES["vocab"])
    check_roundtrip(corr_csv, corr_records, FILES["corr"])
    for name, body in ((FILES["vocab"], vocab_csv), (FILES["corr"], corr_csv)):
        if len(body.encode("utf-8")) > WISPR_MAX_BYTES:
            print(f"FATAL: {name} exceeds 3 MB, Wispr Flow's import limit")
            return 1

    outputs = {
        FILES["vocab"]: vocab_csv,
        FILES["corr"]: corr_csv,
        FILES["list"]: ", ".join(list_terms) + "\n",
        FILES["short"]: ", ".join(short) + "\n",
        FILES["readme"]: readme_text(note, len(short)),
    }

    previous = None
    if out is not None and (out / FILES["vocab"]).is_file():
        with (out / FILES["vocab"]).open(encoding="utf-8", newline="") as f:
            previous = {row[0] for row in csv.reader(f) if row}

    by_cat = {}
    for r in rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    print(f"Source: {note}")
    print(f"Terms: {len(terms)} ({', '.join(f'{k} {v}' for k, v in sorted(by_cat.items()))})")
    print(f"Garbles: {sum(len(r['heard']) for r in rows)}; correction pairs (listed in Replace): "
          f"{len(corr_records)} from {sum(bool(r['replace']) for r in rows)} terms")
    print(f"Short list: {len(short)} terms")
    if previous is not None:
        now = set(terms)
        print(f"Since the last export: {len(now - previous)} added, {len(previous - now)} removed")
        for t in sorted(now - previous):
            print(f"  + {t}")
        for t in sorted(previous - now):
            print(f"  - {t}")
    if rejected:
        print(f"Rejected ({len(rejected)}):")
        for msg in rejected:
            print(f"  ! {msg}")

    if args.check:
        print("Check only, nothing written.")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    changed = []
    for name, body in outputs.items():
        path = out / name
        data = body.encode("utf-8")  # UTF-8 without a byte-order mark
        if not path.is_file() or path.read_bytes() != data:
            path.write_bytes(data)
            changed.append(name)
    print(f"Written to {out}: {', '.join(changed)}" if changed else f"No change in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
