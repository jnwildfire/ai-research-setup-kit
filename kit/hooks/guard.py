#!/usr/bin/env python3
"""Guard hook for Claude Code: protect the originals, keep the agent's writes inside your roots and
its reads out of the part of a cloud drive you keep online only, and refuse the git commands that
lose work.

Claude Code runs this script before every file edit, every shell command, every read (Read, Glob,
Grep) and, if you register them, every note write through a notes connector (the setting is in
settings.example.json next to this file). It receives the planned tool call as JSON on its input
and gives one of three verdicts:

    deny   the call would change an original (a folder listed in IMMUTABLE), read a file in a
           blocked folder (READ_BLOCKED), or run a git command that loses work. Exit code 2: the
           call is refused and the reason is shown to the agent, which then explains and proposes
           another way. No setting and no answer of yours lets the call through.
    ask    the call would write outside your roots and outside any grant, or delete a branch.
           Claude Code shows you a permission prompt. In auto mode the prompt decides, not the
           auto-mode classifier.
    pass   everything else. The script stays silent and Claude Code's own permission settings decide,
           exactly as if the guard were not there.

The rules, as the configuration block below sets them:

| What | Verdict |
|---|---|
| a folder of originals, "deposit-only" (raw data, transcripts) | a new file passes; changing, overwriting, moving or deleting one is refused |
| a folder of originals, "never" (a staging folder that only you fill) | every write, move, copy or delete is refused |
| a folder of originals, "existing-only" (an archive that a script fills) | changing a file in place passes; a new file, a move, a copy or a delete is refused |
| writes inside the roots, ~/.claude, the temporary folder, the job's folder, a granted folder | pass |
| writes anywhere else | ask |
| reads inside a blocked folder (the cloud drive outside your data and notes roots) | refused, "ask the person for the file"; a granted path passes |
| git: force push to a protected branch, reset --hard, clean, branch -D, deleting a protected branch, checkout -- . and restore . | refused |
| git: deleting any other branch | ask |
| the keep-awake battery flag ~/.claude/keep-awake/pause | every call refused until power is back or the person says continue |

Reads are checked for Read, Glob and Grep, for the shell's listing and reading commands (ls, dir,
cat, type, find, Get-ChildItem, Get-Content and their kin, a copy's source), and for a recursive
search started above a blocked folder, which would reach into it.

A grant widens the roots for one job or one session: a small JSON file that the session writes only
after you approved a plan that names the extra folders to write and the exact files to read
(guide 04, write-scope.example.json). A `write` folder may be written and read below it. A `read`
entry is an exact path; an entry ending in `/**` opens that folder and everything below it. An
expired grant grants nothing, and no grant opens a folder of originals.

Two situations change the verdicts (guide 04):

    nobody at the keyboard   in a background job (CLAUDE_CODE_SESSION_ATTENDED=0, observed, not
                             documented) an "ask" becomes a refusal with a note for the morning
                             report, so the job goes on with other work instead of waiting.
    battery pause            while the keep-awake skill's battery watch has written its pause flag
                             (on battery at 20 % or less), every call the guard sees is refused with
                             "paused: battery at N %, connect power or say continue". Power back, or
                             the continue file, ends the pause.

What the guard cannot see: a script that writes or reads files itself (`python make_figures.py`) is
one shell command to the guard, and only the paths written on the command line are checked. Shell
commands are matched by pattern, not parsed the way a shell would, so a heredoc line that reads
like a command on a blocked path is refused too (write such a file with the Write tool). The guard
is a net under the rules, not a sandbox; Claude Code's permission prompts and, in auto mode, its
classifier are the second net.

Set the configuration block below, then check it:
    python guard.py --show-config     the resolved roots, folders, grants and branches
    python guard.py --self-test       about 150 synthetic tool calls against a temporary folder tree
Test one call by hand (bash); a refusal prints the reason and exits with 2:
    echo '{"tool_name":"Edit","tool_input":{"file_path":"<an original>"}}' | python guard.py; echo "exit $?"

Standard library only; Python 3.8 or later.

Derived from guard_raw.py in Kevin Michael Smith's ai-research-starter-kit
(https://github.com/KevinMSmith/ai-research-starter-kit), Copyright (c) 2026 Kevin Michael Smith, MIT
licence, by way of the author's own guard for immutable folders; the write scope, the grants, the
read block, the git guardrails and the self-test are added. Copyright (c) 2026 Johannes Wildfeuer,
MIT licence (see LICENSE.md).
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
import time
from datetime import datetime, timedelta

# ------------------------------------------------------------------------------- configuration
# Paths may use ~, environment variables ($HOME, %USERPROFILE%) and forward slashes on Windows.
# A value still in <angle brackets> counts as not set, and every rule that uses it is skipped.

CODE_ROOT = "<code root, for example C:/dev>"
DATA_ROOT = "<data root, for example C:/Users/you/OneDrive - Your University/research>"
NOTES_ROOT = "<notes vault, for example C:/Users/you/OneDrive - Your University/Vault>"

# The cloud drive your data and notes roots sit in. Everything else on it stays out of the agent's
# reach (READ_BLOCKED below), because listing or opening an online-only file downloads it. Leave the
# placeholder if your roots are not on a cloud drive, or if you want no read block.
CLOUD_ROOT = "<cloud drive folder, for example C:/Users/you/OneDrive - Your University>"


def writable_for(code, data, notes):
    """Where the agent writes without the guard objecting: the three roots and its working folders.
    "<TEMP>" is the system's temporary folder; $CLAUDE_JOB_DIR is a background job's own folder."""
    return [code, data, notes, "~/.claude", "<TEMP>", "$CLAUDE_JOB_DIR"]


def immutable_for(data, notes):
    """Folders that hold originals: (folder, strictness, the reason the agent is shown).

    never          nothing inside is written, moved, copied or deleted, by any tool
    deposit-only   a new file may be added (a download, a copy in); nothing that exists is changed,
                   overwritten, moved or deleted
    existing-only  a file that exists may be changed in place; nothing is created, moved, copied or
                   deleted there by hand (an archive that only a script fills)
    A * stands for exactly one folder name: projects/*/data/raw matches every project's raw folder.
    """
    return [
        (data + "/projects/*/data/raw", "deposit-only",
         "raw data is never changed after download; correct it downstream, in data/processed"),
        (data + "/meeting-transcripts", "deposit-only",
         "a transcript is kept as recorded; correct names and errors in the meeting note"),
        # Two examples for a notes vault; remove the # and use your own folder names:
        # (notes + "/<inbox>/_later", "never", "it is the person's staging area and is never touched"),
        # (notes + "/<agent outputs>/Archive", "existing-only",
        #  "notes reach the archive only through the archive script; write new notes on top"),
    ]


def read_blocked_for(cloud, data, notes):
    """(folder, the folders inside it that stay readable, the reason). Reading elsewhere inside is refused."""
    return [
        (cloud, [data, notes],
         "ask the person for the file. The rest of the cloud drive is kept online only on purpose, and "
         "listing, searching or opening anything there downloads it. Say which file you need: the "
         "person points you to it, copies it into a folder you may read, or grants the exact path in "
         "the plan"),
    ]


WRITABLE = writable_for(CODE_ROOT, DATA_ROOT, NOTES_ROOT)
IMMUTABLE = immutable_for(DATA_ROOT, NOTES_ROOT)
READ_BLOCKED = read_blocked_for(CLOUD_ROOT, DATA_ROOT, NOTES_ROOT)

