# Mastermind v3 – Personal-OS-Anpassung und Zuverlässigkeit (Design / Spec)

Stand: 2026-09-03 (Nacht nach v2). Freigabe: Toni hat die Analyse der Personal-OS-Unterlagen und die
autonome Umsetzung per Nachtsession beauftragt („Arbeite jetzt voll autonom“). Umsetzung: Nachtsession
`.claude/nachtsessions/2026-09-03-nachtsession-mastermind-umbau-v3.md`; danach die angepasste Ernte
`.claude/nachtsessions/2026-09-03-nachtsession-mastermind-ernte.md`.

Quellen der Analyse: `.claude/personal-os-blueprint.md`, `.claude/personal-os-claude-instructions.md`,
`.claude/personal-os-transcript.md` (Masterclass „So baust du dein eigenes PersonalOS mit KI“, Vincent Mumme),
der v2-Stand von Plugin und Vault (`docs/superpowers/specs/2026-09-03-mastermind-v2-design.md`), Messungen
am laufenden System (Index-DB, Hook, Auto-Memory, Prozesse) und die offiziellen Claude-Code-Docs
(hooks, plugins-reference, skills, memory).

---

## 1. Analyse: Personal OS gegen Mastermind

Mastermind ist bereits ein Personal OS im Sinne des Videos, beschränkt auf Engineering-Wissen: ein
Ordner mit Markdown, Regeln, Skills, Agenten und Automatik. Die Stufen 1–5 der Pyramide (Ordner → Kontext
→ Skills → Agenten → Automation) sind alle belegt. Was fehlt, ist weniger Struktur als **Disziplin im
Schreibzyklus** (Belegen, Validieren, Protokollieren) und **ein Ort für das, was noch nicht Wahrheit ist**.

### 1.1 Kernprinzipien

| Personal-OS-Prinzip | Mastermind v2 | Lücke | Entscheidung v3 |
|---|---|---|---|
| File over App | Vault = Markdown, Obsidian und basic-memory nur Zugänge | keine | bleibt |
| Compounding Context | Vault seit 2026-05, Git-Historie | Hub-`## Status` wird bei jedem Wrap **ersetzt**, die Entwicklung ist nur im Git-Log sichtbar | `## Verlauf` (append-only) in Hubs |
| Single Source of Truth | ein Hub je Projekt, eine Notiz je Thema, Dedup-Prozedur | User-Kontext liegt in 32 Auto-Memory-Silos (14 `user`-, 45 `feedback`-Dateien), nichts davon projektübergreifend | `user.md` + `soul.md` im Vault, per Import global geladen |
| Append-only History | nur `(Stand YYYY-MM, Quelle)` je Fakt | kein Protokoll je Datei | `## Verlauf` in Hubs; Wissensnotizen bleiben ohne Timeline (siehe 1.5) |
| Belegpflicht | `source` „optional, aber bevorzugt“; 118 von 174 Notizen haben es, bei den vier künftig pflichtigen Typen 115 von 118 | nicht erzwungen | `source` Pflicht für neue Wissensnotizen, Lint prüft |
| Missing Context | `## Offene Punkte` im Hub-Schema, aber in **keinem** der 33 Phase-2-Hubs vorhanden | Schema ohne Inhalt | Hub-Anatomie v3 mit klarer Definition, Ernte füllt |
| Quelle → Wahrheit → Aktion | Quellen liegen außerhalb (Repos, Transkripte); Wahrheit = Hub; Aktion = Repo-Pläne/Tracker | Hub nennt seine Quellen nicht | `## Quellen` mit „geerntet bis“ |
| Validierung nach dem Schreiben | `/mastermind:index` als Prompt, kein deterministischer Check | Agent prüft sich nicht selbst | `lint.py`, in wrap/project/index/Ernte eingebaut |
| Inbox („nichts bleibt roh liegen“) | Übersprungene Kandidaten stehen nur im Terminal-Report | verloren nach der Session | `inbox/` (sichtbar in Obsidian, nicht indexiert) |
| Regeln/Verfassung (`soul.md`) | Hook-RULES (Recall/Capture), conventions.md | keine Verhaltens-Charta über Projekte hinweg | `soul.md`, klein, evidenzbasiert aus den 45 `feedback`-Dateien |
| Backup über Git-Remote | Vault ist Git-Repo **ohne Remote** | kein Off-Device-Backup | SessionEnd pusht, sobald ein Remote existiert (Remote legt Toni an) |
| Widerspruchs-Prüfung gegen `Decisions/` | Dedup löst Widersprüche zwischen Notizen | Recall behandelt Decisions nicht als Leitplanke | Regel: Decisions sind Constraints; Widerspruch vor dem Handeln nennen |
| Fokus-Prüfung (nur betroffene Dateien) | implizit | nicht formuliert | Regel in checklist.md |

### 1.2 Struktur-Mapping

