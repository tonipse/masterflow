---
name: masterflow-init
description: >
  Initializes a project with full tech-stack analysis, skill audit, documentation scaffolding,
  and CLAUDE.md configuration. Use when setting up a new project or onboarding an existing one.
  Requires superpowers plugin.
disable-model-invocation: true
allowed-tools: Read Glob Grep Write Edit Agent WebSearch WebFetch mcp__context7__resolve-library-id mcp__context7__query-docs
context: fork
effort: max
---

# masterflow-init

Ein einziger Befehl, der alles initialisiert — Tech-Stack-Analyse, Skill-Management, Dokumentations-Workflow und CLAUDE.md-Konfiguration.

## Voraussetzungen

- **Superpowers** muss installiert sein.
- Bei unabhängigen Aufgaben (mehrere Technologien recherchieren, mehrere Skills scoren, mehrere Docs ziehen) **muss `superpowers:dispatching-parallel-agents`** verwendet werden. Sequentiell arbeiten, wo es parallelisierbar ist, ist nicht akzeptabel.

## Wichtig: Nur lokale Skills

Alle Masterflow-Skills arbeiten ausschließlich **lokal innerhalb des aktuellen Projekts**. Skills werden immer als eigener Unterordner in `.claude/skills/` des Projekts angelegt — niemals global oder in einem anderen Verzeichnis. Ein Skill-Ordner enthält die `SKILL.md`, ggf. `README.md`, `AGENTS.md` oder weitere Dateien. Beim Installieren wird immer der komplette Skill-Ordner aus der Quelle übernommen.

---

## Phase 1: Projekt analysieren

Das Projekt wird in 4 Stufen gescannt — von den zuverlässigsten Indikatoren bis zum Fallback. Reihenfolge: Zuerst das Zuverlässigste, dann das Spezifische, dann der Code selbst.

### Stufe 1: Manifest-Dateien (Sprache + Pakete erkennen)

**→ Read** `${CLAUDE_SKILL_DIR}/manifests.md`

Alle gefundenen Manifest-Dateien vollständig lesen und Dependencies extrahieren. Bei Monorepos: Rekursiv in Unterordnern suchen.

### Stufe 2: Infrastruktur- und Framework-Configs

**→ Read** `${CLAUDE_SKILL_DIR}/frameworks.md`

Basierend auf der erkannten Sprache gezielt nach Framework-spezifischen Configs suchen.

### Stufe 3: Source-Code scannen

**→ Read** `${CLAUDE_SKILL_DIR}/source-patterns.md`

Verzeichnisstruktur und Dateiendungen analysieren. Stichprobenartig 5-10 Source-Dateien lesen für Imports/Libraries.

### Stufe 4: Fallback — Markdown / Planungsdateien

Wenn keine Code-Dateien und keine Manifest-Dateien existieren (leeres Projekt / Planungsphase):

- `README.md`, `PLANNING.md`, `ARCHITECTURE.md`, `*.md` scannen
- Erwähnte Technologien extrahieren
- Projekttyp und geplanten Stack als "geplant" markieren

### Output: `context/stack-analysis.md`

Erstelle die Datei `context/stack-analysis.md` mit so vielen Details wie möglich:

```markdown
# Stack-Analyse

> Automatisch generiert von `/masterflow:init` am [Datum]

## Projekttyp

[Web-App / API / CLI-Tool / Library / Monorepo / Unbekannt]

## Erkannter Tech-Stack

| Kategorie | Technologie | Version | Quelle | Details |
|-----------|-------------|---------|--------|---------|
| Sprache | … | … | … | … |
| Runtime | … | … | … | … |
| Framework | … | … | … | … |
| … | … | … | … | … |

## Dependencies

### Production (Top 20)
- [aus Manifest-Dateien extrahiert]

### Dev
- [aus Manifest-Dateien extrahiert]

## Architektur-Hinweise

- [Erkannte Patterns, Verzeichnisstruktur-Besonderheiten, Monorepo-Struktur]

## Nicht erkannt / Offen

- [Technologien, die vermutet aber nicht bestätigt werden konnten]
```

---

## Phase 2: Skill-Management

Kombiniert Audit bestehender Skills und Discovery neuer Skills in einem Schritt.

### Grundsätze

- **Weniger ist mehr** — Lieber wenige, aber wirklich nützliche Skills. Kein Bloat. Jeder installierte Skill kostet Context-Window und erhöht Komplexität — das muss sich lohnen.
- **Keine Überlappungen** — Pro Aufgabenbereich genau ein Skill. Überlappende Skills führen zu widersprüchlichen Instruktionen.

