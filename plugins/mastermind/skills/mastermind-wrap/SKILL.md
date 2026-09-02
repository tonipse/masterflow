---
name: mastermind-wrap
description: Session close-out for the Mastermind brain. Harvests this session's verified learnings into the vault (gotchas, decisions, patterns, how-tos, stack notes), updates the project hub, commits the vault and prints a report. Run at the end of every substantial session; "dry" previews without writing.
disable-model-invocation: true
argument-hint: "[dry] [focus hint]"
effort: max
allowed-tools: Read Grep Glob Bash Skill mcp__plugin_mastermind_mastermind-memory__search_notes mcp__plugin_mastermind_mastermind-memory__read_note mcp__plugin_mastermind_mastermind-memory__build_context mcp__plugin_mastermind_mastermind-memory__write_note mcp__plugin_mastermind_mastermind-memory__edit_note mcp__plugin_mastermind_mastermind-memory__move_note mcp__plugin_mastermind_mastermind-memory__recent_activity mcp__plugin_mastermind_mastermind-memory__list_directory
---

# mastermind-wrap

Close out the current session into the Mastermind vault. This skill runs in the main conversation on
purpose: it needs the full history. Work through the steps in order, do not skip the evidence step,
and never ask the user questions. The user opted into autonomous capture; your job is judgement, not
permission.

Arguments: `$ARGUMENTS`
- contains the word `dry` → plan and report only, write nothing (no vault edits, no commit).
- any other text → a focus hint (e.g. "nur die Refund-Sache", "auch die Deploy-Schritte").

## Step 0: Load conventions, identify the project

1. **→ Read** `${CLAUDE_SKILL_DIR}/../mastermind-brain/conventions.md` and `${CLAUDE_SKILL_DIR}/checklist.md`.
2. Determine the project: `git rev-parse --show-toplevel`, `git remote get-url origin`, folder name.
   The session-start context (`<mastermind>` block) already names the hub if one exists. Otherwise find it:
   `search_notes` with `search_type: "title"` on the folder name, and `list_directory("/projects")`.
   Match by `repo`, then `path`, then title. Never create a second hub.
3. No hub? Run the onboarding procedure first: **→ Read** `${CLAUDE_SKILL_DIR}/../mastermind-project/SKILL.md`
   and execute it inline (it creates the hub), then continue here.
4. Read the hub (`read_note`). Note its `last_wrap` (or `none`) and its current `## Status` / `## Offene Punkte`.

## Step 1: Collect evidence (defeats context loss after compaction)

Run:

```bash
python3 "${CLAUDE_SKILL_DIR}/evidence.py" --session "${CLAUDE_SESSION_ID}" --since "<last_wrap or none>" --cwd "$PWD"
```

It prints: git log and status since `last_wrap`, auto-memory files of this project changed since then,
and a best-effort timeline of this session from the transcript (user prompts, edited files, commands,
error lines). Treat it as evidence to jog your memory, not as truth; the conversation itself is primary.
If the script reports a source as "nicht gefunden", continue without it.

## Step 2: Harvest candidates

Using checklist §A and §B, list every candidate as `type | claim | evidence | confidence`.
Ask for each: would this save a stranger in another project an hour? Is it verified? Is it complete?
Apply the focus hint if given. Keep the list to the strongest 7 (checklist §D).

## Step 3: Dedup and placement

For every candidate run conventions §8: hybrid search + title search, read the top hits, decide
`edit_note` (extend) vs `write_note` (new), resolve contradictions inside the old note.
Record the decision next to the candidate. In `dry` mode stop after this step and print the report.

## Step 4: Write notes

Per conventions §2–§6: complete frontmatter (`created`, `updated`, `tags` with canonical stack tags,
`status: active`, `projects` with the hub, `confidence`, `related`, `source`), German prose, typed
sections, observations with `#tags` and recency hints, `## Verwandt` with the hub and at least one
topical or stack note. Titles ≤ 80 characters, no colon.
For stack facts: append to `stacks/<tool>.md` if it exists (`edit_note`, `append` under
`## Bekannte Gotchas` or `## Bewährte Configs`), otherwise create the stack note.

## Step 5: Update the hub (checklist §C)

`updated` and `last_wrap` = today, links for every new/updated note, `## Status` replaced by one
`Stand YYYY-MM-DD:` line, `## Offene Punkte` replaced (open items kept, finished dropped, new added),
`## Stack` / `## Konventionen` only if something durable changed. Add `repo`/`path` to the frontmatter
if they are missing (values from Step 0).

## Step 6: Commit the vault

```bash
VAULT="${MASTERMIND_VAULT:-$HOME/Mastermind}"; cd "$VAULT" && git add -A && git commit -qm "wrap(<project>): <n> notes" && git log --oneline -1
```

Skip silently if there is nothing to commit.

## Step 7: Report

Print the report from checklist §E in German. Include the index line from the session-start context if
it carried a warning (then also tell the user the reindex command). Do not add questions or offers;
the user can ask for skipped candidates by name.

## Hard rules

- No questions, no confirmation prompts. Decide, write, report.
- Never a second hub for the same project; never `mastermind/<folder>` as folder.
- Never rewrite a note wholesale, never delete notes in a wrap.
- No secrets, no project status, no unverified claims in the vault (checklist §B).
- One topic per note, max 7 notes, extend before create.
