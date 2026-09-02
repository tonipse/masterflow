# Mastermind v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mastermind wird zu einem automatisch lernenden, projektübergreifenden Gedächtnis: reparierter mehrsprachiger Index, Vault außerhalb von TCC, Hooks für Startkontext und Sicherung, autonomes Capture, Session-Abschluss-Command, Projekt-Onboarding.

**Architecture:** Der Vault zieht nach `~/Mastermind`; basic-memory bekommt ein mehrsprachiges Modell und einen vollen Reindex. Das Plugin `mastermind` (0.2.0) erhält einen SessionStart-Hook (Python, liest den Vault direkt), einen SessionEnd-Commit-Hook, drei Skills (`mastermind-brain` mit `conventions.md`, `mastermind-wrap` mit `checklist.md` und `evidence.py`, `mastermind-project`) und fünf dünne Commands.

**Tech Stack:** Claude Code Plugins (hooks.json, SKILL.md), basic-memory 0.22.1 (sqlite-vec, FastEmbed), Python 3 stdlib, bash, git, Obsidian.

**Spec:** `docs/superpowers/specs/2026-09-03-mastermind-v2-design.md`

## Global Constraints

- Vault-Zielpfad: `/Users/toni/Mastermind`; Übergangs-Symlink `~/Desktop/Mastermind → ~/Mastermind` bleibt bis zum Neustart von Claude Code.
- Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, `semantic_embedding_dimensions: 768`, `auto_update: false`.
- Plugin-Version `0.2.0` in `plugins/mastermind/.claude-plugin/plugin.json` **und** `.claude-plugin/marketplace.json`.
- Sprache: Plugin-Skills/Commands/Hook-Kontext Englisch; Notizen, Vault-CLAUDE.md, Report-Ausgaben Deutsch.
- Hook-Skripte: nur Python-3-stdlib und bash; jeder Fehler endet mit Exit 0 (SessionStart) und maximal einer Warnzeile im Kontext.
- Ordnernamen im Vault ohne Projekt-Präfix (`gotchas/`, nie `mastermind/gotchas/`).
- Titel ≤ 80 Zeichen; Frontmatter-Wikilinks immer gequotet.
- Keine Secrets in Notizen.
- Prose-Dateien (SKILL.md, conventions.md, checklist.md, README) werden in der Ausführung nach den Abschnittsvorgaben der Spec §3.6–3.9 verfasst; Skripte stehen in diesem Plan vollständig.

---

### Task 1: Sicherung und Branch

**Files:**
- Modify: Vault-Git (`~/Desktop/Mastermind/.git`)
- Modify: masterflow-Git, Branch `feat/mastermind-v2`

- [x] **Step 1: Vault-Zustand committen (untracked Notizen seit Juli)**

```bash
git -C ~/Desktop/Mastermind add -A
git -C ~/Desktop/Mastermind commit -qm "chore: Stand vor v2-Migration (Notizen Jul–Sep 2026)"
git -C ~/Desktop/Mastermind log --oneline -1
```
Expected: ein neuer Commit, `git status --short` leer.

- [x] **Step 2: Branch anlegen und Spec + Plan committen**

```bash
cd /Users/toni/Desktop/masterflow && git checkout -b feat/mastermind-v2
git add docs/superpowers && git commit -qm "docs: Mastermind v2 Spec und Plan"
```

### Task 2: Vault-Umzug nach ~/Mastermind

**Files:**
- Move: `~/Desktop/Mastermind` → `~/Mastermind`
- Modify: `~/.basic-memory/config.json` (Pfad), `~/Library/Application Support/obsidian/obsidian.json`
- Copy: `~/.claude/projects/-Users-toni-Desktop-Mastermind/memory/` → `~/.claude/projects/-Users-toni-Mastermind/memory/`

- [x] **Step 1: Obsidian beenden (hat den Vault offen)**

```bash
osascript -e 'tell application "Obsidian" to quit'; sleep 2; pgrep -x Obsidian || echo "Obsidian beendet"
```

- [x] **Step 2: Verschieben + Übergangs-Symlink**

```bash
mv ~/Desktop/Mastermind ~/Mastermind && ln -s ~/Mastermind ~/Desktop/Mastermind
ls ~/Mastermind/index.md && readlink ~/Desktop/Mastermind
```

