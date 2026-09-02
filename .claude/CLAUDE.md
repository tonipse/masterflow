# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Was dieses Repo ist

Ein Claude-Code-**Plugin-Marketplace** (`.claude-plugin/marketplace.json`) mit zwei Plugins. Es gibt keinen Build, keine Tests und keinen Laufzeit-Code: Alles ist Markdown (Prompts für das Modell) plus JSON (Manifeste).

| Plugin | Quelle laut `marketplace.json` | Inhalt |
|---|---|---|
| `masterflow` | `./` (Repo-Root) | Skills `/masterflow:init`, `/masterflow:audit`, `/masterflow:apply` und `references/` |
| `mastermind` | `./plugins/mastermind` | MCP-Server `mastermind-memory` (basic-memory), Hooks (SessionStart-Kontext, UserPromptSubmit-Hinweise, SessionEnd-Commit/Push/State), Skills `mastermind-brain`, `mastermind-wrap`, `mastermind-project`, `mastermind-index` (mit `lint.py`, `repair_index.py`), vier `/mastermind:*`-Commands |

Weil die Quelle von `masterflow` das Repo-Root ist, wird **alles** im Root (auch `plugins/`, README, LICENSE und `.claude/`) mit dem masterflow-Plugin ausgeliefert. Für Plugin-Nutzer ist das inert: Claude Code lädt eine CLAUDE.md aus Plugin-Verzeichnissen nie, Plugins liefern Kontext ausschließlich über Skills (siehe code.claude.com/docs/en/plugins-reference).

Diese Datei liegt bewusst unter `.claude/` statt im Repo-Root: Beide Orte werden als Projekt-Kontext geladen, aber eine CLAUDE.md direkt im Plugin-Root meldet `claude plugin validate` als Warnung (mit `--strict` ein Fehler). Nicht ins Root verschieben.

Sie gilt nur für die Entwicklung **an** diesem Repo. Der CLAUDE.md-Abschnitt, den `/masterflow:init` in Zielprojekte schreibt, liegt in `skills/masterflow-init/claudemd-sections.md`.

## Befehle

„Testen" heißt hier: Manifeste und Frontmatter validieren, danach das Plugin in einer echten Claude-Code-Session ausprobieren.

```bash
# Manifeste (--strict: Warnungen gelten als Fehler, unbekannte Felder schlagen fehl)
claude plugin validate . --strict                           # marketplace.json
claude plugin validate .claude-plugin/plugin.json --strict  # masterflow
claude plugin validate plugins/mastermind --strict          # mastermind

# Frontmatter aller Skills/Commands eines Komponenten-Ordners
claude plugin validate skills --strict
claude plugin validate plugins/mastermind/skills --strict
claude plugin validate plugins/mastermind/commands --strict

# Komponenten-Inventar und geschätzte Token-Kosten (always-on / on-invoke) des installierten Stands
claude plugin details masterflow@masterflow
claude plugin details mastermind@masterflow

# Vor einem Release: prüft, dass plugin.json und Marketplace-Eintrag dieselbe Version tragen
# (verlangt einen sauberen Working Tree, sonst --force)
claude plugin tag --dry-run .
claude plugin tag --dry-run plugins/mastermind
```

`validate` akzeptiert einen einzelnen Skill-Ordner (z. B. `skills/masterflow-init`) **nicht**, dort erwartet es ein Manifest. Immer den übergeordneten Komponenten-Ordner angeben.

### Änderungen wirksam machen

Der lokal registrierte Marketplace `masterflow` zeigt auf **GitHub** (`tonipse/masterflow`), nicht auf diesen Ordner. Änderungen hier sind in Claude Code erst nach Commit und Push sichtbar:

```bash
claude plugin marketplace update masterflow
claude plugin update masterflow@masterflow      # bzw. mastermind@masterflow
# danach Claude Code neu starten
```

Installierte Stände liegen unter `~/.claude/plugins/cache/masterflow/<plugin>/<version>/`, der Marketplace-Clone unter `~/.claude/plugins/marketplaces/masterflow/`. Ein lokal per Pfad registrierter Marketplace (`claude plugin marketplace add <pfad>`) bekäme aus `marketplace.json` denselben Namen `masterflow` wie der bestehende GitHub-Marketplace. Vor einem solchen Umbau den User fragen.

