---
name: masterflow-audit
description: >
  Audits installed skills, discovers new ones, and creates a scored skill table.
  Runs independently of masterflow-init for existing projects. Requires superpowers plugin.
disable-model-invocation: true
allowed-tools: Read Glob Grep Write Agent WebSearch WebFetch
context: fork
effort: max
---

# masterflow-audit

Führt ausschließlich Skill-Management durch — unabhängig von `/masterflow:init`. Gedacht für bestehende Projekte, um installierte Skills regelmäßig zu prüfen und neue zu entdecken.

## Voraussetzungen

- **Superpowers** muss installiert sein.
- Bei unabhängigen Aufgaben **muss `superpowers:dispatching-parallel-agents`** verwendet werden.

## Wichtig: Nur lokale Skills

Skills werden immer als eigener Unterordner in `.claude/skills/` des aktuellen Projekts angelegt — niemals global. Beim Installieren wird der komplette Skill-Ordner aus der Quelle übernommen.

---

## Ablauf

### Schritt 1: Projekt analysieren (Phase 1)

Die Projektanalyse wird durchgeführt, um den aktuellen Tech-Stack zu ermitteln. Das Projekt wird in 4 Stufen gescannt.

**Stufe 1 — Manifest-Dateien:**
**→ Read** `${CLAUDE_SKILL_DIR}/../masterflow-init/manifests.md`

**Stufe 2 — Infrastruktur- und Framework-Configs:**
**→ Read** `${CLAUDE_SKILL_DIR}/../masterflow-init/frameworks.md`

**Stufe 3 — Source-Code scannen:**
**→ Read** `${CLAUDE_SKILL_DIR}/../masterflow-init/source-patterns.md`

**Stufe 4 — Fallback (Markdown / Planungsdateien):**
Wenn keine Code-/Manifest-Dateien existieren: `README.md`, `PLANNING.md`, `ARCHITECTURE.md`, `*.md` scannen, erwähnte Technologien extrahieren, Stack als "geplant" markieren.

**Output — `context/stack-analysis.md`:**
- **Existiert bereits** → Phase 1 komplett durchlaufen (Stufe 1-4), bestehende Datei **aktualisieren**. Änderungen am Stack (neue Dependencies, entfernte Pakete, Versions-Updates, geänderte Infrastruktur) einarbeiten, bestehende korrekte Einträge beibehalten.
- **Existiert nicht** → Datei neu erstellen, exakt wie bei `/masterflow:init` beschrieben (siehe `context/stack-analysis.md`-Template in masterflow-init).

---

### Schritt 2: Skill-Management (Phase 2)

Exakt wie in Phase 2 von masterflow-init beschrieben.

#### Grundsätze

- **Weniger ist mehr** — Kein Bloat. Jeder Skill kostet Context-Window.
- **Keine Überlappungen** — Pro Aufgabenbereich genau ein Skill.

#### Ablauf

1. **Installierte Skills auflisten**
2. **Relevanz prüfen** — Braucht das Projekt den Skill?
3. **Überlappungen erkennen** — Besseren behalten, anderen zum Löschen vormerken
4. **Internet-Recherche** — Quellen-Hierarchie systematisch durchsuchen
5. **Aktualitäts-Check** — Neuere Versionen?
6. **Alternativen-Check** — Bessere Alternativen?
7. **Neue Skills finden** — Passend zum Stack, Bereich nicht bereits abgedeckt?
8. **Skills scoren**
9. **Kill-Kriterien prüfen**
10. **Entscheidungsbaum anwenden**
11. **Kritisch filtern** — Nur Score >= 3.0 aufnehmen

#### Referenz-Dateien laden

**Quellen-Hierarchie (Tier 1-5):**
**→ Read** `${CLAUDE_SKILL_DIR}/../../references/sources.md`

**Scoring-System:**
**→ Read** `${CLAUDE_SKILL_DIR}/../../references/scoring.md`

**Kill-Kriterien:**
**→ Read** `${CLAUDE_SKILL_DIR}/../../references/kill-criteria.md`

#### Entscheidungsbaum

Für jeden installierten Skill:

```
Installierter Skill prüfen:
│
├── Wird er vom Stack benötigt?
│   ├── NEIN → Löschen
│   └── JA ↓
│
├── Funktioniert er zuverlässig?
│   ├── NEIN → Alternative vorhanden?
│   │   ├── JA → Ersetzen wenn Alternative > aktueller + 0.5
│   │   └── NEIN → Beibehalten mit Warnung
│   └── JA ↓
│
├── Neuere Version?
│   ├── JA → Breaking Changes? → JA: Updaten mit Hinweis / NEIN: Updaten
│   └── NEIN ↓
│
├── Bessere Alternative?
│   ├── JA → Score-Differenz > 1.0? → JA: Ersetzen / NEIN: Beibehalten
│   └── NEIN → Beibehalten
```

#### Aktualitäts-Check

**Git-basiert:** GitHub-API abfragen, installierte Version mit HEAD vergleichen, bei Unterschied Diff zeigen.
**Ohne Repo:** SKILL.md hashen (SHA-256), aktuelles fetchen, vergleichen.
**Marketplace:** `/plugin marketplace update`

#### Suchstrategie

Die Recherche für einzelne Stack-Komponenten ist unabhängig — **über `superpowers:dispatching-parallel-agents` parallelisieren.** Ablauf pro Komponente: Tier 1 → Tier 2 → Tier 3 → Tier 4, scoren, nur Score >= 3.0 aufnehmen. Zusätzlich Stack-unabhängige Skills prüfen (Workflow, Security, Projekttyp-spezifisch).

---

### Schritt 3: Ergebnis erstellen

**`context/skill-audit.md` erstellen** — Falls die Datei bereits existiert, wird der Inhalt komplett geleert und mit den neuen Erkenntnissen befüllt. Kein Merge mit alten Daten — jeder Audit ist ein frischer Durchlauf.

```markdown
| Skill | Status | Score | Empfehlung | Begründung | Quelle | Sicherheit | Entscheidung |
|-------|--------|-------|------------|------------|--------|------------|--------------|
| … | ✅/❌ | x.x | … | … | … | ✅/⚠️/🔍/❌ | |
```

---

### Schritt 4: Hinweis an den User

```
Skill-Audit abgeschlossen. Die Ergebnisse stehen in context/skill-audit.md.

Nächste Schritte:
1. context/skill-audit.md prüfen und Entscheidungen eintragen
2. /masterflow:apply ausführen, um die Änderungen anzuwenden
```