INSIDE_SCOPE = "pass"   # "pass": silent inside WRITABLE, Claude Code's own mode decides. "allow" would
                        # also skip Claude Code's prompt (and, in auto mode, its classifier) for file and
                        # note writes there, including edits of your settings and of this script.
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

# Nobody at the keyboard. Claude Code sets CLAUDE_CODE_SESSION_ATTENDED=0 in background jobs (seen on
# the author's computer in November 2026; not in the documentation read then). There an "ask" waits
# for an answer nobody gives. "deny": refuse, and tell the agent to put the question into its morning
# report. "ask": keep the prompt. Without the variable the guard asks as usual.
UNATTENDED_ASK = "deny"

# The battery pause of the keep-awake skill (kit/skills/keep-awake). Its battery watch writes the
# pause flag on battery at 20 % or less and rewrites it every minute; the person lifts the pause by
# connecting power or by saying "continue", which the agent records as the continue file.
PAUSE_FLAG = "~/.claude/keep-awake/pause"
CONTINUE_FILE = "~/.claude/keep-awake/continue"

# git guardrails: branches that are never force-pushed or deleted. An empty tuple keeps only the
# rules that protect uncommitted work (reset --hard, clean, checkout -- ., restore .).
PROTECTED_BRANCHES = ("main", "master")
# --------------------------------------------------------------------------- end of configuration

NAME = "guard.py"
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
SHELL_TOOLS = ("Bash", "PowerShell")
READ_TOOLS = ("Read", "Glob", "Grep")
PAUSE_STALE_SECONDS = 600  # a pause flag not rewritten for ten minutes was left behind by a stopped watch
UNATTENDED_NOTE = (" Nobody is at the keyboard to answer a prompt (CLAUDE_CODE_SESSION_ATTENDED=0), so the "
                   "guard refuses instead of letting the job wait: write this down as a question for the "
                   "morning report, with your recommendation, and go on with what does not depend on it.")

_EDGE_L = r"(?<![\w.\-/\\$:])"
_EDGE_R = r"(?=\s|$|;)"
REMOVE_VERBS = {"rm", "rmdir", "rd", "del", "erase", "remove-item", "ri", "mv", "move", "move-item", "mi",
                "ren", "rename", "rename-item", "rni", "git rm", "git mv"}
CREATE_VERBS = {"new-item", "ni", "mkdir", "md"}
WRITE_VERBS = re.compile(
    _EDGE_L + r"(rm|rmdir|rd|del|erase|Remove-Item|ri|mv|move|Move-Item|mi|ren|rename|Rename-Item|rni|"
    r"git\s+rm|git\s+mv|Clear-Content|clc|Set-Content|sc|Add-Content|ac|Out-File|Tee-Object|tee|"
    r"truncate|sed\s+-i\S*|perl\s+-pi\S*|touch|New-Item|ni|mkdir|md)" + _EDGE_R,
    re.IGNORECASE,
)
COPY_VERBS = re.compile(_EDGE_L + r"(cp|copy|Copy-Item|cpi|xcopy|robocopy)" + _EDGE_R, re.IGNORECASE)
READ_VERBS = re.compile(
    _EDGE_L + r"(ls|dir|cat|type|find|Get-ChildItem|gci|Get-Content|gc|head|tail|less|more|grep|egrep|"
    r"fgrep|rg|tree|Select-String|sls|wc|Invoke-Item|ii|Import-Csv|ipcsv)" + _EDGE_R,
    re.IGNORECASE,
)
LISTS_CWD = {"ls", "dir", "get-childitem", "gci", "tree", "find", "rg"}   # without a path they read the cwd
RECURSES = {"find", "rg", "tree"}                                         # recursive without a flag
REDIRECT = re.compile(r"(?<![<>&\-\w])\d?>{1,2}\s*(\"[^\"]*\"|'[^']*'|[^\s;|&<>]+)")
CD = re.compile(r"^\s*(?:cd|Set-Location|sl|pushd)\s+(\S.*?)\s*$", re.IGNORECASE)
SINKS = {"/dev/null", "nul", "$null", "nul:", "/dev/stdout", "/dev/stderr"}
WINDOWS_VERBS = {"robocopy", "xcopy", "copy", "move", "del", "erase", "rd", "rmdir", "md", "ren", "rename", "dir"}
WHOLE_TREE = {".", "./", ".\\", "*", ":/", ":/*", ":(top)"}


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


def literal_prefix(pattern):
    """The folder part of a glob pattern before its first wildcard."""
    out = []
    for seg in re.split(r"[\\/]", pattern):
        if any(c in seg for c in "*?[{"):
            break
        out.append(seg)
    return "/".join(out) if out else ""


# ------------------------------------------------------------------------------- configuration as data

def build_config(code=None, data=None, notes=None, writable=None, immutable=None, read_blocked=None,
                 grant_files=None, inside=None, outside=None, note_prefix=None, attended="env",
                 unattended=None, pause_flag=None, continue_file=None):
    """Collect the configuration into one dict; the self-test passes its own values."""
    cwd = os.getcwd()
    flag = expand(PAUSE_FLAG if pause_flag is None else pause_flag)
    cont = expand(CONTINUE_FILE if continue_file is None else continue_file)
    cfg = {
        "writable": [], "immutable": [], "read_blocked": [], "grant_files": [],
        "inside": inside or INSIDE_SCOPE,
        "outside": outside or OUTSIDE_SCOPE,
        "note_prefix": NOTE_TOOL_PREFIX if note_prefix is None else note_prefix,
        "attended": os.environ.get("CLAUDE_CODE_SESSION_ATTENDED") if attended == "env" else attended,
        "unattended": unattended or UNATTENDED_ASK,
        "pause_flag": norm(flag, cwd) if flag else None,
        "continue_file": norm(cont, cwd) if cont else None,
        "continue_shown": os.path.normpath(cont) if cont else None,
        "protected": tuple(b.lower() for b in PROTECTED_BRANCHES),
        "unset": [],
    }
    n = expand(NOTES_ROOT if notes is None else notes)
    cfg["notes_root"] = norm(n, cwd) if n else None
    for name, val in (("CODE_ROOT", CODE_ROOT if code is None else code),
                      ("DATA_ROOT", DATA_ROOT if data is None else data),
                      ("NOTES_ROOT", NOTES_ROOT if notes is None else notes)):
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
    for folder, keep, why in (READ_BLOCKED if read_blocked is None else read_blocked):
        e = expand(folder)
        if e:
            cfg["read_blocked"].append((norm(e, cwd), [norm(expand(k), cwd) for k in keep if expand(k)], why))
    seen, files = set(), []
    for g in (expand(x) for x in (GRANT_FILES if grant_files is None else grant_files)):
        if g and norm(g, cwd) not in seen:
            seen.add(norm(g, cwd))
            files.append(g)
    cfg["grant_files"] = files
    cfg["granted"], cfg["read_exact"], cfg["read_tree"], cfg["grant_notes"] = load_grants(files, cwd)
    return cfg