### Ablauf

1. **Installierte Skills auflisten** — Welche Skills sind aktuell installiert?
2. **Relevanz prüfen** — Braucht dieses Projekt den Skill wirklich?
3. **Überlappungen erkennen** — Decken zwei oder mehr Skills denselben Bereich ab? Besseren behalten, anderen zum Löschen vormerken
4. **Internet-Recherche** — Quellen-Hierarchie systematisch durchsuchen
5. **Aktualitäts-Check** — Gibt es neuere Versionen?
6. **Alternativen-Check** — Gibt es bessere Alternativen?
7. **Neue Skills finden** — Welche Skills passen zum Stack und fehlen? Prüfen: Bereich bereits abgedeckt?
8. **Skills scoren** — Jeder Kandidat wird nach dem Scoring-System bewertet
9. **Kill-Kriterien prüfen** — Disqualifizierende Merkmale prüfen
10. **Entscheidungsbaum anwenden** — Behalten / Ersetzen / Löschen
11. **Kritisch filtern** — Nur Skills mit Score >= 3.0 aufnehmen. Im Zweifel weglassen

### Quellen-Hierarchie

**→ Read** `${CLAUDE_SKILL_DIR}/../../references/sources.md`

### Scoring-System

**→ Read** `${CLAUDE_SKILL_DIR}/../../references/scoring.md`

### Kill-Kriterien

**→ Read** `${CLAUDE_SKILL_DIR}/../../references/kill-criteria.md`

### Entscheidungsbaum (Behalten / Ersetzen / Löschen)

Für jeden installierten Skill:

```
Installierter Skill prüfen:
│
├── Wird er vom Stack benötigt?
│   ├── NEIN → Empfehlung: Löschen
│   └── JA ↓
│
├── Funktioniert er zuverlässig?
│   ├── NEIN → Gibt es eine Alternative?
│   │   ├── JA → Score vergleichen → Ersetzen wenn Alternative > aktueller + 0.5
│   │   └── NEIN → Beibehalten mit Warnung
│   └── JA ↓
│
├── Gibt es eine neuere Version?
│   ├── JA → Breaking Changes? → JA: Updaten mit Hinweis / NEIN: Updaten
│   └── NEIN ↓
│
├── Gibt es eine bessere Alternative?
│   ├── JA → Score-Differenz > 1.0? → JA: Ersetzen / NEIN: Beibehalten
│   └── NEIN → Beibehalten
```

**Prinzipien:**
1. **Wechselkosten berücksichtigen.** Ein funktionierender Skill hat einen Bonus. Alternative muss _deutlich_ besser sein (Score-Differenz > 1.0).
2. **"Besser" definieren.** Selber Bereich UND mindestens eine Dimension >=2 Punkte besser OHNE in einer anderen >=1 Punkt schlechter.
3. **Aufgegebene Skills erkennen.** Letzter Commit >6 Monate, offene Issues ohne Antwort >3 Monate, veraltete Claude-Code-Referenzen.

### Aktualitäts- und Versions-Check

**Primär — Git-basierter Vergleich:**
1. GitHub-API: Letzter Commit, letzte Release, offene Issues
2. Installierte Version mit `HEAD` vergleichen
3. Compare-URL: `github.com/:owner/:repo/compare/<version>...main`
4. Bei Unterschied: SKILL.md diff lesen, User entscheiden lassen

**Sekundär — Skills ohne Git-Repo:**
1. `version`-Feld im Frontmatter prüfen
2. Fallback: SKILL.md hashen (SHA-256), aktuelles fetchen, vergleichen
3. Bei Unterschied: Diff anzeigen

**Plugin-Marketplace:** `/plugin marketplace update`

### Suchstrategie

Die Recherche für einzelne Stack-Komponenten ist unabhängig — **über `superpowers:dispatching-parallel-agents` parallelisieren:**

```
EINGABE: Erkannter Tech-Stack aus Phase 1

FÜR JEDE Stack-Komponente (parallel über Sub-Agents):
  1. Gibt es bereits einen installierten Skill?
     → JA: Aktualitäts-Check  → NEIN: Weiter
  2. Tier 1: Anthropic Skills Repo + Superpowers
  3. Tier 2: Awesome-Lists durchsuchen
  4. Tier 3: Registries durchsuchen
  5. Tier 4: GitHub-Suche (wenn nichts gefunden)
  6. Gefundene Skills scoren
  7. Nur Score >= 3.0 aufnehmen

ZUSÄTZLICH (Stack-unabhängig):
  - Workflow-Skills (Brainstorming, Planning, Debugging)
  - Security-Skills (Audit, Hooks)
  - Projekttyp-spezifische Skills (z.B. Monorepo-Skills)

ERGEBNIS: Konsolidierte Skill-Tabelle
```

