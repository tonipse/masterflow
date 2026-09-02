#!/usr/bin/env python3
"""Vault lint for the Mastermind brain (skill mastermind-index, `/mastermind:index`).

Checks the vault's Markdown notes against the conventions (frontmatter, note types, titles, wikilinks,
hub anatomy v3, root files, inbox) and the basic-memory index (entities, full-text coverage,
observations, relations, vector chunks). Python 3 standard library only. Read-only unless --fix.

Usage:
  lint.py [--vault PATH] [--changed] [--json] [--strict] [--index-only] [--fix] [--verbose] [PATH ...]

  --vault PATH   vault directory (default $MASTERMIND_VAULT or ~/Mastermind)
  --changed      lint only the files that `git status --porcelain` of the vault reports
  PATH ...       lint only these files (absolute, or relative to the vault)
  --index-only   only the index check (no file checks)
  --fix          apply the safe fixes (missing `related` -> [[index]], unquoted wikilinks in frontmatter,
                 missing `## Verlauf` / `## Quellen` in hubs), then lint again
  --json         machine-readable output
  --strict       exit code 1 when at least one ERROR remains (otherwise always 0)
  --verbose      print every legacy title warning instead of one summary line per rule

Output: one line per finding `ERROR|WARN|INFO <path>: <finding>`, grouped by severity, then a summary line.

Severity policy ("Bestandsschutz"): mandatory fields, value sets, `source` and date rules are ERROR only for
notes with `created` >= 2026-09-04 (fallback: the date git added the file), WARN for older notes. Title
length and title characters are always WARN. Type/folder mismatches and hub structure are always ERROR.
Exempt from frontmatter/type/title checks: templates/, _brainstorming/, inbox/ (INFO only), the root files
(line limits only) and files with prefix `_`.
"""

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "hooks"))
try:
    from session_start import parse_frontmatter, as_list, scalar  # type: ignore