def load_grants(files, cwd):
    """Folders and paths granted by approved plans. An expired or unreadable grant grants nothing."""
    write, exact, tree, notes = [], [], [], []
    for f in files:
        if not os.path.isfile(f):
            continue
        try:
            with open(f, encoding="utf-8-sig") as fh:
                g = json.load(fh)
        except (OSError, ValueError):
            notes.append(f"{f}: unreadable, ignored")
            continue
        if not isinstance(g, dict):
            notes.append(f"{f}: not a JSON object, ignored")
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
                write.append(norm(e, cwd))
        for r in g.get("read", []) or []:
            r = str(r)
            whole = r.rstrip().endswith("**")
            e = expand(re.sub(r"[\\/]\*\*\s*$", "", r) if whole else r)
            if e:
                (tree if whole else exact).append(norm(e, cwd))
        notes.append(f"{f}: grants {len(g.get('write', []) or [])} folder(s) to write and "
                     f"{len(g.get('read', []) or [])} path(s) to read" + (f" until {exp}" if exp else ""))
    return write, exact, tree, notes


# ------------------------------------------------------------------------------- the decision

ALLOWED_OPS = {"never": set(), "deposit-only": {"create", "copy-out"}, "existing-only": {"modify"}}


def immutable_hit(p, cfg):
    """(folder as written, strictness, reason, concrete folder) when p lies in an immutable folder."""
    pp = parts(p)
    for pattern, strictness, why in cfg["immutable"]:
        pat = parts(pattern)
        if len(pp) >= len(pat) and all(fnmatch.fnmatchcase(a, b) for a, b in zip(pp, pat)):
            return pattern, strictness, why, os.sep.join(pp[:len(pat)])
    return None


def immutable_refusal(p, op, cfg, detail=""):
    """The refusal text when op on p breaks an immutable folder's rule; None otherwise.

    op: create (a new file by a file tool, a note tool or a copy), create-other (a new file or folder
    by another shell verb or a redirect), modify, remove (delete, move, rename), copy-out.
    """
    hit = immutable_hit(p, cfg)
    if not hit or op in ALLOWED_OPS.get(hit[1], set()):
        return None
    _, strictness, why, folder = hit
    if strictness == "never":
        return f"`{folder}` is never written to, moved, copied or deleted: {why}."
    if strictness == "existing-only":
        return (f"`{folder}`: {why}. Nothing new is created there and nothing is moved, copied or deleted "
                f"by hand; changing a note that is there, in place, is fine.")
    return (f"`{folder}` holds originals: {why}. {detail} A new file may be added beside the originals; "
            f"nothing that exists there is changed, moved or deleted.").replace("  ", " ")


def scope(p, cfg):
    if any(within(p, r) for r in cfg["writable"] + cfg["granted"]):
        return cfg["inside"], ""
    return cfg["outside"], (
        f"`{p}` is outside the folders this setup writes to without asking. For a job that runs while "
        f"you are away, the plan names such folders and the session writes a grant before the job "
        f"starts (guide 04).")


def read_refusal(p, cfg, recursive=False):
    """The refusal text when reading p (or searching it recursively) is blocked; None otherwise."""
    for root, keep, why in cfg["read_blocked"]:
        if within(p, root):
            if any(within(p, k) for k in keep) or read_granted(p, cfg):
                continue
            return f"{why}. (`{p}` lies in a folder whose reads are blocked.)"
        if recursive and within(root, p):  # p lies above the blocked folder
            return (f"{why}. (A recursive search from `{p}` reaches into `{root}`; search inside the "
                    f"root you need instead.)")
    return None


def read_granted(p, cfg):
    return (p in cfg["read_exact"] or any(within(p, t) for t in cfg["read_tree"])
            or any(within(p, g) for g in cfg["granted"]))


def writes_continue_file(tool, ti, cwd, cfg):
    """True for a file write to the continue file: recording that the person said continue."""
    target = ti.get("file_path") if tool in FILE_TOOLS else ""
    return bool(cfg["continue_file"] and target and norm(target, cwd) == cfg["continue_file"])


def pause_reason(cfg):
    """The refusal text while the battery pause holds; None when there is no pause."""
    flag, cont = cfg["pause_flag"], cfg["continue_file"]
    if not flag or not os.path.isfile(flag) or (cont and os.path.exists(cont)):
        return None
    try:
        if time.time() - os.path.getmtime(flag) > PAUSE_STALE_SECONDS:
            return None
        with open(flag, encoding="utf-8-sig", errors="replace") as fh:
            percent = (fh.read().split() or ["?"])[0]
    except OSError:
        return None
    return (f"paused: battery at {percent} %, connect power or say continue. The guard ({NAME}) refuses "
            f"every action while the battery is this low, so that the job stops before the computer does. "
            f"Stop here and tell the person. If they say continue, create the empty file "
            f"`{cfg['continue_shown']}` with the Write tool: that is the one action allowed while paused, "
            f"and it ends the pause. Connecting power ends it by itself within a minute.")


def decide(tool, ti, cwd, cfg):
    """Return (verdict, reason) with verdict one of pause, deny, ask, allow, pass."""
    cwd = norm(cwd or os.getcwd(), os.getcwd())
    if writes_continue_file(tool, ti, cwd, cfg):
        return "pass", ""  # never refused and never asked, so a paused job can be resumed
    why = pause_reason(cfg)
    if why:
        return "pause", why
    verdict, reason = decide_call(tool, ti, cwd, cfg)
    if verdict == "ask":
        if cfg["attended"] == "0" and cfg["unattended"] == "deny":
            return "deny", reason + UNATTENDED_NOTE
        return "ask", reason + " Confirm only if you asked for this."
    return verdict, reason


def decide_call(tool, ti, cwd, cfg):
    """The verdict on one call from the roots, the originals, the read block, git and the grants."""
    if tool in FILE_TOOLS:
        raw = ti.get("file_path") or ti.get("notebook_path") or ""
        if not raw:
            return "pass", ""
        p = norm(raw, cwd)
        exists = os.path.exists(p)
        op = "create" if tool == "Write" and not exists else "modify"
        refusal = immutable_refusal(p, op, cfg, (f"`{os.path.basename(p)}` exists; a" if exists else "A")
                                    + " corrected version is a new file with a date or version in its name, "
                                      "or belongs downstream.")
        if refusal:
            return "deny", refusal
        return scope(p, cfg)
    if tool in READ_TOOLS:
        return decide_read_tool(tool, ti, cwd, cfg)
    if tool in SHELL_TOOLS:
        return decide_shell(ti.get("command", "") or "", cwd, cfg)
    prefix = cfg["note_prefix"]
    if prefix and tool.startswith(prefix):
        return decide_note(tool[len(prefix):], ti, cfg)
    return "pass", ""


def decide_read_tool(tool, ti, cwd, cfg):
    if not cfg["read_blocked"]:
        return "pass", ""
    if tool == "Read":
        raw = ti.get("file_path") or ""
        refusal = read_refusal(norm(raw, cwd), cfg) if raw else None
    elif tool == "Glob":
        base = norm(ti.get("path") or cwd, cwd)
        pattern = str(ti.get("pattern") or "")
        prefix = literal_prefix(pattern)
        target = norm(prefix, base) if prefix else base
        refusal = read_refusal(target, cfg, recursive="**" in pattern)
    else:  # Grep searches a folder recursively, or one file
        refusal = read_refusal(norm(ti.get("path") or cwd, cwd), cfg, recursive=True)
    return ("deny", refusal) if refusal else ("pass", "")


