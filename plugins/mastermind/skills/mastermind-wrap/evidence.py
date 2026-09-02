#!/usr/bin/env python3
"""Evidence collector for /mastermind:wrap.

Prints a Markdown report with deterministic sources for "what happened since the last wrap":
  1. git log / status of the project since --since
  2. Claude auto-memory files of this project changed since --since
  3. best-effort timeline of the current session from the Claude Code transcript (JSONL)

Everything is optional: a missing source is reported as "nicht gefunden", never as a failure.
Python 3 standard library only. Exit code is always 0.
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_COMMITS = 40
MAX_STATUS = 30
MAX_PROMPTS = 40
MAX_FILES = 40
MAX_COMMANDS = 30
MAX_ERRORS = 15
CLIP_PROMPT = 220
CLIP_LINE = 160
ERROR_RE = re.compile(r"(error|exception|traceback|failed|FAIL\b|ENOENT|EACCES|denied|fatal:)", re.I)
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{10,}|xox[abp]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{12,}"
                       r"|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
DIGEST_MAX_CHARS = 40000
DIGEST_CLIP_USER = 400
DIGEST_CLIP_CLAUDE = 600


def run(cmd, cwd=None, keep_indent=False):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return ""
        return r.stdout.rstrip("\n") if keep_indent else r.stdout.strip()
    except Exception:
        return ""


def clip(s, n):
    s = " ".join(str(s).split())
    s = SECRET_RE.sub("[SECRET ENTFERNT]", s)
    return s if len(s) <= n else s[: n - 1] + "…"


def parse_since(s):
    s = (s or "").strip().strip("'\"").strip()
    if not s or s.lower() in ("none", "null", "never", "~"):
        return None
    for fmt, n in (("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return dt.datetime.strptime(s[:n], fmt)
        except Exception:
            continue
    return None


def project_root(cwd):
    top = run(["git", "rev-parse", "--show-toplevel"], cwd)
    if not top:
        return None, None
    root = top
    common = run(["git", "rev-parse", "--git-common-dir"], cwd)
    if common:
        cp = Path(common)
        if not cp.is_absolute():
            cp = Path(top) / cp
        cp = cp.resolve()
        if cp.name == ".git":
            root = str(cp.parent)
    return top, root


def slug(path):
    return re.sub(r"[^A-Za-z0-9-]", "-", str(path))


def section_git(cwd, since):
    top, root = project_root(cwd)
    out = ["## Git"]
    if not top:
        out.append("- nicht gefunden (kein Git-Repo)")
        return out, None
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    remote = run(["git", "remote", "get-url", "origin"], cwd)
    out.append(f"- Root: `{root}`" + (f" (Worktree: `{top}`)" if top != root else ""))
    out.append(f"- Branch: `{branch or '?'}`" + (f" · Remote: `{remote}`" if remote else ""))
    args = ["git", "log", "--format=%h %ad %s", "--date=short", f"-n{MAX_COMMITS}"]
    if since:
        args.insert(2, f"--since={since.strftime('%Y-%m-%d')}")
    else:
        args.insert(2, "--since=24 hours ago")
    log = run(args, cwd)
    label = f"seit {since.strftime('%Y-%m-%d')}" if since else "letzte 24 h"
    out.append(f"- Commits ({label}):")
    out.extend([f"  - {l}" for l in log.splitlines()] if log else ["  - keine"])
    status = run(["git", "status", "--short"], cwd, keep_indent=True)
    lines = [l for l in status.splitlines() if l.strip()]
    out.append(f"- Working tree: {len(lines)} geänderte/neue Dateien" + (":" if lines else ""))
    out.extend(f"  - {l}" for l in lines[:MAX_STATUS])
    if len(lines) > MAX_STATUS:
        out.append(f"  - … {len(lines) - MAX_STATUS} weitere")
    return out, root


def read_memory_meta(path):
    """name/description/modified from an auto-memory file's frontmatter (best effort)."""
    meta = {"description": "", "modified": None}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return meta
    if text.startswith("---"):
        end = text.find("\n---", 3)
        head = text[3:end] if end != -1 else ""
        m = re.search(r"^description:\s*(.+)$", head, re.M)
        if m:
            meta["description"] = m.group(1).strip().strip("'\"")
        m = re.search(r"modified:\s*(\S+)", head)
        if m:
            try:
                meta["modified"] = dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
    return meta


