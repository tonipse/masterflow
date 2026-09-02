#!/usr/bin/env python3
"""SessionStart hook for the mastermind plugin.

Reads the Claude Code hook JSON from stdin, looks at the current project and the
Mastermind vault (plain files, no index needed) and prints a compact context block
for Claude as hookSpecificOutput.additionalContext.

Design rules:
- Python 3 standard library only.
- Every stage is guarded; problems become one warning line, never a failure.
- Always exit 0 and always print valid JSON.
- Budget: under 150 ms, at most about 650 tokens of output.
"""

import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

MAX_RECENT = 5
MAX_SIMILAR = 3
MAX_OPEN_LINES = 5
LINE_CLIP = 140
NOTE_DIRS = ("gotchas", "patterns", "decisions", "howtos", "stacks")
UNWRAPPED_MIN_EDITS = 5
UNWRAPPED_MAX_AGE_DAYS = 14
UNWRAPPED_MAX_NOTIFY = 3
OLLAMA_TIMEOUT = 0.3

# dependency name -> canonical stack tag (matches the stack/* tags used in the vault)
DEP_TAGS = {
    "next": "nextjs", "react": "react", "react-dom": "react", "vue": "vue", "nuxt": "nuxt",
    "svelte": "svelte", "@sveltejs/kit": "sveltekit", "astro": "astro", "express": "express",
    "fastify": "fastify", "hono": "hono", "electron": "electron", "typescript": "typescript",
    "inngest": "inngest", "@supabase/supabase-js": "supabase", "@supabase/ssr": "supabase",
    "@neondatabase/serverless": "neon", "pg": "postgres", "postgres": "postgres", "mysql2": "mysql",
    "mssql": "mssql", "prisma": "prisma", "@prisma/client": "prisma", "drizzle-orm": "drizzle",
    "mongoose": "mongodb", "redis": "redis", "@upstash/redis": "redis", "ioredis": "redis",
    "@anthropic-ai/sdk": "anthropic", "openai": "openai", "ai": "ai-sdk", "@ai-sdk/openai": "ai-sdk",
    "@shopify/shopify-api": "shopify", "shopify-api-node": "shopify", "@shopify/polaris": "shopify",
    "tailwindcss": "tailwind", "vitest": "vitest", "jest": "jest", "playwright": "playwright",
    "@playwright/test": "playwright", "puppeteer": "puppeteer", "puppeteer-core": "puppeteer",
    "three": "threejs", "@react-three/fiber": "threejs", "gsap": "gsap", "stripe": "stripe",
    "resend": "resend", "googleapis": "google-api", "@aws-sdk/client-s3": "aws", "aws-sdk": "aws",
    "@vercel/blob": "vercel", "@vercel/kv": "vercel", "zod": "zod", "@clickup/rest-client": "clickup",
    "@slack/web-api": "slack", "@slack/bolt": "slack", "@sentry/nextjs": "sentry",
    "fastapi": "fastapi", "django": "django", "flask": "flask", "sqlalchemy": "sqlalchemy",
    "pandas": "pandas", "anthropic": "anthropic", "google-api-python-client": "google-api",
    "playwright-python": "playwright", "laravel/framework": "laravel",
}


# --------------------------------------------------------------------------- helpers
def read_hook_input():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw and raw.strip() else {}
    except Exception:
        return {}


def run_git(args, cwd):
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=2)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def normalize_remote(url):
    u = (url or "").strip().lower()
    if not u:
        return ""
    u = re.sub(r"\.git/?$", "", u)
    u = re.sub(r"^ssh://", "", u)
    u = re.sub(r"^git@([^:/]+):", r"\1/", u)
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^[^@/]+@", "", u)
    return u.rstrip("/")


def realpath(p):
    try:
        return str(Path(p).expanduser().resolve())
    except Exception:
        return str(p)