### Output: `context/skill-audit.md`

Erstelle die Datei `context/skill-audit.md`:

```markdown
| Skill | Status | Score | Empfehlung | Begründung | Quelle | Sicherheit | Entscheidung |
|-------|--------|-------|------------|------------|--------|------------|--------------|
| … | ✅/❌ | x.x | … | … | … | ✅/⚠️/🔍/❌ | |
```

**Spalten:**
- **Status** — ✅ Installiert / ❌ Nicht installiert
- **Score** — Gewichteter Score (1.0-5.0)
- **Empfehlung** — Beibehalten / Updaten / Ersetzen durch [X] / Löschen / Installieren
- **Begründung** — Warum diese Empfehlung
- **Quelle** — GitHub-Link (bei installierten ohne Änderungsbedarf: —)
- **Sicherheit** — ✅ Geprüft / ⚠️ Offene Fragen / 🔍 Noch nicht geprüft / ❌ Bedenken
- **Entscheidung** — Feld für den User. Leer = Empfehlung wird übernommen

---

## Phase 3: Projekt-Scaffolding

Ordnerstruktur anlegen (falls nicht vorhanden):

```
context/
  docs/
    INDEX.md
```

**INDEX.md** mit folgendem Inhalt befüllen:

```markdown
# Dokumentations-Index

Dieser Index ist die **zentrale Pflichtlektüre vor jedem Planungs- und Umsetzungsschritt**. Der Agent darf keinen Code planen, schreiben oder ändern, ohne vorher die relevanten Dokumentationen gelesen zu haben. Code, der nicht auf aktueller Dokumentation basiert, ist fehlerhaft — unabhängig davon, ob er kompiliert oder Tests besteht.

## Workflow

1. Agent liest diesen Index **vor jedem Planungs- und Umsetzungsschritt**
2. Identifiziert, welche Technologien/Libraries für den aktuellen Schritt relevant sind
3. Prüft, ob die benötigte Dokumentation bereits existiert
4. **Vorhanden** → Datei aus `context/docs/` **vollständig lesen**, bevor Code geplant oder geschrieben wird
5. **Nicht vorhanden** → Über die Fallback-Kette ziehen, als `.md` in `context/docs/` ablegen, Index aktualisieren, **dann lesen**

**Erst wenn die Dokumentation gelesen wurde, darf der nächste Schritt beginnen.**

## Fallback-Kette für Dokumentation

1. Context7 (schnell, meist aktuell für populäre Libs) → resolve-library-id → query-docs
2. Offizielle Dokumentation via WebFetch (Primärquelle, immer aktuell)
3. Web-Recherche via WebSearch (für Nischen, Tutorials, Beispiele)

**Hinweis zu Context7:** Community-beigetragen, nicht garantiert korrekt. Bei sicherheitskritischen APIs (Auth, Payment, Crypto) immer gegen offizielle Dokumentation gegenprüfen. Wenn nicht erreichbar, direkt zu Stufe 2/3.

## Regeln

- **Keine Planung ohne Docs** — Kein Planungsschritt ohne relevante Docs
- **Kein Code ohne Docs** — Keine Zeile Code ohne aktuelle Dokumentation
- **Docs sind die Wahrheit** — Bei Widersprüchen gilt die Dokumentation, nicht das Agent-Wissen
- **Docs on-demand laden** — INDEX.md als Verzeichnis nutzen, Docs nur laden wenn relevant
- Index immer aktuell halten, veraltete Einträge entfernen
- Dateien nach Technologie benennen (z.B. `nextjs-app-router.md`, `supabase-rls.md`)
- Pro Thema eine Datei — kein Mega-Dokument

## Inhaltsverzeichnis

| Datei | Thema | Erstellt |
|-------|-------|----------|
| … | … | … |
```

---

## Phase 4: Dokumentation ziehen

Basierend auf `context/stack-analysis.md` werden für **alle erkannten Technologien** Dokumentationen gezogen.

**Ablauf:**