| Personal OS | Mastermind | Bewertung |
|---|---|---|
| `claud.md` / `agents.md` (Einstieg) | Vault-`CLAUDE.md`, SessionStart-Hook, Skill `mastermind-brain` | vorhanden; `AGENTS.md` als tool-neutrale Brücke fehlt (Codex, Antigravity öffnen den Vault sonst blind) |
| `index.md` | `index.md` | vorhanden; bekommt die neuen Ordner/Root-Dateien |
| `user.md` | fehlt (nur projektlokale Auto-Memory) | **neu**, ≤ 60 Zeilen |
| `soul.md` | fehlt | **neu**, ≤ 40 Zeilen |
| `Inbox/` | fehlt (`.ernte/` nur für die Nachtsession) | **neu**: `inbox/<hub>.md` |
| `Projects/` | `projects/` (Hubs) | vorhanden; Anatomie v3 |
| `Knowledge/` (LM-Wiki) | `gotchas/ patterns/ decisions/ howtos/ stacks/` | vorhanden; laut Blueprint ausdrücklich **ohne** 5-Sektionen-Anatomie |
| `Decisions/` | `decisions/` | vorhanden; Leitplanken-Regel neu |
| `Interactions/` (Rohquellen) | Transkripte, Auto-Memory, Specs, Git – bleiben außerhalb | Kopien in den Vault wären Ballast und Secret-Risiko; stattdessen `source` + `## Quellen` |
| `Operations/` (To-dos) | Repo-Pläne, ClickUp | bewusst nicht im Vault; `## Offene Punkte` = Unbekanntes/Risiken, keine To-dos |
| `Skills/` + `resolver.md` | Plugin-Skills/-Commands, Claude-Skill-Liste | vorhanden |
| `System/rules.md`, `templates/`, Validierung | `conventions.md`, `CLAUDE.md`, `templates/`, kein Lint | Lint **neu** |
| `People/`, `Companies/`, `Daily/`, `Identity/`, Extensions | — | nicht übernommen (1.5) |

### 1.3 Datei-Anatomie: Hub v3

Der Blueprint verlangt die 5-Sektionen-Anatomie nur für dynamische Wahrheits-Dateien (Projekte,
Personen, Firmen), nicht für das Wissens-Wiki. Übertragen auf Mastermind: **nur Hubs** bekommen die
Anatomie, Wissensnotizen behalten ihre typspezifischen Abschnitte.

| Personal OS | Hub v3 | Regel |
|---|---|---|
| Front Matter | Frontmatter | wie v2 (`repo`, `path`, `last_wrap`, `group/*`, `stack/*`) |
| Current Truth | `## Zweck`, `## Stack`, `## Architektur / Eigenheiten`, `## Konventionen`, `## Wichtige Decisions`, `## Bekannte Gotchas`, `## Status` | `## Status` = genau eine Zeile `Stand YYYY-MM-DD: …` |
| Missing Context | `## Offene Punkte` | Unbekanntes, Risiken, unbestätigte Annahmen, die eine spätere Session kennen muss; ≤ 8 Punkte; **keine To-dos** |
| Sources & Evidence | `## Quellen` | eine Zeile je Quelle: `- <Quelle> (geerntet bis YYYY-MM-DD)`; Standardquellen: CLAUDE/AGENTS.md, Doku-Index, Specs, Auto-Memory-Ordner, Transkripte, ggf. Antigravity/Codex |
| Timeline | `## Verlauf` | **letzter** Abschnitt, append-only: `- YYYY-MM-DD <wrap\|ernte\|project\|capture\|manuell> · <Änderung, ≤ 120 Zeichen> · Quelle: <Session/Commit/Ledger>`; Zeilen werden nie geändert oder gelöscht |

`## Verwandt` steht vor `## Verlauf`, damit `edit_note append` immer den Verlauf trifft. Dach-Hubs
(`fwg-one`, `rocketads`, `fwg-warehouse`, künftig `moeller`) bekommen nur `## Verlauf`.

### 1.4 Agenten-Zyklus

| Personal OS (6 Schritte) | `/mastermind:wrap` v2 | v3 |
|---|---|---|
| 1 Kontext lesen | Step 0 (Konventionen, Hub) + Step 1 (Evidenz) | + Inbox des Hubs lesen |
| 2 Regeln und Grenzen | checklist §A/§B | + Decisions als Leitplanken, Fokus-Regel |
| 3 Änderungsplan | Step 2/3 (Kandidaten, Dedup) | unverändert |
| 4 Targeted Update | Step 4/5 (`edit_note`-Operationen) | + `## Quellen`, `## Verlauf`, `source` Pflicht |
| 5 Validierung | fehlt | `lint.py --changed` vor dem Commit, Befunde beheben |
| 6 Protokollierung | fehlt | Verlauf-Zeile im Hub; Übersprungenes in `inbox/` |

### 1.5 Bewusst nicht übernommen

- **People/Companies:** Kundendaten gehören nicht in ein Engineering-Vault (Datenschutz, Skip-Liste).
  Firmen sind als Dach-Hubs/`group/*` bereits abgebildet.
- **Daily/Journaling:** Sessions sind die Tageseinheit; der Hub-Verlauf und die Transkripte reichen.
- **Interactions-Kopien:** Transkripte (700 MB) und Auto-Memory bleiben außerhalb; `evidence.py`
  und `session-index.py` erschließen sie bei Bedarf.
- **Timeline in Wissensnotizen:** widerspricht „Weniger ist mehr“; `(Stand YYYY-MM, Quelle)` und
  `(bestätigt YYYY-MM in <projekt>)`-Observations leisten dasselbe.
- **IDs/`schema_version`:** basic-memory-Permalinks sind die IDs; die Hub-Version erkennt der Lint am Vorhandensein von `## Verlauf`.
- **Operations/To-dos:** bleiben im Repo (Pläne, ClickUp). Der Vault führt keine Aufgabenliste.
- **Symlink-Trick für Skills:** Skills leben im Plugin-Repo und werden über den Marketplace verteilt.

---

## 2. Analyse: Zuverlässigkeit in normalen Sessions

Befunde vom 2026-09-03, jeweils mit Beleg. B1 ist ein echter Fehler, B2/B3 sind die größten Hebel.