def norm_name(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def clip(s, n=LINE_CLIP):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def split_inline_list(s):
    items, buf, depth, quote = [], "", 0, None
    for ch in s:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            buf += ch
        elif ch == "[":
            depth += 1
            buf += ch
        elif ch == "]":
            depth -= 1
            buf += ch
        elif ch == "," and depth == 0:
            items.append(buf)
            buf = ""
        else:
            buf += ch
    if buf.strip():
        items.append(buf)
    return [unquote(x) for x in items if x.strip()]


def finalize_scalar(v):
    """Strip surrounding quotes after continuation lines were joined; undo YAML quote escapes."""
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] == "'":
        return v[1:-1].replace("''", "'")
    if len(v) >= 2 and v[0] == v[-1] and v[0] == '"':
        return v[1:-1].replace('\\"', '"')
    return v


def parse_frontmatter(text):
    """Minimal YAML subset: scalars, inline lists, block lists, folded continuation lines."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end].strip("\n")
    body = text[end + 4:]
    data, key = {}, None
    for line in block.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m and not line[0].isspace() and not line.startswith("-"):
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                data[key] = []
            elif val.startswith("[") and val.endswith("]"):
                data[key] = split_inline_list(val[1:-1])
            else:
                data[key] = val  # raw; finalized below (may continue on next lines)
        elif line.lstrip().startswith("- ") and key is not None and isinstance(data.get(key), list):
            data[key].append(unquote(line.lstrip()[2:]))
        elif key is not None and isinstance(data.get(key), str):
            data[key] = (data[key] + " " + line.strip()).strip()
    for k, v in list(data.items()):
        if isinstance(v, str):
            data[k] = finalize_scalar(v)
    return data, body


def as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [x.strip() for x in str(v).split(",") if x.strip()]


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# --------------------------------------------------------------------------- vault
def find_vault():
    raw = os.environ.get("MASTERMIND_VAULT") or "~/Mastermind"
    p = Path(raw).expanduser()
    return p if p.is_dir() else None


def scalar(v):
    """Frontmatter scalar as text; YAML nulls and empty lists count as empty."""
    if v is None or isinstance(v, list):
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("null", "none", "~", "") else s


def load_hubs(vault):
    hubs = []
    for f in sorted((vault / "projects").glob("*.md")):
        if f.name.startswith("_"):
            continue
        fm, body = parse_frontmatter(read_text(f))
        if fm.get("type") not in (None, "project"):
            continue
        tags = as_list(fm.get("tags"))
        paths = [scalar(p) for p in as_list(fm.get("paths"))] + [scalar(fm.get("path"))]
        hubs.append({
            "file": f,
            "stem": f.stem,
            "title": scalar(fm.get("title")) or f.stem,
            "body": body,
            "repo": normalize_remote(scalar(fm.get("repo"))),
            # only absolute paths: "~" or relative values would match far too much
            "paths": [realpath(p) for p in paths if p.startswith("/")],
            "stacks": [t.split("/", 1)[1] for t in tags if t.startswith("stack/")],
            "updated": scalar(fm.get("updated")),
            "last_wrap": scalar(fm.get("last_wrap")),
        })
    return hubs


def project_identity(cwd):
    ident = {"cwd": cwd, "root": None, "name": Path(cwd).name, "remote": "", "git": False}
    top = run_git(["rev-parse", "--show-toplevel"], cwd)
    if top:
        ident["git"] = True
        root = top
        common = run_git(["rev-parse", "--git-common-dir"], cwd)
        if common:
            cp = Path(common)
            if not cp.is_absolute():
                cp = Path(top) / cp
            cp = Path(realpath(cp))
            if cp.name == ".git":
                root = str(cp.parent)  # linked worktree -> main worktree root
        ident["root"] = root
        ident["name"] = Path(root).name
        ident["remote"] = normalize_remote(run_git(["remote", "get-url", "origin"], cwd))
    return ident


def match_hub(hubs, ident):
    if ident["remote"]:
        for h in hubs:
            if h["repo"] and h["repo"] == ident["remote"]:
                return h, "repo"
    # path: the most specific (longest) hub path that contains root or cwd wins
    best = None
    for cand in [c for c in (ident["root"], ident["cwd"]) if c]:
        rc = realpath(cand)
        for h in hubs:
            for p in h["paths"]:
                if rc == p or rc.startswith(p + os.sep):
                    if best is None or len(p) > len(best[1]):
                        best = (h, p)
    if best:
        return best[0], "path"
    n = norm_name(ident["name"])
    if n:
        for h in hubs:
            if norm_name(h["stem"]) == n or norm_name(h["title"]) == n:
                return h, "name"
    return None, None


def recent_notes_for_hub(vault, hub):
    keys = {hub["title"], hub["stem"]}
    found = []
    for d in NOTE_DIRS:
        for f in (vault / d).glob("*.md"):
            fm, _ = parse_frontmatter(read_text(f))
            links = " ".join(as_list(fm.get("projects")))
            if any(f"[[{k}]]" in links for k in keys):
                found.append((str(fm.get("updated") or ""), str(fm.get("title") or f.stem), d))
    found.sort(reverse=True)
    return found[:MAX_RECENT]


GENERIC_STACKS = {"nodejs", "typescript", "javascript", "python", "php", "go", "dotnet"}


def similar_hubs(hubs, stacks, exclude_stem=None):
    """Hubs sharing specific stack tags. Generic language tags alone carry no signal."""
    target = set(stacks)
    specific = target - GENERIC_STACKS
    if not specific:
        return []
    need = 2 if len(specific) > 2 else 1
    scored = []
    for h in hubs:
        if h["stem"] == exclude_stem:
            continue
        shared_specific = specific & set(h["stacks"])
        if len(shared_specific) >= need:
            shared = target & set(h["stacks"])
            scored.append((len(shared_specific), len(shared), h["updated"], h["title"], sorted(shared)))
    scored.sort(reverse=True)
    return [(t, s) for _, _, _, t, s in scored[:MAX_SIMILAR]]


def stack_notes(vault, stacks):
    return [s for s in stacks if (vault / "stacks" / f"{s}.md").is_file()]


def verlauf_last(body):
    """Last bullet of '## Verlauf' (hub anatomy v3), without the leading dash."""
    last, current = "", False
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower() == "verlauf"
            continue
        if current and line.strip().startswith(("- ", "* ")):
            last = line.strip()[2:].strip()
    return clip(last) if last else ""


def inbox_open(vault, hub_stem):
    """Number of open '- [ ]' candidates in inbox/<hub>.md."""
    f = vault / "inbox" / f"{hub_stem}.md"
    if not f.is_file():
        return 0
    return sum(1 for l in read_text(f).splitlines() if l.startswith("- [ ]"))


def state_file_for(root):
    d = Path(os.environ.get("XDG_STATE_HOME") or "~/.local/state").expanduser() / "mastermind"
    return d / ("last-session-" + re.sub(r"[^A-Za-z0-9-]", "-", str(root)) + ".json")


def unwrapped_notice(root, source, session_id):
    """UNWRAPPED line when the previous session of this project ended with edits but without /mastermind:wrap."""
    if source not in ("startup", "clear", "resume"):
        return None
    f = state_file_for(root)
    try:
        st = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    if st.get("wrapped") or (st.get("edits") or 0) < UNWRAPPED_MIN_EDITS:
        return None
    if session_id and st.get("session_id") == session_id:
        return None  # resume of the very same session
    if int(st.get("notified") or 0) >= UNWRAPPED_MAX_NOTIFY:
        return None
    try:
        ended = dt.datetime.fromisoformat(str(st.get("ended")))
        if (dt.datetime.now(ended.tzinfo) - ended).days > UNWRAPPED_MAX_AGE_DAYS:
            return None
        ended_s = ended.strftime("%Y-%m-%d %H:%M")
    except Exception:
        ended_s = str(st.get("ended") or "?")[:16]
    st["notified"] = int(st.get("notified") or 0) + 1
    try:
        f.write_text(json.dumps(st, indent=1), encoding="utf-8")
    except Exception:
        pass
    sid = str(st.get("session_id") or "?")[:8]
    return (f"UNWRAPPED: session {sid} ended {ended_s} with {st.get('edits')} edits and no /mastermind:wrap "
            "-> run /mastermind:wrap last")


def ollama_warning(cfg):
    """Warn when the configured LiteLLM embedding endpoint (local Ollama) does not answer."""
    if (cfg or {}).get("semantic_embedding_provider") != "litellm":
        return None
    base = str(cfg.get("semantic_embedding_api_base") or "")
    if not re.search(r"^https?://(localhost|127\.0\.0\.1)", base):
        return None
    root = re.sub(r"/v1/?$", "", base.rstrip("/"))
    try:
        with urllib.request.urlopen(root + "/api/version", timeout=OLLAMA_TIMEOUT) as r:
            if r.status == 200:
                return None
    except Exception:
        pass
    return f"Ollama not reachable at {base}; semantic search will fail (brew services start ollama)"


def open_points(body):
    """Lines of '## Status' (bullets or the single 'Stand …' line) and '## Offene Punkte'."""
    lines, current = [], None
    for line in body.splitlines():
        if line.startswith("## "):
            head = line[3:].strip().lower()
            current = "open" if head.startswith(("offene punkte", "status", "open")) else None
            continue
        if not current or line.startswith("#"):
            continue
        s = line.strip()
        if s.startswith(("- ", "* ")):
            s = s[2:].strip()
        if s and s not in ("-", "*"):
            lines.append(clip(s))
        if len(lines) >= MAX_OPEN_LINES:
            break
    return lines


# --------------------------------------------------------------------------- stack sniffing
def sniff_stack(root):
    tags = set()
    if not root:
        return []
    r = Path(root)
    pkg = r / "package.json"
    if pkg.is_file():
        try:
            d = json.loads(read_text(pkg) or "{}")
            deps = {**d.get("dependencies", {}), **d.get("devDependencies", {})}
            tags.add("nodejs")
            for name in deps:
                if name in DEP_TAGS:
                    tags.add(DEP_TAGS[name])
                elif name.startswith("@shopify/"):
                    tags.add("shopify")
                elif name.startswith("@aws-sdk/"):
                    tags.add("aws")
        except Exception:
            pass
    for name in ("pyproject.toml", "requirements.txt"):
        f = r / name
        if f.is_file():
            tags.add("python")
            txt = read_text(f).lower()
            for dep, tag in DEP_TAGS.items():
                if re.search(rf"(^|[\s\"'=\[])({re.escape(dep)})([\s\"'>=<\[~!;]|$)", txt, re.M):
                    tags.add(tag)
    if (r / "composer.json").is_file():
        tags.add("php")
        if "laravel/framework" in read_text(r / "composer.json"):
            tags.add("laravel")
    if (r / "go.mod").is_file():
        tags.add("go")
    try:
        if any(r.glob("*.csproj")) or any(r.glob("*/*.csproj")):
            tags.add("dotnet")
    except Exception:
        pass
    if (r / "vercel.json").is_file():
        tags.add("vercel")
    if (r / "serverless.yml").is_file() or (r / "template.yaml").is_file():
        tags.add("aws-lambda")
    return sorted(tags)


# --------------------------------------------------------------------------- index health
def index_health(vault):
    """(files, stats or None, warnings): stats = entities, full-text rows with content, observations in table/FTS."""
    warnings = []
    files = 0
    for dirpath, dirnames, filenames in os.walk(vault):
        # hidden folders and inbox/ are not indexed (.bmignore); templates are indexed and count on both sides
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and not (Path(dirpath) == vault and d == "inbox")]
        # basic-memory indexes Markdown notes and Obsidian canvas files
        files += sum(1 for f in filenames if f.endswith((".md", ".canvas")) and not f.startswith("."))
    cfg_dir = Path(os.environ.get("BASIC_MEMORY_CONFIG_DIR") or "~/.basic-memory").expanduser()
    cfg = {}
    stats = None
    try:
        cfg = json.loads(read_text(cfg_dir / "config.json") or "{}")
        cfg_path = cfg.get("projects", {}).get("mastermind", {}).get("path")
        if cfg_path and realpath(cfg_path) != realpath(vault):
            warnings.append(f"basic-memory config points to {cfg_path}, this hook uses {vault}")
    except Exception:
        pass
    db = cfg_dir / "memory.db"
    if db.is_file():
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=0.5)
            row = con.execute("select id from project where name='mastermind'").fetchone()
            if row:
                pid = row[0]
                q = lambda sql: int(con.execute(sql, (pid,)).fetchone()[0])
                stats = {
                    "entities": q("select count(*) from entity where project_id=?"),
                    "fts": q("select count(distinct file_path) from search_index where project_id=? and type='entity' and length(content_stems)>0"),
                    "obs": q("select count(*) from observation where project_id=?"),
                    "obs_fts": q("select count(*) from search_index where project_id=? and type='observation'"),
                }
            con.close()
        except Exception:
            stats = None
    w = ollama_warning(cfg)
    if w:
        warnings.append(w)
    return files, stats, warnings


# --------------------------------------------------------------------------- rendering
RULES = (
    "RULES\n"
    "- RECALL before non-trivial work (new feature, integration, error, library choice, deploy): "
    "search_notes (hybrid) with stack/error/domain terms; read the stack notes listed below when you touch that stack. "
    "Say which prior knowledge you reuse.\n"
    "- CAPTURE autonomously as soon as you have VERIFIED something non-obvious and reusable "
    "(gotcha with cause+fix, decision with alternatives, pattern, how-to, stack quirk): "
    "load skill mastermind:mastermind-brain (conventions), search_notes for duplicates, then write_note/edit_note, "
    "and tell the user in one line with the note path. Do not ask for permission. "
    "Never put project status, secrets, guesses or trivia into the vault; project status belongs to auto memory. "
    "Promising but unverified -> one line in inbox/<hub>.md, not a note.\n"
    "- GUARDRAILS: a decisions/ note for the area you touch is a constraint; say a contradiction in one line "
    "before acting; if the user overrides, update the decision note (dated fact), never bypass it silently.\n"
    "- SESSION END: the user runs /mastermind:wrap (harvests the session, updates the hub, commits the vault). "
    "If the session did substantial work and the user starts wrapping up without it, remind them once."
)


def render(vault, ident, hub, how, recent, similar, stacks_with_notes, points, sniffed, health, warnings,
           verlauf="", inbox=0, unwrapped=None):
    out = ["<mastermind>"]
    out.append(f"Mastermind brain is active (vault {vault}, MCP server mastermind-memory, notes are written in German).")
    out.append(RULES)
    label = ident["name"] + (f" ({ident['remote']})" if ident["remote"] else "")
    if hub:
        stack = ", ".join(hub["stacks"]) if hub["stacks"] else "no stack tags"
        wrap = hub["last_wrap"] or "never"
        out.append(f"PROJECT: {label} -> hub [[{hub['title']}]] (matched by {how}; updated {hub['updated'] or '?'}; last wrap {wrap}; stack: {stack})")
        if points:
            out.append("  Open points / status: " + " | ".join(points))
        if verlauf:
            out.append("  Verlauf: " + verlauf)
        if inbox:
            out.append(f"  Inbox: {inbox} offene Kandidaten in inbox/{hub['stem']}.md (promote or prune them in /mastermind:wrap)")
        if recent:
            out.append("  Recent notes for this project: " + " · ".join(f"[[{t}]] ({u or '?'})" for u, t, _ in recent))
        if similar:
            out.append("  Similar projects: " + " · ".join(f"[[{t}]] ({', '.join(s)})" for t, s in similar))
        if stacks_with_notes:
            out.append("  Stack notes to consult: " + " · ".join(f"[[{s}]]" for s in stacks_with_notes))
        if not hub["last_wrap"]:
            out.append("  This hub was never wrapped: /mastermind:wrap will also refresh its stack/status sections.")
    else:
        why = "" if ident["git"] else " (not a git repo)"
        out.append(f"PROJECT: {label} -> no hub in the vault yet{why}.")
        if sniffed:
            out.append("  Detected stack: " + ", ".join(sniffed))
        if similar:
            out.append("  Similar projects: " + " · ".join(f"[[{t}]] ({', '.join(s)})" for t, s in similar))
        if stacks_with_notes:
            out.append("  Stack notes to consult: " + " · ".join(f"[[{s}]]" for s in stacks_with_notes))
        if ident["git"]:
            out.append("  Onboarding runs automatically at the first capture or at /mastermind:wrap; run /mastermind:project to create the hub now.")
    if unwrapped:
        out.append(unwrapped)
    files, stats, _ = health
    if stats is None:
        out.append(f"INDEX: {files} notes in vault, index state unknown.")
    else:
        ent, fts, obs, obs_fts = stats["entities"], stats["fts"], stats["obs"], stats["obs_fts"]
        fts_pct = (100 * fts // ent) if ent else 100
        obs_pct = (100 * obs_fts // obs) if obs else 100
        if files and ent < 0.9 * files:
            out.append(f"INDEX WARNING: only {ent}/{files} notes are indexed; search_notes is blind. "
                       "Tell the user to run /mastermind:index repair-index (never basic-memory reindex --full).")
        elif fts_pct < 90 or obs_pct < 90:
            out.append(f"INDEX WARNING: {ent}/{files} notes indexed, but full text covers only {fts}/{ent} ({fts_pct} %) "
                       f"and observations {obs_fts}/{obs} ({obs_pct} %): exact identifiers in note bodies are invisible to "
                       "search_notes. Tell the user to run /mastermind:index repair-index.")
        else:
            out.append(f"INDEX: {ent}/{files} notes indexed, full text {fts_pct} %, observations {obs_pct} %.")
    for w in warnings:
        out.append(f"WARNING: {w}")
    out.append("</mastermind>")
    return "\n".join(out)


def emit(context):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))


def main():
    warnings = []
    data = read_hook_input()
    cwd = data.get("cwd") or os.getcwd()
    vault = find_vault()
    if vault is None:
        emit("<mastermind>\nWARNING: Mastermind vault not found (expected ~/Mastermind or $MASTERMIND_VAULT). "
             "Recall/capture via the mastermind-memory MCP server may still work, but no project context is available.\n</mastermind>")
        return
    try:
        ident = project_identity(cwd)
    except Exception as e:  # pragma: no cover
        ident = {"cwd": cwd, "root": None, "name": Path(cwd).name, "remote": "", "git": False}
        warnings.append(f"project identity failed: {e}")
    hubs, hub, how, recent, similar, notes, points, sniffed = [], None, None, [], [], [], [], []
    verlauf, inbox, unwrapped = "", 0, None
    try:
        hubs = load_hubs(vault)
        hub, how = match_hub(hubs, ident)
    except Exception as e:
        warnings.append(f"hub lookup failed: {e}")
    try:
        if hub:
            recent = recent_notes_for_hub(vault, hub)
            similar = similar_hubs(hubs, hub["stacks"], exclude_stem=hub["stem"])
            notes = stack_notes(vault, hub["stacks"])
            points = open_points(hub["body"])
            verlauf = verlauf_last(hub["body"])
            inbox = inbox_open(vault, hub["stem"])
        else:
            sniffed = sniff_stack(ident["root"] or cwd)
            similar = similar_hubs(hubs, sniffed)
            notes = stack_notes(vault, sniffed)
    except Exception as e:
        warnings.append(f"context enrichment failed: {e}")
    try:
        unwrapped = unwrapped_notice(ident["root"] or cwd, data.get("source") or "startup", data.get("session_id") or "")
    except Exception as e:
        warnings.append(f"state file check failed: {e}")
    try:
        health = index_health(vault)
        warnings.extend(health[2])
    except Exception as e:
        health = (0, None, [])
        warnings.append(f"index health check failed: {e}")
    emit(render(vault, ident, hub, how, recent, similar, notes, points, sniffed, health, warnings,
                verlauf=verlauf, inbox=inbox, unwrapped=unwrapped))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # last line of defense: still valid JSON, still exit 0
        emit(f"<mastermind>\nWARNING: session-start hook failed: {e}\n</mastermind>")
    sys.exit(0)
