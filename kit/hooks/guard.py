#!/usr/bin/env python3
"""Guard hook for Claude Code: protect the originals, and keep the agent's writes inside your roots.

Claude Code runs this script before every file edit, every shell command and, if you register them,
every note write through a notes connector (the setting is in settings.example.json next to this
file). It receives the planned tool call as JSON on its input and gives one of three verdicts:

    deny   the call would change an original (a folder listed in IMMUTABLE). Exit code 2: the call
           is refused and the reason is shown to the agent, which then explains and proposes a fix
           downstream. No setting and no answer of yours lets the call through.
    ask    the call would write outside your roots and outside any grant. Claude Code shows you a
           permission prompt. In auto mode the prompt decides, not the auto-mode classifier.
    pass   everything else. The script stays silent and Claude Code's own permission settings decide,
           exactly as if the guard were not there. Reading is never restricted.

A grant widens the roots for one job or one session: a small JSON file that the session writes only
after you approved a plan that names the extra folders (guide 04). A grant never opens an immutable
folder.

What the guard cannot see: a script that writes files itself (`python make_figures.py`) is one
shell command to the guard, and only the paths written on the command line are checked. Shell
commands are matched by pattern, not parsed like a shell would. The guard is a net under the rules,
not a sandbox; Claude Code's permission prompts and, in auto mode, its classifier are the second net.

Set the configuration block below, then check it:
    python guard.py --show-config     the resolved roots, immutable folders and grants
    python guard.py --self-test       about fifty synthetic tool calls and checks against a temporary folder tree
Test one call by hand (bash); a refusal prints the reason and exits with 2:
    echo '{"tool_name":"Edit","tool_input":{"file_path":"<an original>"}}' | python guard.py; echo "exit $?"

Standard library only; Python 3.8 or later.

Derived from guard_raw.py in Kevin Michael Smith's ai-research-starter-kit
(https://github.com/KevinMSmith/ai-research-starter-kit), Copyright (c) 2026 Kevin Michael Smith, MIT
licence, by way of the author's own guard for immutable folders; the write scope, the grants and the
self-test are added. Copyright (c) 2026 Johannes Wildfeuer, MIT licence (see LICENSE.md).
"""
from __future__ import annotations

import fnmatch
import io
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timedelta

# ------------------------------------------------------------------------------- configuration
# Paths may use ~, environment variables ($HOME, %USERPROFILE%) and forward slashes on Windows.
# A value still in <angle brackets> counts as not set, and every rule that uses it is skipped.

CODE_ROOT = "<code root, for example C:/dev>"
DATA_ROOT = "<data root, for example C:/Users/you/OneDrive - Your University/research>"
NOTES_ROOT = "<notes vault, for example C:/Users/you/OneDrive - Your University/Vault>"

# Where the agent may write without the guard objecting: the three roots and the agent's own
# working folders. "<TEMP>" is the system's temporary folder.
WRITABLE = [
    CODE_ROOT,
    DATA_ROOT,
    NOTES_ROOT,
    "~/.claude",
    "<TEMP>",
]

# Folders that hold originals. Each entry: (folder, strictness, the reason the agent is shown).
#   "never"         nothing inside is written, moved, copied or deleted, by any tool
#   "deposit-only"  a new file may be added (a download, a copy in); nothing that exists is
#                   changed, overwritten, moved or deleted
# A * stands for exactly one folder name: projects/*/data/raw matches every project's raw folder.
IMMUTABLE = [
    (DATA_ROOT + "/projects/*/data/raw", "deposit-only",
     "raw data is never changed after download; correct it downstream, in data/processed"),
    (DATA_ROOT + "/meeting-transcripts", "deposit-only",
     "a transcript is kept as recorded; correct names and errors in the meeting note"),
]

INSIDE_SCOPE = "pass"   # "pass": silent inside WRITABLE. "allow": also skip Claude Code's prompt for
                        # file and note writes there (never for shell commands; settings' deny and
                        # ask rules still apply).
OUTSIDE_SCOPE = "ask"   # "ask": prompt you. "deny": refuse outright.