| # | Befund | Beleg | Folge |
|---|---|---|---|
| B1 | **Volltext-Index ist nur Titel-Index.** `basic-memory reindex` (0.22.1, alle Varianten) schreibt Entity-Zeilen ohne `content_stems`, keine Observation- und Relation-Zeilen und – bei `--full` – Vektor-Chunks nur aus Titel+Permalink. Nur der Watcher-Pfad des laufenden MCP-Servers (`sync_file`) indexiert vollständig. | `select count(*) from search_index where type='observation'` = 0–20 bei 451 Observations; nach `reindex --full`: Chunks 175 × ~70 Zeichen statt 371 × bis 897. Reparaturtest an einer Datei (Checksum `NULL` + `touch`) lieferte Entity 2.250 Zeichen, 2 Observations, 3 Relations. | Exakte Begriffe (Fehlercodes, Identifier) im Notiz-Body sind für `search_notes` unsichtbar; nur die Vektorsuche trägt. Der in v2 empfohlene Fix `reindex --full` verschlimmert den Zustand. |
| B2 | **Recall ist nicht deterministisch.** Ob Claude vor einer Aufgabe sucht, hängt von Modell-Disziplin ab. | Hook-RULES, Skill-Description; keine Messung möglich | pro Prompt ein deterministischer, billiger Hinweis (FTS/BM25 über den Index) |
| B3 | **Wrap wird vergessen → Session-Wissen verloren.** Kein Hub hat `last_wrap` (0 von 35); Capture während der Arbeit ist Best-effort. | `grep -l last_wrap projects/*.md` = 0 | SessionEnd merkt sich ungewrappte Sessions, SessionStart erinnert, `/mastermind:wrap last` holt aus dem Transkript nach |
| B4 | **Stale MCP-Prozesse.** 10 `basic-memory mcp`-Prozesse (einer seit 25.06.), jeder mit eigenem Watcher; bei Dateiänderungen konkurrieren sie um die SQLite-DB (`database is locked` im Log). | `pgrep -fl "basic-memory mcp"`, Log 02:38 | Reparatur/Ernte nur mit möglichst einer aktiven Session; Handout: alte Sessions schließen |
| B5 | **Kein Off-Device-Backup.** Vault ohne Git-Remote. | `git -C ~/Mastermind remote -v` leer | SessionEnd-Push, sobald Remote existiert |
| B6 | **Berechtigungen.** In normalen Sessions (`defaultMode: auto`) können MCP-Schreibaufrufe nachfragen; Capture soll aber ohne Rückfrage laufen. | `~/.claude/settings.json` | Handout: `permissions.allow` für den Server |
| B7 | **Kontextbudget.** Plugin always-on ≈ 531 Token, Hook ≈ 400–500 Token. | `claude plugin details` | v3 bleibt unter ≈ 1.800 Token pro Session (Plugin + Hook + user/soul), Lint erzwingt die Zeilenlimits |
| B8 | **`_brainstorming/` wird indexiert** (Ledger, Pläne) und konkurriert in der Suche mit Wissen. | `list_directory` | Ledger nach `.ernte/`; Berichte bleiben (nützlich) |
| B9 | **`~/.claude/CLAUDE.md` ist leer.** Der Claude-native Ort für globale Regeln ist ungenutzt. | Datei 0 Byte | Importe für `user.md`/`soul.md` |
| B10 | **Codex/Antigravity kennen den Vault nicht.** 9 Codex-, 56 Antigravity-Konversationen ohne Mastermind. | `~/.codex`, `~/.gemini/antigravity` | `AGENTS.md` im Vault; MCP-Eintrag für Codex als optionaler Handout-Schritt |

Nicht verändert wird: Vault-Ort, Hook-Matching, die Trennung Analyse/Ausführung in masterflow, das
Nicht-Ziel „Cloud“. Das Embedding-Modell wird nach 4.12 ersetzt (Entscheidung vom 2026-09-03).

---

## 3. Ziele und Nicht-Ziele

Ziele:
1. Hubs tragen Quellen und Verlauf (POS-Anatomie), Lücken stehen in `## Offene Punkte`.
2. Projektübergreifender User-Kontext liegt an **einer** Stelle (`user.md`, `soul.md`) und ist in jeder Session geladen.
3. Nichts geht verloren: Inbox für Kandidaten, Verlauf für Änderungen, ungewrappte Sessions werden erkannt.
4. Der Agent validiert sich selbst (Lint) und belegt jede Aussage (`source`).
5. Suche ist zuverlässig: vollständiger Volltext-Index, Health-Check erkennt Degradation, dokumentierte Reparatur.
6. Recall wird deterministischer (Prompt-Hinweise), ohne Rauschen (Kalibrierung, Kill-Kriterium).

Nicht-Ziele: People/Companies/Daily-Module, Cloud-Sync, Änderungen an masterflow, Eingriffe in
Projekt-Repos, Änderungen am Embedding-Modell, Kill von fremden MCP-Prozessen.

---

## 4. Design v3

### 4.1 Hub-Anatomie v3 (A1)

Siehe 1.3. Änderungen: `conventions.md` §4 (Hub-Abschnitte), neuer §11 „Verlauf und Quellen“,
`checklist.md` §C, `mastermind-project/SKILL.md` §5, `templates/project.md`, Vault-`CLAUDE.md`.
Migration aller 33 Projekt-Hubs und 3 Dach-Hubs per Skript (deterministisch, siehe 5.1). Der Hook zeigt
zusätzlich die letzte Verlauf-Zeile.

### 4.2 Root-Dateien `user.md`, `soul.md`, `AGENTS.md` (A2)

