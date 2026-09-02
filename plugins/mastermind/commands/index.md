---
description: Health-check the Mastermind brain — index completeness, orphans, duplicates, stale notes, hubs without repo/path.
---

Audit the Mastermind vault. Read-only unless the user confirms fixes afterwards.

1. **Index**: run `basic-memory status --project mastermind` and compare the number of `.md` files in the
   vault (`find "${MASTERMIND_VAULT:-$HOME/Mastermind}" -name '*.md' -not -path '*/.obsidian/*' | wc -l`)
   with the indexed entity count
   (`sqlite3 ~/.basic-memory/memory.db "select count(*) from entity e join project p on p.id=e.project_id where p.name='mastermind'"`).
   Below 90 %: report the fix `basic-memory reindex --full -p mastermind`.
2. **Structure** via `list_directory` (depth 2): files outside the canonical folders (e.g. a stray
   `mastermind/` folder), notes whose `type` does not match their folder.
3. **Hubs**: `projects/*.md` without `repo`/`path`, without `stack/*` tags, or never wrapped (`last_wrap`
   missing) although `updated` is older than 60 days. Duplicate hubs for one repo.
4. **Notes**: orphans (no wikilinks in or out; `basic-memory orphans --project mastermind` helps),
   likely duplicates (`search_notes` with the title words of each recent note, `recent_activity` for the
   last 30 days), `status: draft`, notes without `projects`, titles longer than 80 characters or with a colon
   (they break Obsidian links unless an `aliases` entry exists).
5. Report in German as a short list per category with `[[wikilinks]]` and one suggested fix each.
   Change nothing unless the user confirms.
