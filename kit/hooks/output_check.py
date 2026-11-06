#!/usr/bin/env python3
"""Output check: four writing rules a script can verify before a note or a document is reported
as done.

    dash          an em-dash or en-dash doing punctuation inside a sentence. Structural uses pass:
                  a bullet marker, a heading, a table header row, a cell that holds only a dash, an
                  en-dash between two numbers (a range). Spaced double hyphens between words
                  (" -- ") count as a dash.
    abbreviation  an abbreviation used before its long form in the same file, e.g. "RMSE" on line 3
                  and "root mean square error (RMSE)" on line 12. With --undefined it also lists
                  abbreviations never spelled out (the common ones in COMMON excepted), as hints.
    issue         a bare "#207" that is not inside a Markdown link: issues and pull requests are named
                  as links, [#207](https://github.com/<owner>/<repo>/issues/207).
    frontmatter   YAML frontmatter that does not parse, is not closed, or is not a mapping.

Code (fenced blocks and inline spans), URLs and wikilinks are skipped. A separator that a template
owns is still reported: judge it, do not "fix" it. Drop a rule your house style does not have by
removing its call in check_text().

Usage:
    python -I output_check.py <file.md> [<file.md> ...] [--undefined]
    python -I output_check.py --self-test
Exit code 0 when clean, 1 when there are findings, 2 on a usage error. The check never writes.

Standard library, plus PyYAML for the frontmatter when it is installed (a structural check
otherwise). Part of the ai-research-setup-kit (kit/hooks/README.md); Copyright (c) 2026 Johannes
Wildfeuer, MIT licence (see LICENSE.md).
"""
from __future__ import annotations

import re
import sys

try:
    import yaml  # PyYAML; the fallback below checks structure only
except ImportError:  # pragma: no cover
    yaml = None

DASHES = "—–"  # em-dash, en-dash
# Abbreviations that --undefined never asks about. Add your field's everyday ones.
COMMON = {
    "AI", "API", "CLI", "CO2", "CSS", "CSV", "DKK", "EU", "EUR", "GB", "HTML", "HTTP", "HTTPS", "ID",
    "IDE", "IT", "JSON", "KB", "MB", "MSc", "BSc", "OK", "PDF", "PNG", "PR", "SQL", "SVG", "TB", "UI",
    "UK", "URL", "USA", "USD", "UTC", "UX", "XML", "YAML", "PhD", "TODO", "README", "CEST", "CET",
}

FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
URL = re.compile(r"(?:https?|file)://[^\s)>\]]+")
MD_LINK = re.compile(r"\[[^\]\n]*\]\([^)\n]*\)")
WIKILINK = re.compile(r"\[\[[^\]\n]*\]\]")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
ABBR = re.compile(r"(?<![\w/.\-\\])([A-Z][A-Za-z0-9&]*[A-Z0-9])(s?)(?![\w\-/\\])")
BARE_ISSUE = re.compile(r"(?<![\w/&\[#])#(\d{1,5})\b")  # six digits is a hex colour such as #990000


def blank(m):
    return " " * (m.end() - m.start())


def split_frontmatter(lines):
    """(frontmatter line count incl. both fences, closed?) for a file that opens with ---."""
    if not lines or lines[0].strip() != "---":
        return 0, True
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return i + 1, True
    return len(lines), False


def prose_lines(lines, start):
    """(line number, text with code, URLs and wikilinks blanked) for the lines from start on."""
    out, in_fence = [], False
    for n in range(start, len(lines)):
        line = lines[n]
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        text = INLINE_CODE.sub(blank, line)
        text = URL.sub(blank, text)
        text = WIKILINK.sub(blank, text)
        out.append((n + 1, text))
    return out


def check_dashes(lines, fm_end):
    findings = []
    body = prose_lines(lines, 0)
    by_no = {n: t for n, t in body}
    for n, text in body:
        if n == 1 and fm_end and text.strip() == "---":
            continue
        if text.lstrip().startswith("#"):
            continue  # a heading
        nxt = by_no.get(n + 1, "")
        if text.lstrip().startswith("|") and TABLE_SEP.match(nxt or ""):
            continue  # a table header row
        t = re.sub(r"^\s*[" + DASHES + r"]\s+", "", text)  # a bullet marker
        t = re.sub(r"\|\s*[" + DASHES + r"]\s*(?=\|)", "|", t)  # a cell holding only a dash
        t = re.sub(r"(?<=\d)\s?–\s?(?=\d)", "-", t)  # a numeric range
        for m in re.finditer("[" + DASHES + "]", t):
            name = "em-dash" if m.group() == "—" else "en-dash"
            findings.append((n, "dash", f"{name} inside a sentence: ...{excerpt(lines[n - 1], m.start())}..."))
        for m in re.finditer(r"(?<=\w) -- (?=\w)", t):
            findings.append((n, "dash", f"spaced double hyphen used as a dash: ...{excerpt(lines[n - 1], m.start())}..."))
    return findings