def decide_note(action, ti, cfg):
    if action not in NOTE_TOOL_WRITES or not cfg["notes_root"]:
        return "pass", ""
    for key in NOTE_PATH_KEYS:
        val = ti.get(key)
        if not isinstance(val, str) or not val:
            continue
        p = norm(os.path.join(cfg["notes_root"], val.lstrip("/\\")), cfg["notes_root"])
        exists = os.path.exists(p)
        if key == "path":
            op = {"write": "modify" if exists else "create", "patch": "modify",
                  "append": "modify" if exists else "create", "delete": "remove",
                  "move": "remove", "copy": "copy-out"}[action]
        else:
            op = "create" if not exists else "modify"
        refusal = immutable_refusal(p, op, cfg)
        if refusal:
            return "deny", refusal
    return ("allow", "") if cfg["inside"] == "allow" else ("pass", "")


# ------------------------------------------------------------------------------- the shell

def tokens(seg):
    return [t.strip("\"'") for t in re.findall(r'"[^"]*"|\'[^\']*\'|\S+', seg)]


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
        if re.match(r"\d?>{1,2}|<", t) or t.startswith("-") or not t:
            continue
        if verb in WINDOWS_VERBS and re.fullmatch(r"/[A-Za-z]{1,4}(:\S*)?", t):
            continue
        args.append(t)
    return args


def shell_targets(seg, cwd):
    """(path, op) for every path the segment writes, and every source it copies (op copy-out)."""
    found = []
    for m in REDIRECT.finditer(seg):
        t = m.group(1).strip("\"'")
        if t.count(")") > t.count("("):  # the closing bracket of a $( ... ) around the redirect
            t = t.rstrip(")")
        if t and t.lower() not in SINKS:
            found.append((t, "redirect"))
    cm = COPY_VERBS.search(seg)
    wm = WRITE_VERBS.search(seg)
    if cm and (not wm or cm.start() < wm.start()):
        verb = cm.group(1).lower()
        args = arguments(seg[cm.end():], verb)
        dest = None
        if verb in ("copy-item", "cpi"):
            after = tokens(seg[cm.end():])
            for i, t in enumerate(after[:-1]):
                if t.lower() in ("-destination", "-dest"):
                    dest = after[i + 1]
                    args = [a for a in args if a != dest]
                    break
        if dest is None and verb == "robocopy" and len(args) >= 2:
            dest, args = args[1], args[:1]
        elif dest is None and args:
            dest, args = args[-1], args[:-1]
        if dest:
            found.append((dest, "copy-dest"))
        found += [(a, "copy-out") for a in args]
    elif wm:
        verb = re.sub(r"\s+", " ", wm.group(1).lower())
        kind = "remove" if verb in REMOVE_VERBS else "create-verb" if verb in CREATE_VERBS else "modify-verb"
        found += [(t, kind) for t in arguments(seg[wm.end():], verb) if t.lower() not in SINKS]
    ops = []
    for raw, kind in found:
        if raw.startswith("$") and expand(raw) is None:
            continue  # a shell variable the guard cannot resolve
        p = norm(raw, cwd)
        exists = os.path.exists(p)
        if kind == "copy-dest":
            op = "create" if os.path.isdir(p) or not exists else "modify"
        elif kind in ("redirect", "modify-verb"):
            op = "modify" if exists else "create-other"
        elif kind == "create-verb":
            op = "create-other"
        else:
            op = kind  # remove, copy-out
        ops.append((p, op))
    return ops


def shell_reads(seg, cwd):
    """(path, recursive) for every path the segment lists or reads, copy sources included."""
    reads = []
    m = READ_VERBS.search(seg)
    if m:
        verb = m.group(1).lower()
        rest = seg[m.end():]
        toks = tokens(rest)
        recursive = verb in RECURSES or any(
            t in ("-Recurse", "--recursive", "/s", "/S") or t.lower() == "-recurse"
            or re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", t) and verb not in ("head", "tail", "wc", "cat", "type")
            for t in toks)
        args = arguments(rest, verb)
        if not args and verb in LISTS_CWD:
            reads.append((cwd, recursive))
        reads += [(norm(a, cwd), recursive) for a in args if not (a.startswith("$") and expand(a) is None)]
    for p, op in shell_targets(seg, cwd):
        if op == "copy-out":
            reads.append((p, False))
    return reads


def decide_shell(cmd, cwd, cfg):
    asked = None
    for seg in re.split(r"[;\n|]|&&|\|\|", cmd):
        m = CD.match(seg)
        if m:
            target = m.group(1).strip().strip("\"'")
            if target and target != "-":
                cwd = norm(target, cwd)
            continue
        git = git_call(seg, cwd)
        if git:
            verdict, reason = decide_git(*git, cfg)
            if verdict == "deny":
                return verdict, reason
            if verdict == "ask" and asked is None:
                asked = (verdict, reason)
        if cfg["read_blocked"]:
            for p, recursive in shell_reads(seg, cwd):
                refusal = read_refusal(p, cfg, recursive)
                if refusal:
                    return "deny", refusal
        for p, op in shell_targets(seg, cwd):
            refusal = immutable_refusal(p, op, cfg, "This command would change, move, overwrite or delete there.")
            if refusal:
                return "deny", refusal
            if op == "copy-out":
                continue  # a copy's source is read, not written
            verdict, reason = scope(p, cfg)
            if verdict in ("ask", "deny") and asked is None:
                asked = (verdict, reason)
    if asked:
        return asked
    return "pass", ""  # shell commands never get an explicit allow


# ------------------------------------------------------------------------------- git

GIT_GLOBAL_WITH_VALUE = {"-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--exec-path"}
GIT_WRAPPERS = {"&", "(", "sudo", "command", "time", "exec", "env", "nohup", "call"}
PUSH_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}


def git_call(seg, cwd):
    """(cwd of the git call, subcommand, its arguments) when the segment runs git; None otherwise."""
    toks = tokens(seg)
    i = 0
    while i < len(toks) and (toks[i] in GIT_WRAPPERS or re.fullmatch(r"[A-Za-z_]\w*=\S*", toks[i])):
        i += 1
    if i >= len(toks) or not re.fullmatch(r"\(?(?:.*[\\/])?git(?:\.exe)?", toks[i], re.IGNORECASE):
        return None
    i += 1
    gcwd = cwd
    while i < len(toks) and toks[i].startswith("-"):
        if toks[i] == "-C" and i + 1 < len(toks):
            gcwd = norm(toks[i + 1], gcwd)
            i += 2
        elif toks[i] in GIT_GLOBAL_WITH_VALUE and i + 1 < len(toks):
            i += 2
        else:
            i += 1
    if i >= len(toks):
        return None
    args = [t.rstrip(")") for t in toks[i + 1:]]
    return gcwd, toks[i].lower(), args


def flag_sets(args):
    longs = {a.split("=", 1)[0] for a in args if a.startswith("--") and a != "--"}
    shorts = set("".join(a[1:] for a in args if re.fullmatch(r"-[A-Za-z]+", a)))
    return longs, shorts


def positional(args, with_value=()):
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "--":
            continue
        if a in with_value:
            skip = True
            continue
        if a.startswith("-"):
            continue
        out.append(a)
    return out


def current_branch(cwd):
    """The branch checked out at cwd, read from .git/HEAD (worktrees included); None when unknown."""
    d = cwd
    for _ in range(64):
        g = os.path.join(d, ".git")
        head = None
        if os.path.isdir(g):
            head = os.path.join(g, "HEAD")
        elif os.path.isfile(g):
            try:
                with open(g, encoding="utf-8") as fh:
                    m = re.match(r"gitdir:\s*(.+)", fh.read().strip())
                if m:
                    gd = m.group(1).strip()
                    head = os.path.join(gd if os.path.isabs(gd) else os.path.join(d, gd), "HEAD")
            except OSError:
                return None
        if head:
            try:
                with open(head, encoding="utf-8") as fh:
                    m = re.match(r"ref:\s*refs/heads/(.+)", fh.read().strip())
                return m.group(1).strip() if m else None
            except OSError:
                return None
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent
    return None