except Exception:  # minimal fallback parser (same YAML subset)
    def _unquote(v):
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            return v[1:-1].replace("''", "'") if v[0] == "'" else v[1:-1].replace('\\"', '"')
        return v

    def parse_frontmatter(text):
        if not text.startswith("---"):
            return {}, text
        end = text.find("\n---", 3)
        if end == -1:
            return {}, text
        block, body = text[3:end].strip("\n"), text[end + 4:]
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
                    data[key] = [_unquote(x) for x in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", val[1:-1]) if x.strip()]
                else:
                    data[key] = _unquote(val)
            elif line.lstrip().startswith("- ") and key is not None and isinstance(data.get(key), list):
                data[key].append(_unquote(line.lstrip()[2:]))
            elif key is not None and isinstance(data.get(key), str):
                data[key] = (data[key] + " " + line.strip()).strip()
        return data, body

    def as_list(v):
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return [x.strip() for x in str(v).split(",") if x.strip()]

    def scalar(v):
        if v is None or isinstance(v, list):
            return ""
        s = str(v).strip()
        return "" if s.lower() in ("null", "none", "~", "") else s

NEW_SINCE = dt.date(2026, 9, 4)
REQUIRED = ("title", "type", "created", "updated", "tags", "status", "projects", "confidence", "related")
FOLDER_TYPES = {"gotchas": "gotcha", "patterns": "pattern", "decisions": "decision", "howtos": "howto",
                "stacks": "stack", "projects": "project"}
EXTRA_TYPES = {"note", "inbox", "moc"}
STATUS = {"draft", "active", "archived", "superseded"}
CONFIDENCE = {"low", "medium", "high"}
SOURCE_REQUIRED = {"gotcha", "decision", "pattern", "howto"}
ROOT_LIMITS = {"CLAUDE.md": None, "AGENTS.md": 60, "user.md": 60, "soul.md": 40, "index.md": None}
ROOT_REQUIRED = ("CLAUDE.md", "AGENTS.md")
FORBIDDEN = ':/\\|#^[]?*<>"'
HUB_ORDER = ["Zweck", "Stack", "Architektur / Eigenheiten", "Konventionen", "Wichtige Decisions",
             "Bekannte Gotchas", "Status", "Offene Punkte", "Quellen", "Verwandt", "Verlauf"]
MAX_OPEN_POINTS = 8
INBOX_STALE_DAYS = 90
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERLAUF_RE = re.compile(r"^- \d{4}-\d{2}-\d{2} (wrap|ernte|project|capture|manuell)\b.* · Quelle: .+")
QUELLE_RE = re.compile(r"^- .+ \(geerntet bis \d{4}-\d{2}-\d{2}\)\s*$|^- \(noch nicht erfasst\)\s*$")
INBOX_RE = re.compile(r"^- \[( |x)\] (\d{4}-\d{2}-\d{2}) · ")
LEGACY_TITLE_RULES = ("title-length", "title-chars")
TODAY = dt.date.today()


# --------------------------------------------------------------------------- helpers
class Finding:
    __slots__ = ("level", "path", "message", "rule")

    def __init__(self, level, path, message, rule):
        self.level, self.path, self.message, self.rule = level, path, message, rule

    def as_dict(self):
        return {"level": self.level, "path": self.path, "message": self.message, "rule": self.rule}


def read_text(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def parse_date(s):
    s = scalar(s)
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except Exception:
        return None


def raw_frontmatter(text):
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def sections(body):
    """[(heading, [lines])] for '## ' headings; text before the first heading is dropped."""
    out, cur = [], None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = (line[3:].strip(), [])
            out.append(cur)
        elif cur is not None:
            cur[1].append(line)
    return out


def bullets(lines):
    return [l for l in lines if l.strip().startswith(("- ", "* "))]


def git_add_dates(vault):
    """file -> date the file was first added (one git call), for notes without `created`."""
    dates = {}
    try:
        r = subprocess.run(["git", "-c", "core.quotePath=false", "log", "--diff-filter=A", "--name-only",
                            "--format=%x01%ad", "--date=short"], cwd=str(vault), capture_output=True,
                           text=True, timeout=10)
        cur = None
        for line in r.stdout.splitlines():
            if line.startswith("\x01"):
                cur = parse_date(line[1:])
            elif line.strip() and cur:
                dates[line.strip()] = cur  # log is newest-first, so the earliest add wins
    except Exception:
        pass
    return dates


def git_changed(vault):
    files = []
    try:
        r = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all"], cwd=str(vault),
                           capture_output=True, text=True, timeout=10)
        parts = r.stdout.split("\0")
        i = 0
        while i < len(parts):
            entry = parts[i]
            i += 1
            if len(entry) < 4:
                continue
            status, path = entry[:2], entry[3:]
            if status[0] in ("R", "C"):
                i += 1  # the old name follows as its own entry
            if status.strip() != "D" and path.endswith(".md"):
                files.append(path)
    except Exception:
        pass
    return files


def canonical_stack_tags():
    conv = HERE.parent / "mastermind-brain" / "conventions.md"
    text = read_text(conv)
    if not text:
        return None
    m = re.search(r"^## 7\..*?$(.*?)^## 8\.", text, re.M | re.S)
    if not m:
        return None
    tags = set()
    for line in m.group(1).splitlines():
        for chunk in re.findall(r"`([^`]+)`", line):
            tags.update(chunk.split())
    return tags or None


# --------------------------------------------------------------------------- vault model
class Note:
    def __init__(self, vault, path):
        self.path = path
        self.rel = path.relative_to(vault).as_posix()
        self.text = read_text(path)
        self.fm, self.body = parse_frontmatter(self.text)
        self.raw = raw_frontmatter(self.text)
        self.folder = self.rel.split("/")[0] if "/" in self.rel else ""
        self.name = path.name
        self.stem = path.stem
        self.title = scalar(self.fm.get("title")) or self.stem
        self.type = scalar(self.fm.get("type"))
        self.tags = [scalar(t) for t in as_list(self.fm.get("tags"))]
        self.aliases = [scalar(a) for a in as_list(self.fm.get("aliases")) if scalar(a)]
        self.kind = self.classify()

    def classify(self):
        if self.folder == "":
            return "root" if self.name in ROOT_LIMITS else "stray"
        if self.folder == "templates":
            return "template"
        if self.folder == "_brainstorming":
            return "brainstorm"
        if self.folder == "inbox":
            return "inbox"
        if self.name.startswith("_"):
            return "underscore"
        if self.folder in FOLDER_TYPES and "/" not in self.rel[len(self.folder) + 1:]:
            return "note"
        return "stray"

    def links(self):
        """Wikilink targets in body and frontmatter (deduplicated, order kept)."""
        seen, out = set(), []
        for m in WIKILINK_RE.finditer(self.text):
            t = m.group(1).strip()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out


def load_vault(vault):
    notes = []
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fn in sorted(filenames):
            if fn.endswith(".md") and not fn.startswith("."):
                notes.append(Note(vault, Path(dirpath) / fn))
    return notes


def build_link_index(notes):
    """lowercase key (stem, title, alias) -> set of rel paths; incoming link counts per rel path."""
    keys = {}
    for n in notes:
        if n.kind == "inbox":
            continue
        for k in {n.stem, n.title, *n.aliases}:
            keys.setdefault(k.lower(), set()).add(n.rel)
    incoming = {n.rel: 0 for n in notes}
    for n in notes:
        if n.kind == "inbox":
            continue
        for t in n.links():
            for target in keys.get(t.lower(), ()):
                if target != n.rel:
                    incoming[target] = incoming.get(target, 0) + 1
    return keys, incoming


# --------------------------------------------------------------------------- checks
class Linter:
    def __init__(self, vault, notes, stack_tags, add_dates):
        self.vault = vault
        self.notes = notes
        self.stack_tags = stack_tags
        self.add_dates = add_dates
        self.keys, self.incoming = build_link_index(notes)
        self.findings = []

    def add(self, level, note, message, rule):
        self.findings.append(Finding(level, note.rel if isinstance(note, Note) else note, message, rule))

    def is_new(self, note):
        created = parse_date(note.fm.get("created")) or self.add_dates.get(note.rel) or TODAY
        return created >= NEW_SINCE

    # ---- dispatch
    def check(self, note):
        if note.kind == "note":
            self.check_note(note)
        elif note.kind == "root":
            self.check_root(note)
        elif note.kind == "inbox":
            self.check_inbox(note)
        elif note.kind == "stray":
            self.add("WARN", note, "Datei außerhalb der kanonischen Ordner (gotchas, patterns, decisions, howtos, stacks, projects) und keine Root-Datei", "stray")

    def check_root(self, note):
        limit = ROOT_LIMITS.get(note.name)
        if limit is not None:
            n = len(note.text.splitlines())
            if n > limit:
                self.add("ERROR", note, f"{n} Zeilen, erlaubt sind {limit}", "root-lines")

    def check_inbox(self, note):
        open_, stale, bad = 0, 0, 0
        for line in note.body.splitlines():
            if not line.startswith("- ["):
                continue
            m = INBOX_RE.match(line)
            if not m:
                bad += 1
                continue
            if m.group(1) == " ":
                open_ += 1
                d = parse_date(m.group(2))
                if d and (TODAY - d).days > INBOX_STALE_DAYS:
                    stale += 1
        if note.type != "inbox":
            self.add("WARN", note, "Frontmatter `type: inbox` fehlt", "inbox-type")
        if bad:
            self.add("WARN", note, f"{bad} Zeile(n) nicht im Inbox-Format (conventions.md §12)", "inbox-format")
        self.add("INFO", note, f"{open_} offene Einträge, {stale} älter als {INBOX_STALE_DAYS} Tage", "inbox")

    def check_note(self, note):
        new = self.is_new(note)
        sev = "ERROR" if new else "WARN"
        fm = note.fm
        if not fm:
            self.add(sev, note, "Frontmatter fehlt oder ist nicht parsebar", "frontmatter")
            return
        missing = [k for k in REQUIRED if k not in fm]
        if missing:
            self.add(sev, note, "Pflichtfeld fehlt: " + ", ".join(missing), "required")
        # type vs folder
        expected = FOLDER_TYPES.get(note.folder)
        if not note.type:
            self.add("ERROR", note, f"`type` fehlt (erwartet {expected})", "type")
        elif note.type != expected:
            self.add("ERROR", note, f"`type: {note.type}` passt nicht zum Ordner `{note.folder}/` (erwartet {expected})", "type")
        # titles (always WARN)
        title = scalar(fm.get("title"))
        if title:
            if len(title) > 80:
                self.add("WARN", note, f"Titel hat {len(title)} Zeichen (max. 80)", "title-length")
            bad = sorted({c for c in title if c in FORBIDDEN})
            if bad:
                if bad == [":"] and note.aliases:
                    pass  # documented legacy convention: colon in the title + aliases entry
                else:
                    note_al = "aliases vorhanden" if note.aliases else "kein `aliases`, Wikilinks auf den Titel brechen in Obsidian"
                    self.add("WARN", note, "Titel enthält " + " ".join(f"`{c}`" for c in bad) + f" ({note_al})", "title-chars")
        # raw frontmatter: quoting and null values
        if re.search(r"^\s*-\s*\[\[", note.raw, re.M) or re.search(r"^\w+:\s*\[\[", note.raw, re.M) \
                or re.search(r"^\w+:\s*\[\s*\[\[", note.raw, re.M):
            self.add("ERROR", note, "Wikilink im Frontmatter nicht gequotet (`- '[[…]]'` bzw. `[\"[[…]]\"]`)", "quoting")
        nulls = re.findall(r"^(\w+):\s*(null|~)\s*$", note.raw, re.M)
        if nulls:
            self.add(sev, note, "`null`-Werte im Frontmatter: " + ", ".join(k for k, _ in nulls) + " (Schlüssel weglassen)", "null")
        # value sets and dates
        st = scalar(fm.get("status"))
        if "status" in fm and st not in STATUS:
            self.add(sev, note, f"`status: {st or '(leer)'}` nicht in {sorted(STATUS)}", "status")
        cf = scalar(fm.get("confidence"))
        if "confidence" in fm and cf not in CONFIDENCE:
            self.add(sev, note, f"`confidence: {cf or '(leer)'}` nicht in {sorted(CONFIDENCE)}", "confidence")
        for key in ("created", "updated"):
            v = scalar(fm.get(key))
            if key in fm and not DATE_RE.match(v):
                self.add(sev, note, f"`{key}: {v or '(leer)'}` ist kein Datum YYYY-MM-DD", "date")
        c, u = parse_date(fm.get("created")), parse_date(fm.get("updated"))
        if c and u and u < c:
            self.add(sev, note, f"`updated` ({u}) liegt vor `created` ({c})", "date")
        if note.type in SOURCE_REQUIRED and not scalar(fm.get("source")):
            self.add(sev, note, "`source` fehlt (Pflicht für gotcha, decision, pattern, howto)", "source")
        # stack tags
        if self.stack_tags:
            unknown = sorted({t[6:] for t in note.tags if t.startswith("stack/") and t[6:] not in self.stack_tags})
            if unknown:
                self.add("WARN", note, "Stack-Tag(s) nicht kanonisch (conventions.md §7): " + ", ".join(unknown), "stack-tag")
        # wikilink targets
        dangling = [t for t in note.links() if t.lower() not in self.keys and not t.startswith(("http://", "https://"))]
        if dangling:
            shown = ", ".join(f"[[{t}]]" for t in dangling[:5]) + (" …" if len(dangling) > 5 else "")
            self.add("WARN", note, f"{len(dangling)} Wikilink-Ziel(e) existieren nicht: {shown}", "dangling-link")
        # orphans (MOCs excluded)
        if note.type != "moc" and "moc" not in note.tags and self.incoming.get(note.rel, 0) == 0:
            self.add("WARN", note, "Orphan: keine eingehenden Wikilinks", "orphan")
        if note.type == "project":
            self.check_hub(note)

    def check_hub(self, note):
        secs = sections(note.body)
        names = [h for h, _ in secs]
        moc = "moc" in note.tags
        by_name = {}
        for h, lines in secs:
            by_name.setdefault(h, lines)
        if "Verlauf" not in names:
            self.add("ERROR", note, "`## Verlauf` fehlt (Anatomie v3, letzter Abschnitt)", "hub-verlauf")
        elif names[-1] != "Verlauf":
            self.add("ERROR", note, f"`## Verlauf` ist nicht der letzte Abschnitt (letzter: `## {names[-1]}`)", "hub-verlauf")
        if "Verlauf" in names:
            bad = [l for l in bullets(by_name["Verlauf"]) if not VERLAUF_RE.match(l.strip())]
            if bad:
                self.add("WARN", note, f"{len(bad)} Verlauf-Zeile(n) nicht im Format `- YYYY-MM-DD <wrap|ernte|project|capture|manuell> · … · Quelle: …`", "hub-verlauf-format")
        if moc:
            return
        if not scalar(note.fm.get("repo")):
            self.add("WARN", note, "`repo` fehlt (normalisiertes Remote, z. B. github.com/org/name)", "hub-fields")
        p = scalar(note.fm.get("path"))
        if not p:
            self.add("WARN", note, "`path` fehlt (absoluter Pfad des Checkouts)", "hub-fields")
        elif not Path(p).expanduser().exists():
            self.add("WARN", note, f"`path` existiert nicht: {p}", "hub-fields")
        if "Status" not in names:
            self.add("ERROR", note, "`## Status` fehlt", "hub-status")
        else:
            lines = [l for l in by_name["Status"] if l.strip()]
            if len(lines) != 1 or not lines[0].strip().startswith("Stand "):
                self.add("ERROR", note, f"`## Status` muss genau eine Zeile `Stand YYYY-MM-DD: …` sein ({len(lines)} Zeilen)", "hub-status")
        for h in ("Quellen", "Verwandt"):
            if h not in names:
                self.add("ERROR", note, f"`## {h}` fehlt", "hub-section")
        if "Quellen" in names:
            bad = [l for l in bullets(by_name["Quellen"]) if not QUELLE_RE.match(l.strip())]
            if bad:
                self.add("WARN", note, f"{len(bad)} Quellen-Zeile(n) nicht im Format `- <Quelle> (geerntet bis YYYY-MM-DD)`", "hub-quellen-format")
        if "Offene Punkte" in names:
            n = len(bullets(by_name["Offene Punkte"]))
            if n > MAX_OPEN_POINTS:
                self.add("ERROR", note, f"`## Offene Punkte` hat {n} Punkte (max. {MAX_OPEN_POINTS})", "hub-open-points")
        if "Verwandt" in names and "Verlauf" in names and names.index("Verlauf") - names.index("Verwandt") != 1:
            self.add("WARN", note, "`## Verwandt` steht nicht direkt vor `## Verlauf`", "hub-order")
        known = [h for h in names if h in HUB_ORDER]
        if known != sorted(known, key=HUB_ORDER.index):
            self.add("WARN", note, "Abschnittsreihenfolge weicht von der Anatomie v3 ab: " + " · ".join(known), "hub-order")

    # ---- vault-wide
    def check_root_files(self):
        for name in ROOT_REQUIRED:
            if not (self.vault / name).is_file():
                self.add("ERROR", name, "Root-Datei fehlt", "root-missing")
        for name in ("user.md", "soul.md"):
            if not (self.vault / name).is_file():
                self.add("WARN", name, "Root-Datei fehlt (wird über ~/.claude/CLAUDE.md in jede Session geladen)", "root-missing")


# --------------------------------------------------------------------------- index
def count_vault_files(vault):
    files = set()
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and not (Path(dirpath) == vault and d == "inbox")]
        for fn in filenames:
            if fn.endswith((".md", ".canvas")) and not fn.startswith("."):
                files.add((Path(dirpath) / fn).relative_to(vault).as_posix())
    return files


