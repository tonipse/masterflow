---
name: masterflow-apply
description: >
  Reads context/skill-audit.md and executes the decisions: installs, updates, replaces,
  or removes skills. Creates backups before changes. Requires superpowers plugin.
disable-model-invocation: true
allowed-tools: Read Glob Grep Write Edit Bash Agent
context: fork
effort: max
---

# masterflow-apply

Liest die `context/skill-audit.md` und führt die darin getroffenen Entscheidungen aus — Skills installieren, deinstallieren, updaten oder ersetzen.

## Voraussetzungen

- **Superpowers** muss installiert sein.
- `context/skill-audit.md` muss existieren (erstellt von `/masterflow:init` oder `/masterflow:audit`).

## Wichtig: Nur lokale Skills

Skills werden immer als eigener Unterordner in `.claude/skills/` des aktuellen Projekts angelegt — niemals global. Beim Installieren wird der komplette Skill-Ordner aus der Quelle übernommen (inkl. SKILL.md, README.md, AGENTS.md, Unterordner etc.).

---

## Ablauf

### Schritt 1: Skill-Audit lesen

`context/skill-audit.md` lesen und Tabelle parsen.

### Schritt 2: Entscheidungen auflösen

- **Entscheidung ausgefüllt** → Entscheidung des Users gilt
- **Entscheidung leer** → Empfehlung wird übernommen

### Schritt 3: Backup erstellen

Vor jeglichen Änderungen ein Backup des aktuellen `.claude/skills/`-Verzeichnisses erstellen:

```
.claude/skills-backup-[DATUM]/
```

### Schritt 4: Änderungen bestätigen lassen

Zusammenfassung anzeigen und User um Bestätigung bitten:

```markdown
Folgende Änderungen werden durchgeführt:

Backup erstellt: .claude/skills-backup-[DATUM]/

Installieren:
  - skill-a (Score 4.2) — github.com/…

Updaten:
  - skill-y → v2.0 — github.com/…

Ersetzen:
  - skill-z → skill-a — github.com/…

Deinstallieren:
  - skill-w

Keine Änderung:
  - superpowers (Beibehalten)

Soll ich diese Änderungen jetzt durchführen? (ja/nein)
```

### Schritt 5: Änderungen ausführen

Bei Bestätigung — Änderungen einzeln ausführen.

#### Installations-Hierarchie (in dieser Reihenfolge prüfen)

1. **Plugin-Marketplace** (wenn Skill als Plugin verfügbar): `/plugin install <name>@<marketplace>` — offiziell unterstützt, einfachste Update-Methode
2. **Git Clone** (wenn Skill ein GitHub-Repo ist): Repo klonen, Skill-Ordner nach `.claude/skills/` kopieren, Commit-Hash notieren
3. **Manuelles Kopieren** (Fallback): SKILL.md und Begleitdateien direkt kopieren

#### Aktionen

- **Installieren** — Skill-Ordner über die Installations-Hierarchie holen und komplett in `.claude/skills/` ablegen
- **Updaten** — Skill auf neueste Version aktualisieren
- **Ersetzen** — Alten Skill deinstallieren, neuen installieren
- **Deinstallieren** — Skill-Ordner entfernen

**Nach jeder einzelnen Änderung** kurz prüfen, ob der Skill korrekt installiert ist (SKILL.md vorhanden, Frontmatter valide).

### Schritt 6: Dateien aktualisieren

**`context/skill-audit.md` aktualisieren:**
- Status-Spalte auf neuen Stand bringen
- Empfehlungen als "Durchgeführt" markieren
- **Installationspfad dokumentieren** — Für jeden installierten/aktualisierten Skill festhalten, woher er kam (Marketplace, Git-Repo-URL + Commit-Hash, manuell). Ermöglicht spätere Updates.

### Schritt 7: Abschluss-Report

```markdown
Skill-Änderungen abgeschlossen:

- skill-a installiert (via Git Clone, Commit abc123)
- skill-y auf v2.0 aktualisiert
- skill-z durch skill-a ersetzt
- skill-w deinstalliert

CLAUDE.md wurde aktualisiert.
skill-audit.md wurde aktualisiert.

Rollback: Bei Problemen enthält .claude/skills-backup-[DATUM]/ den vorherigen Stand.
```