def section_memory(cwd, root, since):
    out = ["## Auto-Memory dieses Projekts"]
    candidates = []
    for p in [root, cwd]:
        if p:
            candidates.append(Path.home() / ".claude" / "projects" / slug(p) / "memory")
    mem = next((c for c in candidates if c.is_dir()), None)
    if not mem:
        out.append("- nicht gefunden")
        return out
    out.append(f"- Verzeichnis: `{mem}`")
    rows = []
    for f in sorted(mem.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        meta = read_memory_meta(f)
        mtime = meta["modified"] or dt.datetime.fromtimestamp(f.stat().st_mtime)
        if since is None or mtime >= since:
            rows.append((mtime, f.name, meta["description"]))
    rows.sort(reverse=True)
    label = f"seit {since.strftime('%Y-%m-%d')}" if since else "gesamt"
    out.append(f"- Geänderte Dateien ({label}): {len(rows)}")
    for mtime, name, desc in rows[:MAX_FILES]:
        out.append(f"  - {mtime.strftime('%Y-%m-%d')} `{name}` — {clip(desc, CLIP_LINE) if desc else '(ohne Beschreibung)'}")
    return out


def find_transcript(session_id, cwd, root):
    """Locate this session's transcript; falls back to env and to the newest transcript of the project."""
    base = Path.home() / ".claude" / "projects"
    sid = (session_id or "").strip()
    if not sid or sid.startswith("$"):  # placeholder not substituted (e.g. remote sessions)
        sid = os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    if sid:
        for p in [root, cwd]:
            if p:
                f = base / slug(p) / f"{sid}.jsonl"
                if f.is_file():
                    return f
        try:
            hits = list(base.glob(f"*/{sid}.jsonl"))
            if hits:
                return hits[0]
        except Exception:
            pass
    for p in [root, cwd]:
        if not p:
            continue
        d = base / slug(p)
        try:
            newest = max(d.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, default=None)
        except Exception:
            newest = None
        if newest:
            return newest
    return None


def local_hhmm(ts):
    """Transcript timestamps are ISO-8601 UTC; show local wall-clock time."""
    try:
        d = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d.astimezone().strftime("%H:%M")
    except Exception:
        return str(ts)[11:16]


def block_text(content):
    """Flatten a tool_result/text content (str or list of blocks) to one string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(str(b.get("text", "")))
            elif isinstance(b, str):
                parts.append(b)
        return "\n".join(parts)
    return ""


def section_timeline(transcript):
    out = ["## Session-Zeitachse (Transkript, best effort)"]
    if not transcript:
        out.append("- nicht gefunden (Session-ID oder Transkript unbekannt)")
        return out
    prompts, files, commands, errors = [], [], [], []
    seen_files = set()
    try:
        with open(transcript, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("isSidechain"):
                    continue
                t = o.get("type")
                msg = o.get("message") if isinstance(o.get("message"), dict) else None
                if not msg:
                    continue
                ts = local_hhmm(o.get("timestamp", ""))
                content = msg.get("content")
                if t == "user":
                    if o.get("isMeta"):
                        continue
                    if isinstance(content, str):
                        txt = content.strip()
                        if txt and not txt.startswith(("<", "[Request interrupted")):
                            prompts.append((ts, clip(txt, CLIP_PROMPT)))
                    elif isinstance(content, list):
                        for b in content:
                            if not isinstance(b, dict):
                                continue
                            if b.get("type") == "text":
                                txt = str(b.get("text", "")).strip()
                                if txt and not txt.startswith(("<", "[Request interrupted")):
                                    prompts.append((ts, clip(txt, CLIP_PROMPT)))
                            elif b.get("type") == "tool_result":
                                txt = block_text(b.get("content"))
                                if b.get("is_error") or ERROR_RE.search(txt[:2000]):
                                    for l in txt.splitlines():
                                        if ERROR_RE.search(l):
                                            errors.append((ts, clip(l, CLIP_LINE)))
                                            break
                elif t == "assistant" and isinstance(content, list):
                    for b in content:
                        if not isinstance(b, dict) or b.get("type") != "tool_use":
                            continue
                        name = b.get("name", "")
                        inp = b.get("input") or {}
                        if name in EDIT_TOOLS and isinstance(inp, dict):
                            fp = inp.get("file_path") or inp.get("notebook_path")
                            if fp and fp not in seen_files:
                                seen_files.add(fp)
                                files.append(fp)
                        elif name == "Bash" and isinstance(inp, dict):
                            desc = inp.get("description") or clip(inp.get("command", ""), 80)
                            if desc:
                                commands.append((ts, clip(desc, 100)))
    except Exception as e:
        out.append(f"- Transkript nur teilweise lesbar: {e}")
    out.append(f"- Datei: `{transcript}`")
    out.append(f"- User-Prompts ({len(prompts)}):")
    shown = prompts if len(prompts) <= MAX_PROMPTS else prompts[:MAX_PROMPTS // 2] + [("…", f"… {len(prompts) - MAX_PROMPTS} ausgelassen …")] + prompts[-MAX_PROMPTS // 2:]
    out.extend(f"  - {ts} {p}" for ts, p in shown)
    out.append(f"- Editierte Dateien ({len(files)}):")
    out.extend(f"  - {f}" for f in files[:MAX_FILES])
    if len(files) > MAX_FILES:
        out.append(f"  - … {len(files) - MAX_FILES} weitere")
    out.append(f"- Befehle ({len(commands)}, letzte {min(len(commands), MAX_COMMANDS)}):")
    out.extend(f"  - {ts} {c}" for ts, c in commands[-MAX_COMMANDS:])
    out.append(f"- Fehlerzeilen aus Tool-Ergebnissen ({len(errors)}):")
    out.extend(f"  - {ts} {e}" for ts, e in errors[:MAX_ERRORS])
    return out


def section_digest(transcript, max_chars=DIGEST_MAX_CHARS):
    """Compact session digest (ported from session-index.py): user prompts, last Claude text per turn,
    error lines, edited files. Sidechains and meta lines are skipped, secrets masked, head+tail when too long."""
    out = ["## Session-Digest (Transkript, kompakt)"]
    if not transcript:
        out.append("- nicht gefunden (Session-ID oder Transkript unbekannt)")
        return out
    lines, files = [], []
    prompts = tools = errors = 0
    start = end = None
    try:
        with open(transcript, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                try:
                    o = json.loads(raw)
                except Exception:
                    continue
                if o.get("isSidechain"):
                    continue
                ts = o.get("timestamp")
                if ts:
                    start = start or ts
                    end = ts
                msg = o.get("message") if isinstance(o.get("message"), dict) else None
                if not msg:
                    continue
                t, content = o.get("type"), msg.get("content")
                hhmm = local_hhmm(ts) if ts else "?"
                if t == "user" and not o.get("isMeta"):
                    blocks = [content] if isinstance(content, str) else (content or [])
                    for b in blocks:
                        if isinstance(b, str) or (isinstance(b, dict) and b.get("type") == "text"):
                            txt = (b if isinstance(b, str) else str(b.get("text", ""))).strip()
                            if txt and not txt.startswith(("<", "[Request interrupted")):
                                prompts += 1
                                lines.append(f"\n### {hhmm} USER: {clip(txt, DIGEST_CLIP_USER)}")
                        elif isinstance(b, dict) and b.get("type") == "tool_result":
                            txt = block_text(b.get("content"))
                            if b.get("is_error") or ERROR_RE.search(txt[:3000]):
                                for l in txt.splitlines():
                                    if ERROR_RE.search(l):
                                        errors += 1
                                        lines.append(f"  ! {clip(l, 200)}")
                                        break
                elif t == "assistant" and isinstance(content, list):
                    last_text = ""
                    for b in content:
                        if not isinstance(b, dict):
                            continue
                        if b.get("type") == "tool_use":
                            tools += 1
                            inp = b.get("input") or {}
                            if b.get("name") in EDIT_TOOLS and isinstance(inp, dict):
                                fp = inp.get("file_path") or inp.get("notebook_path")
                                if fp and fp not in files:
                                    files.append(fp)
                        elif b.get("type") == "text":
                            last_text = str(b.get("text", ""))
                    if last_text.strip():
                        lines.append(f"  {hhmm} CLAUDE: {clip(last_text, DIGEST_CLIP_CLAUDE)}")
    except Exception as e:
        lines.append(f"(Transkript nur teilweise lesbar: {e})")
    out.append(f"- Datei: `{transcript}` · Zeitraum: {local_hhmm(start) if start else '?'}–{local_hhmm(end) if end else '?'}"
               f" · Prompts {prompts} · Tool-Aufrufe {tools} · Fehlerzeilen {errors} · editierte Dateien {len(files)}")
    if files:
        out.append("- Editierte Dateien: " + ", ".join(files[:40]) + (" …" if len(files) > 40 else ""))
    body = "\n".join(lines)
    if len(body) > max_chars:
        keep = max_chars // 2
        body = body[:keep] + f"\n\n… [{len(body) - max_chars} Zeichen ausgelassen] …\n\n" + body[-keep:]
    out.append(body)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="")
    ap.add_argument("--since", default="none")
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--digest", action="store_true", help="append the compact session digest (for /mastermind:wrap last)")
    ap.add_argument("--max-chars", type=int, default=DIGEST_MAX_CHARS, help="digest size limit (head + tail beyond)")
    a = ap.parse_args()
    since = parse_since(a.since)
    cwd = str(Path(a.cwd).expanduser())
    print("# Session-Evidenz für /mastermind:wrap")
    print(f"- Erstellt: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} · cwd: `{cwd}` · seit: {since.strftime('%Y-%m-%d') if since else 'kein last_wrap (24 h / gesamt)'}")
    git_lines, root = section_git(cwd, since)
    print("\n".join(git_lines))
    print("\n".join(section_memory(cwd, root, since)))
    transcript = find_transcript(a.session, cwd, root)
    print("\n".join(section_timeline(transcript)))
    if a.digest:
        print("\n".join(section_digest(transcript, a.max_chars)))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"- Evidenz-Skript abgebrochen: {e}")
    sys.exit(0)