def check_index(vault, findings, project=None):
    """Compare vault files with the basic-memory index; returns a dict with the numbers."""
    cfg_dir = Path(os.environ.get("BASIC_MEMORY_CONFIG_DIR") or "~/.basic-memory").expanduser()
    project = project or os.environ.get("BASIC_MEMORY_MCP_PROJECT") or "mastermind"
    db = cfg_dir / "memory.db"
    files = count_vault_files(vault)
    info = {"files": len(files), "db": str(db)}
    if not db.is_file():
        findings.append(Finding("WARN", "index", f"Index-DB nicht gefunden: {db}", "index"))
        return info
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        row = con.execute("select id, path from project where name=?", (project,)).fetchone()
        if not row:
            findings.append(Finding("WARN", "index", f"Projekt `{project}` nicht in der Index-DB", "index"))
            con.close()
            return info
        pid, ppath = row
        info["project_id"] = pid
        try:
            if Path(ppath).expanduser().resolve() != vault.resolve():
                findings.append(Finding("WARN", "index", f"Index-Projekt `{project}` zeigt auf {ppath}, gelintet wird {vault}; Index-Prüfung übersprungen", "index"))
                con.close()
                return info
        except Exception:
            pass
        q = lambda sql, *a: con.execute(sql, a).fetchone()[0]
        entities = q("select count(*) from entity where project_id=?", pid)
        indexed_paths = {r[0] for r in con.execute("select file_path from entity where project_id=?", (pid,))}
        fts_rows = q("select count(*) from search_index where project_id=? and type='entity'", pid)
        fts_content = q("select count(distinct file_path) from search_index where project_id=? and type='entity' and length(content_stems)>0", pid)
        dup = q("select count(*) from (select file_path from search_index where project_id=? and type='entity' group by file_path having count(*)>1)", pid)
        obs = q("select count(*) from observation where project_id=?", pid)
        obs_fts = q("select count(*) from search_index where project_id=? and type='observation'", pid)
        rel = q("select count(*) from relation where project_id=?", pid)
        rel_fts = q("select count(*) from search_index where project_id=? and type='relation'", pid)
        try:
            chunks = q("select count(*) from search_vector_chunks where project_id=?", pid)
            models = [r[0] for r in con.execute("select distinct embedding_model from search_vector_chunks where project_id=?", (pid,))]
        except sqlite3.Error:
            chunks, models = None, []
        con.close()
    except sqlite3.Error as e:
        findings.append(Finding("WARN", "index", f"Index-DB nicht lesbar: {e}", "index"))
        return info
    info.update({"entities": entities, "fts_rows": fts_rows, "fts_content": fts_content, "fts_duplicates": dup,
                 "observations": obs, "observations_fts": obs_fts, "relations": rel, "relations_fts": rel_fts,
                 "chunks": chunks, "embedding_models": models})
    pct = lambda a, b: (100.0 * a / b) if b else 100.0
    missing = sorted(files - indexed_paths)
    extra = sorted(indexed_paths - files)
    info["not_indexed"] = missing
    info["stale_entities"] = extra
    line = (f"Entities {entities}/{len(files)} Dateien · FTS-Inhalt {fts_content}/{entities} ({pct(fts_content, entities):.0f} %)"
            f" · Observations {obs_fts}/{obs} ({pct(obs_fts, obs):.0f} %) · Relations {rel_fts}/{rel} ({pct(rel_fts, rel):.0f} %)"
            + (f" · Chunks {chunks} ({(chunks / entities) if entities else 0:.1f} je Entity)" if chunks is not None else " · keine Vektortabellen"))
    findings.append(Finding("INFO", "index", line, "index"))
    hint = " → /mastermind:index repair-index"
    if entities < 0.9 * len(files):
        findings.append(Finding("WARN", "index", f"nur {entities}/{len(files)} Dateien indexiert" + hint, "index-entities"))
    if missing:
        findings.append(Finding("WARN", "index", f"{len(missing)} Datei(en) ohne Entity: " + ", ".join(missing[:5]) + (" …" if len(missing) > 5 else ""), "index-entities"))
    if extra:
        findings.append(Finding("WARN", "index", f"{len(extra)} Entity/Entities ohne Datei: " + ", ".join(extra[:5]) + (" …" if len(extra) > 5 else ""), "index-entities"))
    if entities and pct(fts_content, entities) < 90:
        findings.append(Finding("WARN", "index", f"Volltext-Inhalt nur für {fts_content}/{entities} Entities; exakte Begriffe aus Notiz-Bodies sind für search_notes unsichtbar" + hint, "index-fts"))
    if dup:
        findings.append(Finding("WARN", "index", f"{dup} Datei(en) mit doppelten Entity-Zeilen im Volltext-Index (konkurrierende Watcher)" + hint, "index-fts"))
    if obs and pct(obs_fts, obs) < 90:
        findings.append(Finding("WARN", "index", f"Observations im Volltext-Index: {obs_fts}/{obs}" + hint, "index-fts"))
    if rel and pct(rel_fts, rel) < 90:
        findings.append(Finding("WARN", "index", f"Relations im Volltext-Index: {rel_fts}/{rel}" + hint, "index-fts"))
    if chunks is not None and entities and chunks < 0.9 * entities:
        findings.append(Finding("WARN", "index", f"nur {chunks} Vektor-Chunks für {entities} Entities (Vektoren werden vom laufenden MCP-Server gebaut; nach einem Modellwechsel retrieval-upgrade.sh)", "index-vectors"))
    if len(models) > 1:
        findings.append(Finding("WARN", "index", "Vektor-Chunks mit mehreren Embedding-Modellen: " + ", ".join(models), "index-vectors"))
    return info