- `~/Mastermind/user.md` (≤ 60 Zeilen): wer Toni ist (Rolle, Firmen/Gruppen `fwg-one`, `rocketads`,
  `moeller`, Standalone), Werkzeuglandschaft (Claude Code mit masterflow/mastermind/superpowers, Codex,
  Antigravity, Obsidian, n8n), Arbeitsweise (autonome Nachtsessions, Spec→Plan→Ausführung), Umgebung
  (macOS, Projekte unter `~/Desktop/*-dev`, Vault `~/Mastermind`), Präferenzen (lokal/kostenlos, Deutsch).
  Nur belegte Fakten aus den 14 `user`-Auto-Memory-Dateien und den masterflow-Memories; Widersprüche
  zwischen Quellen nicht auflösen, sondern im Bericht melden.
- `~/Mastermind/soul.md` (≤ 40 Zeilen): Verhaltens-Charta. Sprache und Form (Deutsch mit Umlauten,
  keine Floskeln, kein Ja-Sager, Widerspruch mit Begründung), Belegpflicht, Lücken benennen statt raten,
  autonom mit klarer Empfehlung statt Rückfrage (Guardrails bleiben), Ergebnisse als Markdown
  persistieren, über den Prompt hinausdenken, Subagenten-Modellregel, keine bezahlte Anthropic-API in
  Skripten, Secrets nie in Notizen, Mastermind-Kurzregel (Recall/Capture/Wrap → Plugin). Quelle: die
  projektübergreifenden unter den 45 `feedback`-Dateien.
- `~/Mastermind/AGENTS.md`: tool-neutrale Fassung von `CLAUDE.md` (Konventionen, Ordner, „lies
  `user.md`/`soul.md`“), damit Codex/Antigravity den Vault ohne Plugin korrekt benutzen.
- `~/.claude/CLAUDE.md` (bisher leer) erhält:
  ```
  @~/Mastermind/user.md
  @~/Mastermind/soul.md
  ```
  Import-Mechanik laut Docs: absolute/Home-Pfade erlaubt, Laden beim Start, User-Scope ohne Dialog.
- `conventions.md` §9: projektübergreifende User-Fakten → `user.md`, Verhaltensregeln → `soul.md`,
  projektspezifisches bleibt Auto-Memory. Lint prüft die Zeilenlimits.

### 4.3 Inbox (A3)

- Ordner `~/Mastermind/inbox/`, eine Datei je Hub: `inbox/<hub>.md`, Frontmatter minimal
  (`title: 'inbox – <hub>'`, `type: inbox`), Zeilen:
  `- [ ] YYYY-MM-DD · <typ> · <Aussage> · Beleg: <Datei/Session> · Grund: <über Limit | unverifiziert>`.
- Nicht indexiert: Eintrag `inbox/` in `~/.basic-memory/.bmignore` (Verzeichnis-Muster, von
  `should_ignore_path` als Pfadbestandteil erkannt). Sichtbar in Obsidian.
- Regeln: nur `wrap`, `project`, die Ernte und `capture` (bei vielversprechend, aber unverifiziert)
  schreiben hinein; Trivia und Skip-Liste nie. `wrap` liest die Inbox seines Hubs in Step 2 und befördert
  Einträge, die die Session verifiziert hat (`- [x] … → [[Titel]]`). `/mastermind:index` meldet Anzahl und
  Alter offener Einträge.
- Health-Checks (Hook, Lint, Ernte) zählen `inbox/` **nicht** als Notiz.

### 4.4 Belegpflicht, Leitplanken, Fokus (A4, A5)

- `source` ist Pflicht für `gotcha`, `decision`, `pattern`, `howto`; Lint: fehlend = ERROR bei
  `created ≥ 2026-09-04`, sonst WARN.
- `mastermind-brain/SKILL.md` RECALL: Trifft eine Suche eine `decisions/`-Notiz zum Bereich, gilt sie
  als Leitplanke. Widerspricht das geplante Vorgehen, wird das **vor** dem Handeln in einer Zeile gesagt.
  Entscheidet der User anders, wird die Notiz aktualisiert (datierter `- [decision]`-Fakt, ggf.
  `status: superseded`), nie stillschweigend umgangen. Gleiche Regel im Hook-RULES-Block (eine Zeile).
- `checklist.md` §B: Nur Notizen und Hubs anfassen, die von der Evidenz dieser Session betroffen sind;
  kein „Aufräumen“ fremder Notizen im Wrap.

### 4.5 Lint und `/mastermind:index` (A6)

Neuer Skill `skills/mastermind-index/` (`name: index`, `disable-model-invocation: true`,
`argument-hint: "[fix] [repair-index]"`) ersetzt `commands/index.md`. Dateien: `SKILL.md`, `lint.py`,
`repair_index.py`.

`lint.py` (Python 3 stdlib, Frontmatter-Parser aus `hooks/session_start.py` importiert):

Bestandsschutz: Der Vault hat heute 89 Titel über 80 Zeichen, 32 Titel mit `/` und ähnlichen Zeichen, rund
25 Notizen ohne `projects`, `confidence` oder `related`, sechs Templates mit `null`-Werten und freie Typen in
`_brainstorming/`. Ein Lint, das das alles als ERROR wertet, wäre nie grün und würde zum Umschreiben von
Titeln verleiten (verboten). Deshalb sind Pflichtfeld-, Mengen-, `source`- und Datumsregeln ERROR nur für
Notizen mit `created ≥ 2026-09-04` und für ältere WARN; Titelregeln sind immer WARN (Wikilinks laufen über
`aliases`). Ausgenommen von Frontmatter-, Typ- und Titelprüfung sind `templates/`, `_brainstorming/`, `inbox/`
(nur INFO), Root-Dateien (nur Zeilenlimits) und Dateien mit Präfix `_`. Dach-Hubs (Tag `moc`) werden nur auf
`## Verlauf` als letzten Abschnitt geprüft. Erlaubte Nicht-Wissens-Typen: `note` (Root), `inbox`, `moc`.

