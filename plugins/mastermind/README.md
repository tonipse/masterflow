# mastermind (plugin)

Central cross-project engineering brain for Claude Code. One local Obsidian vault (`~/Mastermind`)
holds reusable knowledge from all code projects: gotchas, patterns, decisions, how-tos, stack notes and
one hub note per project, plus the root files `user.md` (who the user is) and `soul.md` (behaviour
charter) that every session loads. Access goes through the bundled `basic-memory` MCP server
(`mastermind-memory`, locked to the `mastermind` project regardless of the working directory).

## What happens automatically

| When | What |
|---|---|
| Session start (startup, resume, clear, compact) | `hooks/session_start.py` reads the vault directly (no index needed), matches the project to its hub by `repo`, `path` or name, and injects: the recall/capture/guardrail rules, the hub's status and open points, its last `## Verlauf` line, the number of open inbox candidates, recently learned notes, similar projects (shared `stack/*` tags), stack notes to consult, an `UNWRAPPED` reminder when the previous session of this project ended with edits but without `/mastermind:wrap`, an index health check (entities, full-text and observation coverage) and a warning when the configured Ollama embedding server is down. |
| Every prompt | `hooks/prompt_hint.py` runs a read-only BM25 query over the full-text index (knowledge notes only) and adds `<mastermind-hint>Möglicherweise relevant: [[…]] (gotcha) …</mastermind-hint>` for up to 3 strong matches, each note once per session. Silent for short prompts, slash commands and when `~/Mastermind/.mastermind.json` has `"prompt_hints": false`. |
| During work | The `mastermind-brain` skill (model-invocable) makes Claude search the brain before non-trivial work, treat `decisions/` notes as guardrails, and **capture verified, non-obvious learnings autonomously** (announced in one line, never asked). Promising but unverified findings go to `inbox/<hub>.md` instead. Conventions live in `skills/mastermind-brain/conventions.md`. |
| Session end | `hooks/session-end` → `session_end.py` commits the vault if the session left changes, pushes in the background when the vault has a remote `origin` (disable with `"push": false` in `.mastermind.json`), and writes `~/.local/state/mastermind/last-session-<slug>.json` (session id, transcript, edit count, whether a real `/mastermind:wrap` ran) so the next session can say `UNWRAPPED` and `/mastermind:wrap last` can harvest the transcript. |

## Commands

| Command | Purpose |
|---|---|
| `/mastermind:wrap [dry\|last] [focus]` | **Session close-out.** Collects evidence (`evidence.py`: git log/status since the last wrap, changed auto-memory files, session timeline and, with `--digest`, a compact transcript digest), harvests gotchas/decisions/patterns/how-tos/stack facts, dedups against the vault, promotes or files inbox candidates, updates the project hub (status, open points, sources, timeline line, links, `last_wrap`), lints the changed files, commits the vault, prints a report. `dry` previews without writing; `last` harvests the previous unwrapped session from its transcript and marks the state file. |
| `/mastermind:project [name]` | Onboard the current repo (hub v3 with `repo`/`path`, stack tags, conventions, `## Quellen`, `## Verlauf`, links to similar projects and stack notes) or refresh an existing hub (adds missing v3 sections). |
| `/mastermind:index [fix] [repair-index]` | Health check: `lint.py` (frontmatter, note types, titles, wikilinks, orphans, hub anatomy v3, root-file line limits, inbox, index coverage). `fix` applies the safe fixes and commits; `repair-index` rebuilds incomplete full-text rows through the running MCP watcher (`repair_index.py`). |
| `/mastermind:recall <topic>` | Hybrid search + summary with wikilinks. |
| `/mastermind:capture`, `:gotcha`, `:decision` | Write one note of the given type following the conventions. |

## Vault layout (v3)

- `gotchas/ patterns/ decisions/ howtos/ stacks/` knowledge notes (German, frontmatter with `source`).
- `projects/<hub>.md` one hub per project, anatomy v3: `## Zweck` … `## Bekannte Gotchas` · `## Status` (one
  `Stand YYYY-MM-DD: …` line) · `## Offene Punkte` (unknowns and risks, no to-dos) · `## Quellen`
  (`- <Quelle> (geerntet bis YYYY-MM-DD)`) · `## Verwandt` · `## Verlauf` (last section, append-only). Umbrella
  hubs carry the tag `moc` and only need `## Verlauf`.
- Root files: `CLAUDE.md` (conventions, short form), `AGENTS.md` (tool-neutral version for Codex, Antigravity, …),
  `user.md` (≤ 60 lines) and `soul.md` (≤ 40 lines); the last two are imported by `~/.claude/CLAUDE.md`
  (`@~/Mastermind/user.md`, `@~/Mastermind/soul.md`) into every Claude Code session.
- `inbox/<hub>.md`: unverified or cut candidates, one line each
  (`- [ ] YYYY-MM-DD · <typ> · <Aussage> · Beleg: … · Grund: …`); not indexed (`inbox/` in `~/.basic-memory/.bmignore`).
