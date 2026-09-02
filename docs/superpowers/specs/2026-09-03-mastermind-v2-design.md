# Mastermind v2 – Design / Spec

Stand: 2026-09-03. Freigabe: Der User hat am 2026-09-03 die Umsetzung inklusive Vault-Umzug, Modellwechsel und aller Empfehlungen vorab freigegeben („vollautomatischer Run").

## 1. Ausgangslage (Befund)

| Befund | Beleg |
|---|---|
| Index seit 2026-07-24 praktisch leer (9 von 165 Notizen) | `full_deletions`-Scan am 24.07. 21:58 mit `deleted=166`; am selben Tag 13× `PermissionError: Operation not permitted` (macOS-TCC auf `~/Desktop`) |
| `basic-memory status` meldet fälschlich „No changes" | inkrementeller Scan nutzt mtime-Wasserlinie; alte Dateien liegen darunter |
| Embedding-Modell rein englisch (`bge-small-en-v1.5`), Vault deutsch | `~/.basic-memory/config.json` |
| Dubletten durch blinde Suche | vierter Hub `fwg-warehouse (FWG Lagersystem …)` neben drei bestehenden; Notiz unter `mastermind/gotchas/` statt `gotchas/` |
| Capture nur auf Zuruf, kein Hook aktiv, kein Session-Abschluss | Plugin 0.1.0 |
| Hubs kennen ihr Repo nicht maschinenlesbar | Pfad nur im Fließtext |
| Zweites Gedächtnis: Claude-Auto-Memory, 193 Dateien in 32 Projekten | `~/.claude/projects/*/memory/` |

Mechanismus des Wipes (verifiziert im Code, `sync_service.py`): Sinkt die Dateianzahl unter `last_file_count`, läuft ein `full_deletions`-Scan. Ist das Verzeichnis nicht lesbar (TCC) oder verschoben, ist die Anzahl 0 und **alle** Einträge werden gelöscht.

## 2. Ziele

1. Wissen wird automatisch erfasst, wenn Claude etwas Nicht-Offensichtliches verifiziert hat. Kein Nachfragen, aber eine Meldung.
2. Ein Session-Abschluss-Command erntet alles Wichtige der Session, aktualisiert den Projekt-Hub und sichert den Vault.
3. Neue Projekte werden beim ersten Kontakt sauber angelegt und mit ähnlichen Projekten und Stacks verbunden.
4. Cross-Projekt-Zugriff funktioniert über eine reparierte, mehrsprachige Hybrid-Suche plus deterministisch injizierten Startkontext.
5. Der Juli-Fehler kann nicht unbemerkt wieder passieren.

Nicht-Ziele: Cloud, Per-Prompt-RAG-Hook, Backfill der Auto-Memory-Silos (eigene Phase 2), Umbau von `masterflow`.

## 3. Architektur

```
Projekt X → Claude Code
  ├─ Hook SessionStart (startup|clear|compact)  → hooks/session_start.py
  │     liest Vault direkt (kein Index nötig): Hub, offene Punkte, zuletzt Gelerntes,
  │     ähnliche Projekte, Stack-Notizen, Index-Gesundheit; injiziert ~400 Token + Regeln
  ├─ Hook SessionEnd → hooks/vault-commit  (git commit im Vault, falls dirty)
  ├─ Skill mastermind-brain (modell-aufrufbar): Recall-/Capture-Policy + conventions.md
  ├─ Skill mastermind-wrap (User): Session-Abschluss, Hauptkontext, evidence.py
  ├─ Skill mastermind-project (User): Onboarding / Hub-Pflege
  ├─ Commands recall, capture, gotcha, decision, index (dünn)
  └─ .mcp.json → basic-memory mcp, BASIC_MEMORY_MCP_PROJECT=mastermind
                      ▼
            ~/Mastermind (Obsidian-Vault, git)   ←  Obsidian
            ~/.basic-memory/memory.db (Index, sqlite-vec, FTS5)
```

### 3.1 Vault-Umzug

- Ziel `~/Mastermind` (außerhalb der TCC-geschützten Ordner Desktop/Dokumente/Downloads).
- Ablauf: Vault-Git committen → Obsidian beenden → `mv` → Symlink `~/Desktop/Mastermind → ~/Mastermind` als Übergang (der laufende MCP-Watcher sieht weiter dieselben Dateien, kein Deletion-Scan) → `basic-memory project move mastermind ~/Mastermind` → `config.json` prüfen → `obsidian.json` Pfad ersetzen → Obsidian starten → Claude-Auto-Memory `-Users-toni-Desktop-Mastermind` nach `-Users-toni-Mastermind` kopieren.
- Alle Pfadverweise auf `~/Desktop/Mastermind` in Plugin, README, masterflow-CLAUDE.md, Vault-CLAUDE.md, Template aktualisieren. Code-Projekt-Pfade in Hubs bleiben (die Projekte liegen weiter auf dem Desktop).

### 3.2 basic-memory-Konfiguration

| Schlüssel | Wert | Grund |
|---|---|---|
| `semantic_embedding_model` | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | mehrsprachig, kein Prefix-Zwang, 768 Dim. |
| `semantic_embedding_dimensions` | `768` | Vektortabelle wird bei Dimensionswechsel automatisch neu angelegt (`sqlite_search_repository.py`) |
| `auto_update` | `false` | keine stillen Engine-Updates unter dem Vault; Updates bewusst per `uv tool upgrade basic-memory` |
| `semantic_min_similarity` | nach Kalibrierung mit deutschen Testabfragen (Start 0.55, ggf. 0.45) | mpnet-Ähnlichkeiten verteilen sich anders als bge |

Danach `basic-memory reindex --full -p mastermind`, Erfolg = Entity-Anzahl ≈ Anzahl `.md` (ohne `.obsidian`).

### 3.3 Vault-Hygiene und Schema-Erweiterung

- Verirrte Notiz `mastermind/gotchas/ra-approvals …` nach `gotchas/`, Frontmatter vervollständigen, mit `[[ra-approvals]]` und `[[neon]]` verlinken, Backlink im Hub.
- Dubletten-Hub wird zum Dach-Hub `fwg-warehouse` (Titel `fwg-warehouse`), verlinkt die Repo-Hubs `fwg-warehouse-api-order`, `fwg-warehouse-api-job`, `fwg-warehouse-app`, `fwg-warehouse-prod-document-generator`, `fwg-notfallversand`. Die fünf Notizen mit dem langen Titel bekommen `[[fwg-warehouse]]` plus den passenden Repo-Hub in `projects`; Repo-Hubs erhalten Backlinks; `_projects-overview` und `fwg-one` verlinken den Dach-Hub.
- Neue Hub-Felder im Frontmatter: `repo` (normalisierte Remote-URL, z. B. `github.com/org/name`), `path` (absoluter Pfad), `last_wrap` (YYYY-MM-DD). Bestehende Hubs werden per Skript angereichert, wo der Pfad im Text steht und auf der Platte existiert.
- Vault-`CLAUDE.md` und `templates/project.md` auf Stand v2 (Pfad, Felder, Titelregeln, Ordnerregel ohne `mastermind/`-Präfix).
- Abschluss: Git-Commit im Vault.

### 3.4 SessionStart-Hook (`hooks/session_start.py`, Python 3 stdlib)

Eingabe: Hook-JSON auf stdin (`cwd`, `source`/`how_started`). Ausgabe: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "…"}}`, Exit 0 in jedem Fall (Fehler werden zu einer Warnzeile, nie zu einem Abbruch).

Ablauf:
1. Vault: `$MASTERMIND_VAULT` oder `~/Mastermind`. Fehlt er: Warnzeile, Ende.
2. Projekt-Identität: `git rev-parse --show-toplevel` und `--git-common-dir` (Worktrees → Hauptrepo), `git remote get-url origin` normalisiert, Ordnername.
3. Hub-Match in `projects/*.md`: `repo` > `path` > Titel/Dateiname = Ordnername (case-insensitiv, `-`/`_` egal).
4. Mit Hub: Titel, `updated`, `last_wrap`, Stack-Tags, Abschnitt „Offene Punkte"/„Status" (max. 5 Zeilen), bis zu 5 zuletzt geänderte Notizen, deren `projects` den Hub enthält, ähnliche Projekte (≥ 2 gemeinsame `stack/*`-Tags, Top 3), vorhandene `stacks/*`-Notizen zu den Stack-Tags.
5. Ohne Hub: Stack-Sniff aus Manifesten (package.json, pyproject, requirements, composer.json, go.mod, *.csproj) → Stack-Tags → ähnliche Hubs; Hinweis, dass Onboarding beim ersten Capture oder bei `/mastermind:wrap` läuft, sofort per `/mastermind:project`.
6. Index-Gesundheit: `.md`-Anzahl im Vault vs. `entity`-Zeilen in `~/.basic-memory/memory.db` (sqlite3). Unter 90 %: Warnung mit Fix-Befehl. Zusätzlich Warnung, wenn `config.json` einen anderen Vault-Pfad trägt.
7. Regelblock (englisch, kompakt): RECALL-Trigger, CAPTURE-Policy (autonom, erst Skill `mastermind:mastermind-brain` laden, dann Dubletten-Suche, dann schreiben, eine Meldezeile), was **nicht** in den Vault gehört, Hinweis auf `/mastermind:wrap`.

Budget: < 150 ms, < 500 Token Ausgabe. Wrapper `hooks/session-start` (bash, ohne Endung wie bei superpowers) findet `python3`; fehlt es, Exit 0 ohne Ausgabe.

### 3.5 SessionEnd-Hook (`hooks/vault-commit`)

Bash: wenn der Vault ein Git-Repo ist und `git status --porcelain` nicht leer → `git add -A && git commit -qm "auto: session end (<projektordner>)"`. `timeout: 10`. Sicherheitsnetz für autonome Schreibvorgänge, wenn der User `/mastermind:wrap` vergisst.

### 3.6 Skill `mastermind-brain` (modell-aufrufbar)

Kurz und policy-lastig; Details in `conventions.md` (per `${CLAUDE_SKILL_DIR}/conventions.md`):
- Recall-Trigger und Vorgehen (hybrid, Treffer nennen).
- Capture-Policy: autonom bei erfüllter Qualitätsschwelle (verifiziert, nicht offensichtlich, über das Projekt hinaus nützlich, reproduzierbar formuliert). Nie fragen, immer melden. Dubletten-Suche vor jedem Schreiben, `edit_note` bevorzugen.
- Was wohin: Vault = wiederverwendbares Engineering-Wissen + ein Hub pro Projekt. Auto-Memory = Projektstatus, User-Präferenzen, Session-Stand. Keine Secrets.

`conventions.md`: Notiztypen und Ordner (ohne Projekt-Präfix), Frontmatter-Schema (inkl. Hub-Felder `repo`, `path`, `last_wrap`), Titelregeln (≤ 80 Zeichen, Nominalphrase, Lehre in den Body), Observations `- [gotcha] … #tag`, Recency-Hinweis, Link-Pflicht, kanonische Stack-Tags, Dedup-Prozedur, Hub-Schema, Sprache (Deutsch).

### 3.7 Skill `mastermind-wrap` (Session-Abschluss)

Frontmatter: `disable-model-invocation: true`, **kein** `context: fork` (muss den Verlauf sehen), `effort: max`, `argument-hint: "[dry] [Fokus-Hinweis]"`, `allowed-tools` mit Read, Grep, Glob, Bash und den benötigten `mastermind-memory`-Tools.

Ablauf:
0. `$ARGUMENTS`: `dry` = nur Plan zeigen. Rest = Fokus. `conventions.md` und `checklist.md` lesen. Projekt und Hub bestimmen (Hook-Kontext, sonst Suche). Kein Hub → Onboarding-Prozedur aus `mastermind-project` ausführen, dann weiter.
1. Evidenz sammeln (gegen Kontextverlust durch Compaction): `python3 ${CLAUDE_SKILL_DIR}/evidence.py --session ${CLAUDE_SESSION_ID} --since <last_wrap>` liefert Git-Log/Status seit `last_wrap`, geänderte Auto-Memory-Dateien seit `last_wrap`, Best-effort-Zeitachse der Session aus dem Transkript (User-Prompts gekürzt, editierte Dateien, Fehlermeldungen aus Tool-Results). Plus der Gesprächsverlauf selbst.
2. Kandidaten ernten nach `checklist.md` (Kriterien je Typ, Skip-Liste, Qualitätsschwelle, max. ~7 Notizen, lieber wenige reiche).
3. Dedup und Platzierung: je Kandidat `search_notes` (hybrid) + Titelsuche → `edit_note` (erweitern) oder `write_note` (neu). Widersprüche werden in der alten Notiz aufgelöst („überholt seit …"), nie zwei widersprechende Notizen.
4. Schreiben nach Konventionen, Links: Hub + ≥ 1 thematische Notiz oder Stack-Notiz. Stack-Notizen bekommen Link-Zeilen für neue Gotchas.
5. Hub aktualisieren: `updated`, `last_wrap`, Stack (nur bei Änderung), Gelerntes-Links, Status-Zeile ersetzen, offene Punkte ersetzen (Erledigtes raus).
6. Vault-Commit `wrap(<projekt>): <n> notes`.
7. Report (deutsch): Tabelle Notiz | Typ | neu/aktualisiert | Pfad; Hub-Zeile; übersprungene Kandidaten mit Kurzgrund; Index-Warnung falls vorhanden. Keine Rückfragen.

### 3.8 Skill `mastermind-project` (Onboarding)

`disable-model-invocation: true`, kein Fork. Identität bestimmen, Existenz prüfen (repo/path/name), sonst Update-Modus. Quellen: CLAUDE.md, README, Manifeste, Git-Statistik, Auto-Memory `MEMORY.md`, `context/stack-analysis.md`. Stack-Tags aus kanonischer Liste, ähnliche Hubs und Stack-Notizen verlinken, Hub nach Template mit `repo`/`path`, Eintrag in `_projects-overview`, Vault-Commit, Pfad melden. Ersetzt `commands/project.md`.

### 3.9 Dünne Commands

`recall`, `capture`, `gotcha`, `decision`, `index`: laden zuerst den Skill `mastermind:mastermind-brain` (Konventionen) und folgen der Policy. `index` prüft zusätzlich Hubs ohne `repo`/`path`, Notizen ohne `projects`, Index-Gesundheit.

### 3.10 Manifest, Doku, Deployment

- Plugin-Version 0.2.0 an beiden Stellen (`plugin.json`, `marketplace.json`).
- README des Plugins und masterflow-`.claude/CLAUDE.md` auf v2.
- Branch `feat/mastermind-v2` → Merge in `main` → Push → `claude plugin marketplace update masterflow` → `claude plugin update mastermind@masterflow`. Claude Code danach neu starten (neue Embedding-Dimension im MCP-Server, neue Hooks).

## 4. Tests / Definition of Done

- [ ] `claude plugin validate` strict für Marketplace, Plugin, `skills`, `commands`.
- [ ] Hook-Skript: 5 Szenarien (Hub per Pfad, kein Hub mit Stack-Sniff, Worktree, Nicht-Git-Verzeichnis, fehlender Vault) liefern gültiges JSON, < 150 ms.
- [ ] Index-Check warnt vor dem Reindex (9/…) und ist danach grün.
- [ ] `basic-memory reindex --full` → Entity-Anzahl ≈ Dateianzahl; deutsche Testabfragen (z. B. „Webhook Signatur Raw Body", „Lambda Google Service Account Key") treffen die erwarteten Notizen per `--hybrid` und `--vector`.
- [ ] Vault-Git sauber committet, `mastermind/`-Ordner weg, Dach-Hub verlinkt, keine toten Wikilinks auf den alten Titel.
- [ ] Obsidian öffnet `~/Mastermind`; `basic-memory project list` zeigt den neuen Pfad.
- [ ] End-to-End: `claude --plugin-dir plugins/mastermind -p …` in einem Projekt mit Hub zeigt den injizierten Kontext.
- [ ] Plugin-Cache enthält 0.2.0 mit Hooks (`claude plugin details`).

## 5. Später (nicht Teil von v2)

- Phase 2 „Ernte": Auto-Memory-Silos der 32 Projekte einmalig nach Mastermind überführen.
- Per-Prompt-Hinweise aus dem FTS-Index (UserPromptSubmit) nur, wenn sich Präzision belegen lässt.
- `masterflow:init` schreibt eine Mastermind-Zeile in die Ziel-CLAUDE.md.