# Grant files, read if they exist. A background job writes its grant into its own folder; an
# attended session writes one into the project. Format: see write-scope.example.json.
GRANT_FILES = [
    "$CLAUDE_JOB_DIR/write-scope.json",
    "$CLAUDE_PROJECT_DIR/.claude/write-scope.local.json",
]

# Notes written through an MCP connector, paths relative to NOTES_ROOT. The defaults fit the
# Obsidian connector whose tools are named mcp__obsidian__vault_write and so on. Set the prefix
# to "" if you write notes only with the ordinary file tools.
NOTE_TOOL_PREFIX = "mcp__obsidian__vault_"
NOTE_TOOL_WRITES = ("write", "patch", "append", "delete", "move", "copy")
NOTE_PATH_KEYS = ("path", "newPath", "new_path", "destination", "to", "target_path", "targetPath")
# --------------------------------------------------------------------------- end of configuration

NAME = "guard.py"
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
SHELL_TOOLS = ("Bash", "PowerShell")

_EDGE_L = r"(?<![\w.\-/\\$:])"
_EDGE_R = r"(?=\s|$|;)"
WRITE_VERBS = re.compile(
    _EDGE_L + r"(rm|rmdir|rd|del|erase|Remove-Item|ri|mv|move|Move-Item|mi|ren|rename|Rename-Item|rni|"
    r"git\s+rm|git\s+mv|Clear-Content|clc|Set-Content|sc|Add-Content|ac|Out-File|Tee-Object|tee|"
    r"truncate|sed\s+-i\S*|perl\s+-pi\S*|touch|New-Item|ni|mkdir|md)" + _EDGE_R,
    re.IGNORECASE,
)
COPY_VERBS = re.compile(_EDGE_L + r"(cp|copy|Copy-Item|cpi|xcopy|robocopy)" + _EDGE_R, re.IGNORECASE)
REDIRECT = re.compile(r"(?<![<>&\-\w])\d?>{1,2}\s*([^\s;|&<>]+)")
CD = re.compile(r"^\s*(?:cd|Set-Location|sl|pushd)\s+(\S.*?)\s*$", re.IGNORECASE)
SINKS = {"/dev/null", "nul", "$null", "nul:", "/dev/stdout", "/dev/stderr"}


# ------------------------------------------------------------------------------- paths

def expand(p):
    """Expand ~ and variables; None when unset, a placeholder, or a variable that did not resolve."""
    if not p or "<" in p and p.strip() != "<TEMP>":
        return None
    if p.strip() == "<TEMP>":
        return tempfile.gettempdir()
    p = re.sub(r"\$env:(\w+)", r"${\1}", p)
    p = os.path.expandvars(os.path.expanduser(p))
    if "$" in p or re.search(r"%\w+%", p):
        return None
    return p


def norm(p, cwd):
    """An absolute, case-normalised path; relative paths resolve against cwd. Git Bash /c/... works."""
    p = p.strip().strip("\"'")
    if os.name == "nt":
        m = re.match(r"^/([a-zA-Z])(/.*|$)", p)
        if m:
            p = m.group(1) + ":" + (m.group(2) or "/")
    if p == "/tmp" or p.startswith("/tmp/"):
        p = tempfile.gettempdir() + p[4:]
    p = re.sub(r"\$env:(\w+)", r"${\1}", p)
    p = os.path.expandvars(os.path.expanduser(p))
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    return os.path.normcase(os.path.normpath(p))


def within(p, root):
    root = root.rstrip("\\/")
    return p == root or p.startswith(root + os.sep)


def parts(p):
    return [x for x in re.split(r"[\\/]", p) if x]


# ------------------------------------------------------------------------------- configuration as data