def excerpt(line, col, width=30):
    return line[max(0, col - width):col + width].strip()


def check_abbreviations(lines, fm_end, undefined=False):
    first_use, first_def = {}, {}
    for n, text in prose_lines(lines, fm_end):
        for m in ABBR.finditer(text):
            abbr = m.group(1)
            if sum(c.isupper() for c in abbr) < 2:
                continue
            pos = (n, m.start())
            first_use.setdefault(abbr, pos)
            before = text[:m.start()]
            after = text[m.end():]
            # "long form (ABBR)" or "long form (ABBRs; ...)"
            forward = re.search(r"\(\s*$", before) and re.match(r"\s*[),;:]", after)
            # "ABBR (long form)": two or more words, the first starting with the same letter
            backward = re.match(r"\s*\(([A-Za-z][^()]*)\)", after)
            if backward:
                words = backward.group(1).split()
                backward = len(words) >= 2 and words[0][0].lower() == abbr[0].lower()
            if forward or backward:
                first_def.setdefault(abbr, pos)
    findings = []
    for abbr, use in first_use.items():
        d = first_def.get(abbr)
        if d and use < d:
            findings.append((use[0], "abbreviation",
                             f"`{abbr}` is used on line {use[0]} before its long form on line {d[0]}"))
        elif not d and undefined and abbr not in COMMON:
            findings.append((use[0], "abbreviation (hint)", f"`{abbr}` is never spelled out in this file"))
    return findings


def check_issues(lines, fm_end):
    findings = []
    for n, text in prose_lines(lines, fm_end):
        t = MD_LINK.sub(blank, text)
        if t.lstrip().startswith("#") and re.match(r"\s*#+\s", t):
            t = re.sub(r"^\s*#+\s", lambda m: " " * len(m.group()), t)
        for m in BARE_ISSUE.finditer(t):
            findings.append((n, "issue", f"bare `#{m.group(1)}`: name it as a link, "
                                         f"[#{m.group(1)}](https://github.com/<owner>/<repo>/issues/{m.group(1)})"))
    return findings


def check_frontmatter(lines):
    fm_end, closed = split_frontmatter(lines)
    if not fm_end:
        return []
    if not closed:
        return [(1, "frontmatter", "frontmatter opens with --- but is never closed")]
    block = "\n".join(lines[1:fm_end - 1])
    if yaml is not None:
        try:
            data = yaml.safe_load(block)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            line = (mark.line + 2) if mark else 1
            problem = getattr(e, "problem", None) or str(e).splitlines()[0]
            return [(line, "frontmatter", f"YAML does not parse: {problem}")]
        if data is not None and not isinstance(data, dict):
            return [(2, "frontmatter", f"frontmatter is a {type(data).__name__}, not a set of keys")]
        return []
    seen_key = False
    for i, raw in enumerate(lines[1:fm_end - 1], start=2):  # structural fallback, without PyYAML
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw[:len(raw) - len(raw.lstrip())]:
            return [(i, "frontmatter", "a tab in the indentation")]
        if raw.startswith("-") and not seen_key:
            return [(i, "frontmatter", "frontmatter is a list, not a set of keys")]
        if raw.startswith((" ", "-")):
            continue
        m = re.match(r"[^:]+:(\s|$)(.*)", raw)
        if not m:
            return [(i, "frontmatter", "a line that is neither `key: value` nor a list item")]
        seen_key = True
        value = m.group(2).strip()
        if value and value[0] not in "\"'[{|>&*!" and re.search(r":(\s|$)", value):
            return [(i, "frontmatter", "an unquoted colon in a value: put the value in quotes")]
    return []