- `templates/` (indexed, exempt from the lint), `_brainstorming/` (designs, reports), `.ernte/` (night-session ledgers, hidden).
- `.mastermind.json`: `{"prompt_hints": true, "push": true}`.
- State outside the vault: `~/.local/state/mastermind/last-session-<slug>.json`, `hints-<session>.txt` (safe to delete).

## Prerequisites

- `uv` and `basic-memory` as a uv tool: today `basic-memory` 0.22.1; after the retrieval upgrade 0.23.2
  (`uv tool install --force --prerelease=allow basic-memory==0.23.2`, the prerelease flag is needed for its
  `fastmcp` dependency). `basic-memory` must be on `PATH` for the MCP server.
- Project registered: `basic-memory project add mastermind ~/Mastermind` (or `project move` for an existing one).
- Vault at `~/Mastermind`. Another location: set `MASTERMIND_VAULT=/path` in the environment of Claude Code
  (hooks and skills honour it; the MCP server follows the basic-memory project config).
  Keep the vault **outside** `~/Desktop`, `~/Documents`, `~/Downloads`: macOS TCC can deny a background
  process access to those folders, and basic-memory then treats every note as deleted.
- `python3` (system Python 3.9+ is enough; hooks and scripts use the standard library only). Without it the
  SessionEnd hook falls back to a plain vault commit and the other hooks stay silent.
- `~/.basic-memory/.bmignore` contains `inbox/`; `~/.basic-memory/config.json` keeps `auto_update: false`.
- Semantic search, current: `semantic_embedding_provider: fastembed`,
  `semantic_embedding_model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, 768 dimensions,
  `semantic_min_similarity: 0.45`.
- Semantic search, target stack (switch with `retrieval-upgrade.sh` from the masterflow repo's
  `.claude/nachtsessions/`, run **without any running Claude Code session**, then restart Claude Code):
  basic-memory 0.23.2 with the LiteLLM provider, **Ollama** as a background service
  (`brew install ollama && brew services start ollama`) serving `qwen3-embedding:8b`
  (`ollama pull qwen3-embedding:8b`, 4.7 GB, 4096 dimensions, query instruction prefix), and the local
  fastembed reranker `jinaai/jina-reranker-v2-base-multilingual` (cache `~/.basic-memory/fastembed_cache`).
  RAM ≈ 5–6 GB while the model is loaded; Ollama unloads it after 5 minutes idle, the first query afterwards
  takes 2–4 s. The session-start hook warns when Ollama is not reachable. The switch re-embeds every note
  through a temporary `basic-memory mcp` (about 15 s per note with the 8B model on an M5, i.e. roughly an hour
  for 180 notes; the script shows the progress and only stops when every entity has vector chunks). The
  0.23.2 migration recreates the vector tables and its start-sync also rebuilds the full-text rows, so the
  upgrade doubles as an index repair.

## Maintenance

- Vault lint: `python3 plugins/mastermind/skills/mastermind-index/lint.py [--vault ~/Mastermind] [--changed] [--strict] [--fix] [--json] [PATH …]`
  (0 ERROR expected; older notes only produce WARN).
- Index health: the session-start hook prints `INDEX …`; `/mastermind:index` prints the full line. Full-text
  coverage below 90 % or duplicate entity rows → `/mastermind:index repair-index` (needs one running Claude Code
  session with the plugin; refuses to run while more than two `basic-memory mcp` processes exist, so close other
  sessions first). **Never** run `basic-memory reindex --full` on a healthy index: 0.22.1 and 0.23.2 write
  title-only rows and drop observation/relation rows, and `--embeddings` inflates the vector table. Only after
  an index loss (entities missing) run `reindex --full`, then `repair-index`. Changing the embedding model is
  done through the server path (`retrieval-upgrade.sh` starts a temporary `basic-memory mcp`), never via `reindex`.
- Hook tests: `printf '{"cwd":"/path/to/project","source":"startup","session_id":"x"}' | bash plugins/mastermind/hooks/session-start`,
  `printf '{"cwd":"/path","session_id":"x","transcript_path":"/path/to/transcript.jsonl","reason":"other"}' | MASTERMIND_VAULT=/tmp/testvault bash plugins/mastermind/hooks/session-end`,
  `printf '{"prompt":"…","session_id":"x","cwd":"/path"}' | python3 plugins/mastermind/hooks/prompt_hint.py`.
- After editing this plugin: `claude plugin validate plugins/mastermind --strict`, try it live with
  `claude --plugin-dir plugins/mastermind`, then bump the version, push, and run
  `claude plugin marketplace update masterflow && claude plugin update mastermind@masterflow`.

Local and free: no cloud (`cloud_mode` stays false). The SQLite index lives under `~/.basic-memory/`, outside the vault.