- [x] **Step 3: basic-memory-Projektpfad umziehen und prüfen**

```bash
basic-memory project move mastermind ~/Mastermind
python3 -c "import json;c=json.load(open('$HOME/.basic-memory/config.json'));print(c['projects']['mastermind'])"
sqlite3 ~/.basic-memory/memory.db "select name,path from project;"
```
Expected: beide zeigen `/Users/toni/Mastermind`. Falls `config.json` noch den alten Pfad trägt: per Python-Einzeiler auf den neuen Pfad setzen.

- [x] **Step 4: Obsidian-Vault-Registry umschreiben und Obsidian starten**

```bash
python3 - <<'EOF'
import json,os
p=os.path.expanduser('~/Library/Application Support/obsidian/obsidian.json')
d=json.load(open(p))
for v in d['vaults'].values():
    if v.get('path')=='/Users/toni/Desktop/Mastermind': v['path']='/Users/toni/Mastermind'
json.dump(d,open(p,'w'),indent=2)
print([v['path'] for v in d['vaults'].values()])
EOF
open -a Obsidian
```

- [x] **Step 5: Claude-Auto-Memory des Vault-Projekts mitnehmen**

```bash
mkdir -p ~/.claude/projects/-Users-toni-Mastermind && cp -Rn ~/.claude/projects/-Users-toni-Desktop-Mastermind/memory ~/.claude/projects/-Users-toni-Mastermind/
ls ~/.claude/projects/-Users-toni-Mastermind/memory
```

### Task 3: basic-memory-Konfiguration und voller Reindex

**Files:**
- Modify: `~/.basic-memory/config.json`

- [x] **Step 1: Modell, Dimension, auto_update setzen**

```bash
python3 - <<'EOF'
import json,os
p=os.path.expanduser('~/.basic-memory/config.json'); c=json.load(open(p))
c['semantic_embedding_model']='sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
c['semantic_embedding_dimensions']=768
c['auto_update']=False
json.dump(c,open(p,'w'),indent=2)
print({k:c[k] for k in ('semantic_embedding_model','semantic_embedding_dimensions','auto_update','semantic_min_similarity')})
EOF
```

- [x] **Step 2: Voller Reindex (lädt das Modell, ~1 GB, einmalig)**

```bash
basic-memory reindex --full -p mastermind 2>&1 | tail -15
```

- [x] **Step 3: Vollständigkeit prüfen**

```bash
find ~/Mastermind -name '*.md' -not -path '*/.obsidian/*' | wc -l
sqlite3 ~/.basic-memory/memory.db "select count(*) from entity e join project p on p.id=e.project_id where p.name='mastermind';"
sqlite3 ~/.basic-memory/memory.db "select sql from sqlite_master where name='search_vector_embeddings';" | grep -o 'float\[[0-9]*\]'
```
Expected: Entity-Anzahl = Dateianzahl (±2), Vektortabelle `float[768]`.

- [x] **Step 4: Deutsche Testabfragen (Kalibrierung `semantic_min_similarity`)**

```bash
basic-memory tool search-notes --project mastermind --hybrid "Webhook Signatur Raw Body" --page-size 3
basic-memory tool search-notes --project mastermind --vector "Google Service Account Schlüssel in Lambda" --page-size 3
basic-memory tool search-notes --project mastermind --vector "Testdatei bricht wegen hängendem await" --page-size 3
```
Expected: HMAC-Webhook-Gotcha, Google-Service-Account-Gotcha, Vitest-act-Gotcha unter den Top 3. Liefert `--vector` nichts, `semantic_min_similarity` auf 0.45 senken und wiederholen.

### Task 4: Vault-Hygiene und Schema-Erweiterung

**Files:**
- Move: `~/Mastermind/mastermind/gotchas/ra-approvals …md` → `~/Mastermind/gotchas/`
- Rename: `~/Mastermind/projects/fwg-warehouse (FWG Lagersystem- …).md` → `~/Mastermind/projects/fwg-warehouse.md`
- Modify: 5 Notizen mit Links auf den alten Titel; `projects/fwg-warehouse-api-job.md`, `projects/fwg-notfallversand.md`, `projects/fwg-one.md`, `projects/_projects-overview.md`, `projects/ra-approvals.md`, `CLAUDE.md`, `templates/project.md`, `index.md`
- Create (Scratch, einmalig): `enrich_hubs.py` → schreibt `repo`/`path` in alle Hubs

