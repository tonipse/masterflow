# Mastermind vault conventions

Read this before writing or editing any note. The vault (`~/Mastermind`, Obsidian + basic-memory) is
shared by all code projects; a note is only useful if someone in another project can find and apply it.
Notes are written in **German**; identifiers, commands, error strings stay verbatim.

## 1. Note types and folders

| type | folder (the `folder` argument of `write_note`) | what belongs there |
|---|---|---|
| `gotcha` | `gotchas` | problem → symptom → cause → fix, verified |
| `pattern` | `patterns` | reusable approach that worked ("so macht man X") |
| `decision` | `decisions` | architecture/tech decision with alternatives and consequences (ADR) |
| `howto` | `howtos` | multi-step procedure that took effort to figure out |
| `stack` | `stacks` | experience with one tool/library/service: setup, configs, known gotchas (links) |
| `project` | `projects` | exactly one hub per code project (bridge into the knowledge) |
| `moc` | root / `projects` / `patterns` | maps of content (`index`, `_projects-overview`, `_patterns-overview`) |

Folder names are exactly these words. Permalinks look like `mastermind/gotchas/...` but `mastermind/` is
**not** a folder. Never write into `mastermind/<folder>`.

## 2. Frontmatter (every note)

```yaml
---
title: <title, see §3>
type: gotcha | pattern | decision | howto | stack | project | moc
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'          # bump on every content change
tags: [stack/nextjs, topic/auth]   # stack/* from §7, topic/* free but lowercase-kebab
status: active                  # draft | active | archived | superseded
projects: ["[[supportpilot]]"]  # hubs where this applies; ALWAYS quoted wikilinks
confidence: high                # low | medium | high (how sure, how well verified)
related: ["[[index]]"]          # quoted wikilinks
source: <commit, file, URL or ticket, verbatim>   # optional but strongly preferred
---
```

Project hubs add:

```yaml
repo: github.com/org/name       # normalized remote: no protocol, no .git, lowercase
path: /Users/toni/Desktop/x/y   # absolute path of the main checkout
last_wrap: 'YYYY-MM-DD'         # set by /mastermind:wrap
tags: [project, group/fwg-one, stack/nextjs, ...]   # group/*: fwg-one | rocketads | moeller | standalone
```

`write_note` creates the file from `content`; put the complete frontmatter block at the top of `content`
so every field is set. Never leave `null` values in a note you write.

## 3. Titles

- Max 80 characters, a noun phrase that names the **topic**, not the whole lesson.
  Good: `Inngest step.sendEvent statt inngest.send in step.run`. Bad: `Inngest: inngest.send() in step.run() feuert bei Retry doppelt — step.sendEvent() nutzen`.
- The title becomes the filename and the wikilink target in Obsidian. Do not use `: / \ | # ^ [ ] ? * < > "`.
  Use `–` or `-` instead of a colon.
- One topic per note. If a lesson has two independent parts, write two notes.

## 4. Body structure

Prose first (2–6 sentences of context), then the sections of the type, then `## Verwandt` with links.

- **gotcha**: `## Problem` · `## Symptom` (exact error text) · `## Ursache` · `## Lösung` · `## Verwandt`
- **pattern**: `## Wann anwenden` · `## Ansatz` · `## Beispiel` (code) · `## Fallstricke` · `## Verwandt`
- **decision**: `## Kontext` · `## Entscheidung` · `## Alternativen` · `## Konsequenzen` · `## Verwandt`
- **howto**: `## Ziel` · `## Voraussetzungen` · `## Schritte` (numbered, commands verbatim) · `## Fallstricke` · `## Verwandt`
- **stack**: `## Setup` · `## Bewährte Configs` · `## Bekannte Gotchas` (links) · `## Verwandt`
- **project hub**: `## Zweck` · `## Stack` · `## Architektur / Eigenheiten` · `## Konventionen` · `## Wichtige Decisions` · `## Bekannte Gotchas` · `## Status` · `## Offene Punkte` · `## Verwandt`

## 5. Observations and recency

- Atomic, searchable facts as observations: `- [gotcha] <fact> #tag`, `- [decision] …`, `- [pattern] …`, `- [fact] …`.
  These are plain list items in Obsidian (not checkboxes) and become searchable facts in basic-memory.
- Every fact that can go stale carries a recency hint: `(Stand YYYY-MM, Quelle: <commit/doc>)`.
- Versions matter: name the library/tool version the fact was verified with.

## 6. Linking

- Wikilinks by title: `[[supportpilot]]`, `[[Inngest step.sendEvent statt inngest.send in step.run]]`.
- In frontmatter, wikilinks are always quoted strings.
- Every note links to its project hub **and** at least one topical note or stack note. Hubs link back
  (add a bullet under `## Bekannte Gotchas` / `## Wichtige Decisions`). Stack notes list their gotchas.
- No orphans. If you cannot find a related note, link `[[index]]`.

## 7. Canonical stack tags (`stack/<tag>`)

`nextjs react vue svelte astro typescript nodejs python dotnet blazor php laravel go flutter electron express fastify hono`
`supabase neon postgres mysql mssql mongodb redis prisma drizzle`
`aws-lambda aws vercel docker cloudflare`
`inngest n8n make zapier`
`shopify clickup asana pipedrive slack gmail google-api google-drive google-sheets apps-script`
`anthropic openai ai-sdk`
`vitest jest playwright puppeteer tailwind threejs gsap stripe resend zod obsidian basic-memory claude-code`

Use exactly these spellings so hubs, stack notes and the session-start hook agree. Add a new tag only if
none fits, and then use it consistently.

## 8. Dedup procedure (before every write)

1. `search_notes` (hybrid, `page_size` 5) with two or three key terms: the tool/library, the error string, the domain word.
2. `search_notes` with `search_type: "title"` on the intended title words.
3. Read the top hits (`read_note`). Then decide:
   - **Same problem/topic** → `edit_note` the existing note: append observations or a section, bump `updated`,
     add the current project to `projects`, add `related` links. Do not create a near-duplicate.
   - **Partial overlap** → extend the existing note if it stays one topic; otherwise write the new note and
     cross-link both ways.
   - **Nothing** → `write_note`.
4. **Contradiction** with an existing note: fix the old note (mark the outdated fact
   `(überholt seit YYYY-MM, siehe [[neue Notiz]])`), never leave two notes that disagree.
5. Never create a second hub for a project. Hubs are matched by `repo`, then `path`, then title = folder name.

`edit_note` operations: `append`, `prepend`, `find_replace` (with `find_text`), `replace_section` (with `section`, e.g. `## Status`).

## 9. What goes where

| Content | Goes to |
|---|---|
| Reusable engineering knowledge (gotcha, pattern, decision, how-to, stack quirk) | **Vault** note |
| Project facts others need when they open the repo (stack, conventions, architecture, open points) | **Vault** project hub |
| Project status, deploy state, what is pushed or not, session progress | Claude auto memory (`~/.claude/projects/<project>/memory/`) or the project's own docs |
| User preferences and working style | Claude auto memory |
| Anything already fully documented in the project's docs | link to it from the hub, do not copy |
| Secrets, tokens, customer data, credentials | nowhere in the vault, ever |

## 10. Quality bar for a vault note

Write it only if all four hold: **verified** (test passed, behaviour observed, documentation confirmed),
**non-obvious** (cost real effort or contradicts the naive expectation), **reusable** (formulated so a
stranger in another project can apply it), **complete** (cause and fix, or decision and alternatives).
Otherwise it belongs to auto memory or nowhere.
