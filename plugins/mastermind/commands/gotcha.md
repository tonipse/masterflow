---
description: Quickly record a problem → cause → solution as a gotcha note in the Mastermind brain.
argument-hint: "<what went wrong and how it was fixed>"
---

Record a gotcha in the Mastermind vault about: "$ARGUMENTS"

1. Load the skill `mastermind:mastermind-brain` (Skill tool) and read its `conventions.md`.
2. `search_notes` (hybrid + title) first; if a note about the same problem exists, extend it with
   `edit_note` instead of creating a duplicate.
3. Otherwise `write_note` in folder `gotchas` with the sections `## Problem`, `## Symptom` (exact error
   text), `## Ursache`, `## Lösung`, `## Verwandt`; capture the key facts as `- [gotcha] … #tag` with a
   recency hint and the stack version; frontmatter complete (type `gotcha`, `projects` with the hub,
   `confidence`, `source`). Title ≤ 80 characters, no colon.
4. Link the project hub and at least one stack or topical note; add the backlink bullet to the hub.
5. Reply in German with the note path. No questions.
