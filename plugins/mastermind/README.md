# mastermind (plugin)

Central cross-project engineering brain for Claude Code. One local Obsidian vault (`~/Mastermind`)
holds reusable knowledge from all code projects: gotchas, patterns, decisions, how-tos, stack notes and
one hub note per project. Access goes through the bundled `basic-memory` MCP server
(`mastermind-memory`, locked to the `mastermind` project regardless of the working directory).

## What happens automatically

| When | What |
|---|---|
| Session start (startup, clear, compact) | `hooks/session_start.py` reads the vault directly (no index needed), matches the project to its hub by `repo`, `path` or name, and injects: the recall/capture rules, the hub's status and open points, recently learned notes, similar projects (shared `stack/*` tags), stack notes to consult, and an index health check (warns when `basic-memory` has lost notes). |
| During work | The `mastermind-brain` skill (model-invocable) makes Claude search the brain before non-trivial work and **capture verified, non-obvious learnings autonomously** (announced in one line, never asked). Conventions live in `skills/mastermind-brain/conventions.md`. |
| Session end | `hooks/vault-commit` commits the vault if the session left changes (safety net). |

## Commands

| Command | Purpose |
|---|---|
| `/mastermind:wrap [dry] [focus]` | **Session close-out.** Collects evidence (`evidence.py`: git log/status since the last wrap, changed auto-memory files, session timeline from the transcript), harvests gotchas/decisions/patterns/how-tos/stack facts, dedups against the vault, updates the project hub (status, open points, links, `last_wrap`), commits the vault, prints a report. `dry` previews without writing. |
| `/mastermind:project [name]` | Onboard the current repo (hub with `repo`/`path`, stack tags, conventions, links to similar projects and stack notes) or refresh an existing hub. |
| `/mastermind:recall <topic>` | Hybrid search + summary with wikilinks. |
| `/mastermind:capture`, `:gotcha`, `:decision` | Write one note of the given type following the conventions. |
| `/mastermind:index` | Health check: index completeness, stray folders, hubs without `repo`/`path`, orphans, duplicates, stale notes. |

## Prerequisites

- `uv` and `uv tool install basic-memory` (0.22+). `basic-memory` must be on `PATH` for the MCP server.
- Project registered: `basic-memory project add mastermind ~/Mastermind` (or `project move` for an existing one).
- Vault at `~/Mastermind`. Another location: set `MASTERMIND_VAULT=/path` in the environment of Claude Code
  (hooks and skills honour it; the MCP server follows the basic-memory project config).
  Keep the vault **outside** `~/Desktop`, `~/Documents`, `~/Downloads`: macOS TCC can deny a background
  process access to those folders, and basic-memory then treats every note as deleted.
- `python3` (system Python is enough; the hooks use the standard library only). Without it the hooks stay silent.
- Semantic search: `~/.basic-memory/config.json` with `semantic_search_enabled: true`,
  `semantic_embedding_model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2`,
  `semantic_embedding_dimensions: 768` (multilingual, the vault is German). After changing the model:
  `basic-memory reindex --full -p mastermind`. Set `auto_update: false` so the engine does not update itself
  underneath the vault.

## Maintenance

- Lost notes in the index (session-start hook shows `INDEX WARNING`): `basic-memory reindex --full -p mastermind`.
- After editing this plugin: `claude plugin validate plugins/mastermind --strict`, test the hook with
  `printf '{"cwd":"/path/to/project","source":"startup"}' | bash plugins/mastermind/hooks/session-start`,
  try it live with `claude --plugin-dir plugins/mastermind`, then bump the version, push, and run
  `claude plugin marketplace update masterflow && claude plugin update mastermind@masterflow`.

Local and free: no cloud (`cloud_mode` stays false). The SQLite index lives under `~/.basic-memory/`, outside the vault.
