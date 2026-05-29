# mastermind (plugin)

Central cross-project engineering brain for Claude Code. Bundles a local `basic-memory` MCP server (`mastermind-memory`, locked to the `mastermind` project at `~/Desktop/Mastermind`), a `mastermind-brain` skill (recall-first / capture-after), and `/mastermind:*` commands.

## Prerequisites
- `uv` installed; `uv tool install basic-memory`.
- Project registered: `basic-memory project add mastermind ~/Desktop/Mastermind`.

## Commands
`/mastermind:recall <topic>` · `:capture` · `:gotcha` · `:decision` · `:project <name>` · `:index`

## Optional session-end nudge
Rename `hooks/hooks.json.example` → `hooks/hooks.json` and `/reload-plugins`.

Local & free: no cloud (`cloud_mode` stays false). The SQLite index lives under `~/.basic-memory/` (outside the vault).
