#!/usr/bin/env python3
"""Workflow health: measure how the agent workflow runs, with no model tokens.

Reads Claude Code's session transcripts, the configuration the agent loads, and the structure of
the notes vault, and writes one report note with the week against the week before, the
recommendations whose thresholds were crossed (each with the number that crossed it), and an empty
Judgement section that the workflow-health skill fills when the person asks. Run it weekly from a
scheduled task and on demand:

    python -I workflow_health.py                     measure, write the report note
    python -I workflow_health.py --no-write          measure and print only
    python -I workflow_health.py --session-cost      the cost so far of the newest session, then stop
    python -I workflow_health.py --session-cost 3f2a the same for the session whose id starts so
Options --workspace, --code, --notes and --note override the configuration block below.

What it reads, and never writes:
  transcripts     ~/.claude/projects/<project>/<session>.jsonl, and <session>/subagents/agent-*.jsonl
                  with the agent-*.meta.json beside them
  configuration   the CLAUDE.md files, <workspace>/.claude/context, the skills (project and personal),
                  the settings files, the auto-memory index of the workspace
  the vault       off disk, one folder at a time; never the content of an online-only file of a cloud
                  drive (reading it would download it)
What it writes: the report note (on disk, whole, on every run: keep it closed in the notes app while
the script runs, and edit the script, not the note) and, if JSON_OUT is set, the numbers as JSON.

Transcript fields relied on (Claude Code 2.1, read off real files in November 2026; the format is
not documented and may change, so check the numbers against /context once after an update):
  every line       type; timestamp (UTC) and cwd on user, assistant and system lines; bookkeeping
                   records (api-request, queue-operation, titles and the like) are skipped
  type=user        message.content, a string or blocks (text; tool_result with tool_use_id and
                   is_error); origin.kind "human" for a prompt the person typed; isMeta; isCompactSummary
  type=assistant   requestId (one API call spans several lines: the maximum per field is taken);
                   message.usage: input_tokens, cache_creation_input_tokens, cache_read_input_tokens,
                   output_tokens; tool_use blocks {id, name, input}
  type=system      subtype "compact_boundary" with compactMetadata {trigger, preTokens}
Token sums from the transcripts are a lower bound: side calls (the auto-mode classifier, summaries,
titles) leave no line there. (API means application programming interface: one call is one request
to the model.)

Standard library only; Python 3.8 or later. Part of the ai-research-setup-kit; Copyright (c) 2026
Johannes Wildfeuer, MIT licence (see LICENSE.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ------------------------------------------------------------------------------- configuration
CLAUDE_HOME = "~/.claude"
WORKSPACE = "<the workspace folder that holds your CLAUDE.md, for example C:/dev/research>"
CODE_ROOT = "<code root: every git repository below it counts as one, for example C:/dev>"
NOTES_ROOT = "<notes vault, for example C:/Users/you/OneDrive - Your University/Vault>"
REPORT_NOTE = "<the report note inside the vault, for example Maps/Workflow Health.md>"
JSON_OUT = ""                      # optional: a path for the numbers as JSON (in the data root, not the vault)

NOTES_TOOL_PREFIX = "mcp__obsidian__"           # the notes connector's tools; "" if you have none
SAVE_SKILLS = {"learn", "<your session-closing skill>"}   # a session that ran one of these saved before it ended
SKIP_FOLDERS = {".obsidian", ".trash", ".git"}  # never walked
NOT_KNOWLEDGE = {"<daily notes folder>", "<inbox folder>", "Templates"}  # top-level folders where an orphan is normal
INBOX = "<inbox folder>"                        # counted; "" to skip
AGENT_NOTES = "<the agent-outputs folder>"      # dated notes due for the archive are counted; "" to skip
CONTEXT_WINDOW = 200_000                        # tokens: the context window of the model you run

# Thresholds. Each recommendation prints the number that crossed one. These are starting points, not
# measurements of your work: after three weekly runs, set each from your own numbers (the skill's
# Learn step), and record why in your rules changelog.
T = {
    "reread_ratio": 2.0,           # reads per distinct (file, window) over 30 days
    "split_share": 0.4,            # a session whose context peaked above this share of the window: split by task
    "plan_end_share": 0.6,         # above this share a session plans its own end (save step, handover)
    "repos_per_session": 3,        # more distinct repositories than this in one session: drift
    "orphan_share": 0.10,          # knowledge notes without an inbound link
    "big_note_kb": 100,            # a note this large wants a "where this stands" section on top
    "agent_note_days": 30,         # the archive rule (kit/tools/archive_notes.py)
    "skill_idle_days": 60,         # a skill listed in every session, never invoked this long
    "fixed_start": None,           # median first-call context in tokens; None until you set it from your /context
    "connector_fail_share": 0.05,  # failed notes-connector calls
    "context_file_lines": 400,     # a reference file past this many lines wants a restructure
    "idle_gap_min": 30,            # gaps longer than this do not count as active time
}
# --------------------------------------------------------------------------- end of configuration

SKIP_PREFIXES = ('{"type":"api-request', '{"type":"queue-operation', '{"type":"ai-title', '{"type":"custom-title',
                 '{"type":"last-prompt', '{"type":"summary', '{"type":"file-history', '{"type":"cost-state',
                 '{"type":"permission-mode', '{"type":"mode"', '{"type":"worktree-state')
READ_TOOLS = {"Read"}
DISK_WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
ONLINE_ONLY = 0x1000 | 0x40000 | 0x400000  # Windows attributes of an online-only cloud-drive file
CMD_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
LINK_RE = re.compile(r"!?\[\[([^\]\|#\^\n]+)")
MDLINK_RE = re.compile(r"\]\(([^)\s]+\.md)\)")
FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)
STANDS_RE = re.compile(r"^#{1,6}\s.*where\b.*\bstands?\b", re.I | re.M)
DATED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-.*\.md$")
NOW = dt.datetime.now().astimezone()
TODAY = NOW.date()


def setting(value):
    """A configured path, or None while it is still a <placeholder>."""
    if not value or "<" in str(value):
        return None
    return Path(os.path.expandvars(os.path.expanduser(str(value))))


class Paths:
    def __init__(self, workspace=None, notes=None, note=None, code=None):
        self.home = setting(CLAUDE_HOME)
        self.projects = self.home / "projects"
        self.workspace = setting(workspace or WORKSPACE)
        self.code = setting(code or CODE_ROOT)
        self.notes = setting(notes or NOTES_ROOT)
        self.note = setting(note or REPORT_NOTE)
        self.json = setting(JSON_OUT)
        self.notes_l = str(self.notes).lower() if self.notes else None


P = Paths()


# ---------------------------------------------------------------- helpers
def ts_parse(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone()
    except (AttributeError, ValueError):
        return None


def median(xs):
    return statistics.median(xs) if xs else None


def kfmt(n):
    if n is None:
        return "n/a"
    n = float(n)
    for div, unit in ((1e9, " G"), (1e6, " M"), (1e3, " k")):
        if abs(n) >= div:
            return f"{n / div:.{2 if div == 1e9 else 1 if div == 1e6 else 0}f}{unit}"
    return f"{n:.0f}"


def norm_path(p) -> str:
    if not isinstance(p, str) or not p.strip():
        return ""
    s = p.strip().strip('"')
    m = re.match(r"^/([a-zA-Z])/(.*)", s)  # /c/Users/... from Git Bash
    if m and os.name == "nt":
        s = f"{m.group(1)}:/{m.group(2)}"
    return os.path.normcase(os.path.normpath(os.path.expanduser(s)))


_REPO_CACHE: dict = {}


def repo_of(path: str):
    """The git repository below CODE_ROOT a path belongs to (the nearest folder with a .git; a worktree
    under .claude/worktrees/ counts as its repository). None outside CODE_ROOT."""
    if not P.code:
        return None
    root = norm_path(str(P.code))
    p = re.sub(r"[\\/]\.claude[\\/]worktrees[\\/][^\\/]+", "", norm_path(path))
    if not (p == root or p.startswith(root + os.sep)):
        return None
    d, walked, found = p, [], None
    while d.startswith(root) and len(d) >= len(root):
        if d in _REPO_CACHE:
            found = _REPO_CACHE[d]
            break
        walked.append(d)
        if os.path.exists(os.path.join(d, ".git")):
            found = d
            break
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    for w in walked:
        _REPO_CACHE[w] = found
    return os.path.relpath(found, root).replace("\\", "/") if found else None


def vault_folder(path: str, relative=False):
    """The top-level vault folder of a path; '(root)' for a note at the top. None outside the vault."""
    if relative:
        s = (path or "").replace("\\", "/").strip("/")
        return s.split("/")[0] if "/" in s else "(root)"
    if not P.notes_l:
        return None
    p = norm_path(path)
    root = os.path.normcase(os.path.normpath(P.notes_l))
    if not p.startswith(root + os.sep):
        return None
    rest = p[len(root) + 1:]
    return rest.split(os.sep)[0] if os.sep in rest else "(root)"


def connector_kind(name: str) -> str:
    n = name[len(NOTES_TOOL_PREFIX):]
    if "patch" in n or "append" in n:
        return "patch"
    if any(k in n for k in ("write", "delete", "move", "copy", "create", "put")):
        return "write"
    if any(k in n for k in ("read", "get", "list", "search", "map")):
        return "read"
    return "other"


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_human(d) -> bool:
    if d.get("isSidechain") or d.get("isMeta") or d.get("isCompactSummary"):
        return False
    c = (d.get("message") or {}).get("content")
    if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
        return False
    o = d.get("origin")
    if isinstance(o, dict) and o.get("kind"):
        return o["kind"] == "human"
    t = text_of(c).lstrip()  # older transcripts without origin
    return bool(t) and not t.startswith(("<task-notification", "<local-command", "<system-reminder", "Caveat:",
                                         "[Request interrupted", "This session is being continued"))


# ---------------------------------------------------------------- transcripts
class Acc:
    """What one transcript file (the main thread or one subagent) contributes."""

    def __init__(self):
        self.req, self.req_order, self.times = {}, [], []
        self.tools, self.tool_names, self.errors = Counter(), {}, Counter()
        self.reads, self.read_keys, self.files = 0, Counter(), set()
        self.repos, self.vault_folders = set(), set()
        self.connector, self.disk_vault_writes = Counter(), 0
        self.skills, self.commands, self.agents = Counter(), Counter(), Counter()
        self.compactions, self.human, self.cwds = [], 0, Counter()

    def tool_use(self, b):
        name = b.get("name") or "?"
        inp = b.get("input") if isinstance(b.get("input"), dict) else {}
        self.tools[name] += 1
        if b.get("id"):
            self.tool_names[b["id"]] = name
        fp = inp.get("file_path") or inp.get("notebook_path") or inp.get("path")
        connector = bool(NOTES_TOOL_PREFIX) and name.startswith(NOTES_TOOL_PREFIX)
        if name in READ_TOOLS and fp:
            self.reads += 1
            self.read_keys[(norm_path(fp), inp.get("offset"), inp.get("limit"))] += 1
            self.files.add(norm_path(fp))
        if name in DISK_WRITE_TOOLS and fp and vault_folder(fp):
            self.disk_vault_writes += 1
        if fp and not connector:
            r = repo_of(fp)
            if r:
                self.repos.add(r)
            vf = vault_folder(fp)
            if vf:
                self.vault_folders.add(vf)
        if connector:
            self.connector[connector_kind(name)] += 1
            p = inp.get("path")
            if p:
                self.vault_folders.add(vault_folder(p, relative=True))
                if name.endswith("vault_read") or name.endswith("_read"):
                    self.reads += 1
                    tgt = json.dumps(inp.get("target"), sort_keys=True) if inp.get("target") is not None else None
                    self.read_keys[("vault:" + str(p).lower(), tgt, None)] += 1
                    self.files.add("vault:" + str(p).lower())
        if name == "Skill":
            sk = str(inp.get("skill") or "").lstrip("/")
            if sk:
                self.skills[sk] += 1
        if name in ("Agent", "Task"):
            self.agents[inp.get("subagent_type") or "general-purpose"] += 1


def scan_file(path: Path, acc: Acc, main_thread=True):
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            if line.startswith(SKIP_PREFIXES):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = d.get("type")
            if t not in ("user", "assistant", "system"):
                continue
            if main_thread and d.get("isSidechain"):
                continue  # old-style subagent lines inside the main file
            if d.get("timestamp"):
                acc.times.append(d["timestamp"])
            if d.get("cwd"):
                acc.cwds[d["cwd"]] += 1
            if t == "system":
                if d.get("subtype") == "compact_boundary":
                    md = d.get("compactMetadata") or {}
                    acc.compactions.append({"trigger": md.get("trigger") or "?", "pre": md.get("preTokens")})
                continue
            msg = d.get("message") or {}
            if t == "user":
                if is_human(d):
                    acc.human += 1
                c = msg.get("content")
                for cm in CMD_RE.findall(text_of(c)):
                    acc.commands[cm] += 1
                if isinstance(c, list):
                    for b in c:
                        if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                            acc.errors[acc.tool_names.get(b.get("tool_use_id"), "?")] += 1
                continue
            u = msg.get("usage") or {}
            rid = d.get("requestId") or msg.get("id") or d.get("uuid")
            if u and msg.get("model") != "<synthetic>":
                vals = [u.get("input_tokens") or 0, u.get("cache_creation_input_tokens") or 0,
                        u.get("cache_read_input_tokens") or 0, u.get("output_tokens") or 0]
                if rid in acc.req:
                    acc.req[rid] = [max(a, b) for a, b in zip(acc.req[rid], vals)]
                else:
                    acc.req[rid] = vals
                    acc.req_order.append(rid)
            for b in msg.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    acc.tool_use(b)


def active_seconds(times):
    ts = sorted(x for x in (ts_parse(t) for t in times) if x)
    if len(ts) < 2:
        return 0, (ts[0] if ts else None)
    cap = T["idle_gap_min"] * 60
    return sum(g for g in ((b - a).total_seconds() for a, b in zip(ts, ts[1:])) if g <= cap), ts[0]


def session_record(path: Path, project: str, installed_skills: set):
    acc = Acc()
    scan_file(path, acc, main_thread=True)
    calls = [acc.req[r] for r in acc.req_order if sum(acc.req[r][:3]) > 0]
    if not calls:
        return None
    desks = [c[0] + c[1] + c[2] for c in calls]
    act, start = active_seconds(acc.times)
    sub = {"calls": 0, "tokens": 0, "types": Counter(), "errors": Counter(), "connector": Counter(), "disk": 0}
    sub_dir = path.with_suffix("") / "subagents"
    if sub_dir.is_dir():
        for f in sorted(sub_dir.glob("agent-*.jsonl")):
            a = Acc()
            scan_file(f, a, main_thread=False)
            sc = [a.req[r] for r in a.req_order if sum(a.req[r][:3]) > 0]
            typ = "unknown"
            try:
                typ = json.loads(f.with_name(f.stem + ".meta.json").read_text(encoding="utf-8")).get("agentType") or typ
            except (OSError, ValueError):
                pass
            sub["types"][typ] += 1
            sub["calls"] += len(sc)
            sub["tokens"] += sum(sum(c) for c in sc)
            sub["errors"].update(a.errors)
            sub["connector"].update(a.connector)
            sub["disk"] += a.disk_vault_writes
            acc.repos |= a.repos
            acc.vault_folders |= a.vault_folders
            acc.skills.update(a.skills)
    if not sub["types"] and acc.agents:
        sub["types"] = acc.agents  # older transcripts: subagents only visible as Agent calls
    skills = Counter(acc.skills)
    for cm, n in acc.commands.items():
        if cm in installed_skills:
            skills[cm] += n
    repos = set(acc.repos) | {r for r in (repo_of(c) for c in acc.cwds) if r}
    keys = len(acc.read_keys)
    conn = acc.connector + sub["connector"]
    fails = sum(n for k, n in (acc.errors + sub["errors"]).items() if NOTES_TOOL_PREFIX and k.startswith(NOTES_TOOL_PREFIX))
    main_tokens = sum(sum(c) for c in calls)
    return {
        "id": path.stem, "project": project, "start": start.isoformat() if start else None,
        "active_min": round(act / 60, 1), "human_turns": acc.human, "api_calls": len(calls),
        "tok_in": sum(c[0] + c[1] for c in calls), "tok_cached": sum(c[2] for c in calls),
        "tok_out": sum(c[3] for c in calls), "tok_main": main_tokens,
        "sub_calls": sub["calls"], "sub_tokens": sub["tokens"], "tokens": main_tokens + sub["tokens"],
        "first_context": desks[0], "peak_context": max(desks), "compactions": acc.compactions,
        "subagents": dict(sub["types"].most_common()), "reads": acc.reads, "distinct_read_windows": keys,
        "reread_ratio": round(acc.reads / keys, 2) if keys else None,
        "connector_calls": sum(conn.values()), "connector_writes": conn["patch"] + conn["write"],
        "connector_failures": fails, "disk_vault_writes": acc.disk_vault_writes + sub["disk"],
        "repos": sorted(repos), "skills": dict(skills),
        "save_step": any(s in SAVE_SKILLS for s in skills),
    }


def transcript_files():
    if not P.projects.is_dir():
        return []
    return [f for proj in sorted(P.projects.iterdir()) if proj.is_dir() for f in sorted(proj.glob("*.jsonl"))]


def collect_sessions(installed_skills: set):
    out = []
    for f in transcript_files():
        try:
            r = session_record(f, f.parent.name, installed_skills)
        except Exception as e:  # one unreadable transcript must not stop the run
            print(f"skipped {f.name}: {e}", file=sys.stderr)
            continue
        if r:
            out.append(r)
    return sorted(out, key=lambda s: s["start"] or "")


# ---------------------------------------------------------------- configuration
def text_stats(p: Path):
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return {"path": str(p), "lines": t.count("\n") + (0 if t.endswith("\n") else 1),
            "kb": round(len(t.encode("utf-8")) / 1024, 1), "tokens_est": round(len(t) / 4)}


def frontmatter(text: str) -> dict:
    m = FM_RE.match(text)
    out, key = {}, None
    for ln in (m.group(1).splitlines() if m else []):
        mm = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", ln)
        if mm:
            key = mm.group(1)
            out[key] = mm.group(2).strip().strip('"').strip("'")
        elif key and ln.startswith((" ", "\t")):
            out[key] = (out[key] + " " + ln.strip()).strip()
    return out


def load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def memory_dir():
    """Claude Code keeps a project's auto memory under projects/<the path with every other character as ->/memory."""
    if not P.workspace:
        return None
    return P.projects / re.sub(r"[^A-Za-z0-9]", "-", str(P.workspace).rstrip("\\/")) / "memory"


