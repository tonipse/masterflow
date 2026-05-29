---
description: Central engineering brain for all code projects. Use at the START of a non-trivial coding task to recall prior knowledge (patterns, gotchas, decisions, how-tos) from the Mastermind vault, and AFTER solving something non-obvious to offer to capture the lesson. Backed by the mastermind-memory MCP server (local basic-memory).
---

# Mastermind Brain

You have a central, cross-project engineering knowledge vault ("Mastermind") via the `mastermind-memory` MCP server (basic-memory). It stores reusable knowledge: patterns, gotchas+fixes, architecture decisions, stack experience, how-tos. The vault lives at `~/Desktop/Mastermind` and is the SAME from every project (the server is locked to it via `BASIC_MEMORY_MCP_PROJECT=mastermind`, regardless of your current working directory).

## RECALL first (pull)
At the start of a non-trivial coding task, BEFORE implementing, search the brain with the task's key terms (tech, error, domain) using the `search_notes` tool (semantic/hybrid; prefer `search_type=hybrid`). If relevant notes exist, read them (`read_note` / `build_context`), factor them in, and tell the user which prior knowledge you are reusing.
Triggers: setting up auth, fixing a build/deploy/runtime error, choosing a library, integrating a known API, or anything that smells like "we've hit this before."

## CAPTURE after (push)
After solving something non-obvious, hitting and fixing a gotcha, or making an architectural decision, PROACTIVELY OFFER to capture it (never capture silently). On confirmation:
1. Pick the type: `gotcha | decision | pattern | stack | howto`.
2. `search_notes` first to avoid duplicates — prefer `edit_note` on an existing note over a near-duplicate.
3. `write_note` with full frontmatter (see Conventions).
4. Link it to the relevant `projects/<name>` hub and related notes.
5. Show the created/updated note path.

## Vault layout
`patterns/ gotchas/ decisions/ stacks/ howtos/ projects/ templates/` · `index.md` (entry MOC) · `CLAUDE.md` (conventions).

## Conventions (enforce when writing)
- Frontmatter: `title`, `type` (`pattern|gotcha|decision|howto|stack|project|moc`), `created`, `updated` (YYYY-MM-DD), `tags`, `status` (`draft|active|archived|superseded`), `projects` (quoted wikilinks, e.g. `["[[supportpilot]]"]`), `confidence` (`low|medium|high`), `related`, optional `source` (verbatim).
- Body: clear prose; capture atomic facts as observations `- [gotcha] … #tag` / `- [decision] …`.
- Linking: `[[Note Title]]`; in frontmatter ALWAYS quote internal links. Every note links to ≥1 other (no orphans).
- Add a recency hint on facts: "(Stand YYYY-MM, Quelle)". One topic per note.

## Tools (mastermind-memory)
`write_note, read_note, edit_note, move_note, delete_note, search_notes, recent_activity, build_context, list_directory`. (Note: `search_notes` is the full semantic/hybrid search; a minimal `search` also exists but prefer `search_notes`.)

## Companion commands
`/mastermind:recall`, `:capture`, `:gotcha`, `:decision`, `:project`, `:index`.
