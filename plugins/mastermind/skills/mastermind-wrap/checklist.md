# Wrap checklist: what to harvest, what to skip, how to report

## A. Candidate criteria per type

Walk through the session and the evidence report once per type. Write down every candidate as
`type | one-line claim | evidence | confidence` before touching the vault.

| type | take it when | must contain |
|---|---|---|
| gotcha | a problem cost real effort, the cause was surprising, and the fix is verified | symptom (exact error text), cause, fix, stack + version, source (commit/file) |
| decision | a choice between real alternatives that constrains future work in this or other projects | context, decision, alternatives with why-not, consequences |
| pattern | an approach that worked and generalizes beyond one file (idempotency, retries, auth flows, data modelling, testing techniques) | when to apply, approach, example, pitfalls |
| howto | a multi-step procedure that only worked in a specific order or with specific flags (deploy, migration, setup, tooling) | goal, prerequisites, numbered steps with commands verbatim, pitfalls |
| stack | new experience with a tool/library: version quirk, config that works, limit, API behaviour | fact with version and date. Placement rule: append to an existing `stacks/<tool>.md`; create a new stack note only when there are ≥ 2 facts for that tool; a single fact without a stack note stays inside the note that carries it |
| hub update | stack changed, new convention, architecture insight, changed status or open points | see section C |

## B. Skip list (do not write these into the vault)

- Project status: what is deployed, pushed, merged, pending. That goes to auto memory or the project's docs.
- Anything not verified in this session (a hypothesis, "should work", untested advice).
- Trivia and generic knowledge that any documentation states on page one.
- Content already in the vault unchanged. If the vault note exists and is correct, at most add the
  project to its `projects` list and a `(bestätigt YYYY-MM in <projekt>)` observation.
- User preferences, working style, communication rules → auto memory.
- Secrets, tokens, customer data, internal URLs with credentials.
- Long narratives. A note explains one topic; the session story is not a topic.

**Focus rule (conventions §11):** touch only the notes and hubs that this session's evidence affects. A wrap
never tidies, rewords or "improves" unrelated notes, and never rewrites `## Verlauf` lines.

## C. Hub update schema (anatomy v3)

Use `edit_note` with `replace_section` for `## Status` and `## Offene Punkte`, `append` under
`## Bekannte Gotchas` / `## Wichtige Decisions` for new links, `find_replace` for frontmatter lines.
There is no "add key" operation: to add a missing frontmatter key use `find_replace` with
`find_text: "type: project"` and replacement `type: project\n<key>: <value>` (one key per call).

- frontmatter: `updated: 'YYYY-MM-DD'`, `last_wrap: 'YYYY-MM-DD'`; add `repo`/`path` if missing.
- `## Stack`: only if the stack changed (new major dependency, removed service).
- `## Konventionen`: only durable conventions (log format, branch model, docs workflow), not one-off choices.
- `## Bekannte Gotchas` / `## Wichtige Decisions`: one bullet per new or updated note:
  `- [gotcha] Siehe [[Titel]] #tag` / `- [decision] <one line> (siehe [[Titel]])`.
- `## Status`: replace with exactly one line `Stand YYYY-MM-DD: <state in one sentence>`.
- `## Offene Punkte`: replace the whole list: keep items still open, drop resolved ones, add new ones.
  Only unknowns, risks and unconfirmed assumptions a later session must know (**no to-dos**, tasks live in
  the repo). At most 8 bullets, each one line.
- `## Quellen`: one line per source actually read in this wrap, `- <Quelle> (geerntet bis YYYY-MM-DD)`;
  refresh the date of an existing line (`find_replace`), add a line for a new source (e.g. the project's
  auto-memory folder, the session transcript). Never remove lines. Missing section → add it before `## Verwandt`.
- `## Verlauf` (last section, append-only): `edit_note` `append` exactly one line
  `- YYYY-MM-DD wrap · <n> neu, <m> erweitert, Hub: <was> · Quelle: Session <id-kurz>` (`last` mode:
  `wrap (nachgeholt)`). Existing lines are never edited or deleted. If the hub still lacks `## Verlauf`
  (pre-v3 hub), append the heading first; if `## Verwandt` is not directly before it, leave the order alone
  and mention it in the report (`/mastermind:index fix` repairs structure).
- Stack notes: for each new gotcha with a matching `stacks/<tag>.md`, append `- [gotcha] Siehe [[Titel]] #tag`
  under its `## Bekannte Gotchas`.

## D. Limits

- Rank all candidates by reusability. The top 7 proceed as new or extended notes; hub edits and appends
  to existing stack notes are not counted. Every candidate below the cut is listed under `Übersprungen`
  with a five-word reason so the user can ask for it by name.
- Extend existing notes before creating new ones (conventions §8).
- Never rewrite an existing note wholesale; use `edit_note` operations so nothing gets lost.
- **Inbox rule (conventions §12):** a candidate that is reusable but fell under the 7-note cut, or that is
  promising but not verified in this session, becomes one line in `inbox/<hub>.md`
  (`- [ ] YYYY-MM-DD · <typ> · <Aussage> · Beleg: <Datei/Session> · Grund: <über Limit | unverifiziert>`);
  create the file with its minimal frontmatter if missing. Trivia and skip-list items (§B) only appear in
  the report's `Übersprungen` line, never in the inbox. Inbox lines that this session verified and wrote as
  notes are promoted in place (`[ ]` → `[x]`, ` → [[Titel]]` appended).

## E. Report template (German, printed to the user)

```
## Mastermind Wrap – <projekt> (<YYYY-MM-DD>)

| Notiz | Typ | Aktion | Pfad |
|---|---|---|---|
| [[Titel]] | gotcha | neu | gotchas/Titel.md |
| [[Titel]] | stack | erweitert | stacks/inngest.md |

Hub: [[<hub>]] aktualisiert (Status, offene Punkte: <n>, Quellen: <n>, neue Links: <n>).
Verlauf: 1 Zeile
Inbox: <n> neu, <m> befördert
Übersprungen: <Kandidat> (Grund in 5 Wörtern) · …
Lint: <0 ERROR, n WARN | behoben: …> · Vault-Commit: <hash> · Index: <ok | Warnung + Befehl>
```

`last` mode adds the line `Nachgeholt aus Transkript: Session <id-kurz> (<Datum>)` under the heading.
Dry mode: same tables with action `geplant`; `Hub: [[<hub>]] geplant (…)` or `Hub: fehlt (würde per
/mastermind:project angelegt)`; `Verlauf: geplant`; `Inbox: <n> geplant`; `Lint: übersprungen (dry)`;
`Vault-Commit: keiner (dry)`.