def collect_config() -> dict:
    ws = P.workspace
    claude_md = [P.home / "CLAUDE.md"] + ([ws / "CLAUDE.md"] if ws else [])
    cm = [s for s in (text_stats(p) for p in claude_md if p.is_file()) if s]
    ctx = [s for s in (text_stats(p) for p in sorted((ws / ".claude" / "context").glob("*.md"))) if s] if ws else []
    user_set = load_json(P.home / "settings.json")
    proj_set = load_json(ws / ".claude" / "settings.json") if ws else {}
    overrides = dict(user_set.get("skillOverrides") or {})
    overrides.update(proj_set.get("skillOverrides") or {})
    skills = []
    roots = [("personal", P.home / "skills")] + ([("project", ws / ".claude" / "skills")] if ws else [])
    for scope, root in roots:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            f = d / "SKILL.md"
            if not f.is_file():
                continue
            fm = frontmatter(f.read_text(encoding="utf-8", errors="replace"))
            name = fm.get("name") or d.name
            state = overrides.get(name) or "on"
            if fm.get("disable-model-invocation", "").lower() == "true" and state == "on":
                state = "typed"
            created = dt.datetime.fromtimestamp(f.stat().st_mtime).astimezone()
            skills.append({"name": name, "scope": scope, "state": state, "desc_chars": len(fm.get("description", "")),
                           "age_days": (NOW - created).days})
    mem = memory_dir()
    return {
        "claude_md": cm, "context_files": ctx, "skills": skills,
        "skills_by_state": dict(Counter(s["state"] for s in skills)),
        "skill_listing_chars": sum(s["desc_chars"] for s in skills if s["state"] == "on"),
        "memory_index": text_stats(mem / "MEMORY.md") if mem else None,
        "memory_files": len([f for f in mem.glob("*.md") if f.name != "MEMORY.md"]) if mem and mem.is_dir() else 0,
        "auto_compact": user_set.get("autoCompactEnabled"),
    }


