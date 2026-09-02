# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Was dieses Repo ist

Ein Claude-Code-**Plugin-Marketplace** (`.claude-plugin/marketplace.json`) mit zwei Plugins. Es gibt keinen Build, keine Tests und keinen Laufzeit-Code: Alles ist Markdown (Prompts für das Modell) plus JSON (Manifeste).

| Plugin | Quelle laut `marketplace.json` | Inhalt |
|---|---|---|
| `masterflow` | `./` (Repo-Root) | Skills `/masterflow:init`, `/masterflow:audit`, `/masterflow:apply` und `references/` |
| `mastermind` | `./plugins/mastermind` | MCP-Server `mastermind-memory` (basic-memory), Hooks (SessionStart-Kontext, SessionEnd-Commit), Skills `mastermind-brain`, `mastermind-wrap`, `mastermind-project`, fünf `/mastermind:*`-Commands |

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

Design und Befund zu v2 (Index-Wipe durch macOS-TCC, Vault-Umzug, mehrsprachiges Modell, Hooks) stehen in `docs/superpowers/specs/2026-09-03-mastermind-v2-design.md`.

- `.mcp.json` startet `basic-memory mcp` mit `BASIC_MEMORY_MCP_PROJECT=mastermind`. Der Server ist dadurch fest auf das Vault `~/Mastermind` gepinnt, unabhängig vom Arbeitsverzeichnis und vom `default_project` von basic-memory. Die Tools erscheinen in Claude Code als `mcp__plugin_mastermind_mastermind-memory__<tool>`. Der Vault liegt bewusst **nicht** unter `~/Desktop` (TCC kann Hintergrundprozessen den Zugriff verweigern, basic-memory hält dann alle Notizen für gelöscht).
- `hooks/hooks.json` ist aktiv: SessionStart (`startup|clear|compact`) ruft `hooks/session-start` → `session_start.py` (Python-3-stdlib, liest den Vault direkt vom Dateisystem, ohne Index) und injiziert Regeln, Projekt-Hub, offene Punkte, zuletzt gelernte Notizen, ähnliche Projekte, Stack-Notizen und einen Index-Gesundheitscheck als `hookSpecificOutput.additionalContext`. SessionEnd ruft `hooks/vault-commit` (git commit im Vault, falls dirty). Beide enden immer mit Exit 0. Vault-Pfad per `MASTERMIND_VAULT` überschreibbar. Test ohne Session: `printf '{"cwd":"/pfad/zum/projekt","source":"startup"}' | bash plugins/mastermind/hooks/session-start`.
- Hub-Zuordnung im Hook: Frontmatter `repo` (normalisierte Remote-URL) > `path` (absoluter Pfad, auch Präfix) > Titel/Dateiname = Ordnername. Linked Worktrees werden auf das Hauptrepo aufgelöst.
- `skills/mastermind-brain/SKILL.md` ist **modell-aufrufbar** (kein `disable-model-invocation`, kein `name:`-Feld). Es enthält Recall-Trigger und die **autonome** Capture-Policy (schreiben ohne Rückfrage, eine Meldezeile). Alle Notiz-Konventionen liegen in `skills/mastermind-brain/conventions.md`; `mastermind-wrap` und `mastermind-project` laden sie über `${CLAUDE_SKILL_DIR}/../mastermind-brain/conventions.md`. Dieselben Konventionen stehen im Vault (`~/Mastermind/CLAUDE.md`, `templates/`); beide Stellen müssen zusammenpassen.
- `skills/mastermind-wrap/` (Session-Abschluss) läuft **ohne** `context: fork`, weil es den Gesprächsverlauf braucht. `evidence.py` liefert Git-Log/Status seit `last_wrap`, geänderte Auto-Memory-Dateien und eine Best-effort-Zeitachse aus dem Transkript `~/.claude/projects/<cwd mit / → ->/<${CLAUDE_SESSION_ID}>.jsonl` (undokumentiertes Format, daher defensiv geparst). `checklist.md` enthält Ernte-Kriterien, Skip-Liste, Hub-Schema und Report-Vorlage.
- `skills/mastermind-project/` ist das Onboarding (Hub mit `repo`/`path`/`last_wrap`, Stack-Tags aus `conventions.md` §7, ähnliche Projekte, Eintrag in `_projects-overview`).
- `commands/*.md` sind dünne Prompt-Wrapper mit `$ARGUMENTS`; sie laden zuerst den Skill `mastermind:mastermind-brain`. `claude plugin details` zählt Commands und Skills zusammen (acht Skills).
- Lokale Voraussetzungen: `uv`, `basic-memory` als uv-Tool (0.22+), registriertes Projekt (`basic-memory project list` muss `mastermind` mit Pfad `~/Mastermind` zeigen), `python3`. Semantische Suche mit `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768 Dimensionen) in `~/.basic-memory/config.json`; nach Modellwechsel `basic-memory reindex --full -p mastermind`. `auto_update` ist dort bewusst `false`. Der SQLite-Index liegt unter `~/.basic-memory/`, nicht im Vault.

## Konventionen beim Bearbeiten

- Sprache: README, masterflow-Skills und `references/` sind Deutsch; Manifeste sowie mastermind-Skill und -Commands sind Englisch. Den Stil der jeweiligen Datei beibehalten.
- Skill-Text **ist** das Verhalten. Formulierungen wie „muss", Reihenfolgen und Zahlen in einer SKILL.md sind Instruktionen an das Modell, keine Doku. Entsprechend vorsichtig umformulieren.
- Neue Regeln oder Tabellen als Begleitdatei neben die SKILL.md legen und per `**→ Read** ${CLAUDE_SKILL_DIR}/…` einbinden, statt die SKILL.md wachsen zu lassen. Das Prinzip „Weniger ist mehr" aus den Skills gilt auch für deren eigenen Kontextverbrauch; `claude plugin details` zeigt die Kosten.
