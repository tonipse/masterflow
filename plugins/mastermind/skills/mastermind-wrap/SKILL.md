---
name: wrap
description: Session close-out for the Mastermind brain. Harvests this session's verified learnings into the vault (gotchas, decisions, patterns, how-tos, stack notes), promotes or files inbox candidates, updates the project hub (status, open points, sources, timeline), lints, commits the vault and prints a report. Run at the end of every substantial session; "dry" previews without writing, "last" harvests the previous unwrapped session from its transcript.
disable-model-invocation: true
argument-hint: "[dry|last] [focus hint]"
effort: max
allowed-tools: Read Grep Glob Bash Skill mcp__plugin_mastermind_mastermind-memory__search_notes mcp__plugin_mastermind_mastermind-memory__read_note mcp__plugin_mastermind_mastermind-memory__build_context mcp__plugin_mastermind_mastermind-memory__write_note mcp__plugin_mastermind_mastermind-memory__edit_note mcp__plugin_mastermind_mastermind-memory__move_note mcp__plugin_mastermind_mastermind-memory__recent_activity mcp__plugin_mastermind_mastermind-memory__list_directory
---

# mastermind-wrap (`/mastermind:wrap`)

Close out the current session into the Mastermind vault. This skill runs in the main conversation on
purpose: it needs the full history. Work through the steps in order, do not skip the evidence step,
and never ask the user questions. The user opted into autonomous capture; your job is judgement, not
permission.

Arguments: `$ARGUMENTS`
- contains the word `dry` → **dry mode**: plan and report only. No vault edits, no inbox lines, no
  onboarding, no commit, no state-file change.
- contains the word `last` → **last mode**: harvest the previous session of this project that ended
  without a wrap. Evidence comes from its transcript digest, not from this conversation (see Step 1).
- any other text → a focus hint (e.g. "nur die Refund-Sache", "auch die Deploy-Schritte"). The hint
  narrows the harvest; it is never a hub name.

## Step 0: Load conventions, identify the project

1. **→ Read** `${CLAUDE_SKILL_DIR}/../mastermind-brain/conventions.md` and `${CLAUDE_SKILL_DIR}/checklist.md`.
2. Determine the project: `git rev-parse --show-toplevel` (for a linked worktree the main checkout is the
   parent of `git rev-parse --git-common-dir`), `git remote get-url origin`, folder name.
   The session-start context (`<mastermind>` block) already names the hub if one exists. Otherwise find it:
   `search_notes` with `search_type: "title"` on the folder name, and `list_directory("/projects")`.
   Match by `repo`, then `path`, then title. Never create a second hub.
3. No hub?
   - dry mode: note `Hub: fehlt (würde per /mastermind:project angelegt)` for the report and continue.
   - otherwise: **→ Read** `${CLAUDE_SKILL_DIR}/../mastermind-project/SKILL.md` and execute its sections
     1–5 inline with these overrides: ignore that file's `$ARGUMENTS` (the hub name is the folder name),
     skip its commit and report (this skill commits and reports at the end). Then continue here.
4. Read the hub (`read_note`). Note its `last_wrap` (missing = never), `## Status`, `## Offene Punkte`,
   `## Quellen`, the last line of `## Verlauf`, and whether `repo`/`path` are missing from its frontmatter.
   A hub without `## Quellen` or `## Verlauf` is pre-v3; Step 5 adds the sections.
5. Read the hub's inbox `inbox/<hub-file-stem>.md` in the vault (`cat`; it is not indexed). Keep its open
   `- [ ]` lines at hand for Step 2.
6. **last mode only:** read the state file
   `~/.local/state/mastermind/last-session-<slug>.json` where `<slug>` is the project root path with every
   `/` replaced by `-` (e.g. `-Users-toni-Desktop-supportpilot`; fall back to the cwd if there is no git root).
   Missing file or `"wrapped": true` → print `Keine ungewrappte Session für <projekt> gefunden.` and stop.
   Otherwise take `session_id`, `transcript_path`, `ended` and `edits` from it.

## Step 1: Collect evidence (defeats context loss after compaction)

```bash
python3 "${CLAUDE_SKILL_DIR}/evidence.py" --session "${CLAUDE_SESSION_ID}" --since "<last_wrap date or none>" --cwd "<project root from Step 0>"
```

In last mode use the previous session instead and add the digest:

```bash
python3 "${CLAUDE_SKILL_DIR}/evidence.py" --session "<session_id from the state file>" --since "<last_wrap date or none>" --cwd "<project root>" --digest
```

It prints: git log and status since `last_wrap`, auto-memory files of this project changed since then,
a best-effort timeline of the session from the transcript (user prompts, edited files, commands, error
lines) and, with `--digest`, the compact digest (prompts, Claude's final text per turn, errors, edited
files; at most 40,000 characters). Treat it as evidence to jog your memory, not as truth; in normal mode
the conversation itself is primary, in last mode the digest is all you have, so only harvest what the
digest shows as implemented **and** verified. If the script reports a source as "nicht gefunden",
continue without it.

## Step 2: Harvest and rank candidates

Using checklist §A and §B, list **every** candidate as `type | claim | evidence | confidence`.
Ask for each: would this save a stranger in another project an hour? Is it verified? Is it complete?
Apply the focus hint if given. Then the inbox: an open inbox line that this session verified becomes a
candidate with the inbox line as its origin (promoted in Step 5b); lines the session did not touch stay
untouched. Rank by reusability; the top 7 proceed as new or extended notes (hub edits and appends to
existing stack notes do not count against the 7). Everything below the cut is either an inbox candidate
(checklist §D: reusable but cut, or promising but unverified) or goes verbatim into the report's
`Übersprungen` line with a five-word reason (trivia, skip list).