# ---------------------------------------------------------------- vault
def last_edit(text: str, name: str) -> str:
    """The archive rule's date: date-modified, else date-created, else the file name (archive_notes.py)."""
    fm = frontmatter(text)
    for key in ("date-modified", "date-created"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", fm.get(key, ""))
        if m:
            return m.group(1)
    return name[:10]


def collect_vault() -> dict:
    if not P.notes or not P.notes.is_dir():
        return {"notes": 0, "missing": True}
    notes, online_only, stack = {}, 0, [P.notes]
    while stack:  # one folder at a time: list it, read its notes, then its subfolders
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            if e.is_dir(follow_symlinks=False):
                if e.name not in SKIP_FOLDERS and not e.name.startswith("."):
                    stack.append(Path(e.path))
                continue
            if not e.name.lower().endswith(".md"):
                continue
            st = e.stat()
            rel = os.path.relpath(e.path, P.notes).replace("\\", "/")
            info = {"rel": rel, "folder": rel.split("/")[0] if "/" in rel else "(root)", "kb": st.st_size / 1024,
                    "type": None, "out": set(), "stands": False, "read": False, "last_edit": None}
            notes[rel] = info
            if getattr(st, "st_file_attributes", 0) & ONLINE_ONLY:
                online_only += 1
                continue
            try:
                with open(e.path, encoding="utf-8", errors="replace") as fh:
                    t = fh.read()
            except OSError:
                continue
            info.update(read=True, type=frontmatter(t).get("type") or None, stands=bool(STANDS_RE.search(t)),
                        last_edit=last_edit(t, e.name))
            for m in LINK_RE.findall(t):
                tgt = m.strip().replace("\\", "/").split("/")[-1]
                if "." not in tgt or tgt.lower().endswith(".md"):
                    info["out"].add(tgt.lower()[:-3] if tgt.lower().endswith(".md") else tgt.lower())
            for m in MDLINK_RE.findall(t):
                tgt = m.replace("%20", " ").replace("\\", "/").split("/")[-1].lower()
                info["out"].add(tgt[:-3])
    by_name = defaultdict(list)
    for rel in notes:
        by_name[rel.split("/")[-1].lower()[:-3]].append(rel)
    inbound = Counter()
    for rel, info in notes.items():
        me = rel.split("/")[-1].lower()[:-3]
        for tgt in info["out"]:
            if tgt != me:
                for r2 in by_name.get(tgt, []):
                    inbound[r2] += 1
    folders = defaultdict(lambda: {"notes": 0, "kb": 0.0, "no_type": 0, "orphans": 0})
    big, knowledge, orphans = [], 0, 0
    for rel, i in notes.items():
        f = folders[i["folder"]]
        f["notes"] += 1
        f["kb"] += i["kb"]
        if not i["read"]:
            continue
        f["no_type"] += not i["type"]
        if i["kb"] > T["big_note_kb"]:
            big.append({"note": rel, "kb": round(i["kb"]), "where_this_stands": i["stands"]})
        if i["folder"] not in NOT_KNOWLEDGE:
            knowledge += 1
            if not inbound[rel]:
                f["orphans"] += 1
                orphans += 1
    for f in folders.values():
        f["kb"] = round(f["kb"])
    agent = setting(AGENT_NOTES) and AGENT_NOTES
    cutoff = (TODAY - dt.timedelta(days=T["agent_note_days"])).isoformat()
    due = sorted(rel for rel, i in notes.items()
                 if agent and rel.count("/") == 1 and rel.split("/")[0] == agent and DATED_RE.match(rel.split("/")[1])
                 and (i["last_edit"] or rel.split("/")[1][:10]) < cutoff and not rel.split("/")[1].startswith(TODAY.isoformat()))
    inbox = setting(INBOX) and sum(1 for rel in notes if rel.count("/") == 1 and rel.split("/")[0] == INBOX)
    return {
        "notes": len(notes), "online_only": online_only, "knowledge_notes": knowledge, "orphans": orphans,
        "orphan_share": round(orphans / knowledge, 3) if knowledge else None,
        "folders": dict(sorted(folders.items())), "big_notes": sorted(big, key=lambda b: -b["kb"]),
        "agent_notes_due": due, "inbox": inbox if setting(INBOX) else None,
    }


# ---------------------------------------------------------------- aggregation and recommendations
def window(ss, days_from, days_to):
    lo, hi = NOW - dt.timedelta(days=days_from), NOW - dt.timedelta(days=days_to)
    return [s for s in ss if s["start"] and lo <= ts_parse(s["start"]) < hi]


def aggregate(ss) -> dict:
    if not ss:
        return {"sessions": 0}
    reads = sum(s["reads"] for s in ss)
    keys = sum(s["distinct_read_windows"] for s in ss)
    comps = [c for s in ss for c in s["compactions"]]
    skills, subs = Counter(), Counter()
    for s in ss:
        skills.update(s["skills"])
        subs.update(s["subagents"])
    return {
        "sessions": len(ss), "human_turns": sum(s["human_turns"] for s in ss),
        "calls_per_human_turn": round(sum(s["api_calls"] for s in ss) / max(1, sum(s["human_turns"] for s in ss)), 1),
        "active_min_median": median([s["active_min"] for s in ss]),
        "tokens_median": median([s["tokens"] for s in ss]), "tokens_sum": sum(s["tokens"] for s in ss),
        "sub_tokens_sum": sum(s["sub_tokens"] for s in ss),
        "peak_median": median([s["peak_context"] for s in ss]),
        "fixed_start_median": median([s["first_context"] for s in ss]),
        "over_split": sum(1 for s in ss if s["peak_context"] > T["split_share"] * CONTEXT_WINDOW),
        "compactions": len(comps), "compactions_auto": sum(1 for c in comps if c["trigger"] == "auto"),
        "reads": reads, "reread_ratio": round(reads / keys, 2) if keys else None,
        "connector_calls": sum(s["connector_calls"] for s in ss),
        "connector_writes": sum(s["connector_writes"] for s in ss),
        "connector_failures": sum(s["connector_failures"] for s in ss),
        "disk_vault_writes": sum(s["disk_vault_writes"] for s in ss),
        "drift_sessions": sum(1 for s in ss if len(s["repos"]) > T["repos_per_session"]),
        "save_step_sessions": sum(1 for s in ss if s["save_step"]),
        "skills": dict(skills.most_common()), "subagents": dict(subs.most_common()),
    }


def recommendations(a7, a30, ss, cfg, vault) -> list:
    R = []
    add = lambda rid, level, title, detail: R.append({"id": rid, "level": level, "title": title, "detail": detail})  # noqa: E731
    last7 = window(ss, 7, 0)
    if a30.get("reread_ratio") and a30["reread_ratio"] > T["reread_ratio"]:
        add("reread", "act", "Read sections, not whole files",
            f"re-read ratio {a30['reread_ratio']:.2f} over 30 days (threshold {T['reread_ratio']})")
    split, end = T["split_share"] * CONTEXT_WINDOW, T["plan_end_share"] * CONTEXT_WINDOW
    big = [s for s in last7 if s["peak_context"] > split]
    if big:
        w = max(big, key=lambda s: s["peak_context"])
        add("split", "act", "Split long sessions by task",
            f"{len(big)} session(s) this week peaked above {kfmt(split)} context; largest {kfmt(w['peak_context'])} ({w['id'][:8]})")
    over = [s for s in last7 if s["peak_context"] > end]
    if over:
        add("plan-end", "act", "Plan the end of a long session",
            f"{len(over)} session(s) passed {kfmt(end)}: such a session runs the save step and writes a handover")
    drift = [s for s in last7 if len(s["repos"]) > T["repos_per_session"]]
    if drift:
        w = max(drift, key=lambda s: len(s["repos"]))
        add("drift", "watch", "Sessions drift across repositories",
            f"{len(drift)} session(s) touched more than {T['repos_per_session']} repositories; most: {len(w['repos'])} in {w['id'][:8]}")
    comps = [(s, c) for s in last7 for c in s["compactions"]]
    if comps:
        unsaved = sum(1 for s, _ in comps if not s["save_step"])
        add("compaction", "act" if unsaved else "watch", "Save before compaction",
            f"{len(comps)} compaction(s) this week ({sum(1 for _, c in comps if c['trigger'] == 'auto')} automatic); "
            f"{unsaved} in a session that ran no save step")
    fs = a7.get("fixed_start_median")
    if T["fixed_start"] and fs and fs > T["fixed_start"]:
        add("fixed-start", "act", "Trim the fixed start",
            f"median first-call context {kfmt(fs)} this week (threshold {kfmt(T['fixed_start'])})")
    if a7.get("connector_calls") and a7["connector_failures"] / a7["connector_calls"] > T["connector_fail_share"]:
        add("connector-fail", "watch", "Notes-connector calls fail",
            f"{a7['connector_failures']} of {a7['connector_calls']} calls failed this week")
    if a7.get("disk_vault_writes"):
        add("disk-writes", "watch", "Vault written on disk",
            f"{a7['disk_vault_writes']} on-disk vault write(s) this week against {a7['connector_writes']} through the connector")
    if vault.get("orphan_share") is not None and vault["orphan_share"] > T["orphan_share"]:
        worst = max(vault["folders"].items(), key=lambda kv: kv[1]["orphans"])
        add("orphans", "act", "Link the orphans",
            f"{vault['orphan_share']:.0%} of {vault['knowledge_notes']} knowledge notes have no inbound link "
            f"(threshold {T['orphan_share']:.0%}); most in {worst[0]} ({worst[1]['orphans']})")
    nostand = [b for b in vault.get("big_notes", []) if not b["where_this_stands"]]
    if nostand:
        add("big-notes", "act", "Give long notes a top section",
            f"{len(nostand)} note(s) over {T['big_note_kb']} KB without a \"where this stands\" heading: "
            + ", ".join(f"{b['note'].split('/')[-1][:-3]} ({b['kb']} KB)" for b in nostand[:4]))
    if vault.get("agent_notes_due"):
        add("archive", "act", "Archive the quiet agent notes",
            f"{len(vault['agent_notes_due'])} note(s) last edited more than {T['agent_note_days']} days ago are still on top")
    used = Counter()
    for s in window(ss, T["skill_idle_days"], 0):
        used.update(s["skills"])
    idle = sorted(s["name"] for s in cfg["skills"]
                  if s["state"] == "on" and s["age_days"] >= T["skill_idle_days"] and not used.get(s["name"]))
    if idle and ss and ts_parse(ss[0]["start"]) < NOW - dt.timedelta(days=T["skill_idle_days"]):
        add("idle-skills", "watch", f"Skills not invoked in {T['skill_idle_days']} days",
            f"{len(idle)} skill(s) listed in every session and never invoked: {', '.join(idle)}; candidates for name-only")
    long_ctx = [c for c in cfg["context_files"] if c["lines"] > T["context_file_lines"] and "changelog" not in c["path"]]
    if long_ctx:
        add("context-size", "watch", f"Reference files past {T['context_file_lines']} lines",
            ", ".join(f"{Path(c['path']).name} ({c['lines']})" for c in long_ctx) + "; offer a restructure")
    return R


# ---------------------------------------------------------------- the note
def md_table(head, rows):
    esc = lambda x: str(x).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "|".join([" --- "] * len(head)) + "|"]
                     + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def fmt(v, kind):
    if v is None:
        return "n/a"
    return kfmt(v) if kind == "k" else f"{v:.2f}" if kind == "f" else f"{v:,.0f}"