1. **`context/stack-analysis.md` lesen** — Alle Technologien aus "Erkannter Tech-Stack" extrahieren
2. **Für jede Technologie Docs ziehen** (unabhängig — **über `superpowers:dispatching-parallel-agents` parallelisieren**):
   - Stufe 1: Context7 (`resolve-library-id` → `query-docs`)
   - Stufe 2: Context7 unzureichend → Offizielle Dokumentation via `WebFetch`
   - Stufe 3: Auch WebFetch unzureichend → `WebSearch` → `WebFetch`
   - Bei sicherheitskritischen APIs immer gegen offizielle Docs gegenprüfen
   - Ergebnis als `.md` in `context/docs/` ablegen (z.B. `nextjs-app-router.md`)
3. **`context/docs/INDEX.md` aktualisieren** — Jede Dokumentation ins Inhaltsverzeichnis eintragen
4. **Report** — Welche Docs erfolgreich gezogen, welche nicht gefunden

**Hinweis:** Nur Docs für Haupt-Technologien, nicht für jede Dev-Dependency. Fokus auf Technologien, die für Planung und Umsetzung von Code relevant sind.

---

## Phase 5: CLAUDE.md konfigurieren

### Wenn CLAUDE.md nicht existiert

Erstellen mit Projektname, Beschreibung, Tech Stack. Alle unten genannten Abschnitte einfügen.

### Wenn CLAUDE.md bereits existiert — Merge-Regeln

- **Unsere Sections (`## Skills`, `## Pflichtlektüre`, `## Kontext-Dateien`) werden komplett ersetzt** — alter Inhalt entfernt, durch die definierten Versionen ersetzt.
- **Dokumentationsgetriebene Abschnitte entfernen** — Falls Abschnitte zu "Docs vor Code", Context7-Workflows o.ä. existieren, werden diese gestrichen. `## Pflichtlektüre` ersetzt das vollständig.
- **Alle anderen Abschnitte bleiben erhalten** — Projektbeschreibung, Coding-Konventionen, Custom Rules etc.
- **Standard-Inhalte von `/init` bleiben erhalten.**

### Abschnitt: Skills

**→ Read** `${CLAUDE_SKILL_DIR}/claudemd-sections.md` für den exakten Inhalt des Skills-Abschnitts.

### Abschnitt: Pflichtlektüre

Folgenden Abschnitt einfügen:

```markdown
## Pflichtlektüre

**Vor jedem Planungs- und Umsetzungsschritt** muss `context/docs/INDEX.md` gelesen werden. Dort steht der vollständige Dokumentations-Workflow und das Inhaltsverzeichnis aller verfügbaren Docs. Kein Code ohne vorheriges Lesen der relevanten Docs.
```

### Abschnitt: Kontext-Dateien

Verweise einfügen auf:
- `context/stack-analysis.md` — Bei Änderungen am Stack muss diese Datei aktualisiert werden
- `context/docs/INDEX.md` — Dokumentations-Index

---

## Interaktiver Ablauf

```
1. Projekt erkennen
   └─ Alle Dateien scannen (Stufe 1-4), Tech Stack extrahieren
   └─ context/stack-analysis.md erstellen

2. Skill-Management
   ├─ Installierte Skills auflisten
   ├─ Überlappungen erkennen
   ├─ Internet-Recherche (Quellen-Hierarchie Tier 1-5)
   ├─ Aktualitäts-Check, Alternativen-Check
   ├─ Skills scoren, Kill-Kriterien prüfen, Entscheidungsbaum anwenden
   └─ context/skill-audit.md erstellen

3. Scaffolding
   ├─ Ordnerstruktur anlegen
   └─ INDEX.md befüllen

4. Dokumentation ziehen
   ├─ stack-analysis.md lesen → alle Technologien extrahieren
   ├─ Für jede Technologie: Context7 → WebFetch → WebSearch
   └─ INDEX.md aktualisieren

5. CLAUDE.md konfigurieren
   ├─ Erstellen oder anpassen
   ├─ Skills-Abschnitt eintragen
   ├─ Dokumentations-Workflow eintragen
   └─ Kontext-Verweise eintragen

6. Zusammenfassung
   ├─ Report: Was wurde angelegt und konfiguriert
   └─ Hinweis: "Prüfe context/skill-audit.md und trage deine Entscheidungen ein.
      Danach /masterflow:apply ausführen."
```

**`/masterflow:init` endet hier.** Die Skill-Änderungen werden bewusst NICHT automatisch durchgeführt. Der User bekommt Zeit, die `context/skill-audit.md` zu prüfen und erst dann mit `/masterflow:apply` anzuwenden.