### Versionen

Die Version steht an drei Stellen und muss übereinstimmen: `.claude-plugin/plugin.json` (masterflow), `plugins/mastermind/.claude-plugin/plugin.json` (mastermind) und die jeweiligen `plugins[].version`-Einträge in `.claude-plugin/marketplace.json`. Der Plugin-Cache ist nach Version benannt.

## Architektur: masterflow

### Skills sind Prompts mit hartem Rahmen

Alle drei `skills/*/SKILL.md` teilen dasselbe Frontmatter-Muster:

- `disable-model-invocation: true`: nur der User startet sie per Slash-Command, sie erscheinen nicht in der Skill-Liste des Modells.
- `context: fork` und `effort: max`: sie laufen als eigener Sub-Kontext, nicht im Haupt-Chat.
- `allowed-tools`: restriktive Whitelist. Braucht ein Skill ein weiteres Tool (Bash, ein MCP-Tool wie `mcp__context7__query-docs`), muss es dort eingetragen werden.

Skill-Name entspricht dem Ordnernamen, der Slash-Command ist `/<plugin>:<skill>`.

### Progressive Disclosure über `${CLAUDE_SKILL_DIR}`

Die SKILL.md enthält nur den Ablauf. Tabellen und Regeln liegen in Begleitdateien, die zur Laufzeit über relative Pfade gelesen werden (`**→ Read** ${CLAUDE_SKILL_DIR}/…`):

- `skills/masterflow-init/manifests.md`, `frameworks.md`, `source-patterns.md`: Erkennungs-Tabellen für Phase 1.
- `skills/masterflow-init/claudemd-sections.md`: der Skills-Abschnitt, der wörtlich in die CLAUDE.md des Zielprojekts kommt.
- `references/scoring.md`, `kill-criteria.md`, `sources.md`: von `init` **und** `audit` über `${CLAUDE_SKILL_DIR}/../../references/` geladen.
- `masterflow-audit` liest die Erkennungs-Tabellen aus `${CLAUDE_SKILL_DIR}/../masterflow-init/`.

Ordner umbenennen oder verschieben bricht diese Pfade **still**, die Skills laden die Datei dann einfach nicht. Nach Pfadänderungen alle drei SKILL.md nach `CLAUDE_SKILL_DIR` durchsuchen. Aus demselben Grund funktioniert die manuelle Installation aus der README nur mit angepassten Pfaden.

### Bewusste Duplikate

Phase 2 (Skill-Management) steht vollständig in `masterflow-init/SKILL.md` **und** in `masterflow-audit/SKILL.md`: Entscheidungsbaum, Schwellenwerte, Suchstrategie und das Tabellen-Schema von `skill-audit.md`. Der Gesamt-Workflow ist zusätzlich in `README.md` beschrieben. Regeländerungen müssen an allen Stellen nachgezogen werden. Die Scoring-Gewichte selbst stehen nur in `references/scoring.md`, die Schwellenwerte (Aufnahme ab 3.0, Ersetzen ab Differenz 1.0 bzw. 0.5 bei unzuverlässigem Skill) dagegen im Fließtext beider SKILL.md.

### Datenfluss im Zielprojekt

Die Skills laufen im Projekt des Users, nie hier. Sie übergeben sich Arbeit über Dateien im Zielprojekt:

- `init` und `audit` schreiben `context/stack-analysis.md` (bei `audit` inkrementell aktualisiert) und `context/skill-audit.md` (bei `audit` bei jedem Lauf komplett neu, kein Merge).
- Der User füllt die Spalte „Entscheidung"; leer bedeutet, die Empfehlung gilt.
- `apply` liest die Tabelle, legt vorher `.claude/skills-backup-<Datum>/` an, holt einmal eine Bestätigung ein, installiert ausschließlich nach `.claude/skills/` des Zielprojekts (nie global) und schreibt Status plus Installationsquelle (Marketplace, Repo-URL mit Commit, manuell) in `skill-audit.md` zurück.
- `init` führt Skill-Änderungen absichtlich **nicht** selbst aus. Die Trennung von Analyse und Ausführung ist gewollt.
- `init` Phase 5 ersetzt in der Ziel-CLAUDE.md die Abschnitte `## Skills`, `## Pflichtlektüre` und `## Kontext-Dateien` komplett und lässt alle anderen Abschnitte stehen.