def build_config(code=None, data=None, notes=None, writable=None, immutable=None, grant_files=None,
                 inside=None, outside=None, note_prefix=None):
    """Collect the configuration block into one dict; the self-test passes its own values."""
    cwd = os.getcwd()
    cfg = {
        "notes_root": None,
        "writable": [],
        "immutable": [],
        "grant_files": [],
        "inside": inside or INSIDE_SCOPE,
        "outside": outside or OUTSIDE_SCOPE,
        "note_prefix": NOTE_TOOL_PREFIX if note_prefix is None else note_prefix,
        "unset": [],
    }
    notes_raw = NOTES_ROOT if notes is None else notes
    n = expand(notes_raw)
    cfg["notes_root"] = norm(n, cwd) if n else None
    for name, val in (("CODE_ROOT", CODE_ROOT if code is None else code),
                      ("DATA_ROOT", DATA_ROOT if data is None else data), ("NOTES_ROOT", notes_raw)):
        if not expand(val):
            cfg["unset"].append(name)
    for w in (WRITABLE if writable is None else writable):
        e = expand(w)
        if e:
            cfg["writable"].append(norm(e, cwd))
    for folder, strictness, why in (IMMUTABLE if immutable is None else immutable):
        e = expand(folder)
        if e:
            cfg["immutable"].append((norm(e, cwd), strictness, why))
    cfg["grant_files"] = [g for g in (expand(x) for x in (GRANT_FILES if grant_files is None else grant_files)) if g]
    cfg["granted"], cfg["grant_notes"] = load_grants(cfg["grant_files"], cwd)
    return cfg


def load_grants(files, cwd):
    """Folders granted by approved plans. An expired or unreadable grant grants nothing."""
    roots, notes = [], []
    for f in files:
        if not os.path.isfile(f):
            continue
        try:
            with open(f, encoding="utf-8") as fh:
                g = json.load(fh)
        except (OSError, ValueError):
            notes.append(f"{f}: unreadable, ignored")
            continue
        exp = g.get("expires")
        if exp:
            try:
                if datetime.now() > datetime.fromisoformat(str(exp)):
                    notes.append(f"{f}: expired {exp}, ignored")
                    continue
            except ValueError:
                notes.append(f"{f}: expiry '{exp}' not a date, ignored")
                continue
        for w in g.get("write", []) or []:
            e = expand(str(w))
            if e:
                roots.append(norm(e, cwd))
        notes.append(f"{f}: grants {len(g.get('write', []) or [])} folder(s)" + (f" until {exp}" if exp else ""))
    return roots, notes


# ------------------------------------------------------------------------------- the decision

def immutable_hit(p, cfg):
    """(folder as written, strictness, reason, concrete folder) when p lies in an immutable folder."""
    pp = parts(p)
    for pattern, strictness, why in cfg["immutable"]:
        pat = parts(pattern)
        if len(pp) >= len(pat) and all(fnmatch.fnmatchcase(a, b) for a, b in zip(pp, pat)):
            concrete = os.sep.join(pp[:len(pat)])
            return pattern, strictness, why, concrete
    return None


def deny_text(hit, detail):
    _, strictness, why, folder = hit
    if strictness == "never":
        return f"`{folder}` is never written to, moved or deleted: {why}."
    return (f"`{folder}` holds originals: {why}. {detail} A new file may be added beside the "
            f"originals; nothing that exists there is changed, moved or deleted.")


def scope(p, cfg):
    if any(within(p, r) for r in cfg["writable"] + cfg["granted"]):
        return cfg["inside"], ""
    return cfg["outside"], (
        f"`{p}` is outside the folders this setup writes to without asking. Confirm only if you asked "
        f"for this write. For a job that runs while you are away, the plan names such folders and the "
        f"session writes a grant before the job starts (guide 04).")


def decide(tool, ti, cwd, cfg):
    """Return (verdict, reason) with verdict one of deny, ask, allow, pass."""
    cwd = norm(cwd or os.getcwd(), os.getcwd())
    if tool in FILE_TOOLS:
        raw = ti.get("file_path") or ti.get("notebook_path") or ""
        if not raw:
            return "pass", ""
        p = norm(raw, cwd)
        hit = immutable_hit(p, cfg)
        if hit:
            if hit[1] == "never":
                return "deny", deny_text(hit, "")
            if tool != "Write" or os.path.exists(p):
                return "deny", deny_text(hit, f"`{os.path.basename(p)}` exists; a corrected version is a new file "
                                              f"with a date or version in its name, or belongs downstream.")
        return scope(p, cfg)
    if tool in SHELL_TOOLS:
        return decide_shell(ti.get("command", "") or "", cwd, cfg)
    prefix = cfg["note_prefix"]
    if prefix and tool.startswith(prefix):
        return decide_note(tool[len(prefix):], ti, cfg)
    return "pass", ""


