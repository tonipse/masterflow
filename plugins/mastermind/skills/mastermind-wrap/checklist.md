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
| stack | new experience with a tool/library: version quirk, config that works, limit, API behaviour | fact with version and date; goes into `stacks/<tool>.md` (append) or a new stack note if there are ≥ 2 facts |
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

## C. Hub update schema

Use `edit_note` with `replace_section` for `## Status` and `## Offene Punkte`, `append` under
`## Bekannte Gotchas` / `## Wichtige Decisions` for new links, `find_replace` for frontmatter dates.

- frontmatter: `updated: 'YYYY-MM-DD'`, `last_wrap: 'YYYY-MM-DD'`; add `repo`/`path` if missing.
- `## Stack`: only if the stack changed (new major dependency, removed service).
- `## Konventionen`: only durable conventions (log format, branch model, docs workflow), not one-off choices.
- `## Bekannte Gotchas` / `## Wichtige Decisions`: one bullet per new or updated note:
  `- [gotcha] Siehe [[Titel]] #tag` / `- [decision] <one line> (siehe [[Titel]])`.
- `## Status`: replace with exactly one line `Stand YYYY-MM-DD: <state in one sentence>`.
- `## Offene Punkte`: replace the whole list: keep items still open, drop finished ones, add new ones.
  Keep it under 8 bullets, each one line.

## D. Limits

- At most 7 notes per wrap; prefer fewer, richer notes. If more candidates qualify, take the most
  reusable ones and list the rest under "übersprungen" in the report so the user can ask for them.
- Extend existing notes before creating new ones (conventions §8).
- Never rewrite an existing note wholesale; use `edit_note` operations so nothing gets lost.

## E. Report template (German, printed to the user)

```
## Mastermind Wrap – <projekt> (<YYYY-MM-DD>)

| Notiz | Typ | Aktion | Pfad |
|---|---|---|---|
| [[Titel]] | gotcha | neu | gotchas/Titel.md |
| [[Titel]] | stack | erweitert | stacks/inngest.md |

Hub: [[<hub>]] aktualisiert (Status, offene Punkte: <n>, neue Links: <n>).
Übersprungen: <Kandidat> (Grund in 5 Wörtern) · …
Vault-Commit: <hash> · Index: <ok | Warnung + Befehl>
```

In `dry` mode print the same tables with action `geplant` and change nothing.