### Harte Abhängigkeiten

Alle drei Skills setzen das **superpowers**-Plugin voraus und schreiben `superpowers:dispatching-parallel-agents` für unabhängige Teilaufgaben vor. `init` nutzt für Phase 4 zusätzlich Context7 (MCP); die Fallback-Kette ist Context7, dann WebFetch der offiziellen Docs, dann WebSearch.

## Architektur: mastermind

Design und Befund zu v2 (Index-Wipe durch macOS-TCC, Vault-Umzug, mehrsprachiges Modell, Hooks) stehen in `docs/superpowers/specs/2026-09-03-mastermind-v2-design.md`; v3 (Personal-OS-Anatomie der Hubs, Lint, Inbox, Root-Dateien, Zuverlässigkeit, Retrieval-Upgrade) in `docs/superpowers/specs/2026-09-03-mastermind-v3-personal-os-design.md`.

- `.mcp.json` startet `basic-memory mcp` mit `BASIC_MEMORY_MCP_PROJECT=mastermind`. Der Server ist dadurch fest auf das Vault `~/Mastermind` gepinnt, unabhängig vom Arbeitsverzeichnis und vom `default_project` von basic-memory. Die Tools erscheinen in Claude Code als `mcp__plugin_mastermind_mastermind-memory__<tool>`. Der Vault liegt bewusst **nicht** unter `~/Desktop` (TCC kann Hintergrundprozessen den Zugriff verweigern, basic-memory hält dann alle Notizen für gelöscht).
- `hooks/hooks.json` registriert drei Hooks, alle enden immer mit Exit 0, Python-3-stdlib, Vault-Pfad per `MASTERMIND_VAULT` überschreibbar:
  - **SessionStart** (`startup|resume|clear|compact`) → `hooks/session-start` → `session_start.py` liest den Vault direkt vom Dateisystem und injiziert als `hookSpecificOutput.additionalContext`: RULES (Recall, Capture, Leitplanken, Wrap), Hub, Status/offene Punkte, letzte `## Verlauf`-Zeile, Inbox-Zähler (`- [ ]` in `inbox/<hub>.md`), zuletzt gelernte Notizen, ähnliche Projekte, Stack-Notizen, den `UNWRAPPED`-Hinweis (State-File der letzten Session mit `wrapped: false`, `edits ≥ 5`, ≤ 14 Tage, `notified < 3`, andere `session_id`; `notified` wird hochgezählt), den Index-Check (Entities, Volltext- und Observation-Abdeckung; Warnung < 90 % mit `/mastermind:index repair-index`) und eine Ollama-Warnung (nur bei `semantic_embedding_provider: litellm`, 0,3 s Timeout). Budget ≤ 650 Token, < 150 ms. Test: `printf '{"cwd":"/pfad","source":"startup","session_id":"x"}' | bash plugins/mastermind/hooks/session-start`.
  - **UserPromptSubmit** → `prompt_hint.py`: BM25-Abfrage (`sqlite3`, read-only) über den FTS-Index, nur `gotchas/ patterns/ decisions/ howtos/ stacks/`, ≤ 3 Hinweise als `<mastermind-hint>`, je Notiz einmal pro Session (`~/.local/state/mastermind/hints-<session>.txt`). Stumm bei Prompts < 25 Zeichen, Slash-Commands, `<`-Prompts oder `"prompt_hints": false` in `~/Mastermind/.mastermind.json`. Stellknöpfe `BM25_THRESHOLD`, `MIN_TERMS`, `IDENT_BONUS` (Kalibrierung im Ledger der Umbau-Nachtsession).
  - **SessionEnd** → `hooks/session-end` → `session_end.py` (ohne python3 der alte Bash-Commit): Vault-Commit bei dirty Vault, Hintergrund-Push nur mit Remote `origin` und `push ≠ false`, State-File `~/.local/state/mastermind/last-session-<slug>.json` (Slug = Projekt-Root mit `/` → `-`, wie Claudes Projektordner) mit `session_id`, `transcript_path`, `edits` (Edit/Write/MultiEdit/NotebookEdit in Assistant-Zeilen), `wrapped` (nur echte Marker: `queue-operation`-Zeile, deren `content` mit `/mastermind:wrap` beginnt, oder `isMeta`-Skill-Zeile mit `/skills/mastermind-wrap`; der bloße Substring steht durch den RULES-Block in jedem Transkript), `notified`. Transkripte > 200 MB werden nicht gescannt.