def decide_note(action, ti, cfg):
    if action not in NOTE_TOOL_WRITES or not cfg["notes_root"]:
        return "pass", ""
    for key in NOTE_PATH_KEYS:
        val = ti.get(key)
        if not isinstance(val, str) or not val:
            continue
        p = norm(os.path.join(cfg["notes_root"], val.lstrip("/\\")), cfg["notes_root"])
        hit = immutable_hit(p, cfg)
        if not hit:
            continue
        if hit[1] == "never":
            return "deny", deny_text(hit, "")
        creates = (action == "write" and key == "path") or (action in ("copy", "move") and key != "path")
        if not (creates and not os.path.exists(p)):
            return "deny", deny_text(hit, "")
    return ("allow", "") if cfg["inside"] == "allow" else ("pass", "")


def tokens(seg):
    return [t.strip("\"'") for t in re.findall(r'"[^"]*"|\'[^\']*\'|\S+', seg)]


WINDOWS_VERBS = {"robocopy", "xcopy", "copy", "move", "del", "erase", "rd", "rmdir", "md", "ren", "rename"}


def arguments(rest, verb):
    """The verb's arguments: options, redirections and what a redirection points at are dropped."""
    args, skip_next = [], False
    for t in tokens(rest):
        if skip_next:
            skip_next = False
            continue
        if re.fullmatch(r"\d?>{1,2}", t) or t == "<":
            skip_next = True
            continue
        if re.match(r"\d?>{1,2}|<", t) or t.startswith("-"):
            continue
        if verb in WINDOWS_VERBS and re.fullmatch(r"/[A-Za-z]{1,4}(:\S*)?", t):
            continue
        args.append(t)
    return args


def shell_targets(seg):
    """(path, kind) for every path the segment writes: kind is redirect, copy-dest or change."""
    found = []
    for m in REDIRECT.finditer(seg):
        t = m.group(1).strip("\"'")
        if t.lower() not in SINKS:
            found.append((t, "redirect"))
    cm = COPY_VERBS.search(seg)
    wm = WRITE_VERBS.search(seg)
    if cm and (not wm or cm.start() < wm.start()):
        verb = cm.group(1).lower()
        if verb in ("copy-item", "cpi"):
            after = tokens(seg[cm.end():])
            for i, t in enumerate(after[:-1]):
                if t.lower() in ("-destination", "-dest"):
                    found.append((after[i + 1], "copy-dest"))
                    return found
        args = arguments(seg[cm.end():], verb)
        if verb == "robocopy" and len(args) >= 2:
            found.append((args[1], "copy-dest"))
        elif args:
            found.append((args[-1], "copy-dest"))
    elif wm:
        verb = wm.group(1).lower()
        found += [(t, "change") for t in arguments(seg[wm.end():], verb) if t.lower() not in SINKS]
    return found


def decide_shell(cmd, cwd, cfg):
    asked = None
    for seg in re.split(r"[;\n|]|&&|\|\|", cmd):
        m = CD.match(seg)
        if m:
            target = m.group(1).strip().strip("\"'")
            if target and target != "-":
                cwd = norm(target, cwd)
            continue
        for raw, kind in shell_targets(seg):
            if raw.startswith("$") and expand(raw) is None:
                continue  # a shell variable the guard cannot resolve
            p = norm(raw, cwd)
            hit = immutable_hit(p, cfg)
            if hit:
                if hit[1] == "never":
                    return "deny", deny_text(hit, "")
                deposit = kind == "copy-dest" and (os.path.isdir(p) or not os.path.exists(p))
                if not deposit:
                    return "deny", deny_text(hit, "This command would change, move, overwrite or delete there.")
            verdict, reason = scope(p, cfg)
            if verdict in ("ask", "deny") and asked is None:
                asked = (verdict, reason)
    if asked:
        return asked
    return "pass", ""  # shell commands never get an explicit allow