| Prüfung | Schwere |
|---|---|
| Frontmatter parsebar; Pflichtfelder `title type created updated tags status projects confidence related` | ERROR ab `created ≥ 2026-09-04`, sonst WARN |
| `type` passt zum Ordner (`gotchas→gotcha` …, `projects→project`; Ausnahmen siehe oben) | ERROR |
| Titel ≤ 80 Zeichen; verbotene Zeichen; Doppelpunkt nur mit `aliases` | WARN |
| `projects`/`related`: Wikilinks in Rohzeilen gequotet; keine `null`/`~`-Werte | ERROR (Quoting) / WARN (`null` in Bestand) |
| `status`, `confidence` aus den erlaubten Mengen; `updated ≥ created`; Datumsformat | ERROR ab `created ≥ 2026-09-04`, sonst WARN |
| `source` fehlt (Regel 4.4) | ERROR ab `created ≥ 2026-09-04`, sonst WARN |
| `stack/*`-Tags nicht in conventions.md §7 | WARN |
| Wikilink-Ziel existiert nicht (Titel, Alias oder Dateiname, case-insensitiv) | WARN |
| Orphan (keine eingehenden Links; Index/MOCs ausgenommen) | WARN |
| Projekt-Hub (ohne Tag `moc`): `repo`/`path` fehlt; `path` existiert nicht; `## Status` ≠ genau eine `Stand`-Zeile; `## Quellen`, `## Verwandt`, `## Verlauf` fehlen; `## Verlauf` nicht letzter Abschnitt; `## Offene Punkte` > 8 Punkte | ERROR (Struktur) / WARN (Felder) |
| Dach-Hub (Tag `moc`): `## Verlauf` fehlt oder ist nicht letzter Abschnitt | ERROR |
| Root: `user.md` > 60, `soul.md` > 40 Zeilen; `CLAUDE.md`/`AGENTS.md` fehlen | ERROR |
| Inbox: offene Einträge je Datei, älter als 90 Tage | INFO |
| Index: Dateien (ohne `inbox/`, ohne `.*`) vs. Entities; Entity-Zeilen mit Inhalt; Observation-/Relation-Zeilen im FTS vs. Tabellen; Chunks je Entity | WARN bei < 90 % |

CLI: `lint.py [--vault PFAD] [--changed] [--json] [--strict] [--index-only] [PFAD …]`; `--changed` = Dateien aus
`git status --porcelain` des Vaults, explizite Pfade linten nur diese (für parallele Schreiber), `--index-only`
nur die Index-Zeile; Exit 0, mit `--strict` Exit 1 bei ERROR. Ausgabe gruppiert nach
Schwere, eine Zeile je Befund (`ERROR gotchas/x.md: source fehlt`).

`repair_index.py`: Reparatur nach B1 (siehe 4.7). `/mastermind:index fix` behebt sichere Befunde
(fehlendes `related: [[index]]`, ungequotete Wikilinks, fehlender `## Verlauf` in Hubs) und committet.

### 4.6 Wrap v3, Projekt-Onboarding v3, Evidenz (A1–A6, B3)

`mastermind-wrap/SKILL.md`:
- Argumente: `dry`, `last`, Fokus-Hinweis. `last` = die zuletzt **ungewrappte** Session dieses Projekts
  aus dem State-File nachholen (Evidenz nur aus dem Transkript-Digest, kein Gesprächsverlauf).
- Step 1: `evidence.py --session <id> --since <last_wrap> --cwd <root> [--digest]`; `--digest`
  liefert die kompakte Session-Zusammenfassung (User-Prompts ≤ 400 Zeichen, letzte Claude-Texte ≤ 600,
  Fehlerzeilen, editierte Dateien; ≤ 40.000 Zeichen), portiert aus `session-index.py`.
- Step 2: liest `inbox/<hub>.md`; verifizierte Einträge werden befördert.
- Step 4: `source` Pflicht; Stack-Regel unverändert.
- Step 5: Hub v3 – `## Quellen` aktualisieren (Auto-Memory/Transkript „geerntet bis heute“), `## Verlauf`
  anhängen (`- <heute> wrap · <n> neu, <m> erweitert · Quelle: Session <id-kurz>`), `## Offene Punkte`
  nur mit Unbekanntem/Risiken.
- Step 5b: Übersprungene, aber wiederverwendbare Kandidaten nach `inbox/<hub>.md` (Regel 4.3).
- Step 6: `lint.py --changed --strict`; ERRORs beheben; dann Commit. Bei `last`: Commit
  `wrap(<projekt>, nachgeholt): <n> notes`, State-File auf `wrapped: true`.
- Harte Regeln: + Fokus-Regel, + nie Verlauf-Zeilen ändern.

`mastermind-project/SKILL.md`: schreibt Hub v3 (`## Quellen` aus den gelesenen Quellen, `## Verlauf`
mit `- <heute> project · Hub angelegt|aktualisiert · Quelle: /mastermind:project`), Update-Modus ergänzt
fehlende v3-Abschnitte; Lint vor dem Commit.

### 4.7 Index-Gesundheit und Reparatur (B1)

