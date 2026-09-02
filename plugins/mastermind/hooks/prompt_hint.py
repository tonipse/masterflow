#!/usr/bin/env python3
"""UserPromptSubmit hook for the mastermind plugin: a deterministic, cheap recall hint.

Extracts search terms from the prompt, runs a read-only BM25 query against the basic-memory full-text
index (knowledge notes only: gotchas, patterns, decisions, howtos, stacks) and, when strong matches exist,
adds one line of context: `<mastermind-hint>Möglicherweise relevant: [[A]] (gotcha) · [[B]] (pattern).
Bei Bedarf read_note.</mastermind-hint>`. Each note is hinted at most once per session.

Silent (no output) when: prompt shorter than 25 characters, slash command, prompt starting with `<`,
`~/Mastermind/.mastermind.json` says `"prompt_hints": false`, no index, or no match above the threshold.
Python 3 standard library only. Always exits 0. Budget: under 50 ms, at most 3 hits, about 60 tokens.

Tuning knobs (calibrated in the v3 night session): BM25_THRESHOLD, MIN_TERMS, IDENT_BONUS.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

BM25_THRESHOLD = -12.0  # bm25() is negative; lower = better. Only hits at or below this value are shown.
                        # Calibrated 2026-09-03 on 40 real prompts against the full index: -8 gave precision 0.08
                        # (hint on 57 % of prompts), -12 gave precision 0.50 with a hint on 10 % of prompts.
MIN_TERMS = 2           # prompts with fewer usable terms produce no hint
IDENT_BONUS = -3.0      # added per identifier term (with _ . digits or CamelCase) found in the hit's title
MAX_TERMS = 8
MAX_HITS = 3
MIN_PROMPT_CHARS = 25
NOTE_PREFIXES = ("gotchas/", "patterns/", "decisions/", "howtos/", "stacks/")

STOPWORDS = set("""
aber alle allem allen aller alles also anderen andere auch auf aus bei beim bin bis bist bitte dabei dadurch
dafür damit dann daran darauf daraus das dass dein deine dem den denn der deren des dessen dich die dies diese
diesem diesen dieser dieses doch dort durch eigentlich eine einem einen einer eines einfach einmal erst etwa
etwas euch euer eure für gegen gerade gibt habe haben hast hatte hatten hier hinter ich ihm ihn ihnen ihr ihre
ihrem ihren ihrer immer indem ins ist jede jedem jeden jeder jedes jetzt kann kannst können könnte machen
mache machst macht mal man mehr mein meine meinem meinen meiner mich mir mit muss musst müssen nach nicht
nichts noch nur oder ohne schon sehr sein seine seinem seinen seiner selbst sich sie sind soll sollen sollte
sollten sondern sonst über und uns unser unsere unter viel vielleicht vom von vor wann war waren warum was
weil welche welchem welchen welcher welches wenn werde werden wieder will wird wirst woher wohin würde
würden zum zur zwar zwischen dieses dazu darin dass wäre hätte hast könnten sollen genau gerne bitte danke
about above after again against because been before being below between both cannot could does doing done
down during each from further have having here how into just more most much must need only other
over same shall should since some such than that their them then there these they this those through
under until very want wants were what when where whether which while whom whose will with within without
would your yours please make sure just like also thing things something anything everything nothing
""".split())
FTS_STRIP = re.compile(r'["*()^:{}\[\]\\|~<>!?,;+=]')
WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9_][A-Za-zÄÖÜäöüß0-9_.\-]{2,}")


def read_hook_input():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw and raw.strip() else {}
    except Exception:
        return {}


def hints_enabled(vault):
    try:
        cfg = json.loads((vault / ".mastermind.json").read_text(encoding="utf-8"))
        return cfg.get("prompt_hints") is not False
    except Exception:
        return True


def is_identifier(term):
    return ("_" in term or "." in term or any(c.isdigit() for c in term)
            or (re.search(r"[a-z][A-Z]", term) is not None))


def extract_terms(prompt):
    """(terms, identifiers): lowercase words >= 4 chars without stopwords; identifiers first, max MAX_TERMS.
    Hyphenated compounds (hmac-signatur) are split into their parts: the FTS tokenizer splits on hyphens too."""
    idents, words, seen = [], [], set()

    def add(raw):
        raw = raw.strip(".-_")
        if len(raw) < 4:
            return
        low = raw.lower()
        if low in STOPWORDS or low in seen:
            return
        seen.add(low)
        (idents if is_identifier(raw) else words).append(low)

    for raw in WORD_RE.findall(prompt):
        if "-" in raw and not is_identifier(raw.replace("-", "")):
            for part in raw.split("-"):
                add(part)
        else:
            add(raw)
    terms = (idents + words)[:MAX_TERMS]
    return terms, set(idents)


def fts_query(terms):
    parts = []
    for t in terms:
        clean = FTS_STRIP.sub(" ", t).strip()
        if clean:
            parts.append('"' + clean.replace('"', "") + '"')
    return " OR ".join(parts)


def query_index(db, project, match, idents):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=0.2)
    try:
        row = con.execute("select id from project where name=?", (project,)).fetchone()
        if not row:
            return []
        pid = row[0]
        rows = con.execute(
            "select title, file_path, bm25(search_index) as score from search_index "
            "where search_index match ? and type='entity' and project_id=? "
            "and (file_path like 'gotchas/%' or file_path like 'patterns/%' or file_path like 'decisions/%' "
            "or file_path like 'howtos/%' or file_path like 'stacks/%') order by score limit 20",
            (match, pid)).fetchall()
    finally:
        con.close()
    scored = {}
    for title, fp, score in rows:
        if not title or not fp:
            continue
        low = title.lower()
        bonus = sum(IDENT_BONUS for t in idents if t in low)
        s = score + bonus
        if fp not in scored or s < scored[fp][0]:
            scored[fp] = (s, title)
    return sorted(((s, t, fp) for fp, (s, t) in scored.items()), key=lambda x: x[0])


def note_type(fp):
    return {"gotchas": "gotcha", "patterns": "pattern", "decisions": "decision", "howtos": "howto", "stacks": "stack"}.get(fp.split("/", 1)[0], "note")


def main():
    data = read_hook_input()
    prompt = (data.get("prompt") or "").strip()
    if len(prompt) < MIN_PROMPT_CHARS or prompt.startswith(("/", "<")):
        return
    vault = Path(os.environ.get("MASTERMIND_VAULT") or "~/Mastermind").expanduser()
    if not hints_enabled(vault):
        return
    cfg_dir = Path(os.environ.get("BASIC_MEMORY_CONFIG_DIR") or "~/.basic-memory").expanduser()
    db = cfg_dir / "memory.db"
    if not db.is_file():
        return
    terms, idents = extract_terms(prompt)
    if len(terms) < MIN_TERMS:
        return
    match = fts_query(terms)
    if not match:
        return
    try:
        hits = query_index(db, os.environ.get("BASIC_MEMORY_MCP_PROJECT") or "mastermind", match, idents)
    except sqlite3.Error:
        return
    hits = [h for h in hits if h[0] <= BM25_THRESHOLD]
    if not hits:
        return
    state = Path(os.environ.get("XDG_STATE_HOME") or "~/.local/state").expanduser() / "mastermind"
    sid = re.sub(r"[^A-Za-z0-9-]", "", data.get("session_id") or "nosession")
    seen_file = state / f"hints-{sid}.txt"
    try:
        seen = set(seen_file.read_text(encoding="utf-8").splitlines()) if seen_file.is_file() else set()
    except Exception:
        seen = set()
    fresh = [h for h in hits if h[2] not in seen][:MAX_HITS]
    if not fresh:
        return
    try:
        state.mkdir(parents=True, exist_ok=True)
        with open(seen_file, "a", encoding="utf-8") as fh:
            fh.write("".join(h[2] + "\n" for h in fresh))
    except Exception:
        pass
    text = "Möglicherweise relevant: " + " · ".join(f"[[{t}]] ({note_type(fp)})" for _, t, fp in fresh) + ". Bei Bedarf read_note."
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                             "additionalContext": f"<mastermind-hint>{text}</mastermind-hint>"}},
                     ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