# ------------------------------------------------------------------------------- the hook protocol

def run_hook(stdin_text, cfg, out, err):
    """Read one tool call, write the verdict the way Claude Code expects it, return the exit code."""
    try:
        data = json.loads(stdin_text)
    except ValueError:
        return 0
    if not isinstance(data, dict):
        return 0
    verdict, reason = decide(data.get("tool_name", "") or "", data.get("tool_input", {}) or {},
                             data.get("cwd") or os.getcwd(), cfg)
    if verdict == "deny":
        err.write(f"Refused by the guard ({NAME}): {reason}")
        return 2
    if verdict in ("ask", "allow"):
        out.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": verdict,
            "permissionDecisionReason": f"{NAME}: {reason}" if reason else f"{NAME}: inside your roots",
        }}))
    return 0


def show_config():
    cfg = build_config()
    print(f"{NAME} configuration as resolved on this computer\n")
    if cfg["unset"]:
        print(f"NOT SET (still placeholders): {', '.join(cfg['unset'])}. Edit the block at the top.\n")
    print("Writable without asking:")
    for w in cfg["writable"]:
        print(f"  {w}{'' if os.path.isdir(w) else '   (does not exist)'}")
    print("Immutable:")
    for folder, strictness, why in cfg["immutable"]:
        print(f"  {folder}   [{strictness}]  {why}")
    if not cfg["immutable"]:
        print("  none")
    print("Grant files looked for:")
    for g in cfg["grant_files"]:
        print(f"  {g}")
    for n in cfg["grant_notes"]:
        print(f"  -> {n}")
    print(f"Notes connector prefix: {cfg['note_prefix'] or '(none)'}; notes root: {cfg['notes_root']}")
    print(f"Inside the roots: {cfg['inside']}; outside: {cfg['outside']}")
    return 1 if cfg["unset"] else 0


# ------------------------------------------------------------------------------- self-test