- `repair_index.py` (im Skill `mastermind-index`): setzt `entity.checksum = NULL` für das Projekt
  `mastermind`, `touch`t alle Notizen (ohne `inbox/`, ohne `.*`), wartet, prüft per SQL (Entity-Zeilen mit
  `length(content_stems) > 0`, Observation-Zeilen ≥ 90 % der Tabelle, Relation-Zeilen ≥ 90 %), wiederholt
  für unvollständige Dateien (max. 5 Runden, Batches von 25 Dateien, damit konkurrierende Watcher die DB
  nicht sperren). Voraussetzung: ein laufender MCP-Server mit Watcher (jede Claude-Code-Session). Ohne
  Watcher meldet das Skript das und bricht ab.
- `session_start.py` `index_health()`: zusätzlich FTS-Abdeckung (Entity-Zeilen mit Inhalt / Entities)
  und Observation-Abdeckung; Warnung unter 90 % mit Hinweis `/mastermind:index repair-index`.
- Doku (README, Vault-`CLAUDE.md`, masterflow-`CLAUDE.md`): `basic-memory reindex --full` **nicht** auf
  einen gesunden Index anwenden (0.22.1 baut Titel-only-Zeilen); nur nach Index-Verlust (Entities fehlen)
  und dann immer mit anschließendem `repair-index`; ein Modellwechsel läuft über den Server-Pfad (4.11), nie über `reindex`. Bei einem basic-memory-Update erneut prüfen
  (`lint.py` Index-Zeile).

### 4.8 Prompt-Hinweise (B2)

`hooks/prompt_hint.py` auf `UserPromptSubmit` (Plugin-Hook, `timeout: 5`):
- Eingabe: `prompt`, `session_id`, `cwd`. Abbruch ohne Ausgabe bei Prompts < 25 Zeichen, Slash-Commands,
  Prompts, die mit `<` beginnen, oder wenn `~/Mastermind/.mastermind.json` `"prompt_hints": false` enthält.
- Terme: Wörter ≥ 4 Zeichen, lowercase, Stoppwörter (Deutsch/Englisch, ≈ 150) entfernt, Identifier
  (mit `_`, `.`, Ziffern, CamelCase) bevorzugt, max. 8 Terme, alle FTS-Sonderzeichen entfernt, jeder Term
  gequotet, `OR`-verknüpft.
- Abfrage (read-only, `sqlite3`-Modul, `?mode=ro`): `search_index` mit `type='entity'`, `project_id` des
  Projekts `mastermind`, `file_path` beginnt mit `gotchas/ patterns/ decisions/ howtos/ stacks/`, Ranking
  `bm25(search_index)`, Schwelle kalibriert (Startwert −8), max. 3 Treffer.
- Dedup je Session: `~/.local/state/mastermind/hints-<session_id>.txt`; ein Treffer wird pro Session
  nur einmal gezeigt.
- Ausgabe: `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"<mastermind-hint>Möglicherweise relevant: [[A]] (gotcha) · [[B]] (pattern). Bei Bedarf read_note.</mastermind-hint>"}}`; ≤ 60 Token; Laufzeit < 50 ms; Exit immer 0.
- Kalibrierung in der Nachtsession: 40 echte Prompts (≥ 30 Zeichen, kein Slash) aus `~/.claude/history.jsonl`
  von Projekten mit Hub; Präzision = relevante Hinweise / gezeigte Hinweise (Beurteilung durch die
  Session anhand Titel vs. Prompt), Trefferquote = Prompts mit Hinweis. Ziel: Präzision ≥ 0,6 bei
  Trefferquote 20–50 %. **Kill-Kriterium:** nach drei Tuning-Runden (Schwelle, Mindestanzahl Terme,
  Identifier-Gewicht) Präzision < 0,5 → Hook bleibt installiert, `.mastermind.json` setzt
  `"prompt_hints": false`, Bericht nennt die Messwerte.

### 4.9 Ungewrappte Sessions (B3)

- `hooks/session_end.py` (Wrapper `hooks/session-end`, ersetzt `vault-commit`; ohne `python3` fällt der
  Wrapper auf den bisherigen Bash-Commit zurück): (1) Vault-Commit wie v2; (2) Push im Hintergrund, wenn
  `git remote get-url origin` im Vault erfolgreich ist und `.mastermind.json` nicht `"push": false` sagt
  (`git push -q origin HEAD` als abgesetzter Hintergrundprozess, nie blockierend); (3) State:
  `~/.local/state/mastermind/last-session-<slug>.json` mit `session_id`, `transcript_path`, `cwd`, `root`,
  `ended` (ISO), `reason`, `edits` (Anzahl `"name":"Edit"|"Write"|"MultiEdit"|"NotebookEdit"` im
  Transkript), `wrapped` (eine `queue-operation`-Zeile mit `"content":"/mastermind:wrap` oder eine `isMeta`-Zeile
  mit `Base directory for this skill:` und `/skills/mastermind-wrap`; der bloße Substring `mastermind:wrap` steht
  durch den Hook-RULES-Block in jedem Transkript und zählt nicht), `notified: 0`. Transkripte > 200 MB
  werden nicht gescannt (`edits: null`). Immer Exit 0.
- `session_start.py`: Matcher `startup|resume|clear|compact`. Bei `source` in `startup|clear|resume` und
  vorhandenem State mit `wrapped: false`, `edits ≥ 5`, Alter ≤ 14 Tage, `session_id ≠` aktuelle Session und
  `notified < 3`: Zeile `UNWRAPPED: session <id-kurz> ended <datum> with <n> edits and no /mastermind:wrap
  → run /mastermind:wrap last`; `notified` wird hochgezählt.