# --------------------------------------------------------------------------- fixes
def apply_fixes(vault, notes, targets):
    """Safe, deterministic fixes. Returns list of (rel, description)."""
    done = []
    today = TODAY.isoformat()
    for note in targets:
        if note.kind != "note" or not note.fm:
            continue
        text = note.text
        changed = []
        raw = raw_frontmatter(text)
        new_raw = raw
        # 1. unquoted wikilinks in frontmatter
        fixed = re.sub(r"^(\s*-\s*)(\[\[[^\]]+\]\])\s*$", lambda m: f"{m.group(1)}'{m.group(2)}'", new_raw, flags=re.M)
        fixed = re.sub(r"^(\w+:\s*)(\[\[[^\]]+\]\])\s*$", lambda m: f"{m.group(1)}'{m.group(2)}'", fixed, flags=re.M)
        fixed = re.sub(r"^(\w+:\s*\[)(.*\[\[.*)(\])\s*$",
                       lambda m: m.group(1) + ", ".join(
                           (x.strip() if x.strip()[:1] in ("'", '"') else f"'{x.strip()}'") for x in m.group(2).split(",") if x.strip()
                       ) + m.group(3), fixed, flags=re.M)
        if fixed != new_raw:
            new_raw = fixed
            changed.append("Wikilinks im Frontmatter gequotet")
        # 2. missing related
        if "related" not in note.fm:
            new_raw = new_raw.rstrip("\n") + "\nrelated:\n- '[[index]]'"
            changed.append("`related: [[index]]` ergänzt")
        if new_raw != raw:
            text = text[:3] + new_raw + text[3 + len(raw):]
        # 3./4. hubs: missing Quellen / Verlauf
        if note.type == "project":
            body = text[text.find("\n---", 3) + 4:] if text.startswith("---") else text
            names = [h for h, _ in sections(body)]
            moc = "moc" in note.tags
            if not moc and "Quellen" not in names:
                block = "## Quellen\n- (noch nicht erfasst)\n\n"
                anchors = [i for i in (body.find("\n## Verwandt"), body.find("\n## Verlauf")) if i != -1]
                if anchors:
                    at = min(anchors) + 1
                    body = body[:at] + block + body[at:]
                else:
                    body = body.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
                changed.append("`## Quellen` mit Platzhalter ergänzt")
            if "Verlauf" not in names:
                body = body.rstrip("\n") + f"\n\n## Verlauf\n- {today} manuell · Abschnitt Verlauf ergänzt (Anatomie v3) · Quelle: /mastermind:index fix\n"
                changed.append("`## Verlauf` mit Migrationszeile angehängt")
            if changed and text.startswith("---"):
                head = text[:text.find("\n---", 3) + 4]
                created = parse_date(note.fm.get("created"))
                if any(c.startswith("`##") for c in changed) and (created is None or created <= TODAY):
                    head = re.sub(r"^updated:.*$", f"updated: '{today}'", head, count=1, flags=re.M)
                text = head + body
        if changed and text != note.text:
            note.path.write_text(text, encoding="utf-8")
            done.append((note.rel, "; ".join(changed)))
    return done


