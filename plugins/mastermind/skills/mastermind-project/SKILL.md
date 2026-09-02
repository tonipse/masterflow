---
name: project
description: Onboard the current code project into the Mastermind brain or refresh its hub note. Creates exactly one project hub with repo/path, stack tags, conventions and links to similar projects and stack notes.
disable-model-invocation: true
argument-hint: "[name] [notes]"
effort: high
allowed-tools: Read Grep Glob Bash mcp__plugin_mastermind_mastermind-memory__search_notes mcp__plugin_mastermind_mastermind-memory__read_note mcp__plugin_mastermind_mastermind-memory__build_context mcp__plugin_mastermind_mastermind-memory__write_note mcp__plugin_mastermind_mastermind-memory__edit_note mcp__plugin_mastermind_mastermind-memory__list_directory
---

# mastermind-project (`/mastermind:project`)

Create or update the hub note `projects/<name>.md` for the current project. A hub is the bridge between
a repo and the cross-project knowledge: it names the stack, the conventions, the decisions and gotchas
that apply, and it links similar projects. Arguments: `$ARGUMENTS` (optional name override and free notes).
Never ask questions; decide from the sources below and report.

## 1. Conventions and identity

1. **→ Read** `${CLAUDE_SKILL_DIR}/../mastermind-brain/conventions.md` (§2 hub frontmatter, §4 hub sections, §7 stack tags).
2. Identity: `git rev-parse --show-toplevel` (for a linked worktree use the main checkout: parent of
   `git rev-parse --git-common-dir`), `git remote get-url origin` normalized (`github.com/org/name`, lowercase,
   no `.git`), folder name. The hub name is the folder name in lowercase-kebab unless `$ARGUMENTS` gives one.

## 2. Existing hub? (never create a second one)

- `search_notes` with `search_type: "title"` on the folder name, plus `list_directory("/projects")`.
- A hub matches if its `repo` equals the normalized remote, or its `path` equals the root, or its title
  equals the folder name (case-insensitive, `-`/`_` ignored). Umbrella hubs (e.g. `fwg-one`, `rocketads`,
  `fwg-warehouse`) are groups, not project hubs.
- Match found → **update mode**: keep the note, use `edit_note` to add missing frontmatter (`repo`, `path`,
  `group/*`, `stack/*` tags; a missing key is added with `find_replace` on `type: project` →
  `type: project\n<key>: <value>`), refresh `## Stack`, `## Status`, `## Offene Punkte`, and add links.
  No match → **create mode**.

## 3. Sources (read what exists, do not guess)

- `CLAUDE.md`, `.claude/CLAUDE.md`, `README.md`, `context/stack-analysis.md`, `docs/` index files.
- Manifests: `package.json` (dependencies + scripts), `pyproject.toml` / `requirements.txt`, `composer.json`,
  `go.mod`, `*.csproj`, `pubspec.yaml`; infra: `vercel.json`, `serverless.yml`, `Dockerfile`,
  `.github/workflows/*`.
- Git: `git log --format='%ad %s' --date=short | head -20`, first commit date, commit count, default branch.
- Claude auto memory of the project: `~/.claude/projects/<cwd with / replaced by ->/memory/MEMORY.md`
  (project overview and durable feedback entries are good hub material; status entries are not).

## 4. Connect to the brain

- Map the stack to canonical `stack/*` tags (conventions §7) and a `group/*` tag
  (`fwg-one`, `rocketads`, `moeller`, `standalone`; infer from the parent folder `fwg-dev`, `ra-dev`, `moeller-dev`).
- For the three most important stacks run `search_notes` (hybrid) with the stack name and the project's
  domain words; collect relevant patterns, gotchas and decisions (max 8 links).
- Similar projects: hubs sharing ≥ 2 specific stack tags, or ≥ 1 when the project has at most 2 specific
  tags (generic language tags such as `nodejs`, `typescript`, `python` do not count). Same rule as the
  session-start hook; its `Similar projects` line is the shortcut. Link them under `## Verwandt`.
- Stack notes: link every `stacks/<tag>.md` that exists for the project's stacks.

## 5. Write the hub

`write_note` (create) or `edit_note` (update) with the full frontmatter:

```yaml
---
title: <name>
type: project
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
tags: [project, group/<group>, stack/<a>, stack/<b>]
status: active
projects: []
confidence: high
related: ["[[index]]", "[[_projects-overview]]", "[[<umbrella or similar hub>]]"]
repo: <normalized remote>          # omit the key entirely if the repo has no remote
path: <absolute root path>
---
```

Do not write `last_wrap` (the wrap skill sets it) and never write `null` values; omit unknown keys.

Sections (German): `## Zweck` (2–4 sentences), `## Stack` (bullets with versions), `## Architektur / Eigenheiten`,
`## Konventionen` (build/test/deploy commands, log formats, branch model), `## Wichtige Decisions` (`- [decision] …`),
`## Bekannte Gotchas` (`- [gotcha] Siehe [[…]] #tag`), `## Status` (`Stand YYYY-MM-DD: …`), `## Offene Punkte`,
`## Verwandt` (index, overview, umbrella, similar projects, stack notes).

Then register it in `_projects-overview` (`edit_note`): append the wikilink to the section of its group
(`## FWG.ONE …`, `## RocketAds …`, `## Standalone …`; counts in those headings are informational, do not
maintain them). If the group has no section yet (e.g. `moeller`), add `## Moeller` before `## Standalone`.
Add a backlink in the umbrella hub if one exists.

## 6. Commit and report

```bash
VAULT="${MASTERMIND_VAULT:-$HOME/Mastermind}"; cd "$VAULT" && git add -A && git commit -qm "project(<name>): hub created|updated" && git log --oneline -1
```

Report in German: hub path, mode (neu/aktualisiert), stack tags, linked similar projects and stack notes,
and anything you could not determine (e.g. no remote). No questions.