- [x] **Step 1: Verirrte Notiz verschieben und Frontmatter vervollständigen**
Datei nach `gotchas/` verschieben, Frontmatter um `created: '2026-08-04'`, `updated: '2026-09-03'`, `status: active`, `confidence: high`, `projects: ["[[ra-approvals]]"]`, `related: ["[[ra-approvals]]", "[[neon]]"]` ergänzen, Abschnitt „Verwandt" mit beiden Links anhängen, `mastermind/`-Ordner löschen. In `projects/ra-approvals.md` unter „Bekannte Gotchas" eine Zeile `- [gotcha] Siehe [[ra-approvals brands-Prod-Schema driftet von den Migrationen ab]] #postgres #migrations` ergänzen.

- [x] **Step 2: Dach-Hub `fwg-warehouse`**
Datei umbenennen, `title: fwg-warehouse`, `permalink: mastermind/projects/fwg-warehouse`, Tags → `project, group/fwg-one, stack/aws-lambda, stack/shopify, stack/mysql, stack/nodejs`, `related` um `[[fwg-one]]`, `[[fwg-warehouse-api-order]]`, `[[fwg-warehouse-api-job]]`, `[[fwg-warehouse-app]]`, `[[fwg-warehouse-prod-document-generator]]`, `[[fwg-notfallversand]]` erweitern, Abschnitt „Repo-Hubs" mit denselben Links einfügen. Anschließend im gesamten Vault den alten Wikilink-Text durch `fwg-warehouse` ersetzen:

```bash
cd ~/Mastermind && grep -rl "fwg-warehouse (FWG Lagersystem: api-order + api-job Lambdas)" --include='*.md' . 
# dann per Python: Ersetzung in allen Treffern (Frontmatter + Body), Prüfung: grep liefert 0 Treffer
```
In den fünf Notizen zusätzlich `projects` um den Repo-Hub ergänzen: Shopify-Order-Editing, Refund-Berechnung, DHL-Zollzeilen → `[[fwg-warehouse-api-job]]`; Vitest-act, Roter-Test → `[[fwg-notfallversand]]`. Backlink-Zeilen in beiden Repo-Hubs unter „Bekannte Gotchas". `[[fwg-warehouse]]` in `_projects-overview.md` (FWG-Abschnitt) und `fwg-one.md` eintragen.

- [x] **Step 3: Hubs mit `repo`/`path` anreichern (Skript)**
Skript liest jede `projects/*.md`, sucht im Body nach `` `~/Desktop/…` `` bzw. `` `/Users/toni/…` ``, prüft Existenz, ermittelt `git -C <path> remote get-url origin` (normalisiert: ohne `.git`, `git@host:` → `host/`, `https://host/` → `host/`, lowercase) und fügt `repo:`/`path:` hinter `type:` ins Frontmatter ein, falls nicht vorhanden. Ausgabe: Tabelle Hub | path gefunden | repo.

- [x] **Step 4: Vault-CLAUDE.md, templates/project.md, index.md auf v2**
CLAUDE.md: Pfad `~/Mastermind`, Ordnerregel (kein Präfix), Titelregel, Hub-Felder `repo/path/last_wrap`, Hinweis auf Hooks/`/mastermind:wrap`. Template: Felder `repo: null`, `path: null`, `last_wrap: null`, Hinweistext ohne `~/Desktop/`. index.md: Zeile „Automatik (v2, Stand 2026-09)" mit den Commands.

- [x] **Step 5: Commit und inkrementeller Reindex**

```bash
git -C ~/Mastermind add -A && git -C ~/Mastermind commit -qm "chore(v2): Hygiene, Dach-Hub fwg-warehouse, repo/path in Hubs, Konventionen v2"
basic-memory reindex -p mastermind 2>&1 | tail -3
grep -rL "^repo:" ~/Mastermind/projects/*.md | wc -l   # Hubs ohne repo (nur solche ohne Pfad auf Platte)
```