# --------------------------------------------------------------------------- output
def render(findings, verbose, n_files, exempt):
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    out = []
    legacy = {}
    for f in sorted(findings, key=lambda f: (order[f.level], f.path)):
        if f.level == "WARN" and f.rule in LEGACY_TITLE_RULES and not verbose:
            legacy.setdefault(f.rule, []).append(f.path)
            continue
        out.append(f"{f.level} {f.path}: {f.message}")
    for rule, paths in legacy.items():
        label = "Titel > 80 Zeichen" if rule == "title-length" else "Titel mit unerlaubten Zeichen"
        out.append(f"WARN {len(paths)} Notizen: {label} (Bestand; Wikilinks laufen über aliases; --verbose listet sie): "
                   + ", ".join(paths[:3]) + (" …" if len(paths) > 3 else ""))
    counts = {k: sum(1 for f in findings if f.level == k) for k in order}
    out.append(f"Summe: {counts['ERROR']} ERROR, {counts['WARN']} WARN, {counts['INFO']} INFO · {n_files} Dateien geprüft"
               + (f", {exempt} ausgenommen (templates, _brainstorming, _*)" if exempt else ""))
    return "\n".join(out), counts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", default=os.environ.get("MASTERMIND_VAULT") or "~/Mastermind")
    ap.add_argument("--changed", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--index-only", action="store_true")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()
    vault = Path(a.vault).expanduser()
    if not vault.is_dir():
        print(f"ERROR vault: Verzeichnis nicht gefunden: {vault}")
        sys.exit(1 if a.strict else 0)
    findings = []
    counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
    index_info = {}
    n_files = exempt = 0
    if a.index_only:
        index_info = check_index(vault, findings)
    else:
        notes = load_vault(vault)
        by_rel = {n.rel: n for n in notes}
        selected = None
        if a.paths:
            selected = []
            for p in a.paths:
                pp = Path(p).expanduser()
                cand = pp if pp.is_absolute() else (vault / p if (vault / p).exists() else Path.cwd() / p)
                try:
                    rel = cand.resolve().relative_to(vault.resolve()).as_posix()
                except Exception:
                    findings.append(Finding("WARN", p, "liegt nicht im Vault, übersprungen", "args"))
                    continue
                if rel in by_rel:
                    selected.append(by_rel[rel])
                else:
                    findings.append(Finding("WARN", p, "nicht gefunden (keine .md-Datei im Vault)", "args"))
        elif a.changed:
            selected = [by_rel[r] for r in git_changed(vault) if r in by_rel]
        full = selected is None
        targets = notes if full else selected
        linter = Linter(vault, notes, canonical_stack_tags(), git_add_dates(vault))
        if a.fix:
            for rel, what in apply_fixes(vault, notes, targets):
                findings.append(Finding("INFO", rel, "FIX: " + what, "fix"))
            notes = load_vault(vault)  # re-read after fixes
            by_rel = {n.rel: n for n in notes}
            targets = notes if full else [by_rel[n.rel] for n in targets if n.rel in by_rel]
            linter = Linter(vault, notes, canonical_stack_tags(), git_add_dates(vault))
        linter.findings = findings
        for n in targets:
            if n.kind in ("template", "brainstorm", "underscore"):
                exempt += 1
                continue
            n_files += 1
            linter.check(n)
        if full:
            linter.check_root_files()
            index_info = check_index(vault, findings)
    text, counts = render(findings, a.verbose, n_files, exempt)
    if a.json:
        print(json.dumps({"findings": [f.as_dict() for f in findings], "summary": counts,
                          "files_checked": n_files, "index": index_info}, ensure_ascii=False, indent=1))
    else:
        print(text)
    sys.exit(1 if (a.strict and counts["ERROR"]) else 0)


if __name__ == "__main__":
    main()