def build_note(d) -> str:
    a7, ap, a30, cfg, vault, R = d["last7"], d["prev7"], d["last30"], d["config"], d["vault"], d["recommendations"]
    rows = [(name, fmt(a7.get(k), kind), fmt(ap.get(k), kind)) for name, k, kind in (
        ("Sessions", "sessions", "n"), ("Human turns", "human_turns", "n"),
        ("Active minutes per session, median", "active_min_median", "n"),
        ("Tokens per session, median", "tokens_median", "k"), ("Tokens, all sessions", "tokens_sum", "k"),
        ("Peak context, median", "peak_median", "k"), ("Fixed start, median", "fixed_start_median", "k"),
        (f"Sessions above {kfmt(T['split_share'] * CONTEXT_WINDOW)} context", "over_split", "n"),
        ("Compactions", "compactions", "n"), ("Re-read ratio", "reread_ratio", "f"),
        ("API calls per human turn", "calls_per_human_turn", "f"),
        ("Vault writes through the connector", "connector_writes", "n"), ("Vault writes on disk", "disk_vault_writes", "n"))]
    L = ["---", "type: reference", f"date-modified: {NOW.strftime('%Y-%m-%dT%H:%M:%S')}", "---", "",
         f"Written by `workflow_health.py` on {NOW.strftime('%Y-%m-%d %H:%M')}. The whole note is rewritten on every "
         "run; edit the script, not the note.", "", "# Workflow Health", "", "## This week", "",
         "Last 7 days against the 7 days before. Tokens include subagents; an application programming interface "
         "(API) call is one request to the model.", "",
         md_table(["Measure", "Last 7 days", "7 days before"], rows), "", "## Recommendations", ""]
    L += [f"- **{r['title']}** ({r['level']}): {r['detail']}." for r in R] or ["- None fired."]
    L += ["", "## Judgement", "", "_Empty until the workflow-health skill is run; the next run clears it._", "",
          "## Sessions, last 7 days", ""]
    srows = [[(s["start"] or "")[:16].replace("T", " "), s["id"][:8], s["human_turns"], f"{s['active_min']:.0f}",
              kfmt(s["tokens"]), kfmt(s["peak_context"]), len(s["compactions"]),
              s["reread_ratio"] if s["reread_ratio"] is not None else "", len(s["repos"]),
              ", ".join(f"{k} {v}" for k, v in s["subagents"].items()), "yes" if s["save_step"] else ""]
             for s in d["sessions_last7"]]
    L += [md_table(["Start", "Session", "Turns", "Active min", "Tokens", "Peak", "Compactions", "Re-read",
                    "Repositories", "Subagents", "Save step"], srows) if srows else "No sessions.", ""]
    L += ["## Last 30 days", "",
          f"{a30.get('sessions', 0)} sessions, {kfmt(a30.get('tokens_sum'))} tokens, of them subagents "
          f"{kfmt(a30.get('sub_tokens_sum'))}; {a30.get('compactions', 0)} compactions "
          f"({a30.get('compactions_auto', 0)} automatic); re-read ratio {a30.get('reread_ratio')}; "
          f"{a30.get('drift_sessions', 0)} sessions in more than {T['repos_per_session']} repositories.", "",
          "Skills invoked: " + (", ".join(f"{k} {v}" for k, v in list(a30.get("skills", {}).items())[:20]) or "none") + ".", "",
          "Subagents: " + (", ".join(f"{k} {v}" for k, v in a30.get("subagents", {}).items()) or "none") + ".", "",
          "## Configuration", ""]
    crow = [[c["path"].replace(str(Path.home()), "~"), c["lines"], c["kb"]] for c in cfg["claude_md"]]
    if cfg.get("memory_index"):
        crow.append(["MEMORY.md (auto-memory index)", cfg["memory_index"]["lines"], cfg["memory_index"]["kb"]])
    crow += [[Path(c["path"]).name, c["lines"], c["kb"]] for c in sorted(cfg["context_files"], key=lambda c: -c["lines"])]
    sb = cfg["skills_by_state"]
    L += [md_table(["File", "Lines", "KB"], crow), "",
          f"Skills: {len(cfg['skills'])} ({', '.join(f'{k} {v}' for k, v in sorted(sb.items()))}); the descriptions of the "
          f"\"on\" ones are {cfg['skill_listing_chars']:,} characters. Memory: {cfg['memory_files']} files. Auto-compact: "
          f"{'off' if cfg['auto_compact'] is False else 'on'}.", "", "## Vault", ""]
    if vault.get("missing"):
        L += ["No vault configured (NOTES_ROOT).", ""]
    else:
        L += [f"{vault['notes']} notes; {vault['online_only']} online-only and not read; {vault['orphans']} of "
              f"{vault['knowledge_notes']} knowledge notes are orphans ({(vault['orphan_share'] or 0):.0%})"
              + (f"; inbox {vault['inbox']}" if vault.get("inbox") is not None else "")
              + f"; {len(vault['agent_notes_due'])} agent notes due for the archive.", "",
              md_table(["Folder", "Notes", "KB", "No type", "Orphans"],
                       [[k, v["notes"], v["kb"], v["no_type"], v["orphans"]] for k, v in vault["folders"].items()]), ""]
        if vault["big_notes"]:
            L += [md_table([f"Note over {T['big_note_kb']} KB", "KB", "Where-this-stands heading"],
                           [[b["note"], b["kb"], "yes" if b["where_this_stands"] else "no"] for b in vault["big_notes"]]), ""]
    L += ["## Definitions", "",
          "- **Context**: the input, cache-write and cache-read tokens of one API call: everything the model read on it.",
          "- **Peak context**: the largest context of one main-thread call in the session.",
          "- **Fixed start**: the context of a session's first call: system prompt, tools, rules files, memory index, "
          "skill list, plus the first prompt.",
          "- **Tokens**: input, cache-write, cache-read and output tokens of every call in the transcripts, subagents "
          "included; a lower bound.",
          "- **Human turn**: a line the person typed, or a slash command.",
          f"- **Active time**: the gaps between transcript records shorter than {T['idle_gap_min']} minutes.",
          "- **Re-read ratio**: reads divided by distinct (file, window) pairs; 1.0 means nothing was read twice.",
          "- **Knowledge note**: a note outside the folders in NOT_KNOWLEDGE; an orphan has no link from another note.",
          "", "Thresholds: " + ", ".join(f"{k} {v}" for k, v in T.items()) + f"; context window {kfmt(CONTEXT_WINDOW)}.", ""]
    return "\n".join(L)