## Step 3: Dedup and placement

For every proceeding candidate run conventions §8: hybrid search + title search, read the top hits, decide
`edit_note` (extend) vs `write_note` (new), resolve contradictions inside the old note. A `decisions/`
hit that the session's work contradicts is a guardrail (conventions §11): record the conflict, update
the decision note only if the user decided otherwise in this session, and say so in the report.
Record the decision next to the candidate. **In dry mode stop here and print the report (checklist §E).**

## Step 4: Write notes

Per conventions §2–§6: complete frontmatter (`created`, `updated`, `tags` with canonical stack tags,
`status: active`, `projects` with the hub, `confidence`, `related`, **`source` is mandatory**: the
commit, file, transcript session or URL that verifies the claim; a candidate without one becomes an
inbox line instead), German prose, typed sections, observations with `#tags` and recency hints,
`## Verwandt` with the hub and at least one topical or stack note. Titles ≤ 80 characters, no colon.

Stack facts follow checklist §A: append to an existing `stacks/<tool>.md` (`edit_note`, `append` under
`## Bekannte Gotchas` or `## Bewährte Configs`); create a new stack note only when there are ≥ 2 facts
for that tool; a single fact without a stack note stays inside the note that carries it.
For every new gotcha whose stack has a `stacks/<tag>.md`, append `- [gotcha] Siehe [[Titel]] #tag`
to that stack note's `## Bekannte Gotchas`.

## Step 5: Update the hub (checklist §C, anatomy v3)

`updated` and `last_wrap` = today (`find_replace` on the existing lines, or add `last_wrap` with
`find_replace` on `type: project` → `type: project\nlast_wrap: 'YYYY-MM-DD'`). Missing `repo`/`path`:
same technique (`type: project` → `type: project\nrepo: …\npath: …`).
Then, only where this session changed something (checklist focus rule):
- links for every new or updated note under `## Bekannte Gotchas` / `## Wichtige Decisions`;
- `## Status` replaced by one `Stand YYYY-MM-DD: …` line;
- `## Offene Punkte` replaced (unknowns and risks still open kept, resolved ones dropped, new ones added; ≤ 8; no to-dos);
- `## Quellen`: refresh the date of every source you actually read (`find_replace` on the line), add a
  line for a new one (e.g. `- Auto-Memory ~/.claude/projects/<slug>/memory (geerntet bis YYYY-MM-DD)`,
  `- Transkript Session <id-kurz> (geerntet bis YYYY-MM-DD)`); missing section → `insert_before_section`
  `## Verwandt`;
- `## Stack` / `## Konventionen` only if something durable changed;
- `## Verlauf`: `append` exactly one line
  `- YYYY-MM-DD wrap · <n> neu, <m> erweitert, Hub: <was> · Quelle: Session <id-kurz>`
  (last mode: `wrap (nachgeholt)`). Never touch existing lines. Missing section → append the heading first.

## Step 5b: Inbox

Append the inbox candidates of Step 2 to `inbox/<hub-file-stem>.md` in the vault (plain file write via
Bash; the file is not indexed), one line each in the format of conventions §12
(`- [ ] YYYY-MM-DD · <typ> · <Aussage> · Beleg: <Datei/Session> · Grund: <über Limit | unverifiziert>`).
Create the file when missing with exactly this frontmatter: `title: 'inbox – <hub-file-stem>'`,
`type: inbox`. Promote lines verified in this session in place: `- [ ]` → `- [x]` and ` → [[Titel]]`
appended. Never delete inbox lines.

## Step 6: Lint, then commit the vault

```bash
VAULT="${MASTERMIND_VAULT:-$HOME/Mastermind}"; python3 "${CLAUDE_SKILL_DIR}/../mastermind-index/lint.py" --vault "$VAULT" --changed --strict
```

Fix every ERROR it reports (frontmatter via `edit_note` `find_replace`, hub structure via
`replace_section`/`append`), run it again, then commit:

```bash
VAULT="${MASTERMIND_VAULT:-$HOME/Mastermind}"; cd "$VAULT" && git add -A && git commit -qm "wrap(<project>): <n> notes" && git log --oneline -1
```

Last mode: commit message `wrap(<project>, nachgeholt): <n> notes`, then mark the state file:

```bash
python3 -c 'import json,sys,pathlib; p=pathlib.Path(sys.argv[1]); d=json.loads(p.read_text()); d["wrapped"]=True; p.write_text(json.dumps(d, indent=1))' "$HOME/.local/state/mastermind/last-session-<slug>.json"
```

Skip the commit silently if there is nothing to commit (still mark the state file in last mode).

## Step 7: Report

Print the report from checklist §E in German (last mode adds the `Nachgeholt aus Transkript` line).
Include the index line from the session-start context if it carried a warning (then also name
`/mastermind:index repair-index`). Do not add questions or offers; the user can ask for skipped
candidates by name.

## Hard rules

- No questions, no confirmation prompts. Decide, write, report.
- Never a second hub for the same project; never `mastermind/<folder>` as folder.
- Never rewrite a note wholesale, never delete notes or inbox lines in a wrap.
- Focus (conventions §11): touch only notes and hubs affected by this session's evidence.
- `## Verlauf` lines are immutable: append one line, never edit or remove existing ones.
- No secrets, no project status, no unverified claims in the vault (checklist §B); `source` on every new note.
- One topic per note, max 7 notes, extend before create.
- Dry mode writes nothing at all, not even a hub, an inbox line or the state file.
