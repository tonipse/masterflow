---
description: Central engineering brain for all code projects (Mastermind vault via the mastermind-memory MCP server). Use at the START of a non-trivial coding task to recall prior patterns, gotchas, decisions and how-tos, and IMMEDIATELY after verifying something non-obvious to capture it. Also load it before writing any vault note, it carries the note conventions.
---

# Mastermind Brain

You have a central, cross-project engineering knowledge vault ("Mastermind") through the
`mastermind-memory` MCP server (basic-memory, local, offline). The vault lives at `~/Mastermind` and is
the SAME from every project: the server is locked to it via `BASIC_MEMORY_MCP_PROJECT=mastermind`,
regardless of the current working directory. Notes are German Markdown with frontmatter and wikilinks,
browsable in Obsidian.

The session-start hook of this plugin already told you which project hub applies, which notes were
recently learned for it, which projects are similar and which stack notes to consult. Use that.

## RECALL first (pull)

Before implementing anything non-trivial, search the brain:

- `search_notes` with `search_type: "hybrid"` (semantic + full text) and two or three key terms:
  the tool or library, the error string, the domain word. Try a second phrasing if the first returns nothing.
- Read relevant hits with `read_note`; `build_context("memory://projects/<hub>")` walks the hub's links.
- Tell the user in one line which prior knowledge you are reusing (with `[[wikilinks]]`).

Triggers: new feature in a known stack, integrating an API you have seen before, any build/deploy/runtime
error, choosing a library, touching auth/webhooks/queues/idempotency/money, anything that smells like
"we have hit this before".

## CAPTURE autonomously (push)

Capture **without asking** as soon as you have **verified** something that passes the quality bar in
`conventions.md` §10 (verified, non-obvious, reusable, complete). Typical moments: a bug whose cause was
surprising, a workaround that took several attempts, a decision between real alternatives, a procedure
that only worked in a specific order, a version-specific quirk of a tool.

Procedure:

1. **→ Read** `${CLAUDE_SKILL_DIR}/conventions.md` (types, folders, frontmatter, titles, links, dedup).
2. Run the dedup procedure (conventions §8). Prefer `edit_note` on an existing note over a near-duplicate.
3. `write_note` / `edit_note` with complete frontmatter, German prose, observations with tags and recency hints.
4. Link: the project hub (`projects: ["[[hub]]"]` and `## Verwandt`) plus at least one topical or stack
   note; add a backlink bullet to the hub (`edit_note`, `append` or `replace_section`).
5. Tell the user in one line: type, title, path. Then continue with the task.

Do **not** capture: project status ("deployed", "not pushed"), guesses, unverified hypotheses, trivia,
user preferences, secrets, or what the project's own docs already cover (link instead).
Those belong to Claude's auto memory or nowhere (conventions §9).

If the project has no hub yet, create it first with the procedure of the `mastermind-project` skill
(read `${CLAUDE_SKILL_DIR}/../mastermind-project/SKILL.md`), then capture.

## Tools (mastermind-memory)

`search_notes`, `read_note`, `build_context`, `write_note`, `edit_note`, `move_note`, `delete_note`,
`recent_activity`, `list_directory`. `search_notes` is the full hybrid search; prefer it over the minimal `search`.

## Companion commands

`/mastermind:recall <topic>` · `/mastermind:capture` · `/mastermind:gotcha` · `/mastermind:decision` ·
`/mastermind:project` (onboard or update the hub) · `/mastermind:wrap` (session close-out) · `/mastermind:index` (health check).