def check_text(text, undefined=False):
    lines = text.splitlines()
    fm_end, _ = split_frontmatter(lines)
    findings = check_frontmatter(lines) + check_dashes(lines, fm_end)
    findings += check_abbreviations(lines, fm_end, undefined) + check_issues(lines, fm_end)
    return sorted(findings, key=lambda f: (f[0], f[1]))


def check_file(path, undefined=False):
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return check_text(fh.read(), undefined)


def self_test():
    cases = [
        # (label, text, expected count of (kind) findings)
        ("em-dash in a sentence", "A sentence — with a dash.", {"dash": 1}),
        ("en-dash in a sentence", "Before – after.", {"dash": 1}),
        ("spaced double hyphen", "One word -- another.", {"dash": 1}),
        ("a numeric range", "The years 2020–2023 and pages 4 – 7.", {}),
        ("a heading with a separator", "## Part C — the mechanisms", {}),
        ("a bullet marker", "– first item\n– second item", {}),
        ("a table header passes, a body cell does not",
         "| Rule — what | Verdict |\n|---|---|\n| a — b | – |", {"dash": 1}),
        ("code spans and fences are skipped", "Run `a — b` now.\n```\nx — y -- z\n```", {}),
        ("a command flag is not a dash", "Use git checkout -- . with care.", {}),
        ("abbreviation before its long form",
         "The RMSE is high.\n\nLater the root mean square error (RMSE) is defined.", {"abbreviation": 1}),
        ("long form first, plural later", "A heat pump (HP) runs. HPs are read monthly.", {}),
        ("abbreviation then its long form in brackets", "The HP (heat pump) runs.", {}),
        ("an undefined abbreviation is quiet by default", "We use NMR data and a PDF.", {}),
        ("a bracket that is not a long form", "HP (vendor A) first; later heat pump (HP).",
         {"abbreviation": 1}),
        ("frontmatter is not prose for abbreviations",
         "---\ntype: note\nsummary: about the RMSE\n---\nThe root mean square error (RMSE).", {}),
        ("bare issue number", "See #207 for details.", {"issue": 1}),
        ("linked issue", "See [#207](https://github.com/o/r/issues/207) and [PR #89](https://github.com/o/r/pull/89).", {}),
        ("hex colour, URL anchor, code, wikilink heading",
         "Colour #1f77b4, https://x.org/y#12, `#12`, [[note#3]].", {}),
        ("a hex colour of digits only", "Use the house red #990000 for titles.", {}),
        ("a Markdown heading is not an issue", "# 12 rules\n## 3 steps", {}),
        ("valid frontmatter", "---\ntype: note\ntags:\n  - a\nsummary: \"x: y\"\n---\nBody.", {}),
        ("frontmatter with an unquoted colon", "---\ntype: note\nsummary: a: b\n---\nBody.", {"frontmatter": 1}),
        ("frontmatter never closed", "---\ntype: note\nBody.", {"frontmatter": 1}),
        ("frontmatter that is a list", "---\n- a\n- b\n---\nBody.", {"frontmatter": 1}),
        ("a dash in the summary counts", "---\nsummary: \"a — b\"\n---\nBody.", {"dash": 1}),
    ]
    failed = 0
    for label, text, expected in cases:
        got = {}
        for _, kind, _ in check_text(text):
            got[kind] = got.get(kind, 0) + 1
        ok = got == expected
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f"   expected {expected}, got {got}"))
    hint = check_text("We use NMR data and a PDF.", undefined=True)
    ok = [f[1] for f in hint] == ["abbreviation (hint)"] and "NMR" in hint[0][2]
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} --undefined lists NMR and leaves PDF alone")
    total = len(cases) + 1
    print(f"\n{total - failed} of {total} checks passed." + (" The parser in use: " + ("PyYAML" if yaml else "the structural fallback") + "."))
    return 1 if failed else 0


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    if "--self-test" in argv:
        return self_test()
    undefined = "--undefined" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__.split("\n\n")[0])
        print("usage: output_check.py <file.md> [...] [--undefined] | --self-test")
        return 2
    total = 0
    for path in files:
        try:
            findings = check_file(path, undefined)
        except OSError as e:
            print(f"{path}: cannot read ({e.strerror})")
            return 2
        for line, kind, msg in findings:
            print(f"{path}:{line}: {kind}: {msg}")
        total += sum(1 for f in findings if not f[1].endswith("(hint)"))
    print(f"{total} finding(s) in {len(files)} file(s)." if total else f"clean: {len(files)} file(s).")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
