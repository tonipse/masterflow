# Masterflow

Projekt-Initialisierung, Skill-Management und Dokumentations-Workflow für Claude Code. Analysiert Tech-Stacks, auditiert Skills und konfiguriert Projekte automatisch.

## Voraussetzungen

- **[Superpowers](https://github.com/obra/superpowers)** — AI-driven Development Framework (Pflicht). Masterflow nutzt Superpowers für Parallelisierung, Planung und strukturiertes Arbeiten.
- **[Context7 MCP-Server](https://github.com/upstash/context7)** — Empfohlen für schnellen Zugriff auf aktuelle Library-Dokumentation.

## Installation

### Option 1: Plugin Install

```
/plugin marketplace add tonipse/masterflow
/plugin install masterflow@masterflow
```

### Option 2: Git Clone

```bash
git clone https://github.com/tonipse/masterflow.git
cp -r masterflow/skills/* .claude/skills/
cp -r masterflow/references .claude/skills/masterflow-references/
```

### Option 3: Manuell

Die Ordner `skills/masterflow-init/`, `skills/masterflow-audit/`, `skills/masterflow-apply/` und `references/` in das eigene Projekt unter `.claude/skills/` bzw. `.claude/skills/masterflow-references/` kopieren. Relative Pfade in den SKILL.md-Dateien ggf. anpassen.

## Nutzung

### `/masterflow:init` — Projekt initialisieren

Vollständige Projekt-Initialisierung in einem Durchlauf:

1. **Tech-Stack analysieren** — Manifest-Dateien, Framework-Configs, Source-Code scannen
2. **Skills auditieren** — Installierte prüfen, neue finden, scoren
3. **Scaffolding** — `context/docs/INDEX.md` mit Dokumentations-Workflow anlegen
4. **Dokumentation ziehen** — Für alle erkannten Technologien Docs laden
5. **CLAUDE.md konfigurieren** — Skills, Pflichtlektüre und Kontext-Verweise eintragen

Erstellt `context/stack-analysis.md` und `context/skill-audit.md`.

### `/masterflow:audit` — Skills prüfen

Führt nur das Skill-Management durch — für bestehende Projekte, die regelmäßig ihre Skills prüfen wollen. Aktualisiert `context/stack-analysis.md` und erstellt eine frische `context/skill-audit.md`.

### `/masterflow:apply` — Entscheidungen ausführen

Liest `context/skill-audit.md` und führt die Entscheidungen aus: Skills installieren, updaten, ersetzen oder entfernen. Erstellt vorher ein Backup.

## Workflow

```
┌─────────────────────┐
│  /masterflow:init   │  Neues Projekt oder Onboarding
│  oder               │
│  /masterflow:audit  │  Bestehendes Projekt, Skill-Check
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  context/           │
│  ├─ stack-analysis  │  Tech-Stack-Ergebnis
│  └─ skill-audit     │  Skill-Tabelle mit Empfehlungen
└─────────┬───────────┘
          │
          ▼  User prüft und trägt Entscheidungen ein
          │
┌─────────┴───────────┐
│  /masterflow:apply  │  Führt Entscheidungen aus
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Projekt bereit     │
│  ├─ Skills aktuell  │
│  ├─ Docs geladen    │
│  └─ CLAUDE.md fertig│
└─────────────────────┘
```

## Struktur

```
masterflow/
├── .claude-plugin/
│   └── plugin.json              # Plugin-Manifest
├── skills/
│   ├── masterflow-init/         # Projekt-Initialisierung
│   │   ├── SKILL.md
│   │   ├── manifests.md         # Manifest-Dateien-Tabelle
│   │   ├── frameworks.md        # Framework-Configs-Tabelle
│   │   ├── source-patterns.md   # Source-Code-Muster
│   │   └── claudemd-sections.md # CLAUDE.md-Template
│   ├── masterflow-audit/        # Skill-Audit
│   │   └── SKILL.md
│   └── masterflow-apply/        # Entscheidungen ausführen
│       └── SKILL.md
├── references/                  # Shared Reference-Dateien
│   ├── scoring.md               # Scoring-System
│   ├── kill-criteria.md         # Kill-Kriterien
│   └── sources.md               # Quellen-Hierarchie
├── README.md
├── LICENSE
└── .gitignore
```

## Lizenz

MIT — siehe [LICENSE](LICENSE).
