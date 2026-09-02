---
name: index
description: Health check and maintenance of the Mastermind brain. Runs the vault lint (frontmatter, note types, titles, wikilinks, hub anatomy v3, root files, inbox) and the basic-memory index check; "fix" applies the safe fixes and commits, "repair-index" rebuilds missing full-text rows through the running MCP watcher.
disable-model-invocation: true
argument-hint: "[fix] [repair-index]"
effort: high
allowed-tools: Read Grep Glob Bash mcp__plugin_mastermind_mastermind-memory__search_notes mcp__plugin_mastermind_mastermind-memory__read_note mcp__plugin_mastermind_mastermind-memory__edit_note mcp__plugin_mastermind_mastermind-memory__list_directory
---

# mastermind-index (`/mastermind:index`)

Audit the Mastermind vault deterministically and report in German. Arguments: `$ARGUMENTS`
- no argument → **read-only**: lint, index check, report. Change nothing.
- `fix` → apply the safe fixes, lint again, commit the vault.
- `repair-index` → rebuild the incomplete full-text rows of the basic-memory index.
Both words may be combined. Never ask questions.

## 1. Lint

```bash
python3 "${CLAUDE_SKILL_DIR}/lint.py" --vault "${MASTERMIND_VAULT:-$HOME/Mastermind}"
```

The output has one line per finding (`ERROR|WARN|INFO <pfad>: <Befund>`) and a summary line. Rules and
severities are documented in the script header; the short version: structure errors (type vs folder, hub
anatomy v3 with `## Status` as one `Stand` line, `## Quellen`, `## Verwandt`, `## Verlauf` last, at most 8
open points, root files and their line limits) are ERROR; missing fields, value sets, `source` and dates
are ERROR only for notes created on or after 2026-09-04 and WARN for older notes; titles, non-canonical
stack tags, dangling wikilinks and orphans are WARN; inbox counts and the index line are INFO.

## 2. Report

Summarize in German, grouped by category, with `[[wikilinks]]` and **one concrete fix per finding**:

- **Struktur** (ERROR): file, what is wrong, the `edit_note` operation that fixes it (`replace_section` for
  `## Status`, `append` for a missing `## Verlauf`, `insert_before_section` for `## Quellen`).
- **Frontmatter** (`source`, `projects`, `confidence`, `related`, dates, value sets): file and the missing or
  wrong key; the fix is a `find_replace` on `type: <typ>` → `type: <typ>\n<key>: <value>`.
- **Titel** (length, characters): the lint prints one summary line for the legacy notes; do not propose
  renaming titles (forbidden, wikilinks depend on them), propose an `aliases` entry only when missing.
- **Links**: dangling targets and orphans; propose the nearest existing note or `[[index]]`.
- **Hubs ohne repo/path**: list them; the fix is `/mastermind:project` in that repo.
- **Inbox**: open entries per hub and how many are older than 90 days (the user prunes or promotes them).
- **Index**: the INFO line (entities, full-text coverage, observations, relations, chunks) plus any WARN.
  Coverage below 90 % or duplicate rows → recommend `/mastermind:index repair-index`. Never recommend
  `basic-memory reindex --full` for a healthy index (it writes title-only rows, see README).

End with the summary line of the lint (`Summe: …`).

## 3. `fix`

```bash
python3 "${CLAUDE_SKILL_DIR}/lint.py" --vault "${MASTERMIND_VAULT:-$HOME/Mastermind}" --fix
```

`--fix` applies only the safe fixes and lists them as `INFO … FIX: …`: missing `related` → `[[index]]`,
unquoted wikilinks in frontmatter quoted, missing `## Verlauf` in hubs appended with a migration line,
missing `## Quellen` inserted with the placeholder `- (noch nicht erfasst)`. Everything else stays a
proposal in the report. Then commit:

```bash
VAULT="${MASTERMIND_VAULT:-$HOME/Mastermind}"; cd "$VAULT" && git add -A && git commit -qm "index: fixes" && git log --oneline -1
```

Skip the commit silently when nothing changed. Report the applied fixes and the remaining findings.

## 4. `repair-index`

```bash
python3 "${CLAUDE_SKILL_DIR}/repair_index.py" --vault "${MASTERMIND_VAULT:-$HOME/Mastermind}"
```

The script needs a running `basic-memory mcp` process (this session provides one) and refuses to run with
more than two of them (other Claude Code sessions: tell the user to close them). It backs up
`~/.basic-memory/memory.db` to `backups/repair/`, resets the checksums of the incomplete notes, touches
them in batches so the watcher re-indexes them, and prints the coverage before and after. Report the
`Vorher`/`Nachher` lines and the verdict; if files remain unrepaired, list them. Runtime: about one
minute per 150 files and round.

## Hard rules

- Without `fix`/`repair-index` nothing is written, not even a commit.
- Never rename or rewrite notes, never delete anything, never touch `## Verlauf` lines.
- Never run `basic-memory reindex` or `basic-memory reset` from this skill.