- `/mastermind:wrap last` (4.6) liest das State-File, nutzt `evidence.py --session <id> --digest`, setzt
  am Ende `wrapped: true`.

### 4.10 Hook-Kontext v3 (B7)

Ergänzungen im `<mastermind>`-Block: letzte `## Verlauf`-Zeile des Hubs (eine Zeile), Inbox-Zähler
(`Inbox: n offene Kandidaten`), UNWRAPPED-Zeile (4.9), Leitplanken-Regel (eine Zeile). Health-Check nach
4.7. Budget ≤ 650 Token, Laufzeit < 150 ms. Tests wie v2 plus: State-File-Szenarien, Resume-Guard,
Inbox-Zählung.

### 4.11 Retrieval-Upgrade: basic-memory 0.23.2, Qwen3-Embedding-8B, Reranker

Entscheidung Toni 2026-09-03: bestes lokal betreibbares Modell direkt übernehmen, kein A/B.

- **basic-memory 0.23.2** (25.08.2026): LiteLLM-Embedding-Provider, lokaler Cross-Encoder-Reranker
  (fastembed), Query-/Dokument-Präfixe, Volltext-Fixes für lange Notizen, `inspect query/chunks`.
  Installation braucht `--prerelease=allow` (Abhängigkeit `fastmcp==4.0.0b1`). Isoliert verifiziert am
  2026-09-03: MCP-Sync indexiert vollständig (160 Notizen, 436 Observations, 688 Relations im FTS, 644 Vektor-Chunks),
  `reindex --full` zerstört FTS-Inhalt weiterhin, `reindex --full --embeddings` behält den FTS, bläht aber die
  Chunk-Tabelle auf 2.872 Zeilen auf → Reparaturpfad aus 4.7 bleibt, Vektoren werden nur über den Server-Pfad
  (temporärer `basic-memory mcp`) neu gebaut. Modell-Cache: `~/.basic-memory/fastembed_cache`.
- **Embedding:** `Qwen3-Embedding-8B` über Ollama (`ollama/qwen3-embedding:8b`, 4096 Dimensionen, 32k Kontext,
  Apache-2.0, 4,7 GB). Platz 1 der offenen Modelle auf MTEB multilingual (70,6; 4B 69,5; jina-v3 64,4;
  multilingual-e5-large-instruct 63,2; BGE-M3 59,6), 100+ Sprachen inkl. Programmiersprachen, Code-Retrieval.
  Query-Instruktion per `semantic_embedding_query_prefix` (`Instruct: …\nQuery: `), Dokumente ohne Präfix.
  Warum nicht fastembed: das dort stärkste Modell (jina-v3) verliert Qualität, weil basic-memory dessen
  Aufgaben-Adapter nicht setzt (`model.embed` für Queries und Dokumente).
- **Reranker:** `jinaai/jina-reranker-v2-base-multilingual` (fastembed, 1,1 GB, lokal), `reranker_candidates` 20.
  Qwen3-Reranker wäre stärker, braucht aber einen zweiten Server (llama.cpp) mit bekannten GGUF-Fallen; später.
- **Betrieb:** Ollama als Hintergrunddienst (Homebrew `brew services`), Metal-Beschleunigung, ≈ 5–6 GB RAM bei
  geladenem Modell, Entladen nach 5 Minuten Leerlauf (erste Abfrage danach 2–4 s). Hardware: M5, 24 GB.
- **Ablauf:** Die Umbau-Nachtsession installiert Ollama und Modelle, schreibt `retrieval-upgrade.sh`,
  probt den Wechsel an einer Kopie von Config und Index-DB (`BASIC_MEMORY_CONFIG_DIR`), kalibriert
  `semantic_min_similarity` mit 25 Testfragen (Ziel Trefferquote@3 ≥ 0,85) und ergänzt den Hook um einen
  Ollama-Erreichbarkeitscheck. Der produktive Wechsel läuft morgens per Skript **ohne laufende Session**
  (laufende MCP-Server halten Modell und Vektordimension im Speicher), danach Claude Code neu starten.
  Das Skript sichert Config und DB, kann zurückrollen (`--rollback`) und bricht ab, wenn ein MCP-Prozess läuft.

### 4.12 Konfiguration und Doku

- `~/Mastermind/.mastermind.json` (versteckt, nicht indexiert, git-getrackt): `{"prompt_hints": true|false, "push": true}`.
- `~/.basic-memory/.bmignore`: `inbox/`.
- Plugin 0.3.0 (`plugin.json`, `marketplace.json` mit `metadata.version` 1.2.0); README, masterflow-`.claude/CLAUDE.md`
  (Abschnitt „Architektur: mastermind“), Vault-`CLAUDE.md`, `index.md`, `templates/project.md`, `AGENTS.md`.
- `claude plugin validate --strict` für Marketplace, Plugin, `skills`, `commands`; `claude plugin details`
  (always-on ≤ 800 Token).

---

## 5. Migration

### 5.1 Hubs

Skript `migrate_hubs_v3.py` (einmalig, deterministisch, im Nachtsession-Ordner):
1. Für jeden Projekt-Hub (`type: project`, kein `moc`-Tag): `## Status`-Bullets zu einer Zeile
   `Stand <updated>: <aktiv/archiviert>; letzter bekannter Commit <datum> (Backfill Phase 2)` zusammenfassen
   (Inhalt aus den bisherigen Bullets, nichts erfinden).
2. `## Quellen` einfügen: `- Code, CLAUDE.md, README (Backfill Phase 2, Stand 2026-05-29)` plus
   `- Auto-Memory <pfad> (noch nicht geerntet)`, wenn der Ordner existiert.