def is_protected(name, cfg):
    n = (name or "").lower()
    n = re.sub(r"^refs/heads/", "", n)
    return n in cfg["protected"] or n.split("/", 1)[-1] in cfg["protected"]


def push_destination(ref, gcwd):
    r = ref.lstrip("+")
    if ":" in r:
        r = r.split(":", 1)[1]
    if r.upper() == "HEAD" or not r:
        return current_branch(gcwd)
    return re.sub(r"^refs/heads/", "", r)


LOSES_WORK = ("this discards every uncommitted change in the working tree, with no way back; restore "
              "single files by name, or commit the work on a branch first")


def decide_git(gcwd, sub, args, cfg):
    """git guardrails: refuse what loses work or rewrites a protected branch; ask before other branch deletions."""
    longs, shorts = flag_sets(args)
    if sub == "push":
        pos = positional(args, PUSH_WITH_VALUE)
        refspecs = pos[1:]
        delete = "d" in shorts or "--delete" in longs
        removed = [r[1:] for r in refspecs if r.startswith(":") and len(r) > 1]
        if delete or removed:
            names = removed + ([push_destination(r, gcwd) for r in refspecs if not r.startswith(":")] if delete else [])
            if any(n is None or is_protected(n, cfg) for n in names):
                return "deny", "a protected branch is never deleted, on the remote or locally."
            return "ask", (f"this deletes the remote branch {', '.join('`%s`' % n for n in names) or '(unnamed)'}: "
                           f"branch deletions wait for the person's yes.")
        force = ("f" in shorts or longs & {"--force", "--force-with-lease", "--mirror"}
                 or any(r.startswith("+") for r in refspecs))
        if force:
            if longs & {"--all", "--mirror", "--branches"}:
                return "deny", "a force push of every branch rewrites the protected branches too; push one named branch."
            dests = [push_destination(r, gcwd) for r in refspecs] or [current_branch(gcwd)]
            if any(d is None for d in dests):
                return "deny", ("a force push whose branch the guard cannot see may hit a protected branch: name the branch "
                                "(`git push --force-with-lease origin <branch>`).")
            if any(is_protected(d, cfg) for d in dests):
                return "deny", ("a force push to a protected branch rewrites the history every checkout and the remote "
                                "share; push a branch and open a pull request, or leave it to the person.")
        return "pass", ""
    if sub == "reset" and "--hard" in longs:
        return "deny", ("`git reset --hard` " + LOSES_WORK.replace("this discards", "discards")
                        + "; `git stash push -u -m <tag>` or a WIP commit sets work aside safely.")
    if sub == "clean" and not ("n" in shorts or "--dry-run" in longs):
        return "deny", ("`git clean` deletes untracked files with no way back; `git clean -n` lists what it "
                        "would delete, and the person removes them.")
    if sub == "branch" and ("d" in shorts or "D" in shorts or "--delete" in longs):
        names = positional(args)
        if any(is_protected(n, cfg) for n in names):
            return "deny", "a protected branch is never deleted, locally or on the remote."
        if "D" in shorts or "f" in shorts or "--force" in longs:
            return "deny", ("`git branch -D` deletes a branch even when its work is merged nowhere; "
                            "`git branch -d` refuses an unmerged branch and asks the person first.")
        return "ask", (f"this deletes the branch {', '.join('`%s`' % n for n in names) or '(unnamed)'}: "
                       f"branch deletions wait for the person's yes.")
    if sub == "checkout":
        specs = args[args.index("--") + 1:] if "--" in args else positional(args)
        if any(s in WHOLE_TREE for s in specs):
            return "deny", "`git checkout -- .`: " + LOSES_WORK + "."
    if sub == "restore":
        staged_only = ("--staged" in longs or "S" in shorts) and not ("--worktree" in longs or "W" in shorts)
        if not staged_only and any(s in WHOLE_TREE for s in positional(args, {"-s", "--source"})):
            return "deny", "`git restore .`: " + LOSES_WORK + "."
    return "pass", ""


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
    if verdict == "pause":
        err.write(reason)
        return 2
    if verdict == "deny":
        err.write(f"Refused by the guard ({NAME}): {reason}")
        return 2
    if verdict in ("ask", "allow"):
        out.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": verdict,
            "permissionDecisionReason": f"{NAME}: {reason}" if reason else f"{NAME}: inside the roots",
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
    print("Reads refused below (except the folders in brackets):")
    for root, keep, _ in cfg["read_blocked"]:
        print(f"  {root}   [{'; '.join(keep)}]")
    print("Grant files looked for:")
    for g in cfg["grant_files"]:
        print(f"  {g}")
    for n in cfg["grant_notes"]:
        print(f"  -> {n}")
    print(f"Notes connector prefix: {cfg['note_prefix'] or '(none)'}; notes root: {cfg['notes_root']}")
    print(f"Inside the roots: {cfg['inside']}; outside: {cfg['outside']}")
    att = cfg["attended"]
    print(f"Someone at the keyboard: {'no' if att == '0' else 'yes' if att else 'not said (variable absent)'}"
          f"; an ask without anyone there becomes: {cfg['unattended']}")
    print(f"Battery pause flag: {cfg['pause_flag']}"
          f"{'   (PRESENT)' if cfg['pause_flag'] and os.path.isfile(cfg['pause_flag']) else ''}")
    print(f"Continue file: {cfg['continue_file']}")
    print(f"Protected branches: {', '.join(cfg['protected'])}")
    return 1 if cfg["unset"] else 0


# ------------------------------------------------------------------------------- self-test

