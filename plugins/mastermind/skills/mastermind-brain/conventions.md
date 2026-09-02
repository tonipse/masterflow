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
| `moc` | root / `projects` / `patterns` | maps of content (`index`, `_projects-overview`, `_patterns-overview`); umbrella hubs (`fwg-one`, `rocketads`, `fwg-warehouse`) are projects that also carry the tag `moc` |
| `note` | root only | the root files `CLAUDE.md`, `AGENTS.md`, `user.md`, `soul.md` (conventions, agent instructions, cross-project user facts, behaviour charter) |
| `inbox` | `inbox` | one file per hub with unverified candidates (§12); not indexed |

`note` and `inbox` are **not** knowledge notes: the frontmatter, title and linking rules of §2–§6 do not
apply to them (root files only have line limits, see §9; inbox files follow §12).

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
source: <commit, file, URL or ticket, verbatim>   # REQUIRED for gotcha, decision, pattern, howto; optional for stack, project, moc
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
so every field is set. Never write `null` values: omit a key you cannot fill (`repo` without a remote,
`last_wrap` before the first wrap). Readers treat a missing key as "unknown"/"never".
A gotcha, decision, pattern or howto without a `source` is not written: name the commit, file, session or
URL you verified it with (the lint marks a missing `source` as an error for new notes). If you cannot,
the candidate goes to the inbox (§12), not into a note.
`edit_note` cannot add a key; add one with `find_replace` on an existing line, e.g. `find_text: "type: project"`
→ `type: project\nrepo: github.com/org/name`.

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
- **project hub** (anatomy v3, sections in exactly this order): `## Zweck` · `## Stack` · `## Architektur / Eigenheiten` ·
  `## Konventionen` · `## Wichtige Decisions` · `## Bekannte Gotchas` · `## Status` · `## Offene Punkte` · `## Quellen` ·
  `## Verwandt` · `## Verlauf`
  - `## Status`: exactly one line `Stand YYYY-MM-DD: <state in one sentence>`; replaced on every wrap.
  - `## Offene Punkte`: unknowns, risks and unconfirmed assumptions a later session must know; at most 8 bullets;
    **no to-dos** (tasks live in the repo, never in the vault).
  - `## Quellen`: one line per source that fed the hub: `- <Quelle> (geerntet bis YYYY-MM-DD)`. Standard sources:
    `CLAUDE.md`/`AGENTS.md`, docs index, specs, the project's auto-memory folder, transcripts. Only add or refresh lines.
  - `## Verwandt` stays directly before `## Verlauf`, so that `edit_note` `append` always lands in the timeline.
  - `## Verlauf`: the **last** section, append-only. One line per change:
    `- YYYY-MM-DD <wrap|ernte|project|capture|manuell> · <Änderung ≤ 120 Zeichen> · Quelle: <Session-ID kurz | commit <hash> | Ledger>`.
    Lines are never edited or deleted; add a line with `edit_note` `append`.
  - Umbrella hubs (tag `moc`) keep their own sections and only add `## Verlauf` as the last section.

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

`nextjs react vue nuxt svelte sveltekit astro typescript nodejs python fastapi django flask sqlalchemy pandas dotnet blazor php laravel go flutter electron express fastify hono`
`supabase neon postgres mysql mssql mongodb redis prisma drizzle`
`aws-lambda aws vercel docker cloudflare sentry`
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
| Cross-project user facts (role, companies and project groups, tools, environment, preferences) | `~/Mastermind/user.md` (≤ 60 lines; change with `edit_note` `find_replace`/`append`, condense instead of growing) |
| Behaviour rules that hold in every project (language, autonomy, evidence, limits) | `~/Mastermind/soul.md` (≤ 40 lines; same editing rule) |
| Project-specific status, preferences and working style | Claude auto memory |
| Unverified but promising, reusable candidates (also: candidates cut by the 7-note limit of a wrap) | `inbox/<hub>.md` (§12) |
| Anything already fully documented in the project's docs | link to it from the hub, do not copy |
| Secrets, tokens, customer data, credentials | nowhere in the vault, ever |

## 10. Quality bar for a vault note

Write it only if all four hold: **verified** (test passed, behaviour observed, documentation confirmed),
**non-obvious** (cost real effort or contradicts the naive expectation), **reusable** (formulated so a
stranger in another project can apply it), **complete** (cause and fix, or decision and alternatives).
Otherwise it belongs to auto memory, to the inbox (§12: reusable but not yet verified) or nowhere.

## 11. Guardrails and focus

- **Decisions are constraints.** When a search returns a `decisions/` note for the area you are working in,
  treat it as a guardrail. If the planned approach contradicts it, say so in one line **before** acting.
  If the user overrides it, update the decision note (dated `- [decision]` fact with the new choice; set
  `status: superseded` only when a separate new note replaces it entirely). Never bypass a decision silently.
- **Focus.** Touch only the notes and hubs that the evidence of the current session affects. No tidying,
  rewording or "improving" of unrelated notes during a capture or a wrap.

## 12. Inbox (candidates that are not yet truth)

- Path `inbox/<hub>.md`, one file per hub (`<hub>` = the hub's file stem). Create it when missing, with this
  minimal frontmatter and nothing else: `title: 'inbox – <hub>'`, `type: inbox`.
- One candidate per line:
  `- [ ] YYYY-MM-DD · <typ> · <Aussage> · Beleg: <Datei/Session> · Grund: <über Limit | unverifiziert>`
  (`<typ>` = gotcha | decision | pattern | howto | stack | hub).
- Promoted (the candidate was verified and written as a note): edit that line once, `[ ]` → `[x]`, and
  append ` → [[Titel]]`. Never delete inbox lines in an automated run; the user prunes the inbox.
- Not indexed: `inbox/` is listed in `~/.basic-memory/.bmignore`, so `search_notes` never returns inbox
  lines; the files are visible in Obsidian. Health checks (hook, lint, harvest) do not count `inbox/` as notes.
- Only `/mastermind:wrap`, `/mastermind:project`, the harvest night session and an autonomous capture
  (promising but unverified) write into the inbox. Trivia and everything on the skip list (wrap checklist §B)
  never goes there.