def collect() -> dict:
    cfg = collect_config()
    ss = collect_sessions({s["name"] for s in cfg["skills"]})
    vault = collect_vault()
    d = {"generated": NOW.isoformat(), "thresholds": T, "context_window": CONTEXT_WINDOW,
         "sessions_total": len(ss), "last7": aggregate(window(ss, 7, 0)), "prev7": aggregate(window(ss, 14, 7)),
         "last30": aggregate(window(ss, 30, 0)), "sessions_last7": window(ss, 7, 0), "config": cfg, "vault": vault}
    d["recommendations"] = recommendations(d["last7"], d["last30"], ss, cfg, vault)
    return d


def session_cost(prefix: str) -> int:
    files = transcript_files()
    if prefix != "latest":
        files = [f for f in files if f.stem.startswith(prefix)]
    if not files:
        print("no such session")
        return 1
    f = max(files, key=lambda x: x.stat().st_mtime)
    s = session_record(f, f.parent.name, set())
    if not s:
        print(f"{f.stem[:8]}: no API calls yet")
        return 0
    print(f"session {s['id'][:8]}: {s['api_calls']} API calls, peak context {kfmt(s['peak_context'])}, tokens "
          f"{kfmt(s['tokens'])} (uncached input {kfmt(s['tok_in'])}, cache reads {kfmt(s['tok_cached'])}, output "
          f"{kfmt(s['tok_out'])}, subagents {kfmt(s['sub_tokens'])}), {s['reads']} reads, {s['active_min']:.0f} active minutes")
    return 0