def self_test():
    base = tempfile.mkdtemp(prefix="guard-selftest-")
    try:
        return _self_test(base)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _write(path, text="x\n"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _run_cases(cases, default_cfg):
    failed = 0
    for case in cases:
        label, (tool, ti), cwd, expected = case[:4]
        c = case[4] if len(case) > 4 else default_cfg
        got, reason = decide(tool, ti, cwd, c)
        ok = got == expected
        if ok and len(case) > 5:
            ok = case[5] in reason
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {expected:5} {got:5} {label}" + ("" if ok else f"\n       {reason[:200]}"))
    return failed


def _self_test(base):
    j = lambda *a: os.path.join(base, *a)  # noqa: E731
    W = lambda p: ("Write", {"file_path": p})  # noqa: E731
    E = lambda p: ("Edit", {"file_path": p, "old_string": "x", "new_string": "y"})  # noqa: E731
    B = lambda c: ("Bash", {"command": c})  # noqa: E731
    P = lambda c: ("PowerShell", {"command": c})  # noqa: E731
    N = lambda action, **a: ("mcp__obsidian__vault_" + action, a)  # noqa: E731
    total = failed = 0

    # ---- part 1: the roots, the originals, the grants, the battery pause (no read block)
    print("Part 1: roots, originals, write grants, unattended, battery")
    for d in ("code/repo", "data/projects/p1/data/raw", "data/projects/p1/data/processed",
              "data/meeting-transcripts", "notes/projects", "notes/originals", "outside/granted",
              "outside/expired", "job", "oldjob", "work"):
        os.makedirs(j(*d.split("/")), exist_ok=True)
    for f in ("data/projects/p1/data/raw/original.csv", "data/meeting-transcripts/2026-01-15.vtt",
              "notes/originals/kept.md", "notes/projects/plan.md", "outside/old.txt"):
        _write(j(*f.split("/")))
    future = (datetime.now() + timedelta(days=1)).isoformat(timespec="minutes")
    with open(j("job", "write-scope.json"), "w", encoding="utf-8") as fh:
        json.dump({"plan": "self-test", "expires": future, "write": [j("outside", "granted")]}, fh)
    with open(j("oldjob", "write-scope.json"), "w", encoding="utf-8") as fh:
        json.dump({"plan": "self-test", "expires": "2000-01-01T00:00", "write": [j("outside", "expired")]}, fh)
    for d in ("power", "power-continued", "power-stale"):
        _write(j(d, "pause"), "18\n")
    _write(j("power-continued", "continue"), "")
    hour_ago = time.time() - 3600
    os.utime(j("power-stale", "pause"), (hour_ago, hour_ago))

    kw = dict(code=j("code"), data=j("data"), notes=j("notes"),
              writable=[j("code"), j("data"), j("notes"), j("work")],
              immutable=[(j("data", "projects", "*", "data", "raw"), "deposit-only", "raw data is never changed"),
                         (j("data", "meeting-transcripts"), "deposit-only", "transcripts are kept as recorded"),
                         (j("notes", "originals"), "never", "the originals of the notes")],
              read_blocked=[], grant_files=[j("job", "write-scope.json"), j("oldjob", "write-scope.json")],
              note_prefix="mcp__obsidian__vault_", unattended="deny",
              continue_file=j("power", "continue"))  # the session's own environment never decides
    cfg = build_config(attended=None, pause_flag=j("nopause"), **kw)
    cfg_allow = build_config(inside="allow", attended=None, pause_flag=j("nopause"), **kw)
    cfg_away = build_config(attended="0", pause_flag=j("nopause"), **kw)
    cfg_here = build_config(attended="1", pause_flag=j("nopause"), **kw)
    cfg_low = build_config(attended=None, pause_flag=j("power", "pause"), **kw)
    kw["continue_file"] = j("power-continued", "continue")
    cfg_cont = build_config(attended=None, pause_flag=j("power-continued", "pause"), **kw)
    cfg_stale = build_config(attended=None, pause_flag=j("power-stale", "pause"), **kw)

    raw = j("data", "projects", "p1", "data", "raw")
    orig = os.path.join(raw, "original.csv")
    repo = j("code", "repo")
    out = j("outside")
    first = [
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
        ("Read an original (no read block configured)", ("Read", {"file_path": orig}), out, "pass"),
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
        ("Connector: new note in a never-folder", N("write", path="originals/new.md"), repo, "deny"),
        ("Connector: patch an ordinary note", N("patch", path="projects/plan.md"), repo, "pass"),
        ("Connector: move a note into a never-folder", N("move", path="projects/plan.md", newPath="originals/plan.md"), repo, "deny"),
        ("Connector: read is never checked", N("read", path="originals/kept.md"), repo, "pass"),
        ("allow mode: Write in the repository", W(os.path.join(repo, "a.py")), repo, "allow", cfg_allow),
        ("allow mode: shell is never allowed outright", B("python make.py > out.txt"), repo, "pass", cfg_allow),
        ("allow mode: outside still asks", W(j("outside", "x.txt")), repo, "ask", cfg_allow),
        ("Unattended: a write outside the roots is refused, not asked", W(j("outside", "x.txt")), repo, "deny", cfg_away),
        ("Unattended: a shell write outside is refused", B(f'mkdir "{j("outside", "d2")}"'), repo, "deny", cfg_away),
        ("Unattended: inside the roots stays silent", W(os.path.join(repo, "a.py")), repo, "pass", cfg_away),
        ("Attended (variable 1): outside still asks", W(j("outside", "x.txt")), repo, "ask", cfg_here),
        ("Paused: a write inside the roots is refused", W(os.path.join(repo, "a.py")), repo, "pause", cfg_low),
        ("Paused: a shell command is refused", B("python make.py"), repo, "pause", cfg_low),
        ("Paused: a read is refused", ("Read", {"file_path": orig}), repo, "pause", cfg_low),
        ("Paused: writing the continue file goes through", W(j("power", "continue")), repo, "pass", cfg_low),
        ("Paused, then continue: a write goes through", W(os.path.join(repo, "a.py")), repo, "pass", cfg_cont),
        ("A pause flag left behind an hour ago is ignored", W(os.path.join(repo, "a.py")), repo, "pass", cfg_stale),
    ]
    if os.name == "nt":
        bash_path = "/" + orig[0].lower() + orig[2:].replace("\\", "/")
        first.append(("Git Bash path to an original", B(f'rm "{bash_path}"'), repo, "deny"))
    failed += _run_cases(first, cfg)
    total += len(first)

    proto = [
        ("deny: exit 2, reason on stderr", {"tool_name": "Edit", "tool_input": {"file_path": orig}, "cwd": repo},
         lambda code, o, e: code == 2 and e.startswith("Refused by the guard") and not o),
        ("ask: exit 0, JSON permissionDecision ask", {"tool_name": "Write", "tool_input": {"file_path": j("outside", "y")}, "cwd": repo},
         lambda code, o, e: code == 0 and json.loads(o)["hookSpecificOutput"]["permissionDecision"] == "ask"),
        ("pass: exit 0, nothing written", {"tool_name": "Write", "tool_input": {"file_path": os.path.join(repo, "z")}, "cwd": repo},
         lambda code, o, e: code == 0 and not o and not e),
        ("unattended ask: exit 2, refusal with the morning-report note", {"tool_name": "Write", "tool_input": {"file_path": j("outside", "y")}, "cwd": repo},
         lambda code, o, e: code == 2 and e.startswith("Refused by the guard") and "morning report" in e and not o, cfg_away),
        ("pause: exit 2, 'paused: battery at 18 %, connect power or say continue'", {"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": repo},
         lambda code, o, e: code == 2 and e.startswith("paused: battery at 18 %, connect power or say continue") and not o, cfg_low),
    ]
    for label, call, check, *c in proto:
        o, e = io.StringIO(), io.StringIO()
        code = run_hook(json.dumps(call), c[0] if c else cfg, o, e)
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
    total += len(proto) + 2

    # ---- a layout like a real one: roots on a cloud drive whose name has spaces, a vault with a
    # staging folder ("never") and an archive that a script fills ("existing-only")
    cloud = j("Cloud Drive - Test University")
    D = os.path.join(cloud, "research")
    V = os.path.join(cloud, "Vault")
    dev = j("dev")
    res = os.path.join(dev, "research")
    home = j("home")
    private = os.path.join(cloud, "Private")
    for d in (os.path.join(D, "projects", "p1", "data", "processed"), os.path.join(D, "projects", "p2", "data", "raw"),
              os.path.join(D, "meeting-transcripts", "weekly"), os.path.join(V, "Inbox", "_later"),
              os.path.join(V, "Outputs", "Archive", "2026-10"), os.path.join(cloud, "Documents"),
              os.path.join(home, ".claude", "keep-awake"), os.path.join(home, "Downloads", "export"),
              os.path.join(home, "Downloads", "old"), j("machine-job"), os.path.join(res, ".claude")):
        os.makedirs(d, exist_ok=True)
    raw_file = os.path.join(D, "projects", "p1", "data", "raw", "readings.csv")
    archived = os.path.join(V, "Outputs", "Archive", "2026-09", "2026-09-06-plan.md")
    for f in (raw_file, archived, os.path.join(V, "Maps", "Tasks.md"), os.path.join(V, "Outputs", "x.md"),
              os.path.join(private, "report.pdf"), os.path.join(private, "granted.pdf"),
              os.path.join(private, "Reports", "a.pdf")):
        _write(f)
    _write(os.path.join(res, ".git", "HEAD"), "ref: refs/heads/main\n")
    _write(os.path.join(res, ".git", "worktrees", "wt", "HEAD"), "ref: refs/heads/feature-x\n")
    wt = os.path.join(res, ".claude", "worktrees", "wt")
    _write(os.path.join(wt, ".git"), "gitdir: " + os.path.join(res, ".git", "worktrees", "wt") + "\n")
    with open(j("machine-job", "write-scope.json"), "w", encoding="utf-8") as fh:
        json.dump({"plan": "self-test", "approved": "now", "expires": future,
                   "write": [os.path.join(home, "Downloads", "export")],
                   "read": [os.path.join(private, "granted.pdf"), os.path.join(private, "Reports") + "/**"]}, fh)
    with open(os.path.join(res, ".claude", "write-scope.local.json"), "w", encoding="utf-8") as fh:
        json.dump({"plan": "self-test", "expires": "2000-01-01T00:00", "write": [os.path.join(home, "Downloads", "old")],
                   "read": [os.path.join(private, "report.pdf")]}, fh)
    _write(os.path.join(home, ".claude", "keep-awake", "pause"), "17\n")

    vault_rules = [(V + "/Inbox/_later", "never", "it is the person's staging area and is never touched"),
                   (V + "/Outputs/Archive", "existing-only",
                    "notes reach the archive only through the archive script; write new notes on top")]
    mk = dict(code=dev, data=D, notes=V,
              writable=[dev, D, V, os.path.join(home, ".claude"), j("machine-job")],
              immutable=immutable_for(D, V) + vault_rules, read_blocked=read_blocked_for(cloud, D, V),
              grant_files=[j("machine-job", "write-scope.json"), os.path.join(res, ".claude", "write-scope.local.json")],
              note_prefix="mcp__obsidian__vault_", unattended="deny",
              continue_file=os.path.join(home, ".claude", "keep-awake", "continue"))
    m = build_config(attended=None, pause_flag=j("nopause"), **mk)
    m_away = build_config(attended="0", pause_flag=j("nopause"), **mk)
    m_here = build_config(attended="1", pause_flag=j("nopause"), **mk)
    m_low = build_config(attended=None, pause_flag=os.path.join(home, ".claude", "keep-awake", "pause"), **mk)
    mk_open = dict(mk, read_blocked=read_blocked_for("<cloud drive folder>", D, V))
    m_open = build_config(attended=None, pause_flag=j("nopause"), **mk_open)

    # ---- part 2: the three strictnesses on a vault, through every kind of tool
    print("\nPart 2: never, deposit-only and existing-only folders")
    second = [
        ("Write into the staging folder", W(V + r"\Inbox\_later\x.md"), res, "deny"),
        ("Edit inside the staging folder", E(V + r"\Inbox\_later\sub\note.md"), res, "deny"),
        ("Write a new note into the archive", W(V + r"\Outputs\Archive\2026-09\brand-new.md"), res, "deny"),
        ("Edit an archived note in place", E(archived), res, "pass"),
        ("Write a new note on top of the outputs folder", W(V + r"\Outputs\2026-10-23-new-note.md"), res, "pass"),
        ("Edit a raw file", E(raw_file), res, "deny"),
        ("Write a new raw deposit", W(D + r"\projects\p1\data\raw\2026-10-23_new-deposit.csv"), res, "pass"),
        ("Write a new transcript", W(D + r"\meeting-transcripts\weekly\2099-01-01 does-not-exist.vtt"), res, "pass"),
        ("Write into processed", W(D + r"\projects\p1\data\processed\daily.parquet"), res, "pass"),
        ("rm a raw file", B('rm "' + D + r'\projects\p2\data\raw\x.csv"'), res, "deny"),
        ("sed -i on a transcript", B("sed -i 's/a/b/' \"" + D.replace("\\", "/") + "/meeting-transcripts/weekly/x.vtt\""), res, "deny"),
        ("cp a new file into raw", B('cp new.csv "' + D + r'\projects\p2\data\raw\"'), res, "pass"),
        ("ls a raw folder", B('ls "' + D + r'\projects\p2\data\raw"'), res, "pass"),
        ("Remove-Item in the staging folder", P('Remove-Item "' + V + r'\Inbox\_later\x.md"'), res, "deny"),
        ("cp into the staging folder", B('cp a.md "' + V + r'\Inbox\_later\"'), res, "deny"),
        ("mv a note into the archive", B('mv "' + V + r'\Outputs\x.md" "' + V + r'\Outputs\Archive\2026-09\"'), res, "deny"),
        ("cat an archived note", B('cat "' + V + r'\Outputs\Archive\2026-09\x.md"'), res, "pass"),
        ("Connector: write into the staging folder", N("write", path="Inbox/_later/x.md", content="x"), res, "deny"),
        ("Connector: patch in the staging folder", N("patch", path="Inbox/_later/x.md", targetType="heading", target=["a"], operation="append", content="x"), res, "deny"),
        ("Connector: write a new archived note", N("write", path="Outputs/Archive/2026-09/brand-new.md", content="x"), res, "deny"),
        ("Connector: patch an archived note", N("patch", path="Outputs/Archive/2026-09/2026-09-06-plan.md", targetType="frontmatter", target="status", operation="replace", value="done"), res, "pass"),
        ("Connector: append to an archived note", N("append", path="Outputs/Archive/2026-09/2026-09-06-plan.md", content="x"), res, "pass"),
        ("Connector: move a note into the archive", N("move", path="Outputs/x.md", newPath="Outputs/Archive/2026-10/x.md"), res, "deny"),
        ("Connector: delete in the archive", N("delete", path="Outputs/Archive/2026-09/x.md"), res, "deny"),
        ("Connector: write on top of the outputs folder", N("write", path="Outputs/2026-10-23-fine.md", content="x"), res, "pass"),
        ("Connector: patch an ordinary note", N("patch", path="Maps/Tasks.md", targetType="heading", target=["a"], operation="append", content="x"), res, "pass"),
        ("Read inside the staging folder", ("Read", {"file_path": V + r"\Inbox\_later\x.md"}), res, "pass"),
    ]
    failed += _run_cases(second, m)
    total += len(second)

    # ---- part 3: the roots on a cloud drive, the read block, grants, battery, unattended, git
    print("\nPart 3: roots, the read block, grants, battery, unattended, git")
    ask_p = "ask the person for the file"
    third = [
        ("Root: a write in another repository under the code root", W(os.path.join(dev, "other", "x.py")), res, "pass"),
        ("Root: a write under ~/.claude", W(os.path.join(home, ".claude", "skills", "x", "SKILL.md")), res, "pass"),
        ("Root: a write in the job folder", W(j("machine-job", "tmp", "out.json")), res, "pass"),
        ("Root: a redirect to a quoted path with spaces in the data root", B(f'python make.py > "{D}\\projects\\x.txt"'), res, "pass"),
        ("Root: a write to Downloads asks", W(os.path.join(home, "Downloads", "x.txt")), res, "ask"),
        ("Root: a write into the cloud drive outside the roots asks", W(os.path.join(private, "new.docx")), res, "ask"),
        ("Shell: a redirect to /dev/null inside $( ) passes", B('c=$(curl -s -o page.html https://example.org 2>/dev/null)'), res, "pass", m_away),
        ("Read block: Read a file outside the roots", ("Read", {"file_path": os.path.join(private, "report.pdf")}), res, "deny", m, ask_p),
        ("Read block: Glob in another folder of the drive", ("Glob", {"pattern": "*.docx", "path": os.path.join(cloud, "Documents")}), res, "deny", m, ask_p),
        ("Read block: Glob with an absolute pattern into it", ("Glob", {"pattern": private.replace("\\", "/") + "/**/*.pdf"}), res, "deny"),
        ("Read block: Glob from the drive into the data root passes", ("Glob", {"pattern": "research/projects/*", "path": cloud}), res, "pass"),
        ("Read block: a recursive Glob from above the drive", ("Glob", {"pattern": "**/*.pdf", "path": base}), res, "deny"),
        ("Read block: Grep in a blocked folder", ("Grep", {"pattern": "x", "path": private}), res, "deny"),
        ("Read block: Grep from above the drive", ("Grep", {"pattern": "x", "path": base}), res, "deny"),
        ("Read block: Grep in the vault passes", ("Grep", {"pattern": "x", "path": V}), res, "pass"),
        ("Read block: Read a note in the vault passes", ("Read", {"file_path": os.path.join(V, "Maps", "Tasks.md")}), res, "pass"),
        ("Read block: ls the drive folder itself", B(f'ls "{cloud}"'), res, "deny"),
        ("Read block: ls a blocked folder", B(f'ls -la "{private}"'), res, "deny", m, ask_p),
        ("Read block: cat a file there", B(f'cat "{private}/report.pdf"'), res, "deny"),
        ("Read block: find in another folder", B(f'find "{cloud}/Documents" -name "*.pdf"'), res, "deny"),
        ("Read block: dir (PowerShell)", P(f'dir "{private}"'), res, "deny"),
        ("Read block: type a file (PowerShell)", P(f'type "{private}\\report.pdf"'), res, "deny"),
        ("Read block: Get-ChildItem -Recurse", P(f'Get-ChildItem -Path "{cloud}\\Documents" -Recurse'), res, "deny"),
        ("Read block: Get-Content", P(f'Get-Content "{private}\\report.pdf" -TotalCount 5'), res, "deny"),
        ("Read block: cd into a blocked folder, then ls", B(f'cd "{private}" && ls'), res, "deny"),
        ("Read block: copy a file out of it", B(f'cp "{private}/report.pdf" "{D}/projects/"'), res, "deny"),
        ("Read block: grep -r from above the drive", B(f'grep -rn x "{base}"'), res, "deny"),
        ("Read block: ls in the data root passes", B(f'ls "{D}/projects"'), res, "pass"),
        ("Read block: Get-Content in the vault passes", P(f'Get-Content "{archived}"'), res, "pass"),
        ("Read block: a placeholder drive folder blocks nothing", ("Read", {"file_path": os.path.join(private, "report.pdf")}), res, "pass", m_open),
        ("Grant: an exact read grant opens that file", ("Read", {"file_path": os.path.join(private, "granted.pdf")}), res, "pass"),
        ("Grant: its sibling stays closed", ("Read", {"file_path": os.path.join(private, "other.pdf")}), res, "deny"),
        ("Grant: a folder read grant ending in /** opens the folder", B(f'cat "{private}/Reports/a.pdf"'), res, "pass"),
        ("Grant: the read grant of an expired session file is ignored", ("Read", {"file_path": os.path.join(private, "report.pdf")}), res, "deny"),
        ("Grant: a job's write grant opens Downloads/export", W(os.path.join(home, "Downloads", "export", "a.csv")), res, "pass"),
        ("Grant: an expired session write grant asks", W(os.path.join(home, "Downloads", "old", "a.csv")), res, "ask"),
        ("Battery: a Read is paused", ("Read", {"file_path": os.path.join(V, "x.md")}), res, "pause", m_low, "paused: battery at 17 %, connect power or say continue"),
        ("Battery: a git status is paused", B("git status"), res, "pause", m_low),
        ("Battery: writing the continue file goes through", W(os.path.join(home, ".claude", "keep-awake", "continue")), res, "pass", m_low),
        ("Unattended: a write to Downloads is refused with the note", W(os.path.join(home, "Downloads", "x.txt")), res, "deny", m_away, "morning report"),
        ("Unattended: a blocked read is refused as before", ("Read", {"file_path": os.path.join(private, "report.pdf")}), res, "deny", m_away, ask_p),
        ("Attended (1): a write to Downloads asks", W(os.path.join(home, "Downloads", "x.txt")), res, "ask", m_here),
        ("Variable absent: a write to Downloads asks", W(os.path.join(home, "Downloads", "x.txt")), res, "ask", m),
        ("git: push --force to main", B("git push --force origin main"), res, "deny"),
        ("git: push --force-with-lease to HEAD:main", B("git push --force-with-lease origin HEAD:main"), wt, "deny"),
        ("git: push -f on the main checkout (branch read from HEAD)", B("git push -f"), res, "deny"),
        ("git: push -f in a worktree on its own branch", B("git push -f origin HEAD"), wt, "pass"),
        ("git: push +main", B("git push origin +main"), res, "deny"),
        ("git: force push of a feature branch passes", B("git push --force-with-lease origin feature-x"), res, "pass"),
        ("git: an ordinary push to main passes", B("git push origin HEAD:main"), wt, "pass"),
        ("git: reset --hard", B("git reset --hard HEAD~1"), res, "deny"),
        ("git: reset --hard through -C", P(f'git -C "{res}" reset --hard'), wt, "deny"),
        ("git: clean -fd", B("git clean -fd"), res, "deny"),
        ("git: clean -n (a dry run) passes", B("git clean -n"), res, "pass"),
        ("git: branch -D", B("git branch -D feature-x"), res, "deny"),
        ("git: branch -d main", B("git branch -d main"), res, "deny"),
        ("git: branch -d of another branch asks", B("git branch -d feature-x"), res, "ask"),
        ("git: push --delete main", B("git push origin --delete main"), res, "deny"),
        ("git: push --delete of another branch asks", B("git push origin --delete feature-x"), res, "ask"),
        ("git: push :branch asks", B("git push origin :feature-x"), res, "ask"),
        ("git: checkout -- .", B("git checkout -- ."), res, "deny"),
        ("git: restore .", B("git restore ."), res, "deny"),
        ("git: restore --staged . passes", B("git restore --staged ."), res, "pass"),
        ("git: checkout -- one file passes", B("git checkout -- src/a.py"), res, "pass"),
        ("git: a commit message that names the rules passes", B('git commit -m "Refuse git reset --hard and git clean"'), res, "pass"),
        ("git: unattended branch deletion is refused", B("git branch -d feature-x"), res, "deny", m_away, "morning report"),
    ]
    failed += _run_cases(third, m)
    total += len(third)

    print(f"\n{total - failed} of {total} checks passed ({len(first) + len(proto) + 2} in part 1, {len(second)} in part 2, "
          f"{len(third)} in part 3)." + (" The guard's logic works on this computer." if not failed else ""))
    return 1 if failed else 0


def main():
    if "--self-test" in sys.argv[1:]:
        return self_test()
    if "--show-config" in sys.argv[1:]:
        return show_config()
    return run_hook(sys.stdin.read(), build_config(), sys.stdout, sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
