#!/usr/bin/env python3
"""Guard hook for Claude Code: protect the originals, keep the agent's writes inside your roots and
its reads out of the part of a cloud drive you keep online only and out of secrets files, and refuse
the git commands that lose work.

Claude Code runs this script before every file edit, every shell command, every read (Read, Glob,
Grep) and, if you register them, every note write through a notes connector (the setting is in
settings.example.json next to this file). It receives the planned tool call as JSON on its input
and gives one of three verdicts:

    deny   the call would change an original (a folder listed in IMMUTABLE), read a file in a
           blocked folder (READ_BLOCKED) or a secrets file (SECRETS), or run a git command that
           loses work. Exit code 2: the call is refused and the reason is shown to the agent, which
           then explains and proposes another way. No setting and no answer of yours lets it through.
    ask    the call would write outside your roots and outside any grant, or delete a remote branch.
           Claude Code shows you a permission prompt. In auto mode the prompt decides, not the
           auto-mode classifier.
    pass   everything else. The script stays silent and Claude Code's own permission settings decide,
           exactly as if the guard were not there.

The rules, as the configuration block below sets them:

| What | Verdict |
|---|---|
| a folder of originals, "deposit-only" (raw data, transcripts) | a new file or folder passes; changing, overwriting, moving or deleting one is refused |
| a filed transcript in `meeting-transcripts/` | the one change it takes: an Edit or Write that touches only its corrections block (at the top, or the very end) passes |
| a folder of originals, "never" (a staging folder that only you fill) | every write, move, copy or delete is refused |
| a folder of originals, "existing-only" (an archive that a script fills) | changing a file in place and copying one out pass; a new file, a move or a delete is refused |
| writes inside the roots, ~/.claude, the temporary folder, the job's folder, a granted folder or file | pass |
| writes anywhere else | ask |
| reads inside a blocked folder (the cloud drive outside your data and notes roots) | refused, "ask the person for the file"; a granted folder or file passes |
| reading a secrets file (.env, .env.*, ~/.ssh, ~/.claude/.credentials.json, *.pem, *.key, *credentials*, *token*.json) | refused, "secrets are not for the model to read"; a script may still load it |
| git: force push to a protected branch, reset --hard, clean, branch -D, deleting a protected branch, checkout -- . and restore . | refused |
| git: branch -d (git itself refuses an unmerged branch), worktree remove | pass |
| git: deleting a remote branch, or a local one whose name the guard cannot read | ask |
| the keep-awake battery flag ~/.claude/keep-awake/pause | every call refused until power is back or the person says continue |

Inside the roots everything passes, recursive search included.

Reads are checked for Read, Glob and Grep, for the shell's readers and listers (cat, grep, sed, ls,
find, Get-Content, Get-ChildItem and their kin, a copy's source), for a recursive search started
above a blocked folder, for a cd, Set-Location or git -C into one, for any other command's argument
that names a place in one (pdftotext x.pdf, python script.py x), and for a path into one written in
code handed to an interpreter (python -c, a heredoc to python or node).

Shell commands are parsed the way the shell reads them (Bash for the Bash tool, PowerShell for the
PowerShell tool and for `pwsh -Command`): quotes, escapes, $( ), heredocs, script blocks and
redirections; variables from the environment and from assignments earlier in the same command are
expanded; only a verb's path arguments and the redirect targets count as paths, so a quoted
message, a sed script or a grep pattern is never mistaken for one. The write scope is never
inspected in a -Command body or a heredoc; the folders of originals are also protected by a
substring scan over the whole text (section "the substring backstop").

A grant widens the roots for one job or one session: a small JSON file that the session writes only
after you approved a plan, or pointed to a folder or file yourself (guide 04,
write-scope.example.json; `--grant` writes it). A folder (an entry ending in /, one that exists as a
folder, or one without an extension that does not exist yet) opens everything below it; a file
opens that file alone; the same for `read` and `write`. A write grant may also be read. An expired
grant grants nothing, and no grant opens a folder of originals or a secrets file.

Two situations change the verdicts (guide 04):

    nobody at the keyboard   in a background job (CLAUDE_CODE_SESSION_ATTENDED=0, observed, not
                             documented) an "ask" becomes a refusal with a note for the morning
                             report, so the job goes on with other work instead of waiting.
    battery pause            while the keep-awake skill's battery watch has written its pause flag
                             (on battery at 20 % or less), every call the guard sees is refused with
                             "paused: battery at N %, connect power or say continue". Power back, or
                             the continue file, ends the pause.

What the guard cannot see: a script that writes or reads files itself (`python make_figures.py`) is
one shell command to the guard; only the paths on the command line, and literal blocked paths in
inline code, are checked. A word whose start the guard cannot know (`"$X/file"` with X unknown) is no
path; one with a known folder before the unknown part counts as that folder. `grep -r` in a folder
that holds a .env reads it unseen. The guard is a net under the rules, not a sandbox; Claude Code's
permission prompts and, in auto mode, its classifier are the second net, and on macOS, Linux and
WSL2 Claude Code's own sandbox is the stronger one (guide 04).

Set the configuration block below, then check it:
    python guard.py --show-config     the resolved roots, folders, secrets, grants and branches
    python guard.py --self-test       about 220 synthetic tool calls against a temporary folder tree
    python guard.py --grant read|write PATH... [--hours N] [--plan TEXT]   record a grant
Test one call by hand (bash); a refusal prints the reason and exits with 2:
    echo '{"tool_name":"Edit","tool_input":{"file_path":"<an original>"}}' | python guard.py; echo "exit $?"

Standard library only; Python 3.8 or later.

Derived from guard_raw.py in Kevin Michael Smith's ai-research-starter-kit
(https://github.com/KevinMSmith/ai-research-starter-kit), Copyright (c) 2026 Kevin Michael Smith, MIT
licence, by way of the author's own guard for immutable folders; the write scope, the grants, the
read block, the secrets rule, the git guardrails, the shell parser and the self-test are added.
Copyright (c) 2026 Johannes Wildfeuer, MIT licence (see LICENSE.md).
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
         "a transcript is kept as recorded; correct names and errors in the meeting note, and list "
         "the misheard names in the corrections block at the top of the transcript, the one change "
         "it takes"),
        # Two examples for a notes vault; remove the # and use your own folder names:
        # (notes + "/<inbox>/_later", "never", "it is the person's staging area and is never touched"),
        # (notes + "/<agent outputs>/Archive", "existing-only",
        #  "notes reach the archive only through the archive script; write new notes on top"),
        # Deposit folders for the sources notes are built on (mail as received, partner documents):
        # (data + "/mail", "deposit-only", "a filed mail is kept as received, because notes cite it"),
        # (data + "/sources", "deposit-only", "a source document is kept as received"),
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


def secrets_for(home):
    """Files whose content is not for the model (point 3 of a review of this kit, November 2026).

    names    patterns on the file name, matched without regard to case
    except   names that look like a secret but are the committed, value-free templates
    folders  everything below them; files: exact paths
    Reading them through Read, Grep or a shell reader (cat, Get-Content, a copy's source) is refused.
    A process may still load them: python-dotenv reads .env inside the script, out of the guard's
    sight, and that is the intended route. Listing names (Glob, ls of a folder) is not refused,
    except inside a secrets folder. No grant opens them.
    """
    return {
        "names": [".env", ".env.*", "*.pem", "*.key", "*credentials*", "*token*.json"],
        "except": [".env.example", ".env.sample", ".env.template", ".env.dist"],
        "folders": [home + "/.ssh"],
        "files": [home + "/.claude/.credentials.json"],
    }


SECRETS_REASON = ("secrets are not for the model to read; a script may load them itself (python-dotenv "
                  "reads .env inside the process), but their content never goes through a tool call")


WRITABLE = writable_for(CODE_ROOT, DATA_ROOT, NOTES_ROOT)
IMMUTABLE = immutable_for(DATA_ROOT, NOTES_ROOT)
READ_BLOCKED = read_blocked_for(CLOUD_ROOT, DATA_ROOT, NOTES_ROOT)
SECRETS = secrets_for("~")

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
                 unattended=None, pause_flag=None, continue_file=None, secrets=None):
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
    (cfg["granted"], cfg["granted_files"], cfg["read_exact"], cfg["read_tree"],
     cfg["grant_notes"]) = load_grants(files, cwd)
    s = SECRETS if secrets is None else secrets
    cfg["secret_names"] = [x.lower() for x in s.get("names", [])]
    cfg["secret_except"] = {x.lower() for x in s.get("except", [])}
    cfg["secret_dirs"] = [norm(e, cwd) for e in (expand(x) for x in s.get("folders", [])) if e]
    cfg["secret_files"] = [norm(e, cwd) for e in (expand(x) for x in s.get("files", [])) if e]
    return cfg


def grant_entry(raw, cwd):
    """(path, is_folder) for one grant entry; None when it does not resolve.

    A folder is an entry ending in / or \\ or /**, or one that exists as a folder, or a path that
    does not exist yet and has no extension. Anything else is one file. A folder opens everything
    below it; a file opens that file alone, for reading and for saving alike.
    """
    s = str(raw).strip()
    folder = bool(re.search(r"([\\/]\*\*|[\\/])$", s))
    s = re.sub(r"[\\/]\*\*$", "", s)
    s = s.rstrip("\\/") or s
    e = expand(s)
    if not e:
        return None
    p = norm(e, cwd)
    if not folder:
        folder = os.path.isdir(p) or (not os.path.exists(p) and not os.path.splitext(p)[1])
    return p, folder


def load_grants(files, cwd):
    """Folders and files granted by approved plans. An expired or unreadable grant grants nothing."""
    write, write_files, exact, tree, notes = [], [], [], [], []
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
            entry = grant_entry(w, cwd)
            if entry:
                (write if entry[1] else write_files).append(entry[0])
        for r in g.get("read", []) or []:
            entry = grant_entry(r, cwd)
            if entry:
                (tree if entry[1] else exact).append(entry[0])
        notes.append(f"{f}: grants {len(g.get('write', []) or [])} path(s) to write and "
                     f"{len(g.get('read', []) or [])} path(s) to read" + (f" until {exp}" if exp else ""))
    return write, write_files, exact, tree, notes


def default_grant_file():
    """Where --grant writes: the job folder's file in a background job, else the project's."""
    job = os.environ.get("CLAUDE_JOB_DIR")
    if job:
        return os.path.join(job, "write-scope.json")
    return os.path.join(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(), ".claude", "write-scope.local.json")


def write_grant(path, kind, entries, hours=12.0, plan="", now=None):
    """Add read or write entries to a grant file; returns the file's new content.

    One expiry per file: the later of the one on file and now + hours. An expired or unreadable file
    is started afresh, so an old grant never comes back to life. An existing folder is written with
    a trailing / so the entry says what it opens.
    """
    now = now or datetime.now()
    g = {}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8-sig") as fh:
                g = json.load(fh)
            if not isinstance(g, dict) or datetime.fromisoformat(str(g.get("expires"))) < now:
                g = {}
        except (OSError, ValueError, TypeError):
            g = {}
    expires = now + timedelta(hours=hours)
    if g.get("expires"):
        expires = max(expires, datetime.fromisoformat(str(g["expires"])))
    items = list(g.get(kind, []) or [])
    for e in entries:
        e = str(e).replace("\\", "/")
        if os.path.isdir(expand(e) or "") and not e.endswith("/"):
            e += "/"
        if e not in items:
            items.append(e)
    g[kind] = items
    g["expires"] = expires.isoformat(timespec="minutes")
    g["approved"] = g.get("approved") or now.isoformat(timespec="minutes")
    if plan:
        g["plan"] = plan
    g.setdefault("plan", "pointed to by the person in the session")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(g, fh, indent=1)
    return g


def grant_cli(argv):
    """--grant read|write PATH... [--hours N] [--plan TEXT] [--file F]: record what the person pointed to."""
    args = argv[argv.index("--grant") + 1:]
    if not args or args[0] not in ("read", "write"):
        print("usage: --grant read|write PATH... [--hours 12] [--plan TEXT] [--file GRANT.json]")
        return 2
    kind, rest, opts = args[0], [], {"--hours": "12", "--plan": "", "--file": default_grant_file()}
    i = 1
    while i < len(args):
        if args[i] in opts and i + 1 < len(args):
            opts[args[i]] = args[i + 1]
            i += 2
        else:
            rest.append(args[i])
            i += 1
    if not rest:
        print("name at least one path")
        return 2
    g = write_grant(opts["--file"], kind, rest, float(opts["--hours"]), opts["--plan"])
    print(f"{opts['--file']}: {kind} {', '.join(g[kind])} until {g['expires']}")
    return 0


# ------------------------------------------------------------------------------- the decision

# A deposit is any new file or folder (a copy in, a download, a redirect or mkdir to a name not yet
# there); a copy out of the archive is a read. That is how transcripts and mails get filed:
# `T=...; mkdir -p "$T" && cp x "$T/"`, which the parser resolves.
ALLOWED_OPS = {"never": set(), "deposit-only": {"create", "create-other", "copy-out"},
               "existing-only": {"modify", "copy-out"}}


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


# The one change a filed transcript takes (12 November 2026): a corrections block that tells the next
# reader which names the speech-to-text got wrong, so the corrections travel with the file. It runs
# from a line starting "NOTE CORRECTIONS" to the line "NOTE END CORRECTIONS", sits at the top (after
# the WEBVTT line and its blank line in a .vtt) or at the very end, set apart by a blank line, and
# holds no blank line and no "-->", so a .vtt stays valid: players read the block as a comment.
CORRECTABLE_FOLDER = "meeting-transcripts"
CORRECTIONS_START, CORRECTIONS_END = "NOTE CORRECTIONS", "NOTE END CORRECTIONS"


def without_corrections(text):
    """The text with its corrections block and the blank lines setting it apart taken out (the text
    itself when it has none), or None when the block is malformed: markers unpaired or repeated, a
    blank line or "-->" inside, or the block anywhere but the top or the very end."""
    lines = text.replace("\r\n", "\n").split("\n")
    starts = [i for i, s in enumerate(lines) if s.startswith(CORRECTIONS_START)]
    ends = [i for i, s in enumerate(lines) if s.rstrip() == CORRECTIONS_END]
    if not starts and not ends:
        return "\n".join(lines)
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        return None
    s, e = starts[0], ends[0]
    if any(not ln.strip() or "-->" in ln for ln in lines[s:e + 1]):
        return None
    before, after = lines[:s], lines[e + 1:]
    at_top = not before or (before[0].lstrip("﻿").startswith("WEBVTT")
                            and all(not ln.strip() for ln in before[1:]))
    if at_top:
        while after and not after[0].strip():
            after = after[1:]
        return "\n".join(before + after)
    if all(not ln.strip() for ln in after):
        while before and not before[-1].strip():
            before = before[:-1]
        return "\n".join(before)
    return None


def corrections_only(tool, ti, p, cfg):
    """True when a Write or Edit on a filed transcript leaves everything outside its corrections block
    as it was (line endings and trailing newlines aside); False for any other folder or change."""
    hit = immutable_hit(p, cfg)
    if not hit or parts(hit[0])[-1] != CORRECTABLE_FOLDER or tool not in ("Write", "Edit"):
        return False
    try:
        with open(p, encoding="utf-8") as fh:
            old = fh.read()
    except (OSError, UnicodeDecodeError):
        return False
    if tool == "Write":
        new = str(ti.get("content") or "")
    else:
        find = str(ti.get("old_string") or "").replace("\r\n", "\n")
        repl = str(ti.get("new_string") or "").replace("\r\n", "\n")
        count = old.count(find) if find else 0
        if not count or (count > 1 and not ti.get("replace_all")):
            return False  # the Edit tool itself would fail, so there is nothing to verify
        new = old.replace(find, repl) if ti.get("replace_all") else old.replace(find, repl, 1)
    a, b = without_corrections(old), without_corrections(new)
    return a is not None and b is not None and a.rstrip("\n") == b.rstrip("\n")


def scope(p, cfg):
    if any(within(p, r) for r in cfg["writable"] + cfg["granted"]) or p in cfg["granted_files"]:
        return cfg["inside"], ""
    return cfg["outside"], (
        f"`{p}` is outside the folders this setup writes to without asking. For a job that runs while "
        f"you are away, the plan names such folders and the session writes a grant before the job "
        f"starts (guide 04).")


CODE_EXTENSIONS = {".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".r", ".rs", ".go", ".java",
                   ".cs", ".ps1", ".psm1", ".sh", ".bash", ".html", ".css", ".c", ".h", ".cpp", ".rb", ".php", ".sql"}


def secret_refusal(p, cfg):
    """The refusal text when p is a secrets file or lies in a secrets folder; None otherwise.
    Source code is no secret by its name: a credentials.py handles credentials and holds none."""
    name = os.path.basename(p).lower()
    if name in cfg["secret_except"]:
        return None
    if os.path.splitext(name)[1] in CODE_EXTENSIONS and not any(within(p, d) for d in cfg["secret_dirs"]):
        return None
    if (p in cfg["secret_files"] or any(within(p, d) for d in cfg["secret_dirs"])
            or any(fnmatch.fnmatchcase(name, pat) for pat in cfg["secret_names"])):
        return f"{SECRETS_REASON}. (`{p}`)"
    return None


def read_refusal(p, cfg, recursive=False, content=True):
    """The refusal text when reading p (or searching it recursively) is blocked; None otherwise.

    content=False for a call that only lists names (Glob): a secrets file's name may be seen.
    """
    secret = secret_refusal(p, cfg)
    if secret and (content or any(within(p, d) for d in cfg["secret_dirs"])):
        return secret
    return blocked_refusal(p, cfg, recursive)


def blocked_refusal(p, cfg, recursive=False):
    """The read block alone (READ_BLOCKED), without the secrets rule."""
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
    return (p in cfg["read_exact"] or p in cfg["granted_files"] or any(within(p, t) for t in cfg["read_tree"])
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
        if refusal and exists and corrections_only(tool, ti, p, cfg):
            refusal = None
        if refusal:
            return "deny", refusal
        return scope(p, cfg)
    if tool in READ_TOOLS:
        return decide_read_tool(tool, ti, cwd, cfg)
    if tool in SHELL_TOOLS:
        return decide_shell(ti.get("command", "") or "", cwd, cfg, "ps" if tool == "PowerShell" else "bash")
    prefix = cfg["note_prefix"]
    if prefix and tool.startswith(prefix):
        return decide_note(tool[len(prefix):], ti, cfg)
    return "pass", ""


def decide_read_tool(tool, ti, cwd, cfg):
    if tool == "Read":
        raw = ti.get("file_path") or ""
        refusal = read_refusal(norm(raw, cwd), cfg) if raw else None
    elif tool == "Glob":
        base = norm(ti.get("path") or cwd, cwd)
        pattern = str(ti.get("pattern") or "")
        prefix = literal_prefix(pattern)
        target = norm(prefix, base) if prefix else base
        refusal = read_refusal(target, cfg, recursive="**" in pattern, content=False)
    else:  # Grep searches a folder recursively (hidden and gitignored files skipped), or one file
        refusal = read_refusal(norm(ti.get("path") or cwd, cwd), cfg, recursive=True)
    return ("deny", refusal) if refusal else ("pass", "")


def decide_note(action, ti, cfg):
    if action not in NOTE_TOOL_WRITES or not cfg["notes_root"]:
        return "pass", ""
    for key in NOTE_PATH_KEYS:
        val = ti.get(key)
        if not isinstance(val, str) or not val:
            continue
        if key != "path" and val.endswith(("/", "\\")) and isinstance(ti.get("path"), str):
            # An Obsidian connector reads a trailing slash as "into this folder, keeping the file name"; the
            # folder itself exists, so checked as written a move into a deposit folder counted as a change to it.
            val += os.path.basename(ti["path"].replace("\\", "/"))
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


# ------------------------------------------------------------------------------- the shell, parsed
#
# A command is read the way its shell reads it: quotes, escapes, $( ), backticks, heredocs and
# here-strings, PowerShell script blocks and subexpressions, redirections. Each simple command is
# classified by its verb, and only that verb's path arguments and the redirect targets count as
# paths, so a quoted message, a sed script, a grep pattern or a line of a heredoc is never taken
# for one (the faults of the pattern match it replaces, November 2026). Levels:
#
#   top    the command itself, with its $( ), backtick and subshell parts: every rule applies
#   body   the code of `pwsh -Command`, `bash -c`, and a heredoc fed to a shell: reads, the immutable
#          folders and git apply, the write scope does not (it is never inspected there)
#   data   a heredoc or here-string fed to anything else is not parsed. The immutable folders still
#          match by substring over the whole text (legacy_immutable below), and code fed to an
#          interpreter (python -c, a heredoc to python or node) is searched for paths into the read
#          block.
#
# A word counts as a path only when it expands fully (~, $VAR, ${VAR}, $env:VAR, %VAR% from the
# environment or an assignment earlier in the same command) and resolves under a drive that exists,
# with no colon or quote left in it; for the write scope it must also exist or be creatable (its
# folder exists). A word the guard cannot expand is no path: the substring backstop is the net there.

LIT = "\x01"    # a $ that was quoted literally ('...', \$): never expanded
SUBST = "\x02"  # the place of a $( ), backtick or script block: its value is unknown


class Simple:
    """One simple command: its words (quotes removed), redirections and heredoc bodies."""
    __slots__ = ("words", "redirects", "heredocs", "level", "shell")

    def __init__(self, level, shell):
        self.words, self.redirects, self.heredocs = [], [], []
        self.level, self.shell = level, shell


class _Lexer:
    def __init__(self, src, level, out):
        self.s, self.i, self.level, self.out, self.pending = src, 0, level, out, []

    def at(self, k=0):
        j = self.i + k
        return self.s[j] if 0 <= j < len(self.s) else ""

    def skip_line(self):
        while self.i < len(self.s) and self.s[self.i] != "\n":
            self.i += 1


class BashLexer(_Lexer):
    STOP = set(" \t\r\n;&|()<>")

    def parse_list(self, closer=""):
        cur = None
        while self.i < len(self.s):
            c = self.s[self.i]
            if closer and c == closer:
                self.i += 1
                return
            if c in " \t\r":
                self.i += 1
            elif c == "\\" and self.at(1) == "\n":
                self.i += 2
            elif c == "\n":
                self.i += 1
                self.heredoc_bodies()
                cur = None
            elif c == "#" and (self.i == 0 or self.s[self.i - 1] in " \t\n;&|("):
                self.skip_line()
            elif c == "&" and self.at(1) == ">":
                cur = cur or self.new()
                self.redirect(cur)
            elif c in ";&|":
                while self.at() in (";", "&", "|"):
                    self.i += 1
                cur = None
            elif c == "(":
                if self.at(1) == "(":
                    self.skip_arith(2)
                else:
                    self.i += 1
                    self.parse_list(")")
                cur = None
            elif c == ")":
                self.i += 1
            elif c in "<>" or (c.isdigit() and re.match(r"\d+[<>]", self.s[self.i:])
                                and (cur is None or self.s[self.i - 1] in " \t")):
                cur = cur or self.new()
                self.redirect(cur)
            else:
                cur = cur or self.new()
                cur.words.append(self.word())

    def new(self):
        cur = Simple(self.level, "bash")
        self.out.append(cur)
        return cur

    def redirect(self, cur):
        m = re.match(r"\d*(&>>|&>|<<<|<<-|<<|>>|>&|<&|>\||<>|<\(|>\(|<|>)", self.s[self.i:])
        op = m.group(1)
        self.i += m.end()
        if op in ("<(", ">("):
            self.parse_list(")")
            return
        while self.at() in (" ", "\t"):
            self.i += 1
        w = self.word()
        if op in ("<<", "<<-"):
            self.pending.append((w.replace(LIT, "$"), op == "<<-", cur))
        elif op == "<<<" or (op in (">&", "<&") and re.fullmatch(r"\d*-?", w)):
            pass  # a here-string is data; >&2 duplicates a descriptor
        else:
            cur.redirects.append((op, w))

    def heredoc_bodies(self):
        for delim, strip_tabs, cur in self.pending:
            lines = []
            while self.i < len(self.s):
                j = self.s.find("\n", self.i)
                line = self.s[self.i:j if j >= 0 else len(self.s)]
                self.i = j + 1 if j >= 0 else len(self.s)
                if (line.lstrip("\t") if strip_tabs else line).rstrip("\r") == delim:
                    break
                lines.append(line)
            cur.heredocs.append("\n".join(lines))
        self.pending = []

    def skip_arith(self, start):
        self.i += start
        depth = 1
        while self.i < len(self.s) and depth:
            if self.s.startswith("((", self.i):
                depth, self.i = depth + 1, self.i + 2
            elif self.s.startswith("))", self.i):
                depth, self.i = depth - 1, self.i + 2
            else:
                self.i += 1

    def backtick(self):
        j = self.i
        while j < len(self.s) and self.s[j] != "`":
            j += 2 if self.s[j] == "\\" else 1
        BashLexer(self.s[self.i:j], self.level, self.out).parse_list()
        self.i = j + 1

    def word(self):
        buf = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in self.STOP:
                break
            if c == "\\":
                if self.at(1) != "\n":
                    buf.append(LIT if self.at(1) == "$" else self.at(1))
                self.i += 2
            elif c == "'":
                j = self.s.find("'", self.i + 1)
                j = len(self.s) if j < 0 else j
                buf.append(self.s[self.i + 1:j].replace("$", LIT))
                self.i = j + 1
            elif c == "$" and self.at(1) == "'":
                j = self.i + 2
                while j < len(self.s) and self.s[j] != "'":
                    j += 2 if self.s[j] == "\\" else 1
                buf.append(self.s[self.i + 2:j].replace("$", LIT))
                self.i = j + 1
            elif c == '"':
                self.i += 1
                buf.append(self.dquoted())
            else:
                buf.append(self.dollar_or_char(c))
        return "".join(buf)

    def dollar_or_char(self, c):
        if c == "$" and self.at(1) == "(":
            if self.at(2) == "(":
                self.skip_arith(3)
            else:
                self.i += 2
                self.parse_list(")")
            return SUBST
        if c == "`":
            self.i += 1
            self.backtick()
            return SUBST
        if c == "$" and self.at(1) == "{":
            j = self.s.find("}", self.i)
            j = len(self.s) - 1 if j < 0 else j
            text, self.i = self.s[self.i:j + 1], j + 1
            return text
        self.i += 1
        return c

    def dquoted(self):
        buf = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                break
            if c == "\\" and self.at(1) in '"\\$`\n':
                if self.at(1) != "\n":
                    buf.append(LIT if self.at(1) == "$" else self.at(1))
                self.i += 2
            else:
                buf.append(self.dollar_or_char(c))
        return "".join(buf)


class PsLexer(_Lexer):
    STOP = set(" \t\r\n;|,(){}<>")

    def parse_list(self, closer=""):
        cur = None
        while self.i < len(self.s):
            c = self.s[self.i]
            if closer and c == closer:
                self.i += 1
                return
            if c in " \t\r,":
                self.i += 1
            elif c == "`" and self.at(1) in ("\n", "\r"):
                self.i += 2
            elif c in "\n;":
                self.i += 1
                cur = None
            elif c == "|" or (c == "&" and self.at(1) == "&"):
                self.i += 2 if self.at(1) in ("|", "&") else 1
                cur = None
            elif self.s.startswith("<#", self.i):
                j = self.s.find("#>", self.i)
                self.i = len(self.s) if j < 0 else j + 2
            elif c == "#":
                self.skip_line()
            elif c in "({":
                self.i += 1
                self.parse_list(")" if c == "(" else "}")
                if cur is not None:
                    cur.words.append(SUBST)
            elif c in ")}":
                self.i += 1
            elif c in "<>" or (c in "0123456789*" and self.at(1) == ">"):
                cur = cur or self.new()
                m = re.match(r"[\d*]?(>>|>)(&\d)?", self.s[self.i:])
                if not m:
                    self.i += 1
                    continue
                self.i += m.end()
                if not m.group(2):
                    while self.at() in (" ", "\t"):
                        self.i += 1
                    cur.redirects.append((m.group(1), self.word()))
            else:
                cur = cur or self.new()
                cur.words.append(self.word())

    def new(self):
        cur = Simple(self.level, "ps")
        self.out.append(cur)
        return cur

    def here_string(self, quote):
        end = "\n" + quote + "@"
        j = self.s.find(end, self.i)
        self.i = len(self.s) if j < 0 else j + len(end)
        return SUBST  # a here-string is a value, never a path

    def word(self):
        buf = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == "@" and self.at(1) in ("'", '"') and re.match(r"@['\"][ \t]*\r?\n", self.s[self.i:]):
                q = self.at(1)
                self.i += 2
                buf.append(self.here_string(q))
            elif c in "$@" and self.at(1) in ("(", "{") and not (c == "$" and self.at(1) == "{"):
                self.i += 2
                self.parse_list(")" if self.s[self.i - 1] == "(" else "}")
                buf.append(SUBST)
            elif c == "$" and self.at(1) == "{":
                j = self.s.find("}", self.i)
                j = len(self.s) - 1 if j < 0 else j
                buf.append(self.s[self.i:j + 1])
                self.i = j + 1
            elif c in self.STOP:
                break
            elif c == "`":
                buf.append(LIT if self.at(1) == "$" else self.at(1))
                self.i += 2
            elif c == "'":
                self.i += 1
                part = []
                while self.i < len(self.s):
                    if self.s[self.i] == "'" and self.at(1) == "'":
                        part.append("'")
                        self.i += 2
                    elif self.s[self.i] == "'":
                        self.i += 1
                        break
                    else:
                        part.append(self.s[self.i])
                        self.i += 1
                buf.append("".join(part).replace("$", LIT))
            elif c == '"':
                self.i += 1
                buf.append(self.dquoted())
            else:
                buf.append(c)
                self.i += 1
        return "".join(buf)

    def dquoted(self):
        buf = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == '"' and self.at(1) == '"':
                buf.append('"')
                self.i += 2
            elif c == '"':
                self.i += 1
                break
            elif c == "`":
                buf.append(LIT if self.at(1) == "$" else self.at(1))
                self.i += 2
            elif c == "$" and self.at(1) == "(":
                self.i += 2
                self.parse_list(")")
                buf.append(SUBST)
            else:
                buf.append(c)
                self.i += 1
        return "".join(buf)


def parse(src, shell, level):
    """The simple commands of src, in the order they appear (nested ones included)."""
    out = []
    lexer = (PsLexer if shell == "ps" else BashLexer)(src, level, out)
    try:
        lexer.parse_list()
        if shell != "ps":
            lexer.heredoc_bodies()
    except (IndexError, AttributeError, RecursionError):
        pass  # a construct the lexer does not follow: what was read stands, the backstop covers the rest
    return out


# ------------------------------------------------------------------------------- words to paths

_VAR = re.compile(r"\$\{env:(\w+)\}|\$env:(\w+)|\$\{(\w+)\}|\$(\w+)|%(\w+)%", re.IGNORECASE)
_UNSET = object()
UNKNOWN = "\x03"  # the place of a part the guard cannot know, inside an Unknown word


class Unknown(str):
    """A word with a part the guard cannot know (a loop variable, $(date), $1), marked by UNKNOWN.
    It is no path; its known folder (the part before the unknown one) may be."""


def expand_word(w, state):
    """The word with ~ and its variables expanded; an Unknown when a part cannot be known."""
    if w is None:
        return None
    unknown = [SUBST in w]
    w = w.replace(SUBST, UNKNOWN)
    vars_, ps = state["vars"], state["shell"] == "ps"

    def rep(m):
        env_name, name = m.group(1) or m.group(2) or m.group(5), m.group(3) or m.group(4)
        if env_name:
            val = os.environ.get(env_name)
        else:
            key = name.lower() if ps else name
            val = vars_.get(key, _UNSET)
            if val is _UNSET:
                if name.upper() in ("HOME", "USERPROFILE") and not os.environ.get(name):
                    val = os.path.expanduser("~")
                elif name.upper() == "PWD":
                    val = state["cwd"]
                else:
                    val = os.environ.get(name)
        if val is None or isinstance(val, Unknown):
            unknown[0] = True
        return UNKNOWN if val is None else val

    out = _VAR.sub(rep, w)
    if "$" in out:  # $1, $?, $@ and the like
        out, unknown[0] = re.sub(r"\$[^\w]?\w*", UNKNOWN, out), True
    out = out.replace(LIT, "$")
    if out == "~" or out.startswith(("~/", "~\\")):
        out = os.path.expanduser("~") + out[1:]
    return Unknown(out) if unknown[0] or UNKNOWN in out else out


def shown(w):
    """A word as the agent should see it in a reason: an unknown part as $?."""
    return (w or "").replace(UNKNOWN, "$?")


def known_folder(t, state):
    """For an Unknown word, the folder written before its unknown part (/c/tmp/out/all-$site.log
    gives /c/tmp/out); None when nothing before it names a folder."""
    if not isinstance(t, Unknown):
        return None
    head = t[:t.find(UNKNOWN)]
    cut = max(head.rfind("/"), head.rfind("\\"))
    if cut < 0:
        return None
    return to_path(head[:cut + 1] if cut == 0 or head[cut - 1:cut] == ":" else head[:cut], state)


_GIT_ROOT = []


def git_root():
    """The folder Git Bash calls /, for a path such as /usr/bin."""
    if not _GIT_ROOT:
        g = shutil.which("git")
        _GIT_ROOT.append(os.path.dirname(os.path.dirname(g)) if g else "C:/Program Files/Git")
    return _GIT_ROOT[0]


def to_path(t, state):
    """An absolute, case-normalised path for an expanded word; None when it is not a path."""
    cwd = state["cwd"]
    if t is None or isinstance(t, Unknown) or UNKNOWN in t:
        return None
    t = t.strip()
    if not t or t.lower() in SINKS or t in ("-", "--"):
        return None
    if re.match(r"^[A-Za-z][\w+.\-]*://", t) or re.match(r"^[A-Za-z]{2,}:", t):
        return None  # a URL, or a PowerShell drive such as Env: or HKCU:
    if os.name == "nt":
        m = re.match(r"^/([a-zA-Z])(/.*|$)", t)
        if m:
            t = m.group(1) + ":" + (m.group(2) or "/")
        elif t == "/tmp" or t.startswith("/tmp/"):
            t = tempfile.gettempdir() + t[4:]
        elif t.startswith(("/dev/", "/proc/")):
            return None
        elif t.startswith("/") and not t.startswith("//"):
            t = (git_root() if state["shell"] != "ps" else os.path.splitdrive(cwd or "C:")[0]) + t
    elif t.startswith(("/dev/", "/proc/")):
        return None
    rest = t[2:] if re.match(r"^[A-Za-z]:", t) else t
    if os.name == "nt" and (":" in rest or any(ch in rest for ch in '<>"|\x00')):
        return None
    if any(ch in t for ch in "*?"):
        t = literal_prefix(t.replace("\\", "/")) or "."
    if not os.path.isabs(t) and not re.match(r"^[A-Za-z]:", t):
        if not cwd:
            return None
        t = os.path.join(cwd, t)
    p = os.path.normcase(os.path.normpath(t))
    if os.name == "nt":
        drive = os.path.splitdrive(p)[0]
        if not drive or not os.path.exists(drive + os.sep):
            return None
    return p


def creatable(p, ancestors=False):
    """The path exists, or a single create makes it (its folder exists); any existing ancestor will do
    for mkdir -p and New-Item, which create the folders between."""
    if os.path.exists(p) or os.path.isdir(os.path.dirname(p)):
        return True
    if ancestors:
        d = os.path.dirname(p)
        while d and d != os.path.dirname(d):
            if os.path.isdir(d):
                return True
            d = os.path.dirname(d)
    return False


# ------------------------------------------------------------------------------- verbs

SHELL_KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "for", "in", "case",
                  "esac", "function", "select", "!", "{", "}", "time"}
PS_KEYWORDS = {"if", "elseif", "else", "foreach", "for", "while", "do", "until", "switch", "try", "catch",
               "finally", "function", "filter", "param", "return", "throw", "trap", "begin", "process",
               "end", "break", "continue", "exit", "class", "using"}
WRAPPERS = {"sudo": (), "command": (), "builtin": (), "exec": (), "nohup": (), "winpty": (),
            "nice": ("-n",), "timeout": ("-s", "-k", "--signal", "--kill-after"), "stdbuf": ("-i", "-o", "-e")}
INTERPRETERS = {"python": ("-c",), "python3": ("-c",), "py": ("-c",), "pythonw": ("-c",), "uv": (),
                "node": ("-e", "--eval", "-p", "--print"), "deno": ("eval",), "rscript": ("-e",), "r": ("-e",),
                "ruby": ("-e",), "php": ("-r",)}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
POWERSHELLS = {"pwsh", "powershell"}

READERS = {  # verb: options that take a value
    "cat": (), "tac": (), "nl": (), "head": ("-n", "-c", "--lines", "--bytes"),
    "tail": ("-n", "-c", "--lines", "--bytes", "--pid", "-s"), "less": (), "more": (), "wc": (),
    "ls": ("-I", "--ignore", "-w", "--width", "--hide", "-T"), "dir": (), "vdir": (), "tree": ("-L", "-P", "-I"),
    "stat": ("-c", "--format"), "file": (), "du": ("-d", "--max-depth"), "sort": ("-k", "-t", "-S", "-T", "--key"),
    "uniq": ("-f", "-s", "-w"), "cut": ("-d", "-f", "-c", "-b"), "diff": ("-x", "-X", "-U", "-C"), "cmp": (),
    "comm": (), "paste": ("-d",), "column": ("-s", "-t"), "xxd": ("-l", "-s", "-c"), "od": ("-A", "-t", "-N", "-j"),
    "strings": ("-n",), "base64": (), "md5sum": (), "sha1sum": (), "sha256sum": (), "iconv": ("-f", "-t"),
    "jq": (), "yq": (),
}
ALWAYS_RECURSIVE = {"tree", "du", "rg", "ag", "ack", "find"}
LISTERS = {"ls", "dir", "vdir", "tree", "stat", "du", "file"}  # names and sizes, no content
ARGS_NOT_PATHS = {"echo", "printf", "gh", "git", "write-host", "write-output", "write-error", "test", "[", "[[",
                  "cd", "pushd", "chdir", "set-location", "sl", "push-location"}  # cd has its own rule
LISTS_CWD_VERBS = {"ls", "dir", "vdir", "tree", "du", "rg", "ag", "ack"}
GREPS = {"grep": ("-e", "-f", "-A", "-B", "-C", "-m", "-d", "-D", "--include", "--exclude", "--exclude-dir",
                  "--max-count", "--context", "--after-context", "--before-context", "--regexp", "--file",
                  "--label", "--color", "--colour", "--binary-files", "--devices", "--directories"),
         "rg": ("-e", "-f", "-A", "-B", "-C", "-m", "-g", "--glob", "-t", "--type", "-T", "--type-not", "-M",
                "--max-columns", "-j", "--threads", "--max-count", "--context", "--regexp", "--file", "-E",
                "--encoding", "--iglob", "--max-depth", "-d", "--sort", "--sortr", "--type-add", "-r", "--replace",
                "--color", "--colors", "--max-filesize", "--engine", "--pre", "--path-separator"),
         "ag": ("-G", "--file-search-regex", "-A", "-B", "-C", "-m", "--depth", "--ignore"),
         "ack": ("--type", "-A", "-B", "-C", "-m")}
GREPS["egrep"] = GREPS["fgrep"] = GREPS["grep"]
REMOVERS = {"rm": (), "unlink": (), "shred": ("-n", "-s"), "rmdir": ()}
MOVERS = {"mv": ("-t", "--target-directory", "-S", "--suffix"), "cp": ("-t", "--target-directory", "-S", "--suffix"),
          "ln": ("-t", "--target-directory", "-S", "--suffix"),
          "rsync": ("-e", "--rsh", "--exclude", "--include", "--filter", "-f", "--exclude-from", "--include-from",
                    "--files-from", "--log-file", "--password-file", "--chmod", "--chown", "-T", "--temp-dir",
                    "--backup-dir", "--compare-dest", "--copy-dest", "--link-dest", "--partial-dir")}
MAKERS = {"mkdir": ("-m", "--mode"), "touch": ("-d", "-t", "-r", "--date", "--reference"), "tee": (),
          "truncate": ("-s", "--size", "-r", "--reference")}

PS_ALIASES = {
    "rm": "remove-item", "del": "remove-item", "erase": "remove-item", "rd": "remove-item", "ri": "remove-item",
    "rmdir": "remove-item", "mv": "move-item", "move": "move-item", "mi": "move-item", "cp": "copy-item",
    "copy": "copy-item", "cpi": "copy-item", "ren": "rename-item", "rni": "rename-item", "ni": "new-item",
    "mkdir": "new-item", "md": "new-item", "sc": "set-content", "ac": "add-content", "clc": "clear-content",
    "cat": "get-content", "gc": "get-content", "type": "get-content", "ls": "get-childitem",
    "dir": "get-childitem", "gci": "get-childitem", "sls": "select-string", "ipcsv": "import-csv",
    "ii": "invoke-item", "gi": "get-item", "cd": "set-location", "sl": "set-location", "chdir": "set-location",
    "pushd": "push-location", "tee": "tee-object", "iwr": "invoke-webrequest", "irm": "invoke-restmethod",
    "epcsv": "export-csv",
}
# verb: (roles of the positional arguments, {parameter: role}, parameters that take a non-path value).
# Roles: read, remove, dest, write, create, newname, cd, value. The last positional role repeats.
PS_VERBS = {
    "remove-item": (["remove"], {"path": "remove", "literalpath": "remove"}, ("filter", "include", "exclude", "stream", "credential")),
    "move-item": (["remove", "dest"], {"path": "remove", "literalpath": "remove", "destination": "dest"}, ("filter", "include", "exclude", "credential")),
    "copy-item": (["read", "dest"], {"path": "read", "literalpath": "read", "destination": "dest"}, ("filter", "include", "exclude", "credential", "fromsession", "tosession")),
    "rename-item": (["remove", "newname"], {"path": "remove", "literalpath": "remove", "newname": "newname"}, ("credential",)),
    "new-item": (["create"], {"path": "create"}, ("itemtype", "type", "value", "target", "name", "credential")),
    "set-content": (["write", "value"], {"path": "write", "literalpath": "write"}, ("value", "encoding", "stream", "delimiter", "filter", "include", "exclude")),
    "add-content": (["write", "value"], {"path": "write", "literalpath": "write"}, ("value", "encoding", "stream", "delimiter", "filter", "include", "exclude")),
    "clear-content": (["write"], {"path": "write", "literalpath": "write"}, ("stream", "filter", "include", "exclude")),
    "out-file": (["write"], {"filepath": "write", "literalpath": "write", "path": "write"}, ("encoding", "width", "inputobject")),
    "tee-object": (["write"], {"filepath": "write", "literalpath": "write", "path": "write"}, ("variable", "inputobject", "encoding")),
    "export-csv": (["write"], {"path": "write", "literalpath": "write"}, ("delimiter", "encoding", "inputobject", "quotefields", "usequotes")),
    "export-clixml": (["write"], {"path": "write", "literalpath": "write"}, ("depth", "encoding", "inputobject")),
    "invoke-webrequest": (["value"], {"outfile": "write", "infile": "read"}, ("uri", "method", "body", "headers", "contenttype", "useragent", "timeoutsec", "headers", "credential", "websession", "sessionvariable", "maximumredirection")),
    "invoke-restmethod": (["value"], {"outfile": "write", "infile": "read"}, ("uri", "method", "body", "headers", "contenttype", "useragent", "timeoutsec", "credential", "websession", "sessionvariable")),
    "expand-archive": (["read", "dest"], {"path": "read", "literalpath": "read", "destinationpath": "dest"}, ()),
    "compress-archive": (["read", "dest"], {"path": "read", "literalpath": "read", "destinationpath": "dest"}, ("compressionlevel",)),
    "get-content": (["read"], {"path": "read", "literalpath": "read"}, ("totalcount", "head", "tail", "first", "last", "readcount", "encoding", "delimiter", "stream", "filter", "include", "exclude")),
    "get-childitem": (["read", "value"], {"path": "read", "literalpath": "read"}, ("filter", "include", "exclude", "depth", "attributes")),
    "select-string": (["value", "read"], {"path": "read", "literalpath": "read"}, ("pattern", "context", "encoding", "include", "exclude", "inputobject", "culture")),
    "get-item": (["read"], {"path": "read", "literalpath": "read"}, ("filter", "include", "exclude", "stream")),
    "invoke-item": (["read"], {"path": "read", "literalpath": "read"}, ("filter", "include", "exclude")),
    "get-filehash": (["read"], {"path": "read", "literalpath": "read"}, ("algorithm", "inputstream")),
    "format-hex": (["read"], {"path": "read", "literalpath": "read"}, ("encoding", "count", "offset")),
    "import-csv": (["read"], {"path": "read", "literalpath": "read"}, ("delimiter", "encoding", "header")),
    "import-clixml": (["read"], {"path": "read", "literalpath": "read"}, ()),
    "set-location": (["cd"], {"path": "cd", "literalpath": "cd"}, ("stackname",)),
    "push-location": (["cd"], {"path": "cd", "literalpath": "cd"}, ("stackname",)),
}
PS_SWITCHES = {"recurse", "force", "whatif", "confirm", "passthru", "nonewline", "append", "noclobber", "verbose",
               "debug", "file", "directory", "hidden", "readonly", "system", "raw", "asbytestream", "wait",
               "notypeinformation", "container", "casesensitive", "simplematch", "list", "quiet", "notmatch",
               "allmatches", "usebasicparsing", "followsymlink", "leaf", "parent", "resolve", "noprofile",
               "nologo", "noninteractive", "name", "allowclobber", "skipheadervalidation", "includetotalcount"}
PS_COMMON_VALUES = ("erroraction", "warningaction", "informationaction", "progressaction", "errorvariable",
                    "warningvariable", "informationvariable", "outvariable", "outbuffer", "pipelinevariable")
PS_REMOVE_FIND = {"rm", "rmdir", "unlink", "shred", "mv", "remove-item", "del"}


def verb_name(word):
    """The command's name as a lowercase basename without .exe."""
    if not word:
        return ""
    b = re.split(r"[\\/]", word.replace(LIT, "$"))[-1].lower()
    return b[:-4] if b.endswith(".exe") else b


def gnu_args(args, with_value=()):
    """(positionals, {option: [values]}) for a GNU-style command line; -- ends the options."""
    pos, opts, i, ended = [], {}, 0, False
    while i < len(args):
        a = args[i] or ""
        if ended or not a.startswith("-") or a == "-":
            pos.append(args[i])
        elif a == "--":
            ended = True
        elif a.startswith("--") and "=" in a:
            k, v = a.split("=", 1)
            opts.setdefault(k, []).append(v)
        elif a in with_value and i + 1 < len(args):
            opts.setdefault(a, []).append(args[i + 1])
            i += 1
        else:
            opts.setdefault(a, []).append(None)
        i += 1
    return pos, opts


def short_flags(opts):
    return set("".join(k[1:] for k in opts if re.fullmatch(r"-[A-Za-z]+", k)))


def ps_args(args, verb):
    """(positionals, {role: [words]}) for a PowerShell cmdlet call."""
    roles, params, values = PS_VERBS[verb]
    values = tuple(values) + PS_COMMON_VALUES
    known = list(params) + list(values) + sorted(PS_SWITCHES)
    pos, by_role, switches, i = [], {}, set(), 0
    while i < len(args):
        a = args[i] or ""
        m = re.fullmatch(r"-([A-Za-z][\w-]*)(:(.*))?", a)
        if not m:
            pos.append(args[i])
            i += 1
            continue
        name = m.group(1).lower()
        full = name if name in known else next((k for k in known if k.startswith(name)), name)
        value = m.group(3) if m.group(2) else None
        takes = full in params or (full in values and not (verb == "get-childitem" and full == "name"))
        if takes and value is None and i + 1 < len(args):
            value, i = args[i + 1], i + 1
        if full in params and value is not None:
            by_role.setdefault(params[full], []).append(value)
        elif takes:
            by_role.setdefault("value:" + full, []).append(value)
        else:
            switches.add(full)
        i += 1
    for n, w in enumerate(pos):
        role = roles[min(n, len(roles) - 1)]
        by_role.setdefault(role, []).append(w)
    return by_role, switches


def strip_prefix(words, shell, state):
    """The index of the verb: assignments, wrappers and keywords before it skipped; None for none."""
    i = 0
    while i < len(words):
        w = words[i]
        low = (w or "").lower()
        if shell == "bash" and re.fullmatch(r"[A-Za-z_]\w*=.*", w or "", re.S):
            i += 1
        elif shell == "bash" and low in SHELL_KEYWORDS:
            if low in ("for", "select", "case"):
                if low in ("for", "select") and i + 1 < len(words):
                    state["vars"][words[i + 1]] = None
                return None
            i += 1
        elif shell == "ps" and low in PS_KEYWORDS:
            return None
        elif low in ("&", "."):
            i += 1
        elif low == "env" and shell == "bash":
            i += 1
            while i < len(words) and ((words[i] or "").startswith("-") or "=" in (words[i] or "")):
                i += 2 if words[i] in ("-u", "-C", "--unset", "--chdir") else 1
        elif low in WRAPPERS and shell == "bash":
            i += 1
            while i < len(words) and (words[i] or "").startswith("-"):
                i += 2 if words[i] in WRAPPERS[low] else 1
            if low == "timeout" and i < len(words):
                i += 1
        elif low == "xargs":
            i += 1
            while i < len(words) and (words[i] or "").startswith("-"):
                i += 2 if words[i] in ("-I", "-n", "-P", "-d", "-E", "-L", "-s", "-a") else 1
        else:
            return i
    return None


def record_assignment(simple, state):
    """NAME=value (bash) or $name = value (PowerShell) on its own: remember the value for later words."""
    w = simple.words
    if simple.shell == "bash":
        start = 1 if w and w[0] in ("export", "local", "declare", "readonly", "typeset") else 0
        if w[start:] and all(re.fullmatch(r"[A-Za-z_]\w*=.*", x or "", re.S) for x in w[start:]):
            for x in w[start:]:
                k, v = x.split("=", 1)
                state["vars"][k] = expand_word(v, state)
            return True
        if w and w[0] == "read":
            for x in w[1:]:
                if re.fullmatch(r"[A-Za-z_]\w*", x or ""):
                    state["vars"][x] = None
        return False
    m = re.fullmatch(r"\$(env:)?(\w+)", w[0] or "", re.I) if w else None
    if m and len(w) >= 2 and w[1] in ("=", "+="):
        val = expand_word(w[2], state) if len(w) == 3 and w[1] == "=" else None
        if m.group(1):
            pass  # $env:X = ... changes the process environment; the guard keeps reading its own
        else:
            state["vars"][m.group(2).lower()] = val
        return True
    return False


def effects(simple, state):
    """What one simple command does, as (kind, ...) tuples:
    ("read", path, recursive) ("write", path, op, ancestors) ("git", cwd, sub, args, patterns)
    ("cd", path) ("body", shell, text) ("code", text)."""
    out = []
    shell = simple.shell
    P = lambda w: to_path(w, state)  # noqa: E731

    def reads(ws, rec=False, content=True):
        for w in ws:
            p = P(w)
            if p:
                out.append(("read", p, rec, content, False))
            elif known_folder(w, state):
                out.append(("read", known_folder(w, state), rec, False, True))

    def writes(ws, op=None, anc=False):
        """op None: create when the path is not there, modify when it is (a redirect, tee, Set-Content)."""
        for w in ws:
            p = P(w)
            if p:
                o = op or ("modify" if os.path.exists(p) else "create-other")
                out.append(("write", p, o, anc, False))
            elif known_folder(w, state):  # an unknown name in a known folder
                out.append(("write", known_folder(w, state), op, anc, True))

    def dests(ws):
        for w in ws:
            p = P(w)
            if p:
                out.append(("write", p, "create" if os.path.isdir(p) or not os.path.exists(p) else "modify", False, False))
            elif known_folder(w, state):
                out.append(("write", known_folder(w, state), None, False, True))

    for op, w in simple.redirects:
        w = expand_word(w, state)
        if op == "<":
            reads([w])
        else:
            writes([w])
    if record_assignment(simple, state):
        return out
    i = strip_prefix(simple.words, shell, state)
    if i is None:
        return out
    raw = simple.words[i:]
    verb = verb_name(raw[0])
    words = [expand_word(w, state) for w in raw]
    args = words[1:]
    if verb not in ARGS_NOT_PATHS:  # any argument that names a place in a blocked folder (pdftotext x.pdf)
        out.extend(("blocked-arg", p) for p in map(P, (a for a in args if not (a or "-").startswith("-"))) if p)

    if shell == "ps" and PS_ALIASES.get(verb, verb) in PS_VERBS:
        cmdlet = PS_ALIASES.get(verb, verb)
        by_role, switches = ps_args(args, cmdlet)
        rec = "recurse" in switches
        lists = cmdlet in ("get-childitem", "get-item", "copy-item", "expand-archive", "compress-archive")
        reads(by_role.get("read", []), rec, content=not lists)
        if cmdlet == "copy-item":
            for p in map(P, by_role.get("read", [])):
                if p:
                    out.append(("write", p, "copy-out", False, False))
        writes(by_role.get("remove", []), "remove")
        writes(by_role.get("write", []))
        names = [n for n in by_role.get("value:name", []) if n]
        creates = by_role.get("create", []) or ([state["cwd"]] if names and state["cwd"] else [])
        if names and not isinstance(names[0], Unknown):
            creates = [os.path.join(c, names[0]) if c and not isinstance(c, Unknown) else c for c in creates]
        writes(creates, anc=cmdlet == "new-item")
        dests(by_role.get("dest", []))
        for w in by_role.get("newname", []):
            src = next((P(x) for x in by_role.get("remove", []) if P(x)), None)
            if src and w and not isinstance(w, Unknown) and not re.search(r"[\\/]", w):
                out.append(("write", os.path.join(os.path.dirname(src), os.path.normcase(w)), "create", False, False))
        if cmdlet == "get-childitem" and not by_role.get("read") and state["cwd"]:
            out.append(("read", state["cwd"], rec, False, False))
        for w in by_role.get("cd", [])[:1]:
            out.append(("cd", P(w)))
        return out

    if verb in ("cd", "pushd", "chdir"):
        pos, _ = gnu_args(args)
        target = pos[0] if pos else os.path.expanduser("~")
        out.append(("cd", None if target is None else (state["cwd"] if target == "-" else P(target))))
    elif verb == "git":
        g = git_effect(words, state)
        if g[1] and g[1] != state["cwd"]:
            out.append(("blocked-arg", g[1]))  # git -C into the read block reads there
        out.append(g)
    elif verb in READERS:
        pos, opts = gnu_args(args, READERS[verb])
        flags = short_flags(opts)
        rec = verb in ALWAYS_RECURSIVE or (verb in ("ls", "diff") and ("R" in flags or "r" in flags or "--recursive" in opts))
        if verb == "jq" or verb == "yq":
            pos = pos[1:]
        if verb == "sort" and "-o" in opts:
            writes(opts["-o"])
        lists = verb in LISTERS
        if not pos and verb in LISTS_CWD_VERBS and state["cwd"]:
            out.append(("read", state["cwd"], rec, not lists, False))
        reads(pos, rec, content=not lists)
    elif verb in GREPS:
        pos, opts = gnu_args(args, GREPS[verb])
        flags = short_flags(opts)
        given = any(k in opts for k in ("-e", "-f", "--regexp", "--file"))
        if verb == "rg" and ("--files" in opts or "--type-list" in opts):
            given = True
        paths = pos if given else pos[1:]
        reads([v for k in ("-f", "--file") for v in opts.get(k, []) if v])
        rec = verb in ALWAYS_RECURSIVE or bool(flags & {"r", "R"}) or "--recursive" in opts or "--dereference-recursive" in opts
        if not paths and rec and state["cwd"]:
            out.append(("read", state["cwd"], True, True, False))
        reads(paths, rec)
    elif verb == "find":
        k = 0
        while k < len(args) and not (args[k] is not None and re.match(r"^[-(!]|^\\\(", args[k])):
            k += 1
        starts = args[:k] if k else ["."]
        rest = [(x or "").lower() for x in args[k:]]
        deletes = "-delete" in rest or any(rest[j] in ("-exec", "-execdir", "-ok", "-okdir")
                                           and j + 1 < len(rest) and verb_name(rest[j + 1]) in PS_REMOVE_FIND
                                           for j in range(len(rest)))
        reads(starts, True, content=False)
        if deletes:
            writes(starts, "remove")
    elif verb in ("sed", "perl"):
        vals = ("-e", "--expression", "-f", "--file", "-l", "--line-length") if verb == "sed" else ("-e", "-E", "-I", "-M", "-m", "-x")
        pos, opts = gnu_args(args, vals)
        inplace = any(re.match(r"-[A-Za-z]*i", k) or k.startswith("--in-place") for k in opts)
        has_script = any(k in opts for k in ("-e", "--expression", "-f", "--file", "-E"))
        if verb == "perl" and not has_script:
            return out  # perl script.pl: the script does what it does
        for k in ("-e", "-E"):
            if verb == "perl" and k in opts:
                out.extend(("code", v) for v in opts[k] if v)
        files = pos if has_script else pos[1:]
        if inplace:
            writes(files, "modify")
        else:
            reads(files)
    elif verb in ("awk", "gawk", "mawk"):
        pos, opts = gnu_args(args, ("-f", "-v", "-F", "--file", "--assign", "--field-separator"))
        reads([v for v in opts.get("-f", []) if v])
        reads(pos if "-f" in opts else pos[1:])
    elif verb in REMOVERS:
        pos, _ = gnu_args(args, REMOVERS[verb])
        writes(pos, "remove")
    elif verb in MOVERS or verb in ("robocopy", "xcopy"):
        if verb in ("robocopy", "xcopy"):
            pos = [a for a in args if not re.fullmatch(r"/[A-Za-z]{1,4}(:\S*)?", a or "")]
            pos = pos[:2]
            opts = {"-r": [None]}
        else:
            pos, opts = gnu_args(args, MOVERS[verb])
        target = (opts.get("-t") or opts.get("--target-directory") or [None])[0]
        dest, sources = (target, pos) if target else ((pos[-1], pos[:-1]) if len(pos) >= 2 else (None, []))
        rec = bool(short_flags(opts) & {"r", "R", "a"}) or "--recursive" in opts or "--archive" in opts
        if verb == "mv":
            writes(sources, "remove")
        elif verb != "ln":
            reads(sources, rec, content=False)  # copying .env into a worktree shows the model nothing
            out.extend(("write", p, "copy-out", False, False) for p in map(P, sources) if p)
        dests([dest] if dest is not None else [])
    elif verb in MAKERS:
        pos, opts = gnu_args(args, MAKERS[verb])
        if verb == "mkdir":
            writes(pos, "create-other", anc="p" in short_flags(opts) or "--parents" in opts)
        elif verb == "truncate":
            writes(pos, "modify")
        else:
            writes(pos)
    elif verb == "dd":
        for a in args:
            if a and a.startswith("of="):
                writes([a[3:]])
            elif a and a.startswith("if="):
                reads([a[3:]])
    elif verb in ("curl", "wget"):
        pos, opts = gnu_args(args, ("-o", "--output", "-T", "--upload-file", "-O", "--output-document", "-P",
                                    "--directory-prefix", "-d", "--data", "-H", "--header", "-X", "-u", "-A",
                                    "-w", "--write-out", "-F", "--form", "-e", "--referer", "-b", "-c",
                                    "--max-time", "-m", "--retry", "-x", "--proxy") if verb == "curl" else
                            ("-O", "--output-document", "-P", "--directory-prefix", "-o", "--output-file",
                             "--header", "-U", "--user-agent", "-t", "--tries", "-T", "--timeout"))
        if verb == "curl":
            writes([v for k in ("-o", "--output") for v in opts.get(k, []) if v])
            reads([v for k in ("-T", "--upload-file") for v in opts.get(k, []) if v])
        else:
            writes([v for k in ("-O", "--output-document") for v in opts.get(k, []) if v])
            writes([v for k in ("-P", "--directory-prefix") for v in opts.get(k, []) if v], anc=True)
    elif verb in SHELLS:
        k, body = 0, None
        while k < len(args) and (args[k] or "").startswith("-"):
            if "c" in (args[k] or "")[1:] and not (args[k] or "").startswith("--") and k + 1 < len(args):
                body = raw[k + 2]
                break
            k += 1
        if body is not None:
            out.append(("body", "bash", body.replace(LIT, "$")))
        elif k >= len(args):  # bash, bash -s, bash -l: the script comes on stdin
            out.extend(("body", "bash", h) for h in simple.heredocs)
    elif verb in POWERSHELLS:
        k = 0
        while k < len(args):
            a = (args[k] or "").lower()
            if a in ("-command", "-c") or (a.startswith("-com") and "-command".startswith(a)):
                body = " ".join(w.replace(LIT, "$") for w in raw[k + 2:])
                if body.strip() == "-":
                    out.extend(("body", "ps", h) for h in simple.heredocs)
                else:
                    out.append(("body", "ps", body))
                break
            if a in ("-file", "-f") or a.startswith(("-enc", "-ec", "-e")) and a not in ("-ex", "-executionpolicy", "-ep"):
                break  # a script file, or an encoded command: one command to the guard
            if a in ("-executionpolicy", "-ex", "-ep", "-workingdirectory", "-wd", "-windowstyle", "-w",
                     "-outputformat", "-of", "-o", "-inputformat", "-if", "-in", "-version", "-v",
                     "-settingsfile", "-configurationname", "-custompipename", "-configurationfile"):
                k += 2
                continue
            if not a.startswith("-"):  # powershell.exe "Get-Item x": the rest is the command
                if not a.endswith(".ps1"):
                    out.append(("body", "ps", " ".join(w.replace(LIT, "$") for w in raw[k + 1:])))
                break
            k += 1
        else:
            out.extend(("body", "ps", h) for h in simple.heredocs)
    elif verb in INTERPRETERS:
        pos, opts = gnu_args(args, INTERPRETERS[verb] + ("-m", "-W", "-X"))
        for flag in INTERPRETERS[verb]:
            out.extend(("code", v.replace(LIT, "$")) for v in opts.get(flag, []) if v)
        out.extend(("code", h) for h in simple.heredocs)
    return out


def git_effect(words, state):
    """("git", cwd of the call, subcommand, its arguments); an unknown part of a word stays marked."""
    i, gcwd = 1, state["cwd"]
    while i < len(words) and (words[i] or "").startswith("-"):
        if words[i] == "-C" and i + 1 < len(words):
            gcwd = to_path(words[i + 1], state) or (None if isinstance(words[i + 1], Unknown) else gcwd)
            i += 2
        elif words[i] in GIT_GLOBAL_WITH_VALUE and i + 1 < len(words):
            i += 2
        else:
            i += 1
    if i >= len(words):
        return ("git", gcwd, "", [])
    return ("git", gcwd, (words[i] or "").lower(), [str(w or "") for w in words[i + 1:]])


# ------------------------------------------------------------------------------- the shell, decided

def decide_shell(cmd, cwd, cfg, shell="bash"):
    """The verdict on a shell command: the first refusal, else the first ask, else pass."""
    state = {"cwd": cwd, "vars": {}, "shell": shell}
    asked = None
    for verdict, reason in walk(parse(cmd, shell, "top"), state, cfg):
        if verdict == "deny":
            return verdict, reason
        if verdict == "ask" and asked is None:
            asked = (verdict, reason)
    refusal = legacy_immutable(cmd, cwd, cfg)
    if refusal:
        return "deny", refusal
    return asked or ("pass", "")  # shell commands never get an explicit allow


def walk(simples, state, cfg, depth=0):
    """Yield (verdict, reason) for every effect of the simple commands, bodies included."""
    detail = "This command would change, move, overwrite or delete there."
    for simple in simples:
        state["shell"] = simple.shell
        for e in effects(simple, state):
            kind = e[0]
            if kind == "cd":
                state["cwd"] = e[1]
                # entering a blocked folder is reading there; the blocked folder itself (the cloud
                # drive) is only a way into the roots below it
                if e[1] and not any(e[1] == root for root, _, _ in cfg["read_blocked"]):
                    refusal = blocked_refusal(e[1], cfg)
                    if refusal:
                        yield "deny", refusal
            elif kind == "blocked-arg":
                refusal = blocked_refusal(e[1], cfg)
                if refusal:
                    yield "deny", refusal
            elif kind == "read":
                _, p, rec, content, partial = e
                refusal = read_refusal(p, cfg, rec, content and not partial)
                if refusal:
                    yield "deny", refusal
            elif kind == "write":
                _, p, op, anc, partial = e
                if op:  # with an unknown name, only a removal or a change in place is certain
                    refusal = immutable_refusal(p, op, cfg, detail)
                    if refusal:
                        yield "deny", refusal
                        continue
                if op == "copy-out" or simple.level == "body":
                    continue
                if (os.path.isdir(p) or anc) if partial else creatable(p, anc):
                    verdict, reason = scope(p, cfg)
                    if verdict in ("ask", "deny"):
                        yield verdict, reason
            elif kind == "git":
                _, gcwd, sub, args = e
                if sub:
                    verdict, reason = decide_git(gcwd or state["cwd"] or os.getcwd(), sub, args, cfg)
                    if verdict in ("ask", "deny"):
                        yield verdict, reason
            elif kind == "body" and depth < 4:
                inner = {"cwd": state["cwd"], "vars": dict(state["vars"]), "shell": e[1]}
                yield from walk(parse(e[2], e[1], "body"), inner, cfg, depth + 1)
                state["shell"] = simple.shell
            elif kind == "code":
                refusal = code_reads(e[1], cfg)
                if refusal:
                    yield "deny", refusal


def code_reads(text, cfg):
    """A path into the read block written literally in code handed to an interpreter; the refusal or None."""
    if not cfg["read_blocked"]:
        return None
    flat = text.replace("\\\\", "\\").replace("/", "\\")
    low = flat.lower()
    for root, _, _ in cfg["read_blocked"]:
        r = root.replace("/", "\\").lower()
        variants = [r]
        if os.name == "nt" and re.match(r"^[a-z]:", r):
            variants.append("\\" + r[0] + r[2:])  # /c/Users/... as Git Bash writes it
        for v in variants:
            start = 0
            while True:
                k = low.find(v, start)
                if k < 0:
                    break
                tail = re.match(r"[^\"'\n\r`,;)\]]*", flat[k + len(v):]).group(0).rstrip()
                p = os.path.normcase(os.path.normpath(root + tail.replace("\\", os.sep)))
                refusal = read_refusal(p, cfg)
                if refusal:
                    return refusal
                start = k + 1
    return None


# ------------------------------------------------------------------------------- the substring backstop
# The pattern scan of the first version, kept for one job: a write verb next to a path inside an
# immutable folder refuses, wherever it stands in the text (a heredoc, a -Command body, a message).
# It never asks and never reads; the parser above decides everything else.

_EDGE_L = r"(?<![\w.\-/\\$:])"
_EDGE_R = r"(?=\s|$|;)"
REMOVE_VERBS = {"rm", "rmdir", "rd", "del", "erase", "remove-item", "ri", "ren", "rename", "rename-item", "rni",
                "git rm", "git mv"}
MOVE_VERBS = {"mv", "move", "move-item", "mi"}
CREATE_VERBS = {"new-item", "ni", "mkdir", "md"}
WRITE_VERBS = re.compile(
    _EDGE_L + r"(rm|rmdir|rd|del|erase|Remove-Item|ri|mv|move|Move-Item|mi|ren|rename|Rename-Item|rni|"
    r"git\s+rm|git\s+mv|Clear-Content|clc|Set-Content|sc|Add-Content|ac|Out-File|Tee-Object|tee|"
    r"truncate|sed\s+-i\S*|perl\s+-pi\S*|touch|New-Item|ni|mkdir|md)" + _EDGE_R,
    re.IGNORECASE,
)
COPY_VERBS = re.compile(_EDGE_L + r"(cp|copy|Copy-Item|cpi|xcopy|robocopy)" + _EDGE_R, re.IGNORECASE)
REDIRECT = re.compile(r"(?<![<>&\-\w])\d?>{1,2}\s*(\"[^\"]*\"|'[^']*'|[^\s;|&<>]+)")
CD = re.compile(r"^\s*(?:cd|Set-Location|sl|pushd)\s+(\S.*?)\s*$", re.IGNORECASE)
SINKS = {"/dev/null", "nul", "$null", "nul:", "/dev/stdout", "/dev/stderr", "/dev/tty", "con"}
WINDOWS_VERBS = {"robocopy", "xcopy", "copy", "move", "del", "erase", "rd", "rmdir", "md", "ren", "rename", "dir"}


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


def legacy_targets(seg, cwd):
    """(path, op) for every path the segment writes, by pattern, and every source it copies (copy-out)."""
    found = []
    for m in REDIRECT.finditer(seg):
        t = m.group(1).strip("\"'")
        if t.count(")") > t.count("("):  # the closing bracket of a $( ... ) around the redirect
            t = t.rstrip(")")
        if t and t.lower() not in SINKS:
            found.append((t, "redirect"))
    cm = COPY_VERBS.search(seg)
    wm = WRITE_VERBS.search(seg)
    mover = wm and re.sub(r"\s+", " ", wm.group(1).lower()) in MOVE_VERBS
    if (cm and (not wm or cm.start() < wm.start())) or mover:
        m = cm if cm and (not wm or cm.start() < wm.start()) else wm
        verb = m.group(1).lower()
        args = arguments(seg[m.end():], verb)
        dest = None
        if verb in ("copy-item", "cpi", "move-item", "mi"):
            after = tokens(seg[m.end():])
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
        found += [(a, "remove" if verb in MOVE_VERBS else "copy-out") for a in args]
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


def legacy_immutable(cmd, cwd, cfg):
    """The refusal when a write verb meets an immutable folder anywhere in the text; None otherwise."""
    if not cfg["immutable"]:
        return None
    for seg in re.split(r"[;\n|]|&&|\|\|", cmd):
        m = CD.match(seg)
        if m:
            target = m.group(1).strip().strip("\"'")
            if target and target != "-":
                cwd = norm(target, cwd)
            continue
        try:
            targets = legacy_targets(seg, cwd)
        except (ValueError, OSError):
            continue
        for p, op in targets:
            refusal = immutable_refusal(p, op, cfg, "This command would change, move, overwrite or delete there.")
            if refusal:
                return refusal
    return None


# ------------------------------------------------------------------------------- git

GIT_GLOBAL_WITH_VALUE = {"-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--exec-path"}
GIT_WRAPPERS = {"&", "(", "sudo", "command", "time", "exec", "env", "nohup", "call"}
PUSH_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}


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


def may_be_protected(name, cfg):
    """True when a name with an unknown part could still be a protected branch: `worktree-$w`
    cannot be main, `$b` can."""
    if UNKNOWN not in (name or ""):
        return False
    n = re.sub(r"^refs/heads/", "", name.lower()).replace("*", "[*]").replace(UNKNOWN, "*")
    return any(fnmatch.fnmatchcase(b, n) or fnmatch.fnmatchcase(b, n.split("/", 1)[-1]) for b in cfg["protected"])


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
    """git guardrails: refuse what loses work or rewrites a protected branch; ask before a remote branch deletion."""
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
            return "ask", (f"this deletes the remote branch {', '.join('`%s`' % shown(n) for n in names) or '(unnamed)'}: "
                           f"remote branch deletions wait for the person's yes.")
        force = ("f" in shorts or longs & {"--force", "--force-with-lease", "--mirror"}
                 or any(r.startswith("+") for r in refspecs))
        if force:
            if longs & {"--all", "--mirror", "--branches"}:
                return "deny", "a force push of every branch rewrites the protected branches too; push one named branch."
            dests = [push_destination(r, gcwd) for r in refspecs] or [current_branch(gcwd)]
            if any(d is None or may_be_protected(d, cfg) for d in dests):
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
            return "deny", ("`git branch -D` deletes a branch even when its work is merged nowhere, so the person "
                            "runs it (`! git branch -D <name>` in Claude Code, for a squash-merged branch); "
                            "`git branch -d` deletes a merged branch and passes.")
        if not names or any(may_be_protected(n, cfg) for n in names):
            return "ask", (f"this deletes the branch {', '.join('`%s`' % shown(n) for n in names) or '(unnamed)'}, "
                           f"whose name the guard cannot read, and it could be a protected branch: name the branch.")
        return "pass", ""  # git itself refuses -d on a branch that is not merged
    # git worktree remove passes, with or without --force: no rule below matches it
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
    print("Secrets (reads refused): " + ", ".join(cfg["secret_names"]) + "; folders: "
          + "; ".join(cfg["secret_dirs"]) + "; files: " + "; ".join(cfg["secret_files"])
          + "; templates allowed: " + ", ".join(sorted(cfg["secret_except"])))
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
              "data/meeting-transcripts", "notes/projects", "notes/originals", "notes/filed", "outside/granted",
              "outside/expired", "job", "oldjob", "work"):
        os.makedirs(j(*d.split("/")), exist_ok=True)
    for f in ("data/projects/p1/data/raw/original.csv", "data/meeting-transcripts/2026-01-15.vtt",
              "notes/originals/kept.md", "notes/projects/plan.md", "notes/filed/old.md", "outside/old.txt"):
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
                         (j("notes", "originals"), "never", "the originals of the notes"),
                         (j("notes", "filed"), "deposit-only", "a filed note stays as filed")],
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
        ("Connector: move a note into a deposit folder by its new name", N("move", path="projects/plan.md", newPath="filed/plan.md"), repo, "pass"),
        ("Connector: move to the deposit folder ending in / keeps the name", N("move", path="projects/plan.md", destination="filed/"), repo, "pass"),
        ("Connector: the same with backslashes", N("move", path="projects\\plan.md", destination="filed\\"), repo, "pass"),
        ("Connector: move to the folder onto a filed note", N("move", path="projects/old.md", destination="filed/"), repo, "deny"),
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

    # ---- the corrections block, the one change a filed transcript takes (12 November 2026)
    print("Part 1b: the corrections block in a transcript")
    tr = j("data", "meeting-transcripts", "s", "2026-11-11 m - transcript.txt")
    vt = j("data", "meeting-transcripts", "s", "2026-11-11 m - transcript.vtt")
    done = j("data", "meeting-transcripts", "s", "2026-11-11 n - transcript.txt")
    body = "Transcript: m\n[00:01 A] Holmbler scale is open.\n[00:05 B] So"
    blk = ("NOTE CORRECTIONS (added after filing; the text below is unchanged)\n"
           "Holmbler scale = Holmbladsgade (confirmed 2026-11-12)\nNOTE END CORRECTIONS\n")
    _write(tr, body)
    _write(vt, "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n<v A>Holmbler scale is open.\n")
    _write(done, blk + "\n" + body)
    Ed = lambda p, a, b: ("Edit", {"file_path": p, "old_string": a, "new_string": b})  # noqa: E731
    corr = [
        ("Block added at the top of a transcript", Ed(tr, "Transcript: m\n", blk + "\nTranscript: m\n"), repo, "pass"),
        ("Block added after the WEBVTT line", Ed(vt, "WEBVTT\n\n", "WEBVTT\n\n" + blk + "\n"), repo, "pass"),
        ("Block added at the very end", Ed(tr, "[00:05 B] So", "[00:05 B] So\n\n" + blk), repo, "pass"),
        ("Whole transcript written again with only the block added",
         ("Write", {"file_path": tr, "content": blk + "\n" + body}), repo, "pass"),
        ("Block updated with one more line",
         Ed(done, "Holmbladsgade (confirmed 2026-11-12)\n", "Holmbladsgade (confirmed 2026-11-12)\nB = Bo\n"), repo, "pass"),
        ("A recorded line changed", Ed(tr, "Holmbler scale is open", "Holmbladsgade is open"), repo, "deny"),
        ("A recorded line changed while adding the block",
         Ed(tr, "Transcript: m\n[00:01 A] Holmbler", blk + "\nTranscript: m\n[00:01 A] Holmbladsgade"), repo, "deny"),
        ("A recorded line changed next to the block",
         Ed(done, "NOTE END CORRECTIONS\n\nTranscript: m", "NOTE END CORRECTIONS\n\nTranscript: changed"), repo, "deny"),
        ("Block in the middle of the recording", Ed(tr, "[00:05 B] So", blk + "[00:05 B] So"), repo, "deny"),
        ("A blank line inside the block",
         Ed(tr, "Transcript: m\n", blk.replace("\nHolmbler", "\n\nHolmbler") + "\nTranscript: m\n"), repo, "deny"),
        ("A cue arrow inside the block", Ed(vt, "WEBVTT\n\n", "WEBVTT\n\n" + blk.replace(" = ", " --> ") + "\n"), repo, "deny"),
        ("A second block", Ed(done, "Transcript: m\n", blk + "\nTranscript: m\n"), repo, "deny"),
        ("An edit whose text is not in the file", Ed(tr, "nowhere", blk), repo, "deny"),
        ("sed on a transcript is still refused", B(f'sed -i "1i NOTE CORRECTIONS" "{tr.replace(chr(92), "/")}"'), repo, "deny"),
        ("The block does not open raw data", Ed(orig, "x\n", blk + "\nx\n"), repo, "deny"),
    ]
    failed += _run_cases(corr, cfg)
    total += len(corr)

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
        ("git: branch -d of another branch passes (git refuses it unless merged)", B("git branch -d feature-x"), res, "pass"),
        ("git: push --delete main", B("git push origin --delete main"), res, "deny"),
        ("git: push --delete of another branch asks", B("git push origin --delete feature-x"), res, "ask"),
        ("git: push :branch asks", B("git push origin :feature-x"), res, "ask"),
        ("git: checkout -- .", B("git checkout -- ."), res, "deny"),
        ("git: restore .", B("git restore ."), res, "deny"),
        ("git: restore --staged . passes", B("git restore --staged ."), res, "pass"),
        ("git: checkout -- one file passes", B("git checkout -- src/a.py"), res, "pass"),
        ("git: a commit message that names the rules passes", B('git commit -m "Refuse git reset --hard and git clean"'), res, "pass"),
        ("git: unattended remote branch deletion is refused", B("git push origin --delete feature-x"), res, "deny", m_away, "morning report"),
    ]
    failed += _run_cases(third, m)
    total += len(third)

    print("\nPart 4: the shell parser, variables, git, grants by folder and file, secrets")
    saved = {k: os.environ.get(k) for k in ("TEMP", "TMP", "LOCALAPPDATA", "USERPROFILE", "HOME", "UNSET_VAR_FOR_TEST")}
    try:
        f4, n4 = _part4(j, home, dev, res, D, V, cloud, private, archived, raw_file, mk, future)
        failed += f4
        total += n4
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print(f"\n{total - failed} of {total} checks passed ({len(first) + len(proto) + 2} in part 1, {len(corr)} in part 1b, {len(second)} in part 2, "
          f"{len(third)} in part 3, {n4} in part 4)." + (" The guard's logic works on this computer." if not failed else ""))
    return 1 if failed else 0

def _part4(j, home, dev, res, D, V, cloud, private, archived, raw_file, mk, future):
    """The parser, variables, git, grants by folder and file, secrets; returns (failed, count)."""
    W = lambda p: ("Write", {"file_path": p})  # noqa: E731
    R = lambda p: ("Read", {"file_path": p})  # noqa: E731
    B = lambda c: ("Bash", {"command": c})  # noqa: E731
    P = lambda c: ("PowerShell", {"command": c})  # noqa: E731
    tmp, local = j("machine-temp"), os.path.join(home, "AppData", "Local")
    downloads, exports = os.path.join(home, "Downloads"), os.path.join(home, "Exports")
    for d in (tmp, local, exports, os.path.join(private, "Shared", "sub"), os.path.join(home, ".ssh"),
              os.path.join(res, "code"), os.path.join(private, "Viaclip")):
        os.makedirs(d, exist_ok=True)
    for f in (os.path.join(res, ".env"), os.path.join(res, ".env.example"), os.path.join(res, "code", "credentials.py"),
              os.path.join(home, ".ssh", "id_ed25519"), os.path.join(home, ".claude", ".credentials.json"),
              os.path.join(private, "single.pdf"), os.path.join(res, "a.vtt")):
        _write(f)
    os.environ.update({"TEMP": tmp, "TMP": tmp, "LOCALAPPDATA": local, "USERPROFILE": home, "HOME": home})
    os.environ.pop("UNSET_VAR_FOR_TEST", None)
    grant2 = j("machine-job2", "write-scope.json")
    os.makedirs(os.path.dirname(grant2), exist_ok=True)
    with open(grant2, "w", encoding="utf-8") as fh:
        json.dump({"plan": "self-test", "expires": future,
                   "read": [os.path.join(private, "Shared"), os.path.join(private, "single.pdf")],
                   "write": [os.path.join(downloads, "out.csv"), exports.replace("\\", "/") + "/"]}, fh)
    cli_grant = j("machine-job3", "write-scope.json")
    g = write_grant(cli_grant, "read", [os.path.join(private, "Viaclip")], hours=2, plan="self-test")
    g = write_grant(cli_grant, "write", [os.path.join(downloads, "report.docx")], hours=1)
    kw = dict(mk, writable=mk["writable"] + [tmp], secrets=secrets_for(home),
              grant_files=mk["grant_files"] + [grant2, cli_grant])
    m4 = build_config(attended=None, pause_flag=j("nopause"), **kw)
    away = build_config(attended="0", pause_flag=j("nopause"), **kw)
    job = j("machine-job")
    raw = os.path.dirname(raw_file)
    drive_form = ("/" + dev[0].lower() + dev[2:].replace("\\", "/")) if os.name == "nt" else dev
    secrets = "secrets are not for the model"
    ask_p = "ask the person for the file"
    cases = [
        ("Quoting: pwsh -Command with New-Item \\\"$env:TEMP\\x\\\" in Bash", B('pwsh -NoProfile -Command "New-Item \\"\\$env:TEMP\\keep-awake.stop\\" -Force | Out-Null; Start-Sleep 8"'), res, "pass", away),
        ("Quoting: New-Item \"$env:TEMP\\x\" in PowerShell", P('New-Item "$env:TEMP\\keep-awake.stop" -Force | Out-Null'), res, "pass", away),
        ("Quoting: a commit message that quotes 2>/dev/null)", B('git commit -q -m "a redirect inside \\$( ... ): 2>/dev/null) was refused"'), res, "pass", away),
        ("Quoting: a heredoc whose lines hold p:, 0: and 1:", B(f'cat > "{job}/v.py" <<\'PYEOF\'\nfor p in sys.argv[1:]:\n    print(f"{{p}}: ok")\nrm p: 0: 1:\nPYEOF'), res, "pass", away),
        ("Parse: a sed script is no path", B(f'sed -i \'/^    c=s.get("collect") or {{}}$/d\' "{job}/srcs.py"'), res, "pass", away),
        ("Parse: a grep pattern with quotes and slashes is no path", B('grep -rn "\\"/api/me\\"\\|\'/api/me\'" src/*.py | head -5'), res, "pass", away),
        ("Parse: escaped quotes inside a --body", B('gh issue comment 109 --body "**Confirmed:** the reading of \\"own points\\" stays open"'), res, "pass", away),
        ("Parse: a Git Bash drive path for mkdir -p", B(f'mkdir -p "{drive_form}/research/newdir" && cp a.txt "{drive_form}/research/newdir/"'), res, "pass", away),
        ("Parse: a heredoc fed to bash is code and parsed", B(f'bash <<\'EOF\'\nrm "{raw_file}"\nEOF'), res, "deny"),
        ("Backstop: a heredoc that writes rm on a raw file is still refused", B(f'cat > notes.md <<\'EOF\'\nrm "{raw_file}"\nEOF'), res, "deny"),
        ("Body: the write scope is not inspected in a -Command body", B(f'pwsh -Command "Set-Content -Path \'{downloads}/x.txt\' -Value 1"'), res, "pass"),
        ("Body: the originals still hold in a -Command body", B(f'pwsh -Command "Remove-Item \'{raw_file}\'"'), res, "deny"),
        ("Body: the read block still holds in a -Command body", B(f'pwsh -NoProfile -Command "Get-ChildItem \'{private}\'"'), res, "deny", m4, ask_p),
        ("Variables: an assignment resolves a later word", B(f'D="{downloads}"; touch "$D/x.txt"'), res, "ask"),
        ("Variables: a loop variable leaves the known folder", B(f'for s in a b; do echo x > "{downloads}/all-$s.log"; done'), res, "ask"),
        ("Variables: a known folder of originals with rm", B(f'R="{raw}"; for f in a b; do rm "$R/$f"; done'), res, "deny"),
        ("Expansion: ~/.claude", B("touch ~/.claude/x.txt"), res, "pass", away),
        ("Expansion: ~/Downloads asks", B("touch ~/Downloads/y.txt"), res, "ask"),
        ("Expansion: %LOCALAPPDATA% asks", P('New-Item "%LOCALAPPDATA%\\x.txt"'), res, "ask"),
        ("Read block: cd into it, then a tool the guard does not know", B(f'cd "{private}" && pdftotext a.pdf -'), res, "deny", m4, ask_p),
        ("Read block: an argument into it", B(f'pdftotext "{private}/report.pdf" -'), res, "deny", m4, ask_p),
        ("Read block: git -C into it", B(f'git -C "{private}" log -1'), res, "deny"),
        ("Read block: cd into the cloud drive, then into a root", B(f'cd "{cloud}" && cat research/projects/x.txt'), res, "pass"),
        ("Read block: a Python heredoc that opens a blocked file", B(f'python - <<\'EOF\'\nprint(open(r"{private}/report.pdf", "rb").read(9))\nEOF'), res, "deny", m4, ask_p),
        ("Read block: echo of a blocked path is no read", B(f'echo "{private}/report.pdf"'), res, "pass"),
        ("git: branch -d passes unattended", B("git branch -d feature-x"), res, "pass", away),
        ("git: branch -d in a loop over worktree-$w", B('for w in a b; do git worktree remove ".claude/worktrees/$w"; git branch -d "worktree-$w"; done'), res, "pass", away),
        ("git: branch -d of a name the guard cannot read asks", B('git branch -d "$b"'), res, "ask"),
        ("git: worktree remove --force passes", B("git worktree remove --force .claude/worktrees/wt"), res, "pass", away),
        ("git: an unknown ref is not the whole tree", P("foreach ($ref in @('a','b')) { git checkout -q --detach $ref }"), res, "pass"),
        ("git: a force push to an unknown branch is refused", B('git push --force origin "$b"'), res, "deny"),
        ("Grant: a folder read grant opens its subfolders", R(os.path.join(private, "Shared", "sub", "a.pdf")), res, "pass"),
        ("Grant: a file read grant opens that file", R(os.path.join(private, "single.pdf")), res, "pass"),
        ("Grant: and not its neighbour", R(os.path.join(private, "single2.pdf")), res, "deny", m4, ask_p),
        ("Grant: a file write grant opens that file", W(os.path.join(downloads, "out.csv")), res, "pass"),
        ("Grant: and not its neighbour", W(os.path.join(downloads, "out2.csv")), res, "ask"),
        ("Grant: a folder write grant opens its subfolders", W(os.path.join(exports, "deep", "x.txt")), res, "pass"),
        ("Grant: --grant read of a folder", R(os.path.join(private, "Viaclip", "x.pdf")), res, "pass"),
        ("Grant: --grant write of a file", W(os.path.join(downloads, "report.docx")), res, "pass"),
        ("Secrets: Read .env", R(os.path.join(res, ".env")), res, "deny", m4, secrets),
        ("Secrets: Read .env.example passes", R(os.path.join(res, ".env.example")), res, "pass"),
        ("Secrets: Read credentials.py, source code, passes", R(os.path.join(res, "code", "credentials.py")), res, "pass"),
        ("Secrets: Read ~/.ssh/id_ed25519", R(os.path.join(home, ".ssh", "id_ed25519")), res, "deny", m4, secrets),
        ("Secrets: Read ~/.claude/.credentials.json", R(os.path.join(home, ".claude", ".credentials.json")), res, "deny"),
        ("Secrets: Read a .pem, a .key, a token JSON", R(os.path.join(res, "gh-token.json")), res, "deny"),
        ("Secrets: cat .env", B("cat .env"), res, "deny", m4, secrets),
        ("Secrets: Get-Content .env", P("Get-Content .env"), res, "deny"),
        ("Secrets: ls -la .env lists a name and passes", B("ls -la .env"), res, "pass"),
        ("Secrets: cp .env into a worktree passes (nothing shown)", B("cp .env .claude/worktrees/wt/"), res, "pass"),
        ("Secrets: a script loads .env itself", B("python -I app.py --check"), res, "pass"),
        ("Deposit: a new folder and a transcript by the shell", B(f'T="{D}/meeting-transcripts/new-series"; mkdir -p "$T" && cp a.vtt "$T/2026-11-09 x - transcript.vtt"'), res, "pass"),
        ("Archive: a backup copy out of the archive is a read", B(f'cp "{archived}" "{res}/backup.md"'), res, "pass"),
    ]
    failed = _run_cases(cases, m4)
    ok = g.get("read") and g.get("write") and datetime.fromisoformat(g["expires"]) > datetime.now() + timedelta(hours=1.5)
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} grant     --grant keeps both lists and the later expiry")
    return failed, len(cases) + 1



def main():
    if "--self-test" in sys.argv[1:]:
        return self_test()
    if "--show-config" in sys.argv[1:]:
        return show_config()
    if "--grant" in sys.argv[1:]:
        return grant_cli(sys.argv[1:])
    return run_hook(sys.stdin.read(), build_config(), sys.stdout, sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
