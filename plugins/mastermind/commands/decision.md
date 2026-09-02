---
description: Record an architecture decision (ADR) in the Mastermind brain.
argument-hint: "<decision and why>"
---

Record an architecture decision in the Mastermind vault about: "$ARGUMENTS"

1. Load the skill `mastermind:mastermind-brain` (Skill tool) and read its `conventions.md`.
2. `search_notes` first. An existing decision note on the same question is extended, not duplicated:
   add a dated `- [decision] …` fact and mark the outdated fact inline
   `(überholt seit YYYY-MM, siehe …)`; set `status: superseded` on the old note only when a separate
   new note replaces it entirely.
3. Otherwise `write_note` in folder `decisions` with `## Kontext`, `## Entscheidung` (`- [decision] …`),
   `## Alternativen` (each with why not), `## Konsequenzen`, `## Verwandt`; `status: active`,
   `projects` with the hub, `confidence`, `source` (ticket, commit, discussion date).
4. Link the project hub and the affected stack note; add `- [decision] … (siehe [[Titel]])` to the hub's
   `## Wichtige Decisions`.
5. Reply in German with the note path. No questions.
