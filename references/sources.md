# Quellen-Hierarchie (Wo nach Skills suchen)

Die Suche erfolgt in einer definierten Reihenfolge — von offiziell/vertrauenswürdig bis Community/experimentell.

## Tier 1 — Offizielle & hochgradig vertrauenswürdige Quellen

| Quelle | Stars (Stand: März 2026) | URL | Was man findet |
|--------|--------------------------|-----|----------------|
| Anthropic Official Skills | 101.000+ | github.com/anthropics/skills | Referenz-Skills von Anthropic (docx, pdf, frontend-design, mcp-builder, skill-creator, etc.). Offener Standard, auch für Codex CLI und Gemini CLI. |
| Anthropic Official Plugins | 14.300+ | github.com/anthropics/claude-plugins-official | Kuratierter Plugin-Marketplace mit internen und Partner-Plugins |
| obra/superpowers | — | github.com/obra/superpowers | Framework-Skills (TDD, Brainstorming, Debugging, Git Worktrees) |

**Referenz:** Offizielle Anthropic-Dokumentation für Plugin-Marketplaces: `code.claude.com/docs/en/plugin-marketplaces`

## Tier 2 — Kuratierte Community-Sammlungen (Awesome-Lists)

| Quelle | Stars (Stand: März 2026) | URL |
|--------|--------------------------|-----|
| ComposioHQ/awesome-claude-skills | 47.200+ | github.com/ComposioHQ/awesome-claude-skills |
| hesreallyhim/awesome-claude-code | 30.900+ | github.com/hesreallyhim/awesome-claude-code |
| sickn33/antigravity-awesome-skills | 26.800+ | github.com/sickn33/antigravity-awesome-skills |
| VoltAgent/awesome-agent-skills | 12.500+ | github.com/VoltAgent/awesome-agent-skills |
| travisvn/awesome-claude-skills | 9.600+ | github.com/travisvn/awesome-claude-skills |

## Tier 3 — Registries und Discovery-Plattformen

| Plattform | URL | Besonderheit |
|-----------|-----|-------------|
| claude-plugins.dev | claude-plugins.dev | 12.000+ Plugins, 63.000+ Agent Skills, NPX-Install |
| buildwithclaude.com | buildwithclaude.com | 175 Commands, 26 Skills, 50 Plugins, durchsuchbar |
| SkillsMP.com | skillsmp.com | 500.000+ Agent Skills, intelligentes Filtering |
| PolySkill.ai | polyskill.ai | Cross-Tool Skill-Registry, Sicherheits-Scanning |
| ccpm.dev | ccpm.dev | Rust-basierter Plugin-Manager mit TUI (lazygit-Stil) |
| LobeHub Skills Marketplace | lobehub.com/skills | Cross-Platform, Sicherheits-Vetting |
| SkillHub.club | skillhub.club | 7.000+ AI-evaluierte Skills |
| skillshare CLI | github.com/runkids/skillshare | Cross-Tool-Sync für 50+ AI-CLIs |

## Tier 4 — Direkte GitHub-Suche (für Nischen-Skills)

Suchstrategien:
- `claude code skill [technologie]` (z.B. "claude code skill supabase")
- `agent skill [technologie] SKILL.md`
- `claude code [technologie] .claude/skills`
- `stars:>100 pushed:>2025-10-01 claude skill [technologie]`
- GitHub Topics: `claude-code`, `agent-skills`, `claude-skills`

## Tier 5 — Spezialisierte Sammlungen

| Sammlung | Fokus | URL |
|----------|-------|-----|
| affaan-m/everything-claude-code | Komplettes System (Skills + Hooks + Memory + Security) | github.com/affaan-m/everything-claude-code |
| Jeffallan/claude-skills | 66 Full-Stack-Dev-Skills | github.com/Jeffallan/claude-skills |
| alirezarezvani/claude-skills | 192+ Skills für Engineering | github.com/alirezarezvani/claude-skills |
| trailofbits/skills | Security-Research-Skills | github.com/trailofbits/skills |
| jeremylongshore/claude-code-plugins-plus-skills | 1.695 Stars, 340 Plugins + 1.367 Skills, CCPI Package Manager | github.com/jeremylongshore/claude-code-plugins-plus-skills |
| daymade/claude-code-skills | 711 Stars, Production-Ready Skills | github.com/daymade/claude-code-skills |