### Task 5: Hooks im Plugin

**Files:**
- Create: `plugins/mastermind/hooks/hooks.json`
- Create: `plugins/mastermind/hooks/session-start` (bash-Wrapper, ausführbar)
- Create: `plugins/mastermind/hooks/session_start.py`
- Create: `plugins/mastermind/hooks/vault-commit` (bash, ausführbar)
- Delete: `plugins/mastermind/hooks/hooks.json.example`

**Interfaces:**
- Produces: `session_start.py` liest stdin-JSON (`cwd`, `source`|`how_started`), schreibt `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"…"}}`; Env `MASTERMIND_VAULT` überschreibt `~/Mastermind`; Hub-Match via Frontmatter `repo`, `path`, Titel.

- [x] **Step 1: hooks.json**

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|resume|clear|compact",
        "hooks": [ { "type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/session-start\"", "timeout": 10 } ] }
    ],
    "SessionEnd": [
      { "hooks": [ { "type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/vault-commit\"", "timeout": 10 } ] }
    ]
  }
}
```

- [x] **Step 2: session-start (Wrapper) und session_start.py (Logik laut Spec §3.4)**
Wrapper: `command -v python3 >/dev/null || exit 0; exec python3 "$(dirname "$0")/session_start.py"`. Python: Funktionen `read_hook_input()`, `find_vault()`, `project_identity(cwd)`, `parse_frontmatter(text)`, `load_hubs(vault)`, `match_hub(hubs, identity)`, `recent_notes_for_hub(vault, hub_title)`, `similar_hubs(hubs, tags, exclude)`, `sniff_stack(root)`, `index_health(vault)`, `render(...)`, `main()`; jede Stufe in `try/except`, Sammel-Warnungen; Ausgabe immer JSON, Exit 0.

- [x] **Step 3: vault-commit**

```bash
#!/usr/bin/env bash
VAULT="${MASTERMIND_VAULT:-$HOME/Mastermind}"
[ -d "$VAULT/.git" ] || exit 0
cd "$VAULT" || exit 0
[ -n "$(git status --porcelain)" ] || exit 0
PROJECT="$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")"
git add -A >/dev/null 2>&1 && git commit -qm "auto: session end (${PROJECT})" >/dev/null 2>&1
exit 0
```

- [x] **Step 4: Tests der Hook-Skripte (5 Szenarien + Zeit)**

```bash
H=plugins/mastermind/hooks
for CWD in /Users/toni/Desktop/supportpilot /Users/toni/Desktop/moeller-dev/myCOOassistant /Users/toni/Desktop/fwg-dev/fwg-warehouse-api-job/.claude/worktrees/notfallversand-marketplace-ersatzteile /private/tmp; do
  printf '{"cwd":"%s","source":"startup","hook_event_name":"SessionStart"}' "$CWD" | ( time bash $H/session-start ) 2>&1 | python3 -c 'import sys,json; d=sys.stdin.read(); j=json.loads(d[:d.rfind("}")+1]); print(j["hookSpecificOutput"]["additionalContext"][:1200]); print("---")'