def self_test():
    base = tempfile.mkdtemp(prefix="guard-selftest-")
    try:
        return _self_test(base)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _self_test(base):
    j = lambda *a: os.path.join(base, *a)  # noqa: E731
    for d in ("code/repo", "data/projects/p1/data/raw", "data/projects/p1/data/processed",
              "data/meeting-transcripts", "notes/projects", "notes/originals", "outside/granted",
              "outside/expired", "job", "oldjob", "work"):
        os.makedirs(j(*d.split("/")), exist_ok=True)
    for f in ("data/projects/p1/data/raw/original.csv", "data/meeting-transcripts/2026-01-15.vtt",
              "notes/originals/kept.md", "notes/projects/plan.md", "outside/old.txt"):
        with open(j(*f.split("/")), "w", encoding="utf-8") as fh:
            fh.write("x\n")
    future = (datetime.now() + timedelta(days=1)).isoformat(timespec="minutes")
    with open(j("job", "write-scope.json"), "w", encoding="utf-8") as fh:
        json.dump({"plan": "self-test", "expires": future, "write": [j("outside", "granted")]}, fh)
    with open(j("oldjob", "write-scope.json"), "w", encoding="utf-8") as fh:
        json.dump({"plan": "self-test", "expires": "2000-01-01T00:00", "write": [j("outside", "expired")]}, fh)

    kw = dict(code=j("code"), data=j("data"), notes=j("notes"),
              writable=[j("code"), j("data"), j("notes"), j("work")],
              immutable=[(j("data", "projects", "*", "data", "raw"), "deposit-only", "raw data is never changed"),
                         (j("data", "meeting-transcripts"), "deposit-only", "transcripts are kept as recorded"),
                         (j("notes", "originals"), "never", "the originals of the notes")],
              grant_files=[j("job", "write-scope.json"), j("oldjob", "write-scope.json")],
              note_prefix="mcp__obsidian__vault_")
    cfg = build_config(**kw)
    cfg_allow = build_config(inside="allow", **kw)

    raw = j("data", "projects", "p1", "data", "raw")
    orig = os.path.join(raw, "original.csv")
    repo = j("code", "repo")
    out = j("outside")
    W = lambda p: ("Write", {"file_path": p})  # noqa: E731
    E = lambda p: ("Edit", {"file_path": p, "old_string": "x", "new_string": "y"})  # noqa: E731
    B = lambda c: ("Bash", {"command": c})  # noqa: E731
    P = lambda c: ("PowerShell", {"command": c})  # noqa: E731
    N = lambda action, **a: ("mcp__obsidian__vault_" + action, a)  # noqa: E731

    cases = [
        # file tools
        ("Write a new file in a code repository", W(os.path.join(repo, "a.py")), repo, "pass"),
        ("Edit a file in a code repository", E(os.path.join(repo, "a.py")), repo, "pass"),
        ("Write a new file into raw/ (a deposit)", W(os.path.join(raw, "new.csv")), repo, "pass"),
        ("Write over an existing original", W(orig), repo, "deny"),
        ("Edit an original", E(orig), repo, "deny"),
        ("NotebookEdit inside raw/", ("NotebookEdit", {"notebook_path": os.path.join(raw, "n.ipynb")}), repo, "deny"),
        ("Edit a transcript", E(j("data", "meeting-transcripts", "2026-01-15.vtt")), repo, "deny"),
        ("Write into data/processed", W(j("data", "projects", "p1", "data", "processed", "x.parquet")), repo, "pass"),
        ("Write a note in the vault", W(j("notes", "projects", "new.md")), repo, "pass"),
        ("Write into a never-folder", W(j("notes", "originals", "new.md")), repo, "deny"),
        ("Write outside every root", W(j("outside", "x.txt")), repo, "ask"),
        ("Write in a granted folder", W(j("outside", "granted", "x.txt")), repo, "pass"),
        ("Write in a folder whose grant expired", W(j("outside", "expired", "x.txt")), repo, "ask"),
        ("Relative path inside the repository", W("src/b.py"), repo, "pass"),
        ("Relative path that climbs out of the roots", W("../../outside/c.txt"), repo, "ask"),
        ("Write to a working folder", W(j("work", "scratch.txt")), repo, "pass"),
        ("Read anything (Read tool)", ("Read", {"file_path": orig}), out, "pass"),
        # shell
        ("List an original folder", B(f'ls -la "{raw}"'), repo, "pass"),
        ("Read an original", B(f'cat "{orig}"'), repo, "pass"),
        ("Read a .md file while outside the roots", B("cat README.md"), out, "pass"),
        ("Delete an original", B(f'rm "{orig}"'), repo, "deny"),
        ("Move an original out", B(f'mv "{orig}" "{j("data", "projects", "p1", "data", "processed")}"'), repo, "deny"),
        ("Copy a new file into raw/ (a deposit)", B(f'cp "{j("outside", "old.txt")}" "{raw}/"'), repo, "pass"),
        ("Copy over an existing original", B(f'cp "{j("outside", "old.txt")}" "{orig}"'), repo, "deny"),
        ("Redirect into an original", B(f'echo hi > "{orig}"'), repo, "deny"),
        ("sed -i on an original", B(f"sed -i 's/a/b/' \"{orig}\""), repo, "deny"),
        ("Remove-Item an original (PowerShell)", P(f'Remove-Item -Force "{orig}"'), repo, "deny"),
        ("rm -rf a never-folder", B(f'rm -rf "{j("notes", "originals")}"'), repo, "deny"),
        ("Set-Content outside the roots", P(f'Set-Content -Path "{j("outside", "x.txt")}" -Value hi'), repo, "ask"),
        ("Redirect outside the roots", B(f'echo hi > "{j("outside", "x.txt")}"'), repo, "ask"),
        ("Copy an original out of the roots", B(f'cp "{orig}" "{j("outside", "copy.csv")}"'), repo, "ask"),
        ("Copy into a granted folder", B(f'cp "{j("outside", "old.txt")}" "{j("outside", "granted")}/"'), repo, "pass"),
        ("Copy-Item -Destination outside", P(f'Copy-Item "{orig}" -Destination "{j("outside", "c.csv")}"'), repo, "ask"),
        ("mkdir outside the roots", B(f'mkdir "{j("outside", "newdir")}"'), repo, "ask"),
        ("cd out of the roots, then rm", B(f'cd "{out}" && rm old.txt'), repo, "ask"),
        ("A script's output redirected in the repo", B("python make.py > results.txt 2>&1"), repo, "pass"),
        ("Output to /dev/null", B("git status > /dev/null 2>&1"), repo, "pass"),
        ("A read-only pipeline", B(f'grep -n x "{orig}" | head -5'), repo, "pass"),
        # notes connector
        ("Connector: new note in a never-folder", N("write", path="originals/new.md"), repo, "deny"),
        ("Connector: patch an ordinary note", N("patch", path="projects/plan.md"), repo, "pass"),
        ("Connector: move a note into a never-folder", N("move", path="projects/plan.md", newPath="originals/plan.md"), repo, "deny"),
        ("Connector: read is never checked", N("read", path="originals/kept.md"), repo, "pass"),
        # INSIDE_SCOPE = "allow"
        ("allow mode: Write in the repository", W(os.path.join(repo, "a.py")), repo, "allow", cfg_allow),
        ("allow mode: shell is never allowed outright", B("python make.py > out.txt"), repo, "pass", cfg_allow),
        ("allow mode: outside still asks", W(j("outside", "x.txt")), repo, "ask", cfg_allow),
    ]
    if os.name == "nt":
        bash_path = "/" + orig[0].lower() + orig[2:].replace("\\", "/")
        cases.append(("Git Bash path to an original", B(f'rm "{bash_path}"'), repo, "deny"))

    failed = 0
    for case in cases:
        label, (tool, ti), cwd, expected = case[:4]
        c = case[4] if len(case) > 4 else cfg
        got, _ = decide(tool, ti, cwd, c)
        ok = got == expected
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {expected:5} {got:5} {label}")

    # the protocol: what Claude Code receives
    proto = [
        ("deny: exit 2, reason on stderr", {"tool_name": "Edit", "tool_input": {"file_path": orig}, "cwd": repo},
         lambda code, o, e: code == 2 and e.startswith("Refused by the guard") and not o),
        ("ask: exit 0, JSON permissionDecision ask", {"tool_name": "Write", "tool_input": {"file_path": j("outside", "y")}, "cwd": repo},
         lambda code, o, e: code == 0 and json.loads(o)["hookSpecificOutput"]["permissionDecision"] == "ask"),
        ("pass: exit 0, nothing written", {"tool_name": "Write", "tool_input": {"file_path": os.path.join(repo, "z")}, "cwd": repo},
         lambda code, o, e: code == 0 and not o and not e),
    ]
    for label, call, check in proto:
        o, e = io.StringIO(), io.StringIO()
        code = run_hook(json.dumps(call), cfg, o, e)
        try:
            ok = bool(check(code, o.getvalue(), e.getvalue()))
        except (ValueError, KeyError, TypeError):
            ok = False
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} protocol  {label}")
    o, e = io.StringIO(), io.StringIO()
    ok = run_hook("not json", cfg, o, e) == 0 and not o.getvalue()
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} protocol  input that is not JSON lets the call through untouched")
    ok = expand("<TEMP>") == tempfile.gettempdir() and expand("<code root>") is None
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} config    <TEMP> resolves to the temporary folder; a placeholder counts as not set")

    total = len(cases) + len(proto) + 2
    print(f"\n{total - failed} of {total} checks passed." + (" The guard's logic works on this computer." if not failed else ""))
    return 1 if failed else 0


def main():
    if "--self-test" in sys.argv[1:]:
        return self_test()
    if "--show-config" in sys.argv[1:]:
        return show_config()
    return run_hook(sys.stdin.read(), build_config(), sys.stdout, sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