def main(argv=None) -> int:
    global P
    ap = argparse.ArgumentParser(description="Measure the agent workflow without a model.")
    ap.add_argument("--no-write", action="store_true", help="measure and print; write nothing")
    ap.add_argument("--workspace", help="the workspace folder (default: WORKSPACE)")
    ap.add_argument("--notes", help="the notes vault (default: NOTES_ROOT)")
    ap.add_argument("--note", help="the report note inside the vault (default: REPORT_NOTE)")
    ap.add_argument("--code", help="the code root (default: CODE_ROOT)")
    ap.add_argument("--session-cost", nargs="?", const="latest", metavar="SESSION_ID",
                    help="print the cost so far of one session (default: the newest transcript) and stop")
    args = ap.parse_args(argv)
    P = Paths(args.workspace, args.notes, args.note, args.code)
    if args.session_cost:
        return session_cost(args.session_cost)
    d = collect()
    a7 = d["last7"]
    print(f"sessions {d['sessions_total']} in all; last 7 days {a7.get('sessions', 0)}, tokens {kfmt(a7.get('tokens_sum'))}, "
          f"peak median {kfmt(a7.get('peak_median'))}, fixed start median {kfmt(a7.get('fixed_start_median'))}, "
          f"re-read {a7.get('reread_ratio')}; vault {d['vault'].get('notes', 0)} notes")
    for r in d["recommendations"]:
        print(f"  [{r['level']}] {r['title']}: {r['detail']}")
    if args.no_write:
        return 0
    if not (P.notes and P.note):
        print("Set NOTES_ROOT and REPORT_NOTE (or --notes and --note) to write the note; nothing written.", file=sys.stderr)
        return 2
    target = P.notes / P.note
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_note(d), encoding="utf-8")
    if P.json:
        P.json.parent.mkdir(parents=True, exist_ok=True)
        P.json.write_text(json.dumps({k: v for k, v in d.items()}, indent=1, default=str), encoding="utf-8")
    print(f"written: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