done
MASTERMIND_VAULT=/nonexistent printf '{"cwd":"/tmp","source":"startup"}' | bash $H/session-start
```
Expected: gültiges JSON in allen Fällen; supportpilot zeigt Hub + ähnliche Projekte; myCOOassistant zeigt „kein Hub" + Stack-Sniff; Worktree löst auf `fwg-warehouse-api-job`; `/private/tmp` zeigt nur Regeln; fehlender Vault eine Warnzeile. Laufzeit < 150 ms.

### Task 6: Skills und Commands

**Files:**
- Rewrite: `plugins/mastermind/skills/mastermind-brain/SKILL.md`
- Create: `plugins/mastermind/skills/mastermind-brain/conventions.md`
- Create: `plugins/mastermind/skills/mastermind-wrap/SKILL.md`, `checklist.md`, `evidence.py`
- Create: `plugins/mastermind/skills/mastermind-project/SKILL.md`
- Modify: `plugins/mastermind/commands/{recall,capture,gotcha,decision,index}.md`
- Delete: `plugins/mastermind/commands/project.md`

**Interfaces:**
- `evidence.py --session <id> --since <YYYY-MM-DD|none> [--root <repo>]` druckt Markdown: Git-Log/Status seit `since`, Auto-Memory-Dateien seit `since` (Slug = cwd mit `/`→`-`), Session-Zeitachse aus `~/.claude/projects/<slug>/<session>.jsonl` (User-Prompts gekürzt, editierte Dateien, Fehlerzeilen aus Tool-Results); fehlende Quellen werden als „nicht gefunden" gemeldet, nie als Fehler.

- [x] **Step 1: conventions.md** (Abschnitte: Notiztypen & Ordner, Frontmatter-Schema inkl. Hub-Felder, Titelregeln, Body-Struktur je Typ, Observations & Recency, Links, kanonische Stack-Tags, Dedup-Prozedur, Was-wohin-Regel, Sprache).
- [x] **Step 2: mastermind-brain/SKILL.md** (Recall, autonome Capture-Policy, Qualitätsschwelle, Verweis auf conventions.md, Tools, Companion-Commands).
- [x] **Step 3: mastermind-wrap/SKILL.md + checklist.md + evidence.py** (Ablauf Spec §3.7; Test: `python3 evidence.py --session 98f715ee-3a97-49ef-9bbb-fec396d35c4c --since 2026-09-01` aus diesem Repo liefert Zeitachse).
- [x] **Step 4: mastermind-project/SKILL.md** (Spec §3.8).
- [x] **Step 5: Commands aktualisieren, project.md löschen.**
- [x] **Step 6: Validierung**

```bash
claude plugin validate plugins/mastermind --strict && claude plugin validate plugins/mastermind/skills --strict && claude plugin validate plugins/mastermind/commands --strict
```

### Task 7: Manifest, README, masterflow-CLAUDE.md

- [x] **Step 1:** `plugin.json` → `version: 0.2.0`, Beschreibung erwähnt Hooks/Wrap. `marketplace.json` → mastermind `0.2.0`.
- [x] **Step 2:** `plugins/mastermind/README.md` (Voraussetzungen inkl. Vault-Pfad, `MASTERMIND_VAULT`, python3; Hooks; Skills/Commands; Update-Ablauf; Modellwechsel-Hinweis).
- [x] **Step 3:** `.claude/CLAUDE.md` Abschnitt „Architektur: mastermind" auf v2 (Pfad, Hooks, Skills, conventions.md, Zählung der Komponenten, Test-Befehle für Hook-Skripte).
- [x] **Step 4:** `claude plugin validate . --strict && claude plugin validate .claude-plugin/plugin.json --strict`; Commit.

### Task 8: End-to-End-Test mit lokalem Plugin

- [x] **Step 1:** `cd ~/Desktop/supportpilot && claude --plugin-dir /Users/toni/Desktop/masterflow/plugins/mastermind -p "Gib den Inhalt des <mastermind>-Kontextblocks wörtlich zurück, sonst nichts." --max-turns 1` → Kontextblock erscheint mit Hub `supportpilot`.
- [x] **Step 2:** `claude --plugin-dir … -p "/mastermind:wrap dry" --max-turns 6` in `~/Desktop/supportpilot` → Report ohne Schreibzugriffe, Vault-Git bleibt sauber.

### Task 9: Deployment

- [x] **Step 1:** `git checkout main && git merge --ff-only feat/mastermind-v2 && git push origin main`
- [x] **Step 2:** `claude plugin marketplace update masterflow && claude plugin update mastermind@masterflow`
- [x] **Step 3:** `ls ~/.claude/plugins/cache/masterflow/mastermind/` zeigt `0.2.0`; `claude plugin details mastermind@masterflow` zeigt Hooks (2) und Skills.

### Task 10: Memory und Abschlussbericht

- [x] **Step 1:** Memory-Dateien im masterflow-Memory-Verzeichnis: User-Präferenzen (autonomes Capture, Wrap-Nutzung), Projektstand v2, Vault-Pfad.
- [x] **Step 2:** Abschlussbericht: was geändert wurde, was der User tun muss (Claude Code neu starten, Symlink entfernen), offene Punkte.