- Hub-Zuordnung im Hook: Frontmatter `repo` (normalisierte Remote-URL) > `path` (absoluter Pfad, auch Präfix) > Titel/Dateiname = Ordnername. Linked Worktrees werden auf das Hauptrepo aufgelöst.
- `skills/mastermind-brain/SKILL.md` ist **modell-aufrufbar** (kein `disable-model-invocation`, kein `name:`-Feld). Es enthält Recall-Trigger, die Leitplanken-Regel (Decisions sind Constraints) und die **autonome** Capture-Policy (schreiben ohne Rückfrage, eine Meldezeile; Unverifiziertes als Inbox-Zeile). Alle Notiz-Konventionen liegen in `skills/mastermind-brain/conventions.md` (v3: §1 Nicht-Wissens-Typen `note`/`inbox`, §2 `source` Pflicht für gotcha/decision/pattern/howto, §4 Hub-Anatomie mit `## Quellen` und append-only `## Verlauf`, §9 Was wohin inkl. `user.md`/`soul.md`, §11 Leitplanken und Fokus, §12 Inbox-Format). `mastermind-wrap`, `mastermind-project` und `mastermind-index` laden sie über `${CLAUDE_SKILL_DIR}/../mastermind-brain/conventions.md`; `lint.py` parst daraus die kanonischen Stack-Tags (§7). Dieselben Konventionen stehen im Vault (`~/Mastermind/CLAUDE.md`, `AGENTS.md`, `templates/`); alle Stellen müssen zusammenpassen.
- `skills/mastermind-wrap/` (Session-Abschluss) läuft **ohne** `context: fork`, weil es den Gesprächsverlauf braucht. Argumente `dry|last|Fokus`; `last` holt die letzte ungewrappte Session aus dem State-File und dem Transkript-Digest nach. `evidence.py` liefert Git-Log/Status seit `last_wrap`, geänderte Auto-Memory-Dateien, eine Zeitachse aus dem Transkript `~/.claude/projects/<cwd mit / → ->/<session>.jsonl` (undokumentiertes Format, defensiv geparst) und mit `--digest` die kompakte Zusammenfassung (`--max-chars`, Standard 40.000, Kopf+Schwanz). `checklist.md` enthält Ernte-Kriterien, Skip-Liste, Fokus-Regel, Hub-Schema v3, Inbox-Regel und Report-Vorlage. Vor dem Commit läuft `lint.py --changed --strict`.
- `skills/mastermind-project/` ist das Onboarding (Hub v3 mit `repo`/`path`, Stack-Tags aus `conventions.md` §7, `## Quellen` aus den gelesenen Quellen, `## Verlauf`, ähnliche Projekte, Eintrag in `_projects-overview`, Lint vor dem Commit).
- `skills/mastermind-index/` (`name: index` → `/mastermind:index [fix] [repair-index]`, ersetzt das frühere `commands/index.md`): `lint.py` prüft Frontmatter, Typ/Ordner, Titel, Quoting, Wertemengen, Datumsregeln, `source`, Stack-Tags, Wikilink-Ziele, Orphans, Hub-Anatomie v3, Root-Zeilenlimits (`user.md` ≤ 60, `soul.md` ≤ 40), Inbox und den Index (`~/.basic-memory/memory.db` read-only). Bestandsschutz: Pflichtfelder, Wertemengen, `source` und Datumsregeln sind ERROR nur ab `created ≥ 2026-09-04`, sonst WARN; Titelregeln immer WARN; `templates/`, `_brainstorming/`, `_*` ausgenommen, `inbox/` nur INFO. CLI `[--vault] [--changed] [--json] [--strict] [--index-only] [--fix] [PFAD …]`; `--fix` nur sichere Fixes (`related`, Quoting, `## Verlauf`, `## Quellen`). `repair_index.py` repariert den Volltext-Index über den Watcher der laufenden Session (Checksum `NULL` + `touch` in 25er-Batches, max. 5 Runden, Sicherung nach `~/.basic-memory/backups/repair/`, höchstens 5 Sicherungen dort); ohne Watcher Meldung, bei > 2 Watchern Abbruch (`--force`).
- `commands/*.md` sind vier dünne Prompt-Wrapper mit `$ARGUMENTS` (`capture`, `decision`, `gotcha`, `recall`); sie laden zuerst den Skill `mastermind:mastermind-brain`. `claude plugin details` zählt Commands und Skills zusammen (acht Skills).
- Vault-Struktur v3 (`~/Mastermind`): Wissensordner, `projects/` (Hubs; Dach-Hubs mit Tag `moc`), `templates/`, `inbox/<hub>.md` (nicht indexiert: `inbox/` in `~/.basic-memory/.bmignore`), Root-Dateien `CLAUDE.md`, `AGENTS.md`, `user.md`, `soul.md` (die letzten beiden importiert `~/.claude/CLAUDE.md` mit `@~/Mastermind/user.md` und `@~/Mastermind/soul.md` in jede Session), `.mastermind.json` (`prompt_hints`, `push`), `.ernte/` (Ledger der Nachtsessions, nicht indexiert), `_brainstorming/` (Designs, Berichte). Neue `.md`-Dateien im Vault brauchen Frontmatter mit `title`, `type` und `permalink`, sonst schreibt basic-memory beim Sync selbst hinein.
- **Index-Reparatur-Regel:** `basic-memory reindex` (0.22.1 und 0.23.2, alle Varianten) schreibt Titel-only-Zeilen in den FTS-Index und verliert Observation-/Relation-Zeilen; `reindex --full --embeddings` bläht die Vektortabelle auf. Nur der Watcher des laufenden MCP-Servers indexiert vollständig. Deshalb: nie `reindex --full` auf einen gesunden Index, Reparatur über `/mastermind:index repair-index`; ein Modellwechsel läuft über den Server-Pfad (`retrieval-upgrade.sh`, untracked in `.claude/nachtsessions/`, startet kurz einen eigenen `basic-memory mcp`). Konkurrierende Watcher mehrerer Claude-Sessions erzeugen doppelte FTS-Zeilen und `database is locked`; vor Reparatur und Nachtsessions andere Sessions schließen.
- Lokale Voraussetzungen: `uv`, `basic-memory` als uv-Tool (heute 0.22.1; nach dem Retrieval-Upgrade 0.23.2, Installation mit `--prerelease=allow`), registriertes Projekt (`basic-memory project list` muss `mastermind` mit Pfad `~/Mastermind` zeigen), `python3`. Semantische Suche heute mit `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768 Dimensionen, Schwelle 0.45) in `~/.basic-memory/config.json`; Zielstack nach `retrieval-upgrade.sh`: Ollama (`brew services start ollama`) mit `qwen3-embedding:8b` (4096 Dimensionen, LiteLLM-Provider, Query-Präfix) und fastembed-Reranker `jinaai/jina-reranker-v2-base-multilingual` (Cache `~/.basic-memory/fastembed_cache`). `auto_update` bleibt `false`. Der SQLite-Index liegt unter `~/.basic-memory/`, nicht im Vault.

## Konventionen beim Bearbeiten

- Sprache: README, masterflow-Skills und `references/` sind Deutsch; Manifeste sowie mastermind-Skill und -Commands sind Englisch. Den Stil der jeweiligen Datei beibehalten.
- Skill-Text **ist** das Verhalten. Formulierungen wie „muss", Reihenfolgen und Zahlen in einer SKILL.md sind Instruktionen an das Modell, keine Doku. Entsprechend vorsichtig umformulieren.
- Neue Regeln oder Tabellen als Begleitdatei neben die SKILL.md legen und per `**→ Read** ${CLAUDE_SKILL_DIR}/…` einbinden, statt die SKILL.md wachsen zu lassen. Das Prinzip „Weniger ist mehr" aus den Skills gilt auch für deren eigenen Kontextverbrauch; `claude plugin details` zeigt die Kosten.