3. `## Verlauf` als letzten Abschnitt: eine Zeile je Commit, der die Datei berührt hat
   (`git log --format='%h %ad %s' --date=short -- <datei>`), Form
   `- <datum> manuell · <Commit-Betreff ≤ 120 Zeichen> · Quelle: commit <hash>`, plus
   `- <heute> project · Hub auf Anatomie v3 migriert · Quelle: Umbau v3`.
4. `## Verwandt` bleibt, rückt vor `## Verlauf`. Bestehende Abschnitte werden nicht umformuliert.
5. Dach-Hubs: nur `## Verlauf` anhängen. `_projects-overview` unverändert.
6. `updated` = heute. Danach `lint.py --strict` = 0 ERROR.

### 5.2 Vault-Struktur

`user.md`, `soul.md`, `AGENTS.md`, `inbox/` (leer + `.gitkeep`), `.mastermind.json`; `index.md` erhält die
Ordner-Verantwortlichkeiten (POS-Stil) inkl. `inbox/` und Root-Dateien; `templates/project.md` v3.
Tags: `vor-umbau-v3-<datum>` vor, `umbau-v3-<datum>` nach der Migration.

### 5.3 Index

Nach Abschluss aller Vault-Änderungen `repair_index.py` (4.7), Erfolg per SQL-Zählung: Entity-Zeilen mit
Inhalt ≥ 95 %, Observation-Zeilen ≥ 90 %, Relation-Zeilen ≥ 90 %, Chunks ≥ 1,5 je Entity.

---

## 6. Tests / Definition of Done

- [ ] `claude plugin validate . --strict`, `.claude-plugin/plugin.json --strict`, `plugins/mastermind --strict`,
      `plugins/mastermind/skills --strict`, `plugins/mastermind/commands --strict`.
- [ ] `session_start.py`: 8 Szenarien (Hub per repo/path/name, kein Hub mit Sniff, Worktree, Nicht-Git,
      fehlender Vault, State-File ungewrappt, Resume-Guard, Inbox-Zähler) → gültiges JSON, < 150 ms.
- [ ] `session_end.py`: Commit bei dirty Vault, kein Commit bei sauberem, State-File korrekt, Push nur mit Remote,
      Transkript-Scan mit einem echten Transkript (`edits`, `wrapped`).
- [ ] `prompt_hint.py`: Kalibrierungsprotokoll mit 40 Prompts, Präzision/Trefferquote, Entscheidung laut Kill-Kriterium.
- [ ] `lint.py`: Selbsttest mit einem temporären Mini-Vault (je ein absichtlich kaputter Fall pro Regel); echter Vault nach Migration 0 ERROR.
- [ ] `repair_index.py`: Abdeckung wie 5.3; `search_notes` (hybrid) findet einen nur im Body vorkommenden Fehlercode.
- [ ] `evidence.py --digest` auf einem echten Transkript ≤ 40.000 Zeichen.
- [ ] E2E mit `claude --plugin-dir plugins/mastermind -p …` in einem Projekt mit Hub: `<mastermind>`-Block mit Verlauf-Zeile,
      Prompt-Hinweis bei einem passenden Prompt, State-File nach Ende.
- [ ] Vault: Lint grün, Tags gesetzt, `~/.claude/CLAUDE.md` importiert beide Dateien (Test in einem Fremdordner: `claude -p "Antworte nur mit der ersten Überschrift aus user.md und der ersten aus soul.md, die du im Kontext hast."`).
- [ ] Plugin-Cache 0.3.0 mit 3 Hooks (`claude plugin details`), always-on ≤ 800 Token.
- [ ] Retrieval-Probe (4.11): Ollama antwortet, `qwen3-embedding:8b` liefert 4096 Werte, Reranker-Modell im Cache,
      `retrieval-upgrade.sh --rehearsal` läuft gegen die Kopie durch, Chunks ≥ Entities mit mittlerer Länge ≥ 150 Zeichen,
      Trefferquote@3 ≥ 0,85 bei 25 Testfragen, Schwelle im Skript eingetragen, Hook warnt bei nicht erreichbarem Ollama.

---

## 7. Kontextbudget je Session (Schätzung)

| Quelle | Token |
|---|---|
| Plugin always-on (Skills/Commands-Listing) | ≈ 550 |
| SessionStart-Hook | ≤ 650 |
| `user.md` + `soul.md` (Import) | ≤ 500 |
| Prompt-Hinweis (nur bei Treffer) | ≤ 60 je Prompt |

---

## 8. Was Toni selbst tun muss

Steht im Handout `.claude/nachtsessions/toni-handout-mastermind-v3.md`: andere Claude-Sessions vor den
Nachtsessions schließen (B4), nach dem Umbau Claude Code neu starten, privates Git-Remote für den Vault
anlegen (B5), `permissions.allow` für den MCP-Server (B6), optional Codex-MCP-Eintrag (B10), Namensfrage
in `user.md` prüfen, morgens Bericht und `git log` lesen.

## 9. Später

- Per-Prompt-Hinweise mit Vektorsuche (wenn ein leichtgewichtiger Embedding-Pfad ohne 1-GB-Modell-Load verfügbar ist).
- `masterflow:init` ruft `/mastermind:project` für neue Projekte.
- Upstream-Meldung an basic-memory: Batch-Indexer schreibt keine Inhalts-/Observation-/Relation-Zeilen (0.22.1).
- Obsidian-Dataview/Bases-Ansicht über `inbox/` und `## Verlauf`.
